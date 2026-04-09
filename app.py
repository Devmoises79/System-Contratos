from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, send_file
from config import Config
from core.database import Database, close_db
from auth.login import LoginManager
from auth.permissoes import login_required
from auth.ip_blocker import IPBlocker
from models.usuario import Usuario
from models.empresa import Empresa
from models.contrato import Contrato
from models.notificacao import Notificacao, SistemaNotificacoes
from core.logging_config import logger
import secrets
from datetime import datetime, timedelta
import os

from admin.empresa import admin_empresa_bp
from admin.sistema import admin_sistema_bp

app = Flask(__name__)
app.config.from_object(Config)

app.secret_key = Config.SECRET_KEY
app.permanent_session_lifetime = Config.PERMANENT_SESSION_LIFETIME

app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'logos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'contratos'), exist_ok=True)

app.register_blueprint(admin_empresa_bp)
app.register_blueprint(admin_sistema_bp)

app.teardown_appcontext(close_db)


@app.route('/')
def index():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
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
    LoginManager.logout()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
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
    from auth.permissoes import gestor_required
    gestor_required(lambda: None)()
    empresa_id = session['usuario']['empresa_id']
    stats = Contrato.estatisticas(empresa_id)
    contratos_pendentes = Contrato.listar_pendentes_aprovacao(empresa_id)
    return render_template('dashboard/gestor.html', stats=stats, contratos_pendentes=contratos_pendentes)


@app.route('/dashboard/analista')
@login_required
def dashboard_analista():
    from auth.permissoes import analista_required
    analista_required(lambda: None)()
    empresa_id = session['usuario']['empresa_id']
    stats = Contrato.estatisticas(empresa_id)
    contratos = Contrato.listar_por_empresa(empresa_id)
    top_contratos = sorted(contratos, key=lambda x: x.valor, reverse=True)[:5] if contratos else []
    contratos_em_analise = Contrato.listar_em_analise(empresa_id)
    return render_template('dashboard/analista.html', 
                         stats=stats, 
                         top_contratos=top_contratos,
                         contratos_em_analise=contratos_em_analise)


@app.route('/dashboard/assistente')
@login_required
def dashboard_assistente():
    from auth.permissoes import assistente_required
    assistente_required(lambda: None)()
    usuario_id = session['usuario']['id']
    contratos = Contrato.listar_por_criador(usuario_id)
    return render_template('dashboard/assistente.html', contratos=contratos)


@app.route('/contratos')
@login_required
def listar_contratos():
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
        contratos = [c for c in contratos if busca in (c.numero_contrato or '').lower() or busca in (c.contratante_nome or '').lower() or busca in (c.contratada_nome or '').lower()]
    return render_template('contratos/listar.html', contratos=contratos)


@app.route('/contratos/novo', methods=['GET', 'POST'])
@login_required
def contrato_novo():
    from auth.permissoes import pode_criar_contrato
    if not pode_criar_contrato():
        flash('Você não tem permissão para criar contratos.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        empresa_id = session['usuario']['empresa_id']
        usuario_id = session['usuario']['id']
        data_inicio_str = request.form.get('data_inicio')
        data_inicio = None
        if data_inicio_str:
            try:
                dia, mes, ano = map(int, data_inicio_str.split('/'))
                data_inicio = datetime(ano, mes, dia).date()
            except:
                data_inicio = None
        prazo_dias = request.form.get('prazo_dias', type=int)
        data_fim = None
        if data_inicio and prazo_dias:
            data_fim = data_inicio + timedelta(days=prazo_dias)
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
            prazo_dias=prazo_dias,
            data_inicio=data_inicio,
            data_fim=data_fim,
            descricao=request.form.get('descricao'),
            criado_por=usuario_id
        )
        contrato.save()
        SistemaNotificacoes.notificar_contrato_criado(contrato, Usuario.get_by_id(usuario_id))
        flash('Contrato criado com sucesso!', 'success')
        return redirect(url_for('ver_contrato', id=contrato.id))
    return render_template('contratos/novo.html')


@app.route('/contratos/<int:id>')
@login_required
def ver_contrato(id):
    contrato = Contrato.get_by_id(id)
    if not contrato:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    empresa_id = session['usuario']['empresa_id']
    if contrato.empresa_id != empresa_id and session['usuario']['perfil'] != 'admin_sistema':
        flash('Acesso negado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    usuario_atual = Usuario.get_by_id(session['usuario']['id'])
    
    if session['usuario']['perfil'] == 'analista' and contrato.status == 'rascunho':
        contrato.status = 'em_analise'
        contrato.atualizado_por = session['usuario']['id']
        contrato.save()
        SistemaNotificacoes.notificar_contrato_em_analise(contrato, usuario_atual)
        flash('Contrato agora está em análise!', 'info')
    
    if not (contrato.status == 'rascunho' and contrato.criado_por == session['usuario']['id']):
        SistemaNotificacoes.notificar_contrato_visualizado(contrato, usuario_atual)
    
    dias_restantes = contrato.get_dias_restantes()
    pdf_url = None
    if contrato.pdf_path:
        pdf_url = contrato.pdf_path.replace('\\', '/')
        if pdf_url.startswith('static/'):
            pdf_url = pdf_url[7:]
    return render_template('contratos/detalhe.html', contrato=contrato, pdf_url=pdf_url, dias_restantes=dias_restantes)


@app.route('/contratos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_contrato(id):
    from auth.permissoes import pode_editar_contrato
    contrato = Contrato.get_by_id(id)
    if not contrato:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    if not pode_editar_contrato(contrato):
        flash('Você não tem permissão para editar este contrato.', 'danger')
        return redirect(url_for('ver_contrato', id=id))
    if request.method == 'POST':
        usuario_editor = Usuario.get_by_id(session['usuario']['id'])
        
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
        
        SistemaNotificacoes.notificar_contrato_editado(contrato, usuario_editor)
        
        flash('Contrato atualizado com sucesso!', 'success')
        return redirect(url_for('ver_contrato', id=id))
    return render_template('contratos/editar.html', contrato=contrato)


@app.route('/contratos/<int:id>/enviar-analista', methods=['POST'])
@login_required
def enviar_para_analista(id):
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
        usuario_envio = Usuario.get_by_id(session['usuario']['id'])
        SistemaNotificacoes.notificar_contrato_enviado_analista(contrato, usuario_envio)
        flash('Contrato enviado para análise do analista!', 'success')
    else:
        flash('Este contrato não pode ser enviado para análise.', 'danger')
    return redirect(url_for('ver_contrato', id=id))


@app.route('/contratos/<int:id>/enviar-gestor', methods=['POST'])
@login_required
def enviar_para_gestor(id):
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
        usuario_analista = Usuario.get_by_id(session['usuario']['id'])
        SistemaNotificacoes.notificar_contrato_enviado_gestor(contrato, usuario_analista)
        flash('Contrato enviado para aprovação do gestor!', 'success')
    else:
        flash('Este contrato não pode ser enviado para aprovação.', 'danger')
    return redirect(url_for('dashboard_analista'))


@app.route('/contratos/<int:id>/aprovar', methods=['POST'])
@login_required
def aprovar_contrato(id):
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
        usuario_aprovador = Usuario.get_by_id(session['usuario']['id'])
        SistemaNotificacoes.notificar_contrato_aprovado(contrato, usuario_aprovador)
        flash('Contrato aprovado com sucesso!', 'success')
    else:
        flash('Este contrato não pode ser aprovado.', 'danger')
    return redirect(url_for('dashboard_gestor'))


@app.route('/contratos/<int:id>/devolver-analista', methods=['POST'])
@login_required
def devolver_para_analista(id):
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
        usuario_devolveu = Usuario.get_by_id(session['usuario']['id'])
        analista = Usuario.get_by_id(contrato.atualizado_por) if contrato.atualizado_por else None
        contrato.devolver_para_analista(session['usuario']['id'], motivo)
        if analista:
            SistemaNotificacoes.notificar_contrato_devolvido_analista(contrato, usuario_devolveu, analista, motivo)
        flash('Contrato devolvido para análise do analista.', 'warning')
    else:
        flash('Este contrato não pode ser devolvido.', 'danger')
    return redirect(url_for('dashboard_gestor'))


@app.route('/contratos/<int:id>/devolver-assistente', methods=['POST'])
@login_required
def devolver_para_assistente(id):
    from auth.permissoes import analista_required
    analista_required(lambda: None)()
    contrato = Contrato.get_by_id(id)
    motivo = request.form.get('motivo', '')
    if not contrato:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    if contrato.status == 'em_analise':
        usuario_devolveu = Usuario.get_by_id(session['usuario']['id'])
        assistente = Usuario.get_by_id(contrato.criado_por)
        contrato.devolver_para_assistente(session['usuario']['id'], motivo)
        if assistente:
            SistemaNotificacoes.notificar_contrato_devolvido_assistente(contrato, usuario_devolveu, assistente, motivo)
        flash('Contrato devolvido para o assistente revisar.', 'warning')
    else:
        flash('Este contrato não pode ser devolvido.', 'danger')
    return redirect(url_for('dashboard_analista'))


@app.route('/contratos/<int:id>/download')
@login_required
def download_contrato_pdf(id):
    from utils.gerador_pdf import gerar_pdf_contrato
    contrato = Contrato.get_by_id(id)
    if not contrato:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    empresa_id = session['usuario']['empresa_id']
    if contrato.empresa_id != empresa_id and session['usuario']['perfil'] != 'admin_sistema':
        flash('Acesso negado', 'danger')
        return redirect(url_for('listar_contratos'))
    pdf_filename = f'contrato_{contrato.numero_contrato}.pdf'
    pdf_path = os.path.join('static', 'uploads', 'contratos', pdf_filename).replace('\\', '/')
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True, download_name=pdf_filename, mimetype='application/pdf')
    novo_pdf = gerar_pdf_contrato(contrato)
    if novo_pdf and os.path.exists(novo_pdf):
        novo_pdf = novo_pdf.replace('\\', '/')
        contrato.pdf_path = novo_pdf
        contrato.save()
        return send_file(novo_pdf, as_attachment=True, download_name=pdf_filename, mimetype='application/pdf')
    else:
        flash('Erro ao gerar o PDF. Tente novamente.', 'danger')
        return redirect(url_for('ver_contrato', id=id))


@app.route('/perfil')
@login_required
def perfil():
    usuario = Usuario.get_by_id(session['usuario']['id'])
    empresa = None
    if usuario and usuario.empresa_id:
        empresa = Empresa.get_by_id(usuario.empresa_id)
    return render_template('perfil.html', usuario=usuario, empresa=empresa)


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro_usuario():
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
        empresa = Empresa(nome=empresa_nome, cnpj=empresa_cnpj, email=email, telefone=telefone, celular=celular, status='trial')
        empresa.save()
        usuario = Usuario(empresa_id=empresa.id, nome=nome, email=email, perfil='admin_empresa', cargo=cargo, telefone=telefone, celular=celular, email_corporativo=email_corporativo, primeiro_acesso=True)
        usuario.definir_senha(senha)
        usuario.save()
        flash('Cadastro realizado com sucesso! Faça login para continuar.', 'success')
        return redirect(url_for('login'))
    db = Database()
    ramos = db.fetch_all("SELECT id, nome FROM ramos_atividade ORDER BY nome") or []
    return render_template('admin/empresa/usuario_form.html', cadastro_publico=True, ramos=ramos, form_data={})


@app.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
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
        print(f"\n{'='*50}\nLink de recuperação: {link}\n{'='*50}\n")
        flash('Enviamos um link de recuperação para seu e-mail.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/recuperar_senha.html')


@app.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
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


@app.route('/feedback', methods=['POST'])
@login_required
def feedback():
    nota = request.form.get('nota')
    recomendaria = request.form.get('recomendaria') == 'true'
    sugestao = request.form.get('sugestao')
    db = Database()
    db.execute("INSERT INTO feedbacks (empresa_id, usuario_id, nota, recomendaria, sugestao) VALUES (%s, %s, %s, %s, %s)",
               (session['usuario'].get('empresa_id'), session['usuario']['id'], nota, recomendaria, sugestao))
    session['feedback_enviado'] = True
    return jsonify({'sucesso': True, 'mensagem': 'Feedback enviado com sucesso!'})


# ==================== ROTAS DE MÉTRICAS ====================

@app.route('/metricas/pessoais')
@login_required
def metricas_pessoais():
    """Métricas pessoais do usuário"""
    usuario_id = session['usuario']['id']
    empresa_id = session['usuario']['empresa_id']
    db = Database()
    
    try:
        total_contratos = db.fetch_one("""
            SELECT COUNT(*) as total FROM contratos 
            WHERE criado_por = %s AND empresa_id = %s
        """, (usuario_id, empresa_id)) or {'total': 0}
        
        aprovados = db.fetch_one("""
            SELECT COUNT(*) as total FROM contratos 
            WHERE criado_por = %s AND empresa_id = %s AND status = 'ativo'
        """, (usuario_id, empresa_id)) or {'total': 0}
        
        em_analise = db.fetch_one("""
            SELECT COUNT(*) as total FROM contratos 
            WHERE criado_por = %s AND empresa_id = %s AND status = 'em_analise'
        """, (usuario_id, empresa_id)) or {'total': 0}
        
        aguardando = db.fetch_one("""
            SELECT COUNT(*) as total FROM contratos 
            WHERE criado_por = %s AND empresa_id = %s AND status = 'aguardando_aprovacao'
        """, (usuario_id, empresa_id)) or {'total': 0}
        
        valor_total = db.fetch_one("""
            SELECT SUM(valor) as total FROM contratos 
            WHERE criado_por = %s AND empresa_id = %s AND status = 'ativo'
        """, (usuario_id, empresa_id)) or {'total': 0}
        
        contratos_por_mes = db.fetch_all("""
            SELECT 
                DATE_FORMAT(data_criacao, '%Y-%m') as mes,
                COUNT(*) as total
            FROM contratos 
            WHERE criado_por = %s AND empresa_id = %s 
                AND data_criacao >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(data_criacao, '%Y-%m')
            ORDER BY mes DESC
        """, (usuario_id, empresa_id)) or []
        
        status_contratos = db.fetch_all("""
            SELECT 
                status,
                COUNT(*) as total
            FROM contratos 
            WHERE criado_por = %s AND empresa_id = %s
            GROUP BY status
        """, (usuario_id, empresa_id)) or []
        
        ultimos_contratos = db.fetch_all("""
            SELECT id, numero_contrato, contratante_nome, valor, status, data_criacao
            FROM contratos 
            WHERE criado_por = %s AND empresa_id = %s
            ORDER BY data_criacao DESC
            LIMIT 5
        """, (usuario_id, empresa_id)) or []
        
        taxa_aprovacao = 0
        if total_contratos['total'] > 0:
            taxa_aprovacao = (aprovados['total'] / total_contratos['total']) * 100
        
        stats = {
            'total_contratos': total_contratos['total'] or 0,
            'aprovados': aprovados['total'] or 0,
            'em_analise': em_analise['total'] or 0,
            'aguardando': aguardando['total'] or 0,
            'valor_total': float(valor_total['total'] or 0),
            'taxa_aprovacao': round(taxa_aprovacao, 1)
        }
        
        return render_template('metricas/pessoais.html',
                             stats=stats,
                             contratos_por_mes=contratos_por_mes,
                             status_contratos=status_contratos,
                             ultimos_contratos=ultimos_contratos)
                             
    except Exception as e:
        logger.error(f"Erro em metricas_pessoais: {e}")
        stats = {
            'total_contratos': 0,
            'aprovados': 0,
            'em_analise': 0,
            'aguardando': 0,
            'valor_total': 0,
            'taxa_aprovacao': 0
        }
        return render_template('metricas/pessoais.html',
                             stats=stats,
                             contratos_por_mes=[],
                             status_contratos=[],
                             ultimos_contratos=[])


@app.route('/metricas/empresa')
@login_required
def metricas_empresa():
    """Métricas da empresa"""
    empresa_id = session['usuario']['empresa_id']
    db = Database()
    
    try:
        total_contratos = db.fetch_one("""
            SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s
        """, (empresa_id,)) or {'total': 0}
        
        contratos_por_status = db.fetch_all("""
            SELECT status, COUNT(*) as total 
            FROM contratos 
            WHERE empresa_id = %s 
            GROUP BY status
        """, (empresa_id,)) or []
        
        valor_total = db.fetch_one("""
            SELECT SUM(valor) as total FROM contratos 
            WHERE empresa_id = %s AND status = 'ativo'
        """, (empresa_id,)) or {'total': 0}
        
        total_usuarios = db.fetch_one("""
            SELECT COUNT(*) as total FROM usuarios WHERE empresa_id = %s AND ativo = 1
        """, (empresa_id,)) or {'total': 0}
        
        contratos_por_mes = db.fetch_all("""
            SELECT 
                DATE_FORMAT(data_criacao, '%Y-%m') as mes,
                COUNT(*) as total
            FROM contratos 
            WHERE empresa_id = %s 
                AND data_criacao >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(data_criacao, '%Y-%m')
            ORDER BY mes DESC
        """, (empresa_id,)) or []
        
        stats = {
            'total_contratos': total_contratos['total'] or 0,
            'valor_total': float(valor_total['total'] or 0),
            'total_usuarios': total_usuarios['total'] or 0
        }
        
        return render_template('metricas/empresa.html',
                             stats=stats,
                             contratos_por_status=contratos_por_status,
                             contratos_por_mes=contratos_por_mes)
                             
    except Exception as e:
        logger.error(f"Erro em metricas_empresa: {e}")
        stats = {
            'total_contratos': 0,
            'valor_total': 0,
            'total_usuarios': 0
        }
        return render_template('metricas/empresa.html',
                             stats=stats,
                             contratos_por_status=[],
                             contratos_por_mes=[])


# ==================== ROTAS DE GAMIFICAÇÃO ====================

@app.route('/gamificacao/perfil')
@login_required
def gamificacao_perfil():
    """Perfil de gamificação do usuário"""
    usuario_id = session['usuario']['id']
    db = Database()
    
    try:
        pontos = db.fetch_one("""
            SELECT COALESCE(SUM(pontos), 0) as total FROM gamificacao_pontos 
            WHERE usuario_id = %s
        """, (usuario_id,)) or {'total': 0}
        
        conquistas = db.fetch_all("""
            SELECT g.*, 
                   CASE WHEN gp.id IS NOT NULL THEN TRUE ELSE FALSE END as conquistada
            FROM gamificacao_conquistas g
            LEFT JOIN gamificacao_pontos gp ON g.id = gp.conquista_id AND gp.usuario_id = %s
            WHERE g.empresa_id = %s OR g.empresa_id IS NULL
            ORDER BY g.pontos_necessarios ASC
        """, (usuario_id, session['usuario']['empresa_id'])) or []
        
        nivel = 'Bronze'
        if pontos['total'] >= 1000:
            nivel = 'Diamante'
        elif pontos['total'] >= 500:
            nivel = 'Ouro'
        elif pontos['total'] >= 200:
            nivel = 'Prata'
        
        return render_template('gamificacao/perfil.html',
                             pontos=pontos['total'],
                             nivel=nivel,
                             conquistas=conquistas)
    except Exception as e:
        logger.error(f"Erro em gamificacao_perfil: {e}")
        return render_template('gamificacao/perfil.html',
                             pontos=0,
                             nivel='Bronze',
                             conquistas=[])


@app.route('/gamificacao/ranking')
@login_required
def gamificacao_ranking():
    """Ranking da empresa"""
    empresa_id = session['usuario']['empresa_id']
    db = Database()
    
    try:
        ranking = db.fetch_all("""
            SELECT u.id, u.nome, u.email, u.perfil,
                   COALESCE(SUM(gp.pontos), 0) as pontos,
                   RANK() OVER (ORDER BY COALESCE(SUM(gp.pontos), 0) DESC) as posicao
            FROM usuarios u
            LEFT JOIN gamificacao_pontos gp ON u.id = gp.usuario_id
            WHERE u.empresa_id = %s AND u.ativo = 1
            GROUP BY u.id, u.nome, u.email, u.perfil
            ORDER BY pontos DESC
            LIMIT 20
        """, (empresa_id,)) or []
        
        return render_template('gamificacao/ranking.html', ranking=ranking)
    except Exception as e:
        logger.error(f"Erro em gamificacao_ranking: {e}")
        return render_template('gamificacao/ranking.html', ranking=[])


@app.route('/gamificacao/historico')
@login_required
def gamificacao_historico():
    """Histórico de pontos do usuário"""
    usuario_id = session['usuario']['id']
    db = Database()
    
    try:
        historico = db.fetch_all("""
            SELECT * FROM gamificacao_pontos 
            WHERE usuario_id = %s 
            ORDER BY data_criacao DESC
            LIMIT 50
        """, (usuario_id,)) or []
        
        return render_template('gamificacao/historico.html', historico=historico)
    except Exception as e:
        logger.error(f"Erro em gamificacao_historico: {e}")
        return render_template('gamificacao/historico.html', historico=[])


# ==================== ROTAS DE NOTIFICAÇÕES ====================

@app.route('/notificacoes')
@login_required
def notificacoes():
    usuario_id = session['usuario']['id']
    notificacoes = Notificacao.listar_por_usuario(usuario_id, limite=100)
    notificacoes_nao_lidas = Notificacao.contar_nao_lidas(usuario_id)
    return render_template('notificacoes/index.html', 
                         notificacoes=notificacoes,
                         notificacoes_nao_lidas=notificacoes_nao_lidas)


@app.route('/notificacoes/nao-lidas/count')
@login_required
def notificacoes_count():
    usuario_id = session['usuario']['id']
    total = Notificacao.contar_nao_lidas(usuario_id)
    return jsonify({'total': total})


@app.route('/notificacoes/<int:id>/marcar-lida', methods=['POST'])
@login_required
def notificacao_marcar_lida(id):
    db = Database()
    result = db.fetch_one("SELECT * FROM notificacoes WHERE id = %s", (id,))
    if not result:
        return jsonify({'sucesso': False, 'erro': 'Notificação não encontrada'}), 404
    if result['usuario_id'] != session['usuario']['id']:
        return jsonify({'sucesso': False, 'erro': 'Acesso negado'}), 403
    db.execute("UPDATE notificacoes SET lida = TRUE, data_leitura = NOW() WHERE id = %s", (id,))
    return jsonify({'sucesso': True})


@app.route('/notificacoes/marcar-todas', methods=['POST'])
@login_required
def notificacoes_marcar_todas():
    db = Database()
    db.execute("UPDATE notificacoes SET lida = TRUE, data_leitura = NOW() WHERE usuario_id = %s AND lida = FALSE", 
               (session['usuario']['id'],))
    return jsonify({'sucesso': True})


@app.route('/testar-notificacao')
@login_required
def testar_notificacao():
    Notificacao.criar(
        usuario_id=session['usuario']['id'],
        empresa_id=session['usuario'].get('empresa_id'),
        titulo="🔔 Teste de Notificação",
        mensagem="Se você está vendo esta mensagem, o sistema de notificações está funcionando!",
        tipo="success",
        link="/dashboard"
    )
    flash('Notificação de teste criada!', 'success')
    return redirect(url_for('dashboard'))


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
    def csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(16)
        return session['_csrf_token']
    return dict(csrf_token=csrf_token, now=datetime.now)


@app.context_processor
def notificacoes_context():
    """Adiciona informações de notificações em todos os templates"""
    if 'usuario' in session:
        try:
            usuario_id = session['usuario']['id']
            total_nao_lidas = Notificacao.contar_nao_lidas(usuario_id)
            ultimas_notificacoes = Notificacao.listar_por_usuario(usuario_id, apenas_nao_lidas=True, limite=5)
            
            # Buscar pontos de gamificação
            db = Database()
            pontos = db.fetch_one("SELECT COALESCE(SUM(pontos), 0) as total FROM gamificacao_pontos WHERE usuario_id = %s", (usuario_id,))
            total_pontos = pontos['total'] if pontos else 0
            
            nivel = 'Bronze'
            if total_pontos >= 1000:
                nivel = 'Diamante'
            elif total_pontos >= 500:
                nivel = 'Ouro'
            elif total_pontos >= 200:
                nivel = 'Prata'
            
            return {
                'total_notificacoes_nao_lidas': total_nao_lidas,
                'ultimas_notificacoes': ultimas_notificacoes,
                'gamificacao_pontos': total_pontos,
                'gamificacao_titulo': nivel
            }
        except Exception as e:
            print(f"Erro ao carregar notificações: {e}")
    return {
        'total_notificacoes_nao_lidas': 0, 
        'ultimas_notificacoes': [],
        'gamificacao_pontos': 0,
        'gamificacao_titulo': 'Bronze'
    }


if __name__ == '__main__':
    logger.info("ValidaPy iniciado")
    app.run(debug=True, host='0.0.0.0', port=5000)