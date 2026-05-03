from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, send_file, Response, stream_with_context
from config import Config
from core.database import Database, close_db
from core.logging_config import logger
from auth.login import LoginManager
from auth.permissoes import login_required
from models.usuario import Usuario
from models.empresa import Empresa
from models.contrato import Contrato
from models.notificacao import Notificacao
from datetime import datetime
import os
import secrets
import time
import json
from queue import Queue

# Blueprints
from admin.empresa import empresa_bp as admin_empresa_bp
from admin.clientes import clientes_bp
from admin.sistema import sistema_bp as admin_sistema_bp

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
app.permanent_session_lifetime = Config.PERMANENT_SESSION_LIFETIME
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'logos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'contratos'), exist_ok=True)

# Registrar blueprints
app.register_blueprint(admin_empresa_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(admin_sistema_bp)
app.teardown_appcontext(close_db)

# ==================== GERENCIADOR SSE ====================

class SSEManager:
    def __init__(self):
        self.connections = {}
    
    def add_connection(self, usuario_id, queue):
        if usuario_id not in self.connections:
            self.connections[usuario_id] = []
        self.connections[usuario_id].append(queue)
        logger.info(f"SSE connection added for user {usuario_id}")
    
    def remove_connection(self, usuario_id, queue):
        if usuario_id in self.connections:
            if queue in self.connections[usuario_id]:
                self.connections[usuario_id].remove(queue)
            if not self.connections[usuario_id]:
                del self.connections[usuario_id]
    
    def send_to_user(self, usuario_id, data):
        if usuario_id in self.connections:
            to_remove = []
            for queue in self.connections[usuario_id]:
                try:
                    queue.put(data)
                except:
                    to_remove.append(queue)
            for queue in to_remove:
                self.remove_connection(usuario_id, queue)

sse_manager = SSEManager()

# ==================== ROTAS PRINCIPAIS ====================

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

# ==================== ROTAS DE RECUPERAÇÃO DE SENHA ====================

@app.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Digite seu e-mail.', 'danger')
            return redirect(url_for('recuperar_senha'))
        
        usuario = Usuario.get_by_email(email)
        
        if not usuario:
            flash('Se o e-mail estiver cadastrado, você receberá as instruções.', 'info')
            return redirect(url_for('login'))
        
        token = secrets.token_urlsafe(32)
        
        Database.execute(
            "UPDATE usuarios SET token_recuperacao = %s, token_expiracao = DATE_ADD(NOW(), INTERVAL 1 HOUR) WHERE id = %s",
            (token, usuario.id)
        )
        
        link = url_for('redefinir_senha', token=token, _external=True)
        
        print(f"\n{'='*60}")
        print(f"🔐 LINK DE RECUPERAÇÃO DE SENHA")
        print(f"Usuário: {usuario.nome} ({usuario.email})")
        print(f"Link: {link}")
        print(f"{'='*60}\n")
        
        flash('Enviamos um link de recuperação para seu e-mail.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/recuperar_senha.html')

@app.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    usuario_data = Database.fetch_one(
        """SELECT id, nome, email FROM usuarios 
           WHERE token_recuperacao = %s 
           AND token_expiracao > NOW() 
           AND token_utilizado = 0""",
        (token,)
    )
    
    if not usuario_data:
        flash('Link inválido ou expirado. Solicite uma nova recuperação.', 'danger')
        return redirect(url_for('recuperar_senha'))
    
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        if not nova_senha or not confirmar_senha:
            flash('Preencha todos os campos.', 'danger')
            return redirect(url_for('redefinir_senha', token=token))
        
        if nova_senha != confirmar_senha:
            flash('As senhas não conferem.', 'danger')
            return redirect(url_for('redefinir_senha', token=token))
        
        if len(nova_senha) < 8:
            flash('A senha deve ter no mínimo 8 caracteres.', 'danger')
            return redirect(url_for('redefinir_senha', token=token))
        
        usuario = Usuario.get_by_id(usuario_data['id'])
        usuario.set_senha(nova_senha)
        usuario.save()
        
        Database.execute(
            "UPDATE usuarios SET token_recuperacao = NULL, token_expiracao = NULL, token_utilizado = 1 WHERE id = %s",
            (usuario.id,)
        )
        
        flash('Senha redefinida com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/redefinir_senha.html', usuario=usuario_data)

@app.route('/logout')
def logout():
    LoginManager.logout()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))

# ==================== DASHBOARDS ====================

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        usuario = session.get('usuario', {})
        perfil = usuario.get('perfil')
        
        if not perfil:
            flash('Erro na autenticação. Faça login novamente.', 'danger')
            return redirect(url_for('login'))
        
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
        else:
            return redirect(url_for('listar_contratos'))
    except Exception as e:
        logger.error(f"Erro no dashboard: {str(e)}")
        flash('Erro ao carregar dashboard. Faça login novamente.', 'danger')
        return redirect(url_for('login'))

@app.route('/dashboard/gestor')
@login_required
def dashboard_gestor():
    try:
        empresa_id = session['usuario']['empresa_id']
        stats = Contrato.estatisticas(empresa_id)
        contratos_pendentes = Contrato.listar_pendentes_aprovacao(empresa_id)
        contratos_em_analise = Contrato.listar_em_analise(empresa_id)
        
        return render_template('dashboard/gestor.html', 
                             stats=stats, 
                             contratos_pendentes=contratos_pendentes, 
                             contratos_em_analise=contratos_em_analise)
    except Exception as e:
        logger.error(f"Erro no dashboard_gestor: {str(e)}")
        flash('Erro ao carregar dashboard do gestor.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/dashboard/analista')
@login_required
def dashboard_analista():
    try:
        empresa_id = session['usuario']['empresa_id']
        stats = Contrato.estatisticas(empresa_id)
        contratos = Contrato.listar_por_empresa(empresa_id)
        top_contratos = sorted(contratos, key=lambda x: x.valor, reverse=True)[:5] if contratos else []
        contratos_em_analise = Contrato.listar_em_analise(empresa_id)
        return render_template('dashboard/analista.html', stats=stats, top_contratos=top_contratos, contratos_em_analise=contratos_em_analise)
    except Exception as e:
        logger.error(f"Erro no dashboard_analista: {str(e)}")
        flash('Erro ao carregar dashboard do analista.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/dashboard/assistente')
@login_required
def dashboard_assistente():
    try:
        usuario = session.get('usuario', {})
        usuario_id = usuario.get('id')
        usuario_nome = usuario.get('nome', 'Usuário')
        
        logger.info(f"Acessando dashboard assistente - Usuário ID: {usuario_id}, Nome: {usuario_nome}")
        
        if not usuario_id:
            logger.error("Usuário ID não encontrado na sessão")
            flash('Sessão expirada. Faça login novamente.', 'danger')
            return redirect(url_for('login'))
        
        # Buscar contratos do assistente (apenas os que ele criou)
        contratos = Contrato.listar_por_criador(usuario_id)
        logger.info(f"Contratos encontrados: {len(contratos) if contratos else 0}")
        
        # Inicializar estatísticas
        stats = {
            'total_contratos': 0,
            'aprovados': 0,
            'em_analise': 0,
            'aguardando': 0,
            'rascunhos': 0,
            'encerrados': 0,
            'cancelados': 0,
            'total_valor': 0.0,
            'taxa_aprovacao': 0
        }
        
        if contratos:
            stats['total_contratos'] = len(contratos)
            
            for c in contratos:
                if c.status == 'ativo':
                    stats['aprovados'] += 1
                    stats['total_valor'] += float(c.valor or 0)
                elif c.status == 'em_analise':
                    stats['em_analise'] += 1
                elif c.status == 'aguardando_aprovacao':
                    stats['aguardando'] += 1
                elif c.status == 'rascunho':
                    stats['rascunhos'] += 1
                elif c.status == 'encerrado':
                    stats['encerrados'] += 1
                elif c.status == 'cancelado':
                    stats['cancelados'] += 1
            
            if stats['total_contratos'] > 0:
                stats['taxa_aprovacao'] = round((stats['aprovados'] / stats['total_contratos']) * 100, 1)
        
        logger.info(f"Estatísticas calculadas: {stats}")
        
        return render_template('dashboard/assistente.html', 
                             contratos=contratos or [],
                             stats=stats,
                             usuario_nome=usuario_nome)
                             
    except Exception as e:
        logger.error(f"Erro no dashboard_assistente: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar dashboard do assistente.', 'danger')
        return redirect(url_for('dashboard'))

# ==================== CONTRATOS ====================

@app.route('/contratos')
@login_required
def listar_contratos():
    try:
        usuario = session.get('usuario', {})
        usuario_perfil = usuario.get('perfil')
        usuario_id = usuario.get('id')
        empresa_id = usuario.get('empresa_id')
        
        # Pegar filtros da URL
        status_filtro = request.args.get('status', '')
        busca_filtro = request.args.get('busca', '')
        
        print(f"🔍 FILTROS - Status: '{status_filtro}', Busca: '{busca_filtro}'")  # Debug
        
        # Buscar contratos baseado no perfil
        if usuario_perfil == 'admin_sistema':
            contratos = Contrato.listar_todos()
        elif usuario_perfil in ['admin_empresa', 'gestor', 'analista']:
            contratos = Contrato.listar_por_empresa(empresa_id)
        elif usuario_perfil == 'assistente':
            contratos = Contrato.listar_por_criador(usuario_id)
        else:
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('dashboard'))
        
        # Aplicar filtros
        contratos_filtrados = []
        for contrato in contratos:
            # Filtro por status
            if status_filtro and status_filtro != '':
                if contrato.status != status_filtro:
                    continue
            
            # Filtro por busca
            if busca_filtro and busca_filtro != '':
                busca_lower = busca_filtro.lower()
                match = False
                
                # Verificar em número do contrato
                if contrato.numero_contrato and busca_lower in contrato.numero_contrato.lower():
                    match = True
                # Verificar em contratante
                elif contrato.contratante_nome and busca_lower in contrato.contratante_nome.lower():
                    match = True
                # Verificar em contratada
                elif contrato.contratada_nome and busca_lower in contrato.contratada_nome.lower():
                    match = True
                
                if not match:
                    continue
            
            contratos_filtrados.append(contrato)
        
        print(f"📊 Total contratos: {len(contratos)}, Filtrados: {len(contratos_filtrados)}")  # Debug
        
        return render_template('contratos/listar.html', contratos=contratos_filtrados)
    except Exception as e:
        logger.error(f"Erro ao listar contratos: {str(e)}")
        flash('Erro ao carregar lista de contratos.', 'danger')
        return redirect(url_for('dashboard'))

# ==================== DEMAIS ROTAS ====================

@app.route('/contratos/novo', methods=['GET', 'POST'])
@login_required
def contrato_novo():
    try:
        from auth.permissoes import pode_criar_contrato
        if not pode_criar_contrato():
            flash('Você não tem permissão para criar contratos.', 'danger')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            contrato = Contrato(
                empresa_id=session['usuario']['empresa_id'],
                criado_por=session['usuario']['id'],
                contratante_nome=request.form.get('contratante_nome'),
                contratante_cnpj=request.form.get('contratante_cnpj'),
                contratante_email=request.form.get('contratante_email'),
                contratante_telefone=request.form.get('contratante_telefone'),
                contratada_nome=request.form.get('contratada_nome'),
                contratada_cnpj=request.form.get('contratada_cnpj'),
                contratada_email=request.form.get('contratada_email'),
                valor=request.form.get('valor'),
                prazo_dias=request.form.get('prazo_dias', type=int),
                data_inicio=request.form.get('data_inicio'),
                data_fim=request.form.get('data_fim'),
                descricao=request.form.get('descricao'),
                status='rascunho'
            )
            contrato.save()
            
            admins = Usuario.listar_por_perfil('admin_empresa', contrato.empresa_id)
            for admin in admins:
                if admin.id != session.get('usuario_id'):
                    Notificacao.criar(
                        usuario_id=admin.id,
                        empresa_id=contrato.empresa_id,
                        titulo='Novo Contrato Criado',
                        mensagem=f"{session.get('usuario', {}).get('nome')} criou um novo contrato: {contrato.numero_contrato}",
                        tipo='info',
                        link=f'/contratos/{contrato.id}'
                    )
            
            flash('Contrato criado com sucesso!', 'success')
            return redirect(url_for('ver_contrato', id=contrato.id))
        
        return render_template('contratos/novo.html')
    except Exception as e:
        logger.error(f"Erro ao criar contrato: {str(e)}")
        flash('Erro ao criar contrato.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/contratos/<int:id>')
@login_required
def ver_contrato(id):
    try:
        contrato = Contrato.get_by_id(id)
        if not contrato:
            flash('Contrato não encontrado.', 'danger')
            return redirect(url_for('listar_contratos'))
        
        usuario = session.get('usuario', {})
        usuario_perfil = usuario.get('perfil')
        usuario_id = usuario.get('id')
        usuario_nome = usuario.get('nome')
        empresa_id = usuario.get('empresa_id')
        
        pode_visualizar = False
        
        if usuario_perfil == 'admin_sistema':
            pode_visualizar = True
        elif usuario_perfil in ['admin_empresa', 'gestor', 'analista']:
            pode_visualizar = (contrato.empresa_id == empresa_id)
        elif usuario_perfil == 'assistente':
            pode_visualizar = (contrato.criado_por == usuario_id) or \
                              (contrato.empresa_id == empresa_id and contrato.status in ['rascunho', 'em_analise'])
        
        if not pode_visualizar:
            flash('Você não tem permissão para visualizar este contrato.', 'danger')
            return redirect(url_for('listar_contratos'))
        
        if contrato.criado_por != usuario_id:
            Notificacao.criar(
                usuario_id=contrato.criado_por,
                empresa_id=contrato.empresa_id,
                titulo='Contrato Visualizado',
                mensagem=f"{usuario_nome} visualizou o contrato {contrato.numero_contrato}",
                tipo='info',
                link=f'/contratos/{contrato.id}'
            )
        
        dias_restantes = None
        if contrato.data_fim and contrato.status == 'ativo':
            try:
                if isinstance(contrato.data_fim, str):
                    data_fim = datetime.strptime(contrato.data_fim, '%Y-%m-%d').date()
                else:
                    data_fim = contrato.data_fim
                hoje = datetime.now().date()
                dias = (data_fim - hoje).days
                dias_restantes = max(0, dias)
            except:
                dias_restantes = None
        
        pode_editar = contrato.pode_editar(usuario_perfil, usuario_id)
        return render_template('contratos/detalhe.html', contrato=contrato, dias_restantes=dias_restantes, pode_editar=pode_editar)
    except Exception as e:
        logger.error(f"Erro ao ver contrato {id}: {str(e)}")
        flash('Erro ao carregar contrato.', 'danger')
        return redirect(url_for('listar_contratos'))

@app.route('/contratos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_contrato(id):
    try:
        contrato = Contrato.get_by_id(id)
        if not contrato:
            flash('Contrato não encontrado.', 'danger')
            return redirect(url_for('listar_contratos'))
        
        usuario_perfil = session.get('usuario', {}).get('perfil')
        usuario_id = session.get('usuario_id')
        usuario_nome = session.get('usuario', {}).get('nome')
        
        if not contrato.pode_editar(usuario_perfil, usuario_id):
            flash('Você não tem permissão para editar este contrato.', 'danger')
            return redirect(url_for('listar_contratos'))
        
        if request.method == 'POST':
            contrato.contratante_nome = request.form.get('contratante_nome')
            contrato.contratante_cnpj = request.form.get('contratante_cnpj')
            contrato.contratante_email = request.form.get('contratante_email')
            contrato.contratante_telefone = request.form.get('contratante_telefone')
            contrato.contratada_nome = request.form.get('contratada_nome')
            contrato.contratada_cnpj = request.form.get('contratada_cnpj')
            contrato.contratada_email = request.form.get('contratada_email')
            contrato.valor = float(request.form.get('valor') or 0)
            contrato.prazo_dias = int(request.form.get('prazo_dias') or 0)
            contrato.descricao = request.form.get('descricao')
            contrato.atualizado_por = usuario_id
            contrato.save()
            
            if contrato.criado_por != usuario_id:
                Notificacao.criar(
                    usuario_id=contrato.criado_por,
                    empresa_id=contrato.empresa_id,
                    titulo='Contrato Editado',
                    mensagem=f"{usuario_nome} editou o contrato {contrato.numero_contrato}",
                    tipo='warning',
                    link=f'/contratos/{contrato.id}'
                )
            
            flash('Contrato atualizado com sucesso!', 'success')
            return redirect(url_for('ver_contrato', id=id))
        
        return render_template('contratos/editar.html', contrato=contrato)
    except Exception as e:
        logger.error(f"Erro ao editar contrato {id}: {str(e)}")
        flash('Erro ao editar contrato.', 'danger')
        return redirect(url_for('ver_contrato', id=id))

@app.route('/contratos/<int:id>/enviar-analista', methods=['POST'])
@login_required
def enviar_para_analista(id):
    try:
        contrato = Contrato.get_by_id(id)
        
        if not contrato:
            flash('Contrato não encontrado.', 'danger')
            return redirect(url_for('listar_contratos'))
        
        if contrato.status != 'rascunho':
            flash('Apenas contratos em rascunho podem ser enviados para análise.', 'warning')
            return redirect(url_for('ver_contrato', id=id))
        
        contrato.enviar_para_analista(session.get('usuario_id'))
        
        analistas = Usuario.listar_por_perfil('analista', contrato.empresa_id)
        for analista in analistas:
            if analista.id != session.get('usuario_id'):
                Notificacao.criar(
                    usuario_id=analista.id,
                    empresa_id=contrato.empresa_id,
                    titulo='Novo Contrato para Análise',
                    mensagem=f"O contrato {contrato.numero_contrato} foi enviado para análise",
                    tipo='warning',
                    link=f'/contratos/{contrato.id}'
                )
        
        flash('Contrato enviado para análise!', 'success')
        return redirect(url_for('ver_contrato', id=id))
    except Exception as e:
        logger.error(f"Erro ao enviar contrato para análise: {str(e)}")
        flash('Erro ao enviar contrato para análise.', 'danger')
        return redirect(url_for('ver_contrato', id=id))

@app.route('/contratos/<int:id>/enviar-gestor', methods=['POST'])
@login_required
def enviar_para_gestor(id):
    try:
        contrato = Contrato.get_by_id(id)
        
        if not contrato:
            flash('Contrato não encontrado.', 'danger')
            return redirect(url_for('listar_contratos'))
        
        if contrato.status != 'em_analise':
            flash('Apenas contratos em análise podem ser enviados para aprovação.', 'warning')
            return redirect(url_for('ver_contrato', id=id))
        
        contrato.enviar_para_gestor(session.get('usuario_id'))
        
        gestores = Usuario.listar_por_perfil('gestor', contrato.empresa_id)
        for gestor in gestores:
            if gestor.id != session.get('usuario_id'):
                Notificacao.criar(
                    usuario_id=gestor.id,
                    empresa_id=contrato.empresa_id,
                    titulo='Contrato Aguardando Aprovação',
                    mensagem=f"O contrato {contrato.numero_contrato} aguarda sua aprovação",
                    tipo='warning',
                    link=f'/contratos/{contrato.id}'
                )
        
        flash('Contrato enviado para aprovação do gestor!', 'success')
        return redirect(url_for('ver_contrato', id=id))
    except Exception as e:
        logger.error(f"Erro ao enviar contrato para gestor: {str(e)}")
        flash('Erro ao enviar contrato para gestor.', 'danger')
        return redirect(url_for('ver_contrato', id=id))

@app.route('/contratos/<int:id>/aprovar', methods=['POST'])
@login_required
def aprovar_contrato(id):
    try:
        contrato = Contrato.get_by_id(id)
        usuario_nome = session.get('usuario', {}).get('nome')
        
        if not contrato:
            flash('Contrato não encontrado.', 'danger')
            return redirect(url_for('listar_contratos'))
        
        if contrato.status != 'aguardando_aprovacao':
            flash('Apenas contratos aguardando aprovação podem ser aprovados.', 'warning')
            return redirect(url_for('ver_contrato', id=id))
        
        contrato.aprovar(session.get('usuario_id'))
        
        if contrato.criado_por != session.get('usuario_id'):
            Notificacao.criar(
                usuario_id=contrato.criado_por,
                empresa_id=contrato.empresa_id,
                titulo='Contrato Aprovado!',
                mensagem=f"O contrato {contrato.numero_contrato} foi aprovado por {usuario_nome}",
                tipo='success',
                link=f'/contratos/{contrato.id}'
            )
        
        flash('Contrato aprovado com sucesso!', 'success')
        return redirect(url_for('ver_contrato', id=id))
    except Exception as e:
        logger.error(f"Erro ao aprovar contrato: {str(e)}")
        flash('Erro ao aprovar contrato.', 'danger')
        return redirect(url_for('ver_contrato', id=id))

@app.route('/contratos/<int:id>/devolver-analista', methods=['POST'])
@login_required
def devolver_para_analista(id):
    try:
        contrato = Contrato.get_by_id(id)
        motivo = request.form.get('motivo', '')
        usuario_nome = session.get('usuario', {}).get('nome')
        
        if not contrato:
            flash('Contrato não encontrado.', 'danger')
            return redirect(url_for('listar_contratos'))
        
        contrato.devolver_para_analista(session.get('usuario_id'), motivo)
        
        if contrato.criado_por != session.get('usuario_id'):
            Notificacao.criar(
                usuario_id=contrato.criado_por,
                empresa_id=contrato.empresa_id,
                titulo='Contrato Devolvido para Análise',
                mensagem=f"O contrato {contrato.numero_contrato} foi devolvido para análise por {usuario_nome}",
                tipo='danger',
                link=f'/contratos/{contrato.id}'
            )
        
        flash('Contrato devolvido para análise.', 'warning')
        return redirect(url_for('ver_contrato', id=id))
    except Exception as e:
        logger.error(f"Erro ao devolver contrato para análise: {str(e)}")
        flash('Erro ao devolver contrato.', 'danger')
        return redirect(url_for('ver_contrato', id=id))

@app.route('/contratos/<int:id>/devolver-assistente', methods=['POST'])
@login_required
def devolver_para_assistente(id):
    try:
        contrato = Contrato.get_by_id(id)
        motivo = request.form.get('motivo', '')
        usuario_nome = session.get('usuario', {}).get('nome')
        
        if not contrato:
            flash('Contrato não encontrado.', 'danger')
            return redirect(url_for('listar_contratos'))
        
        contrato.devolver_para_assistente(session.get('usuario_id'), motivo)
        
        if contrato.criado_por != session.get('usuario_id'):
            Notificacao.criar(
                usuario_id=contrato.criado_por,
                empresa_id=contrato.empresa_id,
                titulo='Contrato Devolvido para Revisão',
                mensagem=f"O contrato {contrato.numero_contrato} foi devolvido para revisão por {usuario_nome}",
                tipo='danger',
                link=f'/contratos/{contrato.id}'
            )
        
        flash('Contrato devolvido para o assistente.', 'warning')
        return redirect(url_for('ver_contrato', id=id))
    except Exception as e:
        logger.error(f"Erro ao devolver contrato para assistente: {str(e)}")
        flash('Erro ao devolver contrato.', 'danger')
        return redirect(url_for('ver_contrato', id=id))

@app.route('/contratos/<int:id>/download')
@login_required
def download_contrato_pdf(id):
    try:
        from utils.gerador_pdf import gerar_pdf_contrato
        contrato = Contrato.get_by_id(id)
        if not contrato:
            flash('Contrato não encontrado.', 'danger')
            return redirect(url_for('listar_contratos'))
        
        usuario_perfil = session.get('usuario', {}).get('perfil')
        empresa_id = session.get('empresa_id')
        
        if usuario_perfil != 'admin_sistema' and contrato.empresa_id != empresa_id:
            flash('Você não tem permissão para baixar este contrato.', 'danger')
            return redirect(url_for('listar_contratos'))
        
        pdf_path = gerar_pdf_contrato(contrato)
        if pdf_path and os.path.exists(pdf_path):
            return send_file(pdf_path, as_attachment=True, download_name=f'contrato_{contrato.numero_contrato}.pdf', mimetype='application/pdf')
        else:
            flash('Erro ao gerar o PDF. Tente novamente.', 'danger')
            return redirect(url_for('ver_contrato', id=id))
    except Exception as e:
        logger.error(f"Erro ao baixar PDF: {str(e)}")
        flash('Erro ao gerar o PDF.', 'danger')
        return redirect(url_for('ver_contrato', id=id))
    

@app.route('/contratos/filtrar')
@login_required
def contratos_filtrar():
    """API para filtro dinâmico de contratos - SEM RELOAD"""
    try:
        usuario = session.get('usuario', {})
        usuario_perfil = usuario.get('perfil')
        usuario_id = usuario.get('id')
        empresa_id = usuario.get('empresa_id')
        
        status_filtro = request.args.get('status', '')
        busca_filtro = request.args.get('busca', '')
        
        # Buscar contratos baseado no perfil
        if usuario_perfil == 'admin_sistema':
            contratos = Contrato.listar_todos()
        elif usuario_perfil in ['admin_empresa', 'gestor', 'analista']:
            contratos = Contrato.listar_por_empresa(empresa_id)
        elif usuario_perfil == 'assistente':
            contratos = Contrato.listar_por_criador(usuario_id)
        else:
            return jsonify({'success': False, 'error': 'Permissão negada'})
        
        if not contratos:
            return jsonify({'success': True, 'contratos': [], 'total': 0})
        
        # Aplicar filtros
        contratos_filtrados = []
        for contrato in contratos:
            if status_filtro and status_filtro != '':
                if contrato.status != status_filtro:
                    continue
            
            if busca_filtro and busca_filtro != '':
                busca_lower = busca_filtro.lower()
                match = False
                if contrato.numero_contrato and busca_lower in contrato.numero_contrato.lower():
                    match = True
                elif contrato.contratante_nome and busca_lower in contrato.contratante_nome.lower():
                    match = True
                elif contrato.contratada_nome and busca_lower in contrato.contratada_nome.lower():
                    match = True
                
                if not match:
                    continue
            
            contratos_filtrados.append(contrato)
        
        # Converter para JSON
        dados = []
        for c in contratos_filtrados:
            dados.append({
                'id': c.id,
                'numero_contrato': str(c.numero_contrato) if c.numero_contrato else '',
                'contratante_nome': str(c.contratante_nome) if c.contratante_nome else '',
                'contratante_cnpj': str(c.contratante_cnpj) if c.contratante_cnpj else '',
                'contratada_nome': str(c.contratada_nome) if c.contratada_nome else '',
                'contratada_cnpj': str(c.contratada_cnpj) if c.contratada_cnpj else '',
                'valor': float(c.valor) if c.valor else 0,
                'status': str(c.status) if c.status else '',
                'data_criacao': c.data_criacao.strftime('%d/%m/%Y') if c.data_criacao else None
            })
        
        return jsonify({'success': True, 'contratos': dados, 'total': len(dados)})
        
    except Exception as e:
        logger.error(f"Erro no filtro: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
    



# ==================== PERFIL E MÉTRICAS ====================

@app.route('/perfil')
@login_required
def perfil():
    try:
        usuario = Usuario.get_by_id(session['usuario']['id'])
        empresa = None
        if usuario and usuario.empresa_id:
            empresa = Empresa.get_by_id(usuario.empresa_id)
        return render_template('perfil.html', usuario=usuario, empresa=empresa)
    except Exception as e:
        logger.error(f"Erro ao carregar perfil: {str(e)}")
        flash('Erro ao carregar perfil.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/metricas/pessoais')
@login_required
def metricas_pessoais():
    try:
        usuario_id = session['usuario']['id']
        empresa_id = session['usuario']['empresa_id']
        total = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE criado_por = %s AND empresa_id = %s", (usuario_id, empresa_id)) or {'total': 0}
        aprovados = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE criado_por = %s AND empresa_id = %s AND status = 'ativo'", (usuario_id, empresa_id)) or {'total': 0}
        em_analise = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE criado_por = %s AND empresa_id = %s AND status = 'em_analise'", (usuario_id, empresa_id)) or {'total': 0}
        aguardando = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE criado_por = %s AND empresa_id = %s AND status = 'aguardando_aprovacao'", (usuario_id, empresa_id)) or {'total': 0}
        valor_total = Database.fetch_one("SELECT SUM(valor) as total FROM contratos WHERE criado_por = %s AND empresa_id = %s AND status = 'ativo'", (usuario_id, empresa_id)) or {'total': 0}
        taxa = 0
        if total['total'] > 0:
            taxa = (aprovados['total'] / total['total']) * 100
        stats = {
            'total_contratos': total['total'] or 0,
            'aprovados': aprovados['total'] or 0,
            'em_analise': em_analise['total'] or 0,
            'aguardando': aguardando['total'] or 0,
            'valor_total': float(valor_total['total'] or 0),
            'taxa_aprovacao': round(taxa, 1),
            'taxa_acerto': round(taxa, 1)
        }
        return render_template('metricas/pessoais.html', stats=stats)
    except Exception as e:
        logger.error(f"Erro ao carregar métricas pessoais: {str(e)}")
        flash('Erro ao carregar métricas.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/metricas/empresa')
@login_required
def metricas_empresa():
    try:
        empresa_id = session['usuario']['empresa_id']
        total = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s", (empresa_id,)) or {'total': 0}
        usuarios = Database.fetch_one("SELECT COUNT(*) as total FROM usuarios WHERE empresa_id = %s AND ativo = 1", (empresa_id,)) or {'total': 0}
        stats = {'total_contratos': total['total'] or 0, 'total_usuarios': usuarios['total'] or 0}
        return render_template('metricas/empresa.html', stats=stats)
    except Exception as e:
        logger.error(f"Erro ao carregar métricas da empresa: {str(e)}")
        flash('Erro ao carregar métricas.', 'danger')
        return redirect(url_for('dashboard'))

# ==================== GAMIFICAÇÃO ====================

@app.route('/gamificacao/perfil')
@login_required
def gamificacao_perfil():
    return render_template('gamificacao/perfil.html')

@app.route('/gamificacao/ranking')
@login_required
def gamificacao_ranking():
    return render_template('gamificacao/ranking.html')

@app.route('/gamificacao/historico')
@login_required
def gamificacao_historico():
    return render_template('gamificacao/historico.html')

@app.route('/gamificacao/notificacoes/pendentes')
@login_required
def gamificacao_notificacoes_pendentes():
    return jsonify({'conquistas': [], 'nivel': {'subiu_nivel': False}})

# ==================== NOTIFICAÇÕES ====================

@app.route('/notificacoes')
@login_required
def notificacoes():
    try:
        usuario_id = session['usuario']['id']
        notificacoes_lista = Notificacao.listar_por_usuario(usuario_id, limite=50)
        notificacoes_nao_lidas = Notificacao.contar_nao_lidas(usuario_id)
        return render_template('notificacoes/index.html', 
                             notificacoes=notificacoes_lista, 
                             notificacoes_nao_lidas=notificacoes_nao_lidas)
    except Exception as e:
        logger.error(f"Erro ao carregar notificações: {str(e)}")
        flash('Erro ao carregar notificações.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/notificacoes/nao-lidas/count')
@login_required
def notificacoes_count():
    try:
        usuario_id = session['usuario']['id']
        total = Notificacao.contar_nao_lidas(usuario_id)
        return jsonify({'total': total})
    except Exception as e:
        logger.error(f"Erro ao contar notificações: {str(e)}")
        return jsonify({'total': 0})

@app.route('/notificacoes/ultimas')
@login_required
def notificacoes_ultimas():
    try:
        usuario_id = session['usuario']['id']
        limite = request.args.get('limite', 10, type=int)
        
        notificacoes = Database.fetch_all("""
            SELECT id, titulo, mensagem, tipo, link, lida,
                   DATE_FORMAT(data_criacao, '%%d/%%m/%%Y %%H:%%i') as data_formatada
            FROM notificacoes 
            WHERE usuario_id = %s 
            ORDER BY data_criacao DESC 
            LIMIT %s
        """, (usuario_id, limite))
        
        nao_lidas = Database.fetch_one(
            "SELECT COUNT(*) as total FROM notificacoes WHERE usuario_id = %s AND lida = 0",
            (usuario_id,)
        )
        
        return jsonify({
            'notificacoes': notificacoes or [],
            'nao_lidas': nao_lidas['total'] if nao_lidas else 0,
            'timestamp': time.time()
        })
    except Exception as e:
        logger.error(f"Erro ao buscar últimas notificações: {str(e)}")
        return jsonify({'notificacoes': [], 'nao_lidas': 0, 'timestamp': time.time()})

@app.route('/notificacoes/<int:id>/marcar-lida', methods=['POST'])
@login_required
def notificacao_marcar_lida(id):
    try:
        notificacao = Notificacao.get_by_id(id)
        if not notificacao or notificacao.usuario_id != session['usuario']['id']:
            return jsonify({'sucesso': False}), 403
        notificacao.marcar_como_lida()
        return jsonify({'sucesso': True})
    except Exception as e:
        logger.error(f"Erro ao marcar notificação como lida: {str(e)}")
        return jsonify({'sucesso': False}), 500

@app.route('/notificacoes/marcar-todas', methods=['POST'])
@login_required
def notificacoes_marcar_todas():
    try:
        Notificacao.marcar_todas_como_lidas(session['usuario']['id'])
        return jsonify({'sucesso': True})
    except Exception as e:
        logger.error(f"Erro ao marcar todas notificações: {str(e)}")
        return jsonify({'sucesso': False}), 500

@app.route('/notificacoes/<int:id>/excluir', methods=['POST'])
@login_required
def notificacao_excluir(id):
    try:
        notificacao = Notificacao.get_by_id(id)
        if not notificacao or notificacao.usuario_id != session['usuario']['id']:
            return jsonify({'sucesso': False}), 403
        notificacao.excluir()
        return jsonify({'sucesso': True})
    except Exception as e:
        logger.error(f"Erro ao excluir notificação: {str(e)}")
        return jsonify({'sucesso': False}), 500

@app.route('/notificacoes/preferencias', methods=['GET', 'POST'])
@login_required
def notificacoes_preferencias():
    try:
        usuario_id = session['usuario']['id']
        
        if request.method == 'POST':
            som_ativado = request.form.get('som_ativado') == 'on'
            Database.execute(
                "UPDATE usuarios SET notificacao_som = %s WHERE id = %s",
                (1 if som_ativado else 0, usuario_id)
            )
            flash('Preferências salvas com sucesso!', 'success')
            return redirect(url_for('notificacoes_preferencias'))
        
        usuario = Database.fetch_one(
            "SELECT notificacao_som FROM usuarios WHERE id = %s",
            (usuario_id,)
        )
        som_ativado = usuario.get('notificacao_som', 1) if usuario else 1
        
        return render_template('notificacoes/preferencias.html', som_ativado=som_ativado)
    except Exception as e:
        logger.error(f"Erro ao carregar preferências: {str(e)}")
        flash('Erro ao carregar preferências.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/notificacoes/preferencias/api', methods=['GET'])
@login_required
def notificacoes_preferencias_api():
    try:
        usuario_id = session['usuario']['id']
        usuario = Database.fetch_one(
            "SELECT notificacao_som FROM usuarios WHERE id = %s",
            (usuario_id,)
        )
        som_ativado = 1
        if usuario and usuario.get('notificacao_som') is not None:
            som_ativado = usuario['notificacao_som']
        return jsonify({'som_ativado': som_ativado})
    except Exception as e:
        logger.error(f"Erro ao carregar preferências API: {str(e)}")
        return jsonify({'som_ativado': 1})

@app.route('/notificacoes/stream')
@login_required
def notificacoes_stream():
    def event_stream():
        while True:
            yield f": heartbeat {time.time()}\n\n"
            time.sleep(30)
    
    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Content-Type': 'text/event-stream'
        }
    )

@app.route('/testar-notificacao')
@login_required
def testar_notificacao():
    try:
        Notificacao.criar(
            usuario_id=session['usuario']['id'],
            empresa_id=session['usuario']['empresa_id'],
            titulo='🧪 Notificação de Teste',
            mensagem='O sistema de notificações em tempo real está funcionando perfeitamente!',
            tipo='success',
            link='/dashboard'
        )
        
        flash('✅ Notificação de teste enviada com sucesso!', 'success')
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de teste: {str(e)}")
        flash('Erro ao enviar notificação de teste.', 'danger')
    
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/limpar-sessao')
def limpar_sessao():
    session.clear()
    flash('Sessão limpa. Faça login novamente.', 'info')
    return redirect(url_for('login'))

# ==================== ERROR HANDLERS ====================

@app.errorhandler(403)
def forbidden(e):
    return render_template('erros/403.html'), 403

@app.errorhandler(404)
def page_not_found(e):
    return render_template('erros/404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Erro 500: {str(e)}")
    return render_template('erros/500.html'), 500

# ==================== CONTEXT PROCESSORS ====================

@app.context_processor
def utility_processor():
    def csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(16)
        return session['_csrf_token']
    return dict(csrf_token=csrf_token, now=datetime.now)

@app.context_processor
def notificacoes_context():
    if 'usuario' in session:
        try:
            total = Notificacao.contar_nao_lidas(session['usuario']['id'])
            return {'notificacoes_nao_lidas': total}
        except:
            pass
    return {'notificacoes_nao_lidas': 0}

# ==================== MAIN ====================

if __name__ == '__main__':
    logger.info("System-Contratos iniciado")
    app.run(debug=True, host='0.0.0.0', port=5000)