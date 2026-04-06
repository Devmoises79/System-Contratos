from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, send_file
from config import Config
from core.database import Database, close_db
from auth.login import LoginManager
from auth.permissoes import login_required
from auth.ip_blocker import IPBlocker
from models.usuario import Usuario
from models.empresa import Empresa
from models.contrato import Contrato
from core.logging_config import logger
import secrets
from datetime import datetime
import os

# Importação dos Blueprints
from admin.empresa import admin_empresa_bp
from admin.sistema import admin_sistema_bp

app = Flask(__name__)
app.config.from_object(Config)

# Configuração de segurança
app.secret_key = Config.SECRET_KEY
app.permanent_session_lifetime = Config.PERMANENT_SESSION_LIFETIME

# Configuração para upload de arquivos
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'logos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'contratos'), exist_ok=True)

# Registrar blueprints
app.register_blueprint(admin_empresa_bp)
app.register_blueprint(admin_sistema_bp)

# Fechar conexão do banco ao final da requisição
app.teardown_appcontext(close_db)

# ==================== ROTAS PRINCIPAIS ====================

@app.route('/')
def index():
    """Página inicial"""
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        lembrar = request.form.get('lembrar') == 'on'
        
        sucesso, resultado = LoginManager.login(email, senha, lembrar)
        
        if sucesso:
            flash(resultado.get('mensagem', 'Login realizado com sucesso!'), 'success')
            return redirect(resultado.get('redirect', url_for('dashboard')))
        else:
            flash(resultado.get('mensagem', 'Erro ao fazer login'), 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout do usuário"""
    LoginManager.logout()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard baseado no perfil do usuário"""
    usuario = session['usuario']
    perfil = usuario['perfil']
    
    if perfil == 'admin_sistema':
        return redirect(url_for('admin_sistema.dashboard'))
    elif perfil == 'admin_empresa':
        return redirect(url_for('admin_empresa.dashboard'))
    elif perfil == 'gestor':
        return redirect(url_for('dashboard_gestor'))
    elif perfil == 'analista':
        return redirect(url_for('dashboard_analista'))
    elif perfil == 'assistente':
        return redirect(url_for('dashboard_assistente'))
    
    return redirect(url_for('listar_contratos'))


@app.route('/dashboard/gestor')
@login_required
def dashboard_gestor():
    """Dashboard para gestores"""
    from auth.permissoes import gestor_required
    gestor_required(lambda: None)()
    
    empresa_id = session['usuario']['empresa_id']
    stats = Contrato.estatisticas(empresa_id)
    contratos_pendentes = Contrato.listar_pendentes_aprovacao(empresa_id)
    
    return render_template('dashboard/gestor.html', 
                         stats=stats, 
                         contratos_pendentes=contratos_pendentes)


@app.route('/dashboard/analista')
@login_required
def dashboard_analista():
    """Dashboard para analistas"""
    from auth.permissoes import analista_required
    analista_required(lambda: None)()
    
    empresa_id = session['usuario']['empresa_id']
    stats = Contrato.estatisticas(empresa_id)
    
    contratos = Contrato.listar_por_empresa(empresa_id)
    top_contratos = sorted(contratos, key=lambda x: x.valor, reverse=True)[:5] if contratos else []
    
    return render_template('dashboard/analista.html', 
                         stats=stats, 
                         top_contratos=top_contratos)


@app.route('/dashboard/assistente')
@login_required
def dashboard_assistente():
    """Dashboard para assistentes"""
    from auth.permissoes import assistente_required
    assistente_required(lambda: None)()
    
    usuario_id = session['usuario']['id']
    contratos = Contrato.listar_por_criador(usuario_id)
    
    return render_template('dashboard/assistente.html', contratos=contratos)


# ==================== ROTAS DE CONTRATOS ====================

@app.route('/contratos')
@login_required
def listar_contratos():
    """Lista todos os contratos"""
    empresa_id = session['usuario']['empresa_id']
    
    status = request.args.get('status')
    busca = request.args.get('busca')
    
    contratos = Contrato.listar_por_empresa(empresa_id)
    
    if status:
        if status == 'aguardando':
            contratos = [c for c in contratos if c.status == 'aguardando_aprovacao']
        elif status == 'em_analise':
            contratos = [c for c in contratos if c.status == 'em_analise']
        else:
            contratos = [c for c in contratos if c.status == status]
    
    if busca:
        busca = busca.lower()
        contratos = [c for c in contratos if 
                    busca in (c.numero_contrato or '').lower() or 
                    busca in (c.contratante_nome or '').lower() or 
                    busca in (c.contratada_nome or '').lower()]
    
    return render_template('contratos/listar.html', contratos=contratos)


@app.route('/contratos/novo', methods=['GET', 'POST'])
@login_required
def contrato_novo():
    """Cria um novo contrato"""
    from auth.permissoes import pode_criar_contrato
    
    if not pode_criar_contrato():
        flash('Você não tem permissão para criar contratos.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        empresa_id = session['usuario']['empresa_id']
        usuario_id = session['usuario']['id']
        
        contrato = Contrato(
            empresa_id=empresa_id,
            contratante_nome=request.form.get('contratante_nome'),
            contratante_cnpj=request.form.get('contratante_cnpj'),
            contratante_email=request.form.get('contratante_email'),
            contratante_telefone=request.form.get('contratante_telefone'),
            contratada_nome=request.form.get('contratada_nome'),
            contratada_cnpj=request.form.get('contratada_cnpj'),
            contratada_email=request.form.get('contratada_email'),
            valor=request.form.get('valor'),
            prazo_dias=request.form.get('prazo_dias'),
            descricao=request.form.get('descricao'),
            criado_por=usuario_id
        )
        
        contrato.save()
        flash('Contrato criado com sucesso!', 'success')
        return redirect(url_for('ver_contrato', id=contrato.id))
    
    return render_template('contratos/novo.html')


@app.route('/contratos/<int:id>')
@login_required
def ver_contrato(id):
    """Visualiza um contrato"""
    contrato = Contrato.get_by_id(id)
    
    if not contrato:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    empresa_id = session['usuario']['empresa_id']
    if contrato.empresa_id != empresa_id and session['usuario']['perfil'] != 'admin_sistema':
        flash('Acesso negado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    info_auditoria = {}
    try:
        if hasattr(contrato, 'get_info_auditoria'):
            info_auditoria = contrato.get_info_auditoria()
        else:
            info_auditoria = {
                'criado_por_nome': contrato.get_criador_nome() if hasattr(contrato, 'get_criador_nome') else 'Desconhecido',
                'criado_em': contrato.data_criacao.strftime('%d/%m/%Y %H:%M') if contrato.data_criacao else None,
                'atualizado_em': contrato.data_atualizacao.strftime('%d/%m/%Y %H:%M') if contrato.data_atualizacao else None,
                'aprovado_por_nome': contrato.get_aprovador_nome() if hasattr(contrato, 'get_aprovador_nome') else None,
                'aprovado_em': contrato.data_aprovacao.strftime('%d/%m/%Y %H:%M') if contrato.data_aprovacao else None
            }
    except Exception as e:
        logger.error(f"Erro ao obter info auditoria: {e}")
        info_auditoria = {
            'criado_por_nome': 'Desconhecido',
            'criado_em': contrato.data_criacao.strftime('%d/%m/%Y %H:%M') if contrato.data_criacao else None,
            'atualizado_em': None,
            'aprovado_por_nome': None,
            'aprovado_em': None
        }
    
    # Corrige o caminho do PDF para exibir no template
    pdf_url = None
    if contrato.pdf_path:
        pdf_url = contrato.pdf_path.replace('\\', '/')
        if pdf_url.startswith('static/'):
            pdf_url = pdf_url[7:]  # Remove 'static/' para usar com url_for
    
    return render_template('contratos/detalhe.html', 
                         contrato=contrato,
                         info_auditoria=info_auditoria,
                         pdf_url=pdf_url)


@app.route('/contratos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_contrato(id):
    """Edita um contrato"""
    from auth.permissoes import pode_editar_contrato
    
    contrato = Contrato.get_by_id(id)
    
    if not contrato:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    if not pode_editar_contrato(contrato):
        flash('Você não tem permissão para editar este contrato.', 'danger')
        return redirect(url_for('ver_contrato', id=id))
    
    if request.method == 'POST':
        contrato.contratante_nome = request.form.get('contratante_nome')
        contrato.contratante_cnpj = request.form.get('contratante_cnpj')
        contrato.contratante_email = request.form.get('contratante_email')
        contrato.contratante_telefone = request.form.get('contratante_telefone')
        contrato.contratada_nome = request.form.get('contratada_nome')
        contrato.contratada_cnpj = request.form.get('contratada_cnpj')
        contrato.contratada_email = request.form.get('contratada_email')
        contrato.valor = request.form.get('valor')
        contrato.prazo_dias = request.form.get('prazo_dias')
        contrato.descricao = request.form.get('descricao')
        contrato.atualizado_por = session['usuario']['id']
        
        contrato.save()
        flash('Contrato atualizado com sucesso!', 'success')
        return redirect(url_for('ver_contrato', id=id))
    
    return render_template('contratos/editar.html', contrato=contrato)


@app.route('/contratos/<int:id>/enviar-analista', methods=['POST'])
@login_required
def enviar_para_analista(id):
    """Assistente envia contrato para análise do analista"""
    from auth.permissoes import pode_enviar_para_analista
    
    if not pode_enviar_para_analista():
        flash('Você não tem permissão para enviar contratos para análise.', 'danger')
        return redirect(url_for('dashboard'))
    
    contrato = Contrato.get_by_id(id)
    
    if not contrato:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    if contrato.criado_por != session['usuario']['id']:
        flash('Você só pode enviar seus próprios contratos.', 'danger')
        return redirect(url_for('ver_contrato', id=id))
    
    if contrato.status == 'rascunho' and not contrato.solicitado_aprovacao:
        contrato.enviar_para_analista(session['usuario']['id'])
        flash('Contrato enviado para análise do analista!', 'success')
    else:
        flash('Este contrato não pode ser enviado para análise.', 'danger')
    
    return redirect(url_for('ver_contrato', id=id))


@app.route('/contratos/<int:id>/enviar-gestor', methods=['POST'])
@login_required
def enviar_para_gestor(id):
    """Analista envia contrato para aprovação do gestor"""
    from auth.permissoes import pode_enviar_para_gestor
    
    if not pode_enviar_para_gestor():
        flash('Você não tem permissão para enviar contratos para aprovação.', 'danger')
        return redirect(url_for('dashboard'))
    
    contrato = Contrato.get_by_id(id)
    
    if not contrato:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    if contrato.status == 'em_analise':
        contrato.enviar_para_gestor(session['usuario']['id'])
        flash('Contrato enviado para aprovação do gestor!', 'success')
    else:
        flash('Este contrato não pode ser enviado para aprovação.', 'danger')
    
    return redirect(url_for('ver_contrato', id=id))


@app.route('/contratos/<int:id>/aprovar', methods=['POST'])
@login_required
def aprovar_contrato(id):
    """Gestor aprova o contrato"""
    from auth.permissoes import pode_aprovar_contrato
    
    if not pode_aprovar_contrato():
        flash('Você não tem permissão para aprovar contratos.', 'danger')
        return redirect(url_for('dashboard'))
    
    contrato = Contrato.get_by_id(id)
    
    if not contrato:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    if contrato.status == 'aguardando_aprovacao':
        contrato.aprovar(session['usuario']['id'])
        flash('Contrato aprovado com sucesso!', 'success')
    else:
        flash('Este contrato não pode ser aprovado.', 'danger')
    
    return redirect(url_for('ver_contrato', id=id))


@app.route('/contratos/<int:id>/devolver-analista', methods=['POST'])
@login_required
def devolver_para_analista(id):
    """Gestor devolve contrato para análise do analista"""
    from auth.permissoes import pode_aprovar_contrato
    
    if not pode_aprovar_contrato():
        flash('Você não tem permissão para devolver contratos.', 'danger')
        return redirect(url_for('dashboard'))
    
    contrato = Contrato.get_by_id(id)
    motivo = request.form.get('motivo', '')
    
    if not contrato:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    if contrato.status == 'aguardando_aprovacao':
        contrato.devolver_para_analista(session['usuario']['id'], motivo)
        flash('Contrato devolvido para análise do analista.', 'warning')
    else:
        flash('Este contrato não pode ser devolvido.', 'danger')
    
    return redirect(url_for('ver_contrato', id=id))


@app.route('/contratos/<int:id>/devolver-assistente', methods=['POST'])
@login_required
def devolver_para_assistente(id):
    """Analista devolve contrato para assistente revisar"""
    from auth.permissoes import analista_required
    analista_required(lambda: None)()
    
    contrato = Contrato.get_by_id(id)
    motivo = request.form.get('motivo', '')
    
    if not contrato:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    if contrato.status == 'em_analise':
        contrato.devolver_para_assistente(session['usuario']['id'], motivo)
        flash('Contrato devolvido para o assistente revisar.', 'warning')
    else:
        flash('Este contrato não pode ser devolvido.', 'danger')
    
    return redirect(url_for('ver_contrato', id=id))


@app.route('/contratos/<int:id>/download')
@login_required
def download_contrato_pdf(id):
    """Download do contrato em PDF"""
    from utils.gerador_pdf import gerar_pdf_contrato
    
    contrato = Contrato.get_by_id(id)
    
    if not contrato:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    # Verifica permissão
    empresa_id = session['usuario']['empresa_id']
    if contrato.empresa_id != empresa_id and session['usuario']['perfil'] != 'admin_sistema':
        flash('Acesso negado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    # Define o caminho correto do PDF (NORMALIZADO)
    pdf_filename = f'contrato_{contrato.numero_contrato}.pdf'
    pdf_path = os.path.join('static', 'uploads', 'contratos', pdf_filename).replace('\\', '/')
    
    # Verifica se o PDF já existe
    if os.path.exists(pdf_path):
        logger.info(f"PDF encontrado: {pdf_path}")
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )
    
    # Gera o PDF
    logger.info(f"Gerando PDF para contrato {contrato.numero_contrato}")
    flash('Gerando PDF, aguarde...', 'info')
    
    novo_pdf = gerar_pdf_contrato(contrato)
    
    if novo_pdf and os.path.exists(novo_pdf):
        # Normaliza o caminho
        novo_pdf = novo_pdf.replace('\\', '/')
        contrato.pdf_path = novo_pdf
        contrato.save()
        
        logger.info(f"PDF gerado com sucesso: {novo_pdf}")
        flash('PDF gerado com sucesso!', 'success')
        
        return send_file(
            novo_pdf,
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )
    else:
        logger.error(f"Erro ao gerar PDF para contrato {contrato.numero_contrato}")
        flash('Erro ao gerar o PDF. Tente novamente.', 'danger')
        return redirect(url_for('ver_contrato', id=id))


# ==================== ROTAS DE USUÁRIO ====================

@app.route('/perfil')
@login_required
def perfil():
    """Perfil do usuário"""
    usuario = Usuario.get_by_id(session['usuario']['id'])
    empresa = None
    
    if usuario and usuario.empresa_id:
        empresa = Empresa.get_by_id(usuario.empresa_id)
    
    return render_template('perfil.html', usuario=usuario, empresa=empresa)


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro_usuario():
    """Cadastro público de novo usuário"""
    from core.utils import sanitizar_entrada, apenas_digitos, validar_email
    
    if request.method == 'POST':
        empresa_nome = sanitizar_entrada(request.form.get('empresa_nome'))
        empresa_cnpj = apenas_digitos(request.form.get('empresa_cnpj'))
        
        nome = sanitizar_entrada(request.form.get('nome'))
        email = sanitizar_entrada(request.form.get('email'))
        perfil = request.form.get('perfil', 'admin_empresa')
        cargo = sanitizar_entrada(request.form.get('cargo'))
        telefone = apenas_digitos(request.form.get('telefone'))
        celular = apenas_digitos(request.form.get('celular'))
        email_corporativo = sanitizar_entrada(request.form.get('email_corporativo'))
        senha = request.form.get('senha')
        
        if not empresa_nome or not nome or not email or not senha:
            flash('Preencha todos os campos obrigatórios', 'danger')
            return redirect(url_for('cadastro_usuario'))
        
        if not validar_email(email):
            flash('Email inválido', 'danger')
            return redirect(url_for('cadastro_usuario'))
        
        if Usuario.get_by_email(email):
            flash('Email já cadastrado', 'danger')
            return redirect(url_for('cadastro_usuario'))
        
        # Cria a empresa
        empresa = Empresa(
            nome=empresa_nome,
            cnpj=empresa_cnpj,
            email=email,
            telefone=telefone,
            celular=celular,
            status='trial'
        )
        empresa.save()
        
        # Cria o usuário admin
        usuario = Usuario(
            empresa_id=empresa.id,
            nome=nome,
            email=email,
            perfil='admin_empresa',
            cargo=cargo,
            telefone=telefone,
            celular=celular,
            email_corporativo=email_corporativo,
            primeiro_acesso=True
        )
        usuario.definir_senha(senha)
        usuario.save()
        
        flash('Cadastro realizado com sucesso! Faça login para continuar.', 'success')
        return redirect(url_for('login'))
    
    db = Database()
    ramos = db.fetch_all("SELECT id, nome FROM ramos_atividade ORDER BY nome") or []
    
    return render_template('admin/empresa/usuario_form.html', 
                         cadastro_publico=True, 
                         ramos=ramos,
                         form_data={})


# ==================== ROTAS DE RECUPERAÇÃO DE SENHA ====================

@app.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
    """Página de recuperação de senha"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Digite seu e-mail', 'danger')
            return redirect(url_for('recuperar_senha'))
        
        usuario = Usuario.get_by_email(email)
        
        if not usuario:
            flash('Se o e-mail estiver cadastrado, você receberá as instruções em breve.', 'info')
            return redirect(url_for('login'))
        
        token = usuario.gerar_token_recuperacao()
        link = url_for('redefinir_senha', token=token, _external=True)
        print(f"\n{'='*50}")
        print(f"Link de recuperação: {link}")
        print(f"{'='*50}\n")
        
        flash('Enviamos um link de recuperação para seu e-mail.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/recuperar_senha.html')


@app.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    """Página de redefinição de senha"""
    usuario = Usuario.get_by_token_recuperacao(token)
    
    if not usuario:
        flash('Link inválido ou expirado. Solicite uma nova recuperação.', 'danger')
        return redirect(url_for('recuperar_senha'))
    
    if request.method == 'POST':
        senha = request.form.get('senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        if not senha or not confirmar_senha:
            flash('Preencha todos os campos', 'danger')
            return redirect(url_for('redefinir_senha', token=token))
        
        if senha != confirmar_senha:
            flash('As senhas não conferem', 'danger')
            return redirect(url_for('redefinir_senha', token=token))
        
        usuario.definir_senha(senha)
        usuario.limpar_token_recuperacao()
        usuario.save()
        
        flash('Senha alterada com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/redefinir_senha.html')


# ==================== ROTAS DE FEEDBACK ====================

@app.route('/feedback', methods=['POST'])
@login_required
def feedback():
    """Recebe feedback do usuário"""
    nota = request.form.get('nota')
    recomendaria = request.form.get('recomendaria') == 'true'
    sugestao = request.form.get('sugestao')
    
    db = Database()
    query = """
        INSERT INTO feedbacks (empresa_id, usuario_id, nota, recomendaria, sugestao)
        VALUES (%s, %s, %s, %s, %s)
    """
    db.execute(query, (
        session['usuario'].get('empresa_id'),
        session['usuario']['id'],
        nota,
        recomendaria,
        sugestao
    ))
    
    session['feedback_enviado'] = True
    
    return jsonify({'sucesso': True, 'mensagem': 'Feedback enviado com sucesso!'})


# ==================== TRATAMENTO DE ERROS ====================

@app.errorhandler(403)
def forbidden(e):
    return render_template('erros/403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('erros/404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('erros/500.html'), 500


# ==================== CONTEXTO DO TEMPLATE ====================

@app.context_processor
def utility_processor():
    """Funções disponíveis em todos os templates"""
    def csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(16)
        return session['_csrf_token']
    
    return dict(csrf_token=csrf_token, now=datetime.now)


# ==================== INICIALIZAÇÃO ====================

if __name__ == '__main__':
    logger.info("ValidaPy iniciado")
    app.run(debug=True, host='0.0.0.0', port=5000)