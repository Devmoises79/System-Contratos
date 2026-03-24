# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify, make_response
from datetime import timedelta, datetime
import os
import functools
import logging
import re
import secrets
import html
from logging.handlers import RotatingFileHandler
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from core.database import get_db, close_db
from auth.login import LoginManager
from auth.permissoes import (
    login_required, perfil_required, 
    admin_sistema_required, admin_empresa_required,
    gestor_required, assistente_required, analista_required
)
from auth.ip_blocker import IPBlocker
from core.utils import sanitizar_entrada, validar_cnpj, formatar_cnpj, apenas_digitos

# Blueprints
from admin.sistema import admin_sistema_bp
from admin.empresa import admin_empresa_bp

# Modelos
from models.contrato import Contrato
from models.usuario import Usuario
from models.empresa import Empresa

# =====================================================
# CONFIGURAÇÃO DA APLICAÇÃO
# =====================================================

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# =====================================================
# CONFIGURAÇÕES DE SEGURANÇA
# =====================================================

# Sessão - 2 horas no máximo
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['SESSION_COOKIE_SECURE'] = True  # Apenas HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Impede acesso via JavaScript
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Proteção contra CSRF
app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # Renova a sessão

# Proteção CSRF
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = secrets.token_hex(32)
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hora

# Headers de segurança
@app.after_request
def add_security_headers(response):
    """Adiciona headers de segurança em todas as respostas"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'; style-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'; font-src 'self' https://cdnjs.cloudflare.com; img-src 'self' data:;"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

# =====================================================
# PROTEÇÃO CSRF
# =====================================================

def gerar_csrf_token():
    """Gera token CSRF para formulários"""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

app.jinja_env.globals['csrf_token'] = gerar_csrf_token

def validar_csrf_token(token):
    """Valida token CSRF"""
    token_sessao = session.get('_csrf_token')
    if not token_sessao or token_sessao != token:
        return False
    return True

def csrf_protegido(f):
    """Decorator para proteger rotas contra CSRF"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
            if not token or not validar_csrf_token(token):
                app.logger.warning(f"Tentativa de CSRF detectada: {request.remote_addr}")
                flash('Erro de validação do formulário. Tente novamente.', 'danger')
                return redirect(request.referrer or url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# PROTEÇÃO XSS
# =====================================================

def xss_protegido(f):
    """Decorator para sanitizar entradas"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Sanitiza dados do formulário
        if request.form:
            request.form = sanitizar_entrada(request.form.to_dict())
        
        # Sanitiza query parameters
        if request.args:
            request.args = sanitizar_entrada(request.args.to_dict())
        
        # Sanitiza JSON
        if request.is_json:
            request.json = sanitizar_entrada(request.get_json())
        
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# PROTEÇÃO SQL INJECTION
# =====================================================

def sql_injection_protegido(f):
    """Adiciona camada extra de proteção SQL Injection"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Padrões suspeitos de SQL Injection
        sql_patterns = [
            r'(\bSELECT\b.*\bFROM\b)',
            r'(\bINSERT\b.*\bINTO\b)',
            r'(\bUPDATE\b.*\bSET\b)',
            r'(\bDELETE\b.*\bFROM\b)',
            r'(\bDROP\b.*\bTABLE\b)',
            r'(\bUNION\b.*\bSELECT\b)',
            r'(--)',
            r'(\bOR\b.*=.*\bOR\b)',
            r'(\bAND\b.*=.*\bAND\b)',
            r'(\bEXEC\b)',
            r'(\bXP_\w+\b)',
            r'(\bWAITFOR\b.*\bDELAY\b)',
            r'(\bBENCHMARK\b)',
            r'(\bSLEEP\b)',
            r'(\bCONCAT\b)',
            r'(\bGROUP_CONCAT\b)',
            r'(\bINFORMATION_SCHEMA\b)'
        ]
        
        # Verifica parâmetros
        for key, value in request.args.items():
            if isinstance(value, str):
                for pattern in sql_patterns:
                    if re.search(pattern, value.upper()):
                        app.logger.warning(f"Tentativa de SQL Injection detectada: {request.remote_addr} - {key}={value}")
                        flash('Entrada inválida detectada.', 'danger')
                        return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# VERIFICAÇÃO DE IP BLOQUEADO
# =====================================================

def ip_bloqueado_verificado(f):
    """Verifica se o IP não está bloqueado"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        bloqueado, minutos = IPBlocker.verificar_bloqueio(ip)
        
        if bloqueado:
            app.logger.warning(f"Tentativa de acesso de IP bloqueado: {ip}")
            return render_template('auth/bloqueado.html', 
                                 minutos=minutos,
                                 motivo='Múltiplas tentativas falhas',
                                 ip=ip), 403
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# VERIFICAÇÃO DE TEMPO DE SESSÃO
# =====================================================

def tempo_sessao_required(f):
    """Verifica se a sessão ainda é válida (máx 2 horas)"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' in session:
            if 'login_time' in session:
                try:
                    login_time = datetime.fromisoformat(session['login_time'])
                    if datetime.now() - login_time > timedelta(hours=2):
                        session.clear()
                        flash('Sessão expirada. Faça login novamente.', 'warning')
                        return redirect(url_for('login'))
                except:
                    session.clear()
                    return redirect(url_for('login'))
            
            # Renova o tempo de login
            session['login_time'] = datetime.now().isoformat()
        
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# LOG DE ACESSO
# =====================================================

def log_acesso(f):
    """Registra acesso às rotas"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        resposta = f(*args, **kwargs)
        
        # Registra log
        try:
            usuario_id = session.get('usuario', {}).get('id') if 'usuario' in session else None
            empresa_id = session.get('usuario', {}).get('empresa_id') if 'usuario' in session else None
            
            log_data = {
                'endpoint': request.endpoint,
                'method': request.method,
                'ip': request.remote_addr,
                'user_agent': request.user_agent.string,
                'usuario_id': usuario_id,
                'empresa_id': empresa_id,
                'status_code': resposta.status_code if hasattr(resposta, 'status_code') else 200
            }
            
            app.logger.info(f"Acesso: {log_data}")
            
        except Exception as e:
            app.logger.error(f"Erro ao registrar log: {e}")
        
        return resposta
    return decorated_function

# =====================================================
# DECORATOR COMPOSTO PARA ROTAS PROTEGIDAS
# =====================================================

def rota_protegida(*perfis):
    """Decorator composto que aplica todas as proteções"""
    def decorator(f):
        @functools.wraps(f)
        @login_required
        @tempo_sessao_required
        @ip_bloqueado_verificado
        @csrf_protegido
        @xss_protegido
        @sql_injection_protegido
        @log_acesso
        def decorated_function(*args, **kwargs):
            if perfis and session.get('usuario', {}).get('perfil') not in perfis:
                flash('Acesso negado. Você não tem permissão.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# =====================================================
# REGISTRA BLUEPRINTS
# =====================================================

app.register_blueprint(admin_sistema_bp)
app.register_blueprint(admin_empresa_bp)

# =====================================================
# CRIA PASTAS NECESSÁRIAS
# =====================================================

os.makedirs('static/uploads/logos', exist_ok=True)
os.makedirs('static/uploads/contratos', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Configuração de logging
if not app.debug:
    file_handler = RotatingFileHandler('logs/validapy.log', maxBytes=10485760, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('ValidaPy iniciado')

# =====================================================
# ROTAS PÚBLICAS (menos proteção)
# =====================================================

@app.route('/')
@ip_bloqueado_verificado
@xss_protegido
@sql_injection_protegido
def index():
    """Página inicial - redireciona para login"""
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@ip_bloqueado_verificado
@xss_protegido
@sql_injection_protegido
def login():
    """Página de login"""
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = sanitizar_entrada(request.form.get('email', ''))
        senha = request.form.get('senha', '')
        lembrar = request.form.get('lembrar') == 'on'
        
        if not email or not senha:
            flash('Email e senha são obrigatórios.', 'danger')
            return render_template('login.html')
        
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            flash('Formato de email inválido.', 'danger')
            return render_template('login.html')
        
        sucesso, resultado = LoginManager.login(email, senha, lembrar)
        
        if sucesso:
            session['_csrf_token'] = secrets.token_hex(32)
            session['login_time'] = datetime.now().isoformat()
            
            flash(resultado['mensagem'], 'success')
            return redirect(resultado['redirect'])
        else:
            if resultado.get('erro') == 'ip_bloqueado':
                return render_template('auth/bloqueado.html', 
                                     minutos=resultado['minutos'],
                                     ip=request.remote_addr), 403
            else:
                flash(resultado['mensagem'], 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@ip_bloqueado_verificado
def logout():
    """Logout do usuário"""
    LoginManager.logout()
    session.clear()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('login'))

@app.route('/recuperar-senha', methods=['GET', 'POST'])
@ip_bloqueado_verificado
@xss_protegido
@sql_injection_protegido
def recuperar_senha():
    """Recuperação de senha"""
    if request.method == 'POST':
        email = sanitizar_entrada(request.form.get('email', ''))
        
        if not email:
            flash('Email é obrigatório.', 'danger')
            return render_template('auth/recuperar_senha.html')
        
        usuario = Usuario.get_by_email(email)
        if usuario:
            app.logger.info(f"Token de recuperação gerado para: {email}")
            flash('Instruções enviadas para seu email.', 'success')
        else:
            flash('Se o email existir, enviaremos instruções.', 'info')
        
        return redirect(url_for('login'))
    
    return render_template('auth/recuperar_senha.html')

@app.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
@ip_bloqueado_verificado
@xss_protegido
@sql_injection_protegido
def redefinir_senha(token):
    """Redefine senha com token"""
    token = sanitizar_entrada(token)
    usuario = Usuario.get_by_token(token)
    
    if not usuario:
        flash('Token inválido ou expirado.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        senha = request.form.get('senha', '')
        confirmar = request.form.get('confirmar_senha', '')
        
        if len(senha) < 8:
            flash('A senha deve ter no mínimo 8 caracteres.', 'danger')
        elif not re.search(r'[A-Z]', senha):
            flash('A senha deve conter pelo menos uma letra maiúscula.', 'danger')
        elif not re.search(r'[a-z]', senha):
            flash('A senha deve conter pelo menos uma letra minúscula.', 'danger')
        elif not re.search(r'[0-9]', senha):
            flash('A senha deve conter pelo menos um número.', 'danger')
        elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', senha):
            flash('A senha deve conter pelo menos um caractere especial.', 'danger')
        elif senha != confirmar:
            flash('As senhas não conferem.', 'danger')
        else:
            usuario.definir_senha(senha)
            usuario.limpar_token()
            usuario.primeiro_acesso = False
            usuario.save()
            
            app.logger.info(f"Senha redefinida para usuário: {usuario.email}")
            flash('Senha redefinida com sucesso!', 'success')
            return redirect(url_for('login'))
    
    return render_template('auth/redefinir_senha.html', token=token)

@app.route('/cadastro', methods=['GET', 'POST'])
@ip_bloqueado_verificado
@xss_protegido
@sql_injection_protegido
def cadastro_usuario():
    """Página pública de cadastro de usuário"""
    from models.empresa import Empresa
    from models.usuario import Usuario
    from core.database import Database
    
    db = Database()
    ramos = db.fetch_all("SELECT id, nome, descricao FROM ramos_atividade WHERE ativo = TRUE ORDER BY nome")
    
    perfis = [
        {'valor': 'admin_empresa', 'nome': 'Administrador da Empresa', 'descricao': 'Acesso total à gestão da empresa'},
        {'valor': 'gestor', 'nome': 'Gestor', 'descricao': 'Gerencia contratos e aprovações'},
        {'valor': 'analista', 'nome': 'Analista', 'descricao': 'Visualiza relatórios e estatísticas, cria e edita contratos'},
        {'valor': 'assistente', 'nome': 'Assistente', 'descricao': 'Cria e edita contratos'}
    ]
    
    if request.method == 'POST':
        app.logger.info(f"Dados recebidos no POST: {dict(request.form)}")
        
        nome = sanitizar_entrada(request.form.get('nome', ''))
        email = sanitizar_entrada(request.form.get('email', ''))
        senha = request.form.get('senha', '')
        confirmar_senha = request.form.get('confirmar_senha', '')
        perfil = request.form.get('perfil', '')
        
        perfis_permitidos = ['admin_empresa', 'gestor', 'analista', 'assistente']
        if perfil not in perfis_permitidos:
            app.logger.warning(f"Perfil inválido tentado: {perfil}")
            flash('Selecione um cargo válido na empresa.', 'danger')
            return render_template('admin/empresa/usuario_form.html', 
                                 cadastro_publico=True, 
                                 ramos=ramos, 
                                 perfis=perfis,
                                 form_data=request.form)
        
        email_corporativo = sanitizar_entrada(request.form.get('email_corporativo', ''))
        cargo = sanitizar_entrada(request.form.get('cargo', ''))
        telefone = apenas_digitos(request.form.get('telefone', ''))
        celular = apenas_digitos(request.form.get('celular', ''))
        
        empresa_nome = sanitizar_entrada(request.form.get('empresa_nome', ''))
        empresa_cnpj = apenas_digitos(request.form.get('empresa_cnpj', ''))
        ramo_id = request.form.get('ramo_id', '')
        novo_ramo = sanitizar_entrada(request.form.get('novo_ramo', ''))
        
        if not nome or not email or not senha or not perfil or not empresa_nome:
            flash('Todos os campos obrigatórios devem ser preenchidos.', 'danger')
            return render_template('admin/empresa/usuario_form.html', 
                                 cadastro_publico=True, 
                                 ramos=ramos, 
                                 perfis=perfis,
                                 form_data=request.form)
        
        if senha != confirmar_senha:
            flash('As senhas não conferem.', 'danger')
            return render_template('admin/empresa/usuario_form.html', 
                                 cadastro_publico=True, 
                                 ramos=ramos, 
                                 perfis=perfis,
                                 form_data=request.form)
        
        if len(senha) < 8:
            flash('A senha deve ter no mínimo 8 caracteres.', 'danger')
            return render_template('admin/empresa/usuario_form.html', 
                                 cadastro_publico=True, 
                                 ramos=ramos, 
                                 perfis=perfis,
                                 form_data=request.form)
        
        if Usuario.get_by_email(email):
            flash('Este email já está cadastrado. Use outro email.', 'danger')
            return render_template('admin/empresa/usuario_form.html', 
                                 cadastro_publico=True, 
                                 ramos=ramos, 
                                 perfis=perfis,
                                 form_data=request.form)
        
        try:
            if ramo_id == 'outro' and novo_ramo:
                query = "INSERT INTO ramos_atividade (nome, descricao, ativo) VALUES (%s, %s, TRUE)"
                ramo_id = db.execute_return_id(query, (novo_ramo, f"Ramo cadastrado por {empresa_nome}"))
                app.logger.info(f"Novo ramo cadastrado: {novo_ramo}")
            
            empresa_id = None
            if empresa_cnpj:
                empresa_existente = Empresa.get_by_cnpj(empresa_cnpj)
                if empresa_existente:
                    empresa_id = empresa_existente.id
                    app.logger.info(f"Empresa existente encontrada: {empresa_id} - {empresa_existente.nome}")
            
            if not empresa_id:
                empresa = Empresa(
                    nome=empresa_nome,
                    cnpj=empresa_cnpj if empresa_cnpj else None,
                    email=email,
                    status='trial'
                )
                empresa_id = empresa.save()
                
                if not empresa_id:
                    raise Exception("Erro ao criar empresa - ID não retornado")
                
                app.logger.info(f"Nova empresa criada com ID: {empresa_id}")
            
            usuario = Usuario(
                empresa_id=empresa_id,
                nome=nome,
                email=email,
                perfil=perfil,
                cargo=cargo,
                telefone=telefone,
                celular=celular,
                email_corporativo=email_corporativo if email_corporativo else None,
                ativo=True,
                primeiro_acesso=False
            )
            
            if not usuario.definir_senha(senha):
                raise Exception("Erro ao definir hash da senha")
            
            usuario_id = usuario.save()
            
            if not usuario_id:
                raise Exception("Erro ao criar usuário - ID não retornado")
            
            app.logger.info(f"Usuário criado com ID: {usuario_id} - Perfil: {perfil} - Empresa: {empresa_id}")
            
            flash('Cadastro realizado com sucesso! Faça o login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            app.logger.error(f"Erro no cadastro: {str(e)}")
            import traceback
            traceback.print_exc()
            flash('Erro ao realizar cadastro. Tente novamente.', 'danger')
            return render_template('admin/empresa/usuario_form.html', 
                                 cadastro_publico=True, 
                                 ramos=ramos, 
                                 perfis=perfis,
                                 form_data=request.form)
    
    return render_template('admin/empresa/usuario_form.html', 
                         cadastro_publico=True, 
                         ramos=ramos, 
                         perfis=perfis,
                         form_data={})

# =====================================================
# ROTA DE PERFIL
# =====================================================

@app.route('/perfil')
@rota_protegida()
def perfil():
    """Página de perfil do usuário"""
    usuario_id = session['usuario']['id']
    usuario = Usuario.get_by_id(usuario_id)
    
    if not usuario:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('dashboard'))
    
    empresa = Empresa.get_by_id(usuario.empresa_id)
    
    return render_template('perfil.html', usuario=usuario, empresa=empresa)

# =====================================================
# ROTAS DE DASHBOARD (PROTEGIDAS)
# =====================================================

@app.route('/dashboard')
@rota_protegida()
def dashboard():
    """Redireciona para dashboard apropriado"""
    perfil = session['usuario']['perfil']
    
    redirects = {
        'admin_sistema': url_for('admin_sistema.dashboard'),
        'admin_empresa': url_for('admin_empresa.dashboard'),
        'gestor': url_for('gestor_dashboard'),
        'assistente': url_for('assistente_dashboard'),
        'analista': url_for('analista_dashboard')
    }
    
    return redirect(redirects.get(perfil, url_for('login')))

@app.route('/dashboard/gestor')
@rota_protegida('gestor', 'admin_empresa', 'admin_sistema')
def gestor_dashboard():
    """Dashboard do gestor"""
    empresa_id = session['usuario']['empresa_id']
    
    stats = Contrato.estatisticas(empresa_id)
    contratos_pendentes = Contrato.listar_por_empresa(empresa_id, 'rascunho')
    
    return render_template('dashboard/gestor.html',
                         stats=stats,
                         contratos_pendentes=contratos_pendentes)

@app.route('/dashboard/assistente')
@rota_protegida('assistente', 'gestor', 'admin_empresa', 'admin_sistema')
def assistente_dashboard():
    """Dashboard do assistente"""
    empresa_id = session['usuario']['empresa_id']
    
    db = get_db()
    meus_contratos = db.fetch_all("""
        SELECT * FROM contratos 
        WHERE empresa_id = %s AND criado_por = %s
        ORDER BY data_criacao DESC
        LIMIT 10
    """, (empresa_id, session['usuario']['id']))
    
    return render_template('dashboard/assistente.html', contratos=meus_contratos)



# =====================================================
# ROTA DO ANALISTA (CORRIGIDA)
# =====================================================

@app.route('/dashboard/analista')
@rota_protegida('analista', 'gestor', 'admin_empresa', 'admin_sistema')
def analista_dashboard():
    """Dashboard do analista - Visualização de dados e estatísticas"""
    try:
        empresa_id = session['usuario']['empresa_id']
        db = get_db()
        
        # Buscar estatísticas
        stats = Contrato.estatisticas(empresa_id)
        
        if not stats:
            stats = {
                'total': 0,
                'ativos': 0,
                'rascunhos': 0,
                'aguardando': 0,
                'encerrados': 0,
                'cancelados': 0,
                'suspensos': 0,
                'total_valor': 0,
                'media': 0,
                'por_mes': []
            }
        
        # Adicionar por_status para compatibilidade com template
        stats['por_status'] = {
            'rascunho': stats.get('rascunhos', 0),
            'aguardando': stats.get('aguardando', 0),
            'encerrado': stats.get('encerrados', 0),
            'cancelado': stats.get('cancelados', 0),
            'suspenso': stats.get('suspensos', 0)
        }
        
        # Buscar top 5 contratos por valor
        top_contratos_raw = db.fetch_all("""
            SELECT id, numero_contrato, contratante_nome, valor
            FROM contratos 
            WHERE empresa_id = %s
            ORDER BY valor DESC
            LIMIT 5
        """, (empresa_id,))
        
        top_contratos = []
        for c in top_contratos_raw:
            top_contratos.append({
                'id': c['id'],
                'numero_contrato': c['numero_contrato'],
                'contratante_nome': c['contratante_nome'],
                'valor': c['valor']
            })
        
        app.logger.info(f"Dashboard analista carregado - Empresa: {empresa_id}, Contratos: {stats['total']}")
        
        return render_template('dashboard/analista.html', 
                             stats=stats,
                             top_contratos=top_contratos)
                             
    except Exception as e:
        app.logger.error(f"Erro no dashboard do analista: {e}")
        import traceback
        traceback.print_exc()
        # Retorna template com dados vazios em vez de redirecionar
        return render_template('dashboard/analista.html', 
                             stats={
                                 'total': 0, 'ativos': 0, 'rascunhos': 0, 'aguardando': 0,
                                 'encerrados': 0, 'cancelados': 0, 'suspensos': 0,
                                 'total_valor': 0, 'media': 0, 'por_mes': [],
                                 'por_status': {'rascunho': 0, 'aguardando': 0, 'encerrado': 0, 'cancelado': 0, 'suspenso': 0}
                             }, 
                             top_contratos=[])

# =====================================================
# ROTAS DE CONTRATO COM PERMISSÕES CORRETAS
# =====================================================

@app.route('/contrato/<int:id>/enviar-aprovacao', methods=['POST'])
@rota_protegida('analista', 'assistente', 'admin_empresa', 'admin_sistema')
def enviar_contrato_aprovacao(id):
    """Envia contrato para aprovação"""
    contrato = Contrato.get_by_id(id)
    
    if not contrato or contrato.empresa_id != session['usuario']['empresa_id']:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    # Verificar se já está aprovado
    if contrato.status == 'ativo':
        flash('Contrato já está aprovado!', 'warning')
        return redirect(url_for('ver_contrato', id=contrato.id))
    
    # Verificar se já foi enviado
    if contrato.solicitado_aprovacao:
        flash('Este contrato já foi enviado para aprovação.', 'warning')
        return redirect(url_for('ver_contrato', id=contrato.id))
    
    # Verificar se está em rascunho
    if contrato.status != 'rascunho':
        flash('Apenas contratos em rascunho podem ser enviados para aprovação.', 'warning')
        return redirect(url_for('ver_contrato', id=contrato.id))
    
    # Solicitar aprovação
    contrato.solicitar_aprovacao(session['usuario']['id'])
    
    app.logger.info(f"Contrato {contrato.numero_contrato} enviado para aprovação por {session['usuario']['id']}")
    
    flash(f'Contrato {contrato.numero_contrato} enviado para aprovação!', 'success')
    return redirect(url_for('listar_contratos'))

@app.route('/contrato/<int:id>/aprovar', methods=['POST'])
@rota_protegida('gestor', 'admin_empresa', 'admin_sistema')
def aprovar_contrato(id):
    """Aprova contrato (apenas gestor e admin)"""
    contrato = Contrato.get_by_id(id)
    
    if not contrato or contrato.empresa_id != session['usuario']['empresa_id']:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    # Verificar se já está aprovado
    if contrato.status == 'ativo':
        flash('Contrato já está aprovado!', 'warning')
        return redirect(url_for('ver_contrato', id=contrato.id))
    
    # Verificar se foi solicitado aprovação
    if not contrato.solicitado_aprovacao:
        flash('Este contrato não foi solicitado para aprovação ainda.', 'warning')
        return redirect(url_for('ver_contrato', id=contrato.id))
    
    # Aprovar usando o método existente
    contrato.aprovar(session['usuario']['id'])
    
    app.logger.info(f"Contrato {contrato.numero_contrato} aprovado por {session['usuario']['id']}")
    
    flash(f'Contrato {contrato.numero_contrato} aprovado com sucesso!', 'success')
    return redirect(url_for('listar_contratos'))

@app.route('/contrato/<int:id>/rejeitar', methods=['POST'])
@rota_protegida('gestor', 'admin_empresa', 'admin_sistema')
def rejeitar_contrato(id):
    """Rejeita a aprovação do contrato"""
    contrato = Contrato.get_by_id(id)
    
    if not contrato or contrato.empresa_id != session['usuario']['empresa_id']:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    # Verificar se foi solicitado aprovação
    if not contrato.solicitado_aprovacao:
        flash('Este contrato não está aguardando aprovação.', 'warning')
        return redirect(url_for('ver_contrato', id=contrato.id))
    
    # Rejeitar aprovação
    contrato.rejeitar_aprovacao(session['usuario']['id'])
    
    app.logger.info(f"Contrato {contrato.numero_contrato} rejeitado por {session['usuario']['id']}")
    
    flash(f'Contrato {contrato.numero_contrato} rejeitado. Retornado para rascunho.', 'warning')
    return redirect(url_for('listar_contratos'))

@app.route('/contrato/<int:id>/editar', methods=['GET', 'POST'])
@rota_protegida('analista', 'gestor', 'assistente', 'admin_empresa', 'admin_sistema')
def editar_contrato(id):
    """Edita contrato existente"""
    contrato = Contrato.get_by_id(id)
    
    if not contrato or contrato.empresa_id != session['usuario']['empresa_id']:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    # Verificar se pode editar (analista não pode editar contratos já enviados para aprovação)
    if session['usuario']['perfil'] == 'analista' and contrato.solicitado_aprovacao:
        flash('Contrato já enviado para aprovação. Não pode ser editado.', 'danger')
        return redirect(url_for('ver_contrato', id=contrato.id))
    
    if request.method == 'POST':
        contrato.contratante_nome = sanitizar_entrada(request.form.get('contratante_nome', contrato.contratante_nome))
        contrato.contratante_cnpj = apenas_digitos(request.form.get('contratante_cnpj', contrato.contratante_cnpj))
        contrato.contratante_email = sanitizar_entrada(request.form.get('contratante_email', contrato.contratante_email))
        contrato.contratante_telefone = apenas_digitos(request.form.get('contratante_telefone', contrato.contratante_telefone))
        contrato.contratada_nome = sanitizar_entrada(request.form.get('contratada_nome', contrato.contratada_nome))
        contrato.contratada_cnpj = apenas_digitos(request.form.get('contratada_cnpj', contrato.contratada_cnpj))
        contrato.contratada_email = sanitizar_entrada(request.form.get('contratada_email', contrato.contratada_email))
        contrato.valor = float(request.form.get('valor', contrato.valor))
        contrato.prazo_dias = int(request.form.get('prazo_dias', contrato.prazo_dias))
        contrato.descricao = sanitizar_entrada(request.form.get('descricao', contrato.descricao))
        contrato.atualizado_por = session['usuario']['id']
        
        contrato.save()
        
        flash('Contrato atualizado com sucesso!', 'success')
        return redirect(url_for('ver_contrato', id=contrato.id))
    
    return render_template('contratos/editar.html', contrato=contrato)


# =====================================================
# ROTAS DE CONTRATOS (PROTEGIDAS)
# =====================================================

@app.route('/contratos')
@rota_protegida('analista', 'gestor', 'assistente', 'admin_empresa', 'admin_sistema')
def listar_contratos():
    """Lista contratos da empresa"""
    empresa_id = session['usuario']['empresa_id']
    status = sanitizar_entrada(request.args.get('status', ''))
    
    contratos = Contrato.listar_por_empresa(empresa_id, status if status else None)
    
    return render_template('contratos/listar.html', contratos=contratos)

@app.route('/contrato/novo', methods=['GET', 'POST'])
@rota_protegida('analista', 'gestor', 'assistente', 'admin_empresa', 'admin_sistema')
def contrato_novo():
    """Cria novo contrato"""
    if request.method == 'POST':
        dados = {
            'contratante_nome': sanitizar_entrada(request.form.get('contratante_nome', '')),
            'contratante_cnpj': apenas_digitos(request.form.get('contratante_cnpj', '')),
            'contratante_email': sanitizar_entrada(request.form.get('contratante_email', '')),
            'contratante_telefone': apenas_digitos(request.form.get('contratante_telefone', '')),
            'contratada_nome': sanitizar_entrada(request.form.get('contratada_nome', '')),
            'contratada_cnpj': apenas_digitos(request.form.get('contratada_cnpj', '')),
            'contratada_email': sanitizar_entrada(request.form.get('contratada_email', '')),
            'valor': request.form.get('valor', '0'),
            'prazo_dias': request.form.get('prazo_dias', '0'),
            'descricao': sanitizar_entrada(request.form.get('descricao', ''))
        }
        
        if not dados['contratante_nome'] or not dados['contratada_nome']:
            flash('Nome do contratante e contratada são obrigatórios.', 'danger')
            return redirect(url_for('contrato_novo'))
        
        if not dados['valor'] or float(dados['valor']) <= 0:
            flash('Valor deve ser maior que zero.', 'danger')
            return redirect(url_for('contrato_novo'))
        
        if not dados['prazo_dias'] or int(dados['prazo_dias']) <= 0:
            flash('Prazo deve ser maior que zero.', 'danger')
            return redirect(url_for('contrato_novo'))
        
        contrato = Contrato(
            empresa_id=session['usuario']['empresa_id'],
            contratante_nome=dados['contratante_nome'],
            contratante_cnpj=dados['contratante_cnpj'],
            contratante_email=dados['contratante_email'],
            contratante_telefone=dados['contratante_telefone'],
            contratada_nome=dados['contratada_nome'],
            contratada_cnpj=dados['contratada_cnpj'],
            contratada_email=dados['contratada_email'],
            valor=float(dados['valor']),
            prazo_dias=int(dados['prazo_dias']),
            descricao=dados['descricao'],
            criado_por=session['usuario']['id']
        )
        
        contrato.save()
        contrato.gerar_pdf()
        
        app.logger.info(f"Novo contrato criado: {contrato.numero_contrato} por usuário {session['usuario']['id']}")
        
        flash('Contrato criado com sucesso!', 'success')
        return redirect(url_for('listar_contratos'))
    
    return render_template('contratos/novo.html')

@app.route('/contrato/<int:id>')
@rota_protegida('analista', 'gestor', 'assistente', 'admin_empresa', 'admin_sistema')
def ver_contrato(id):
    """Visualiza contrato"""
    contrato = Contrato.get_by_id(id)
    
    if not contrato or contrato.empresa_id != session['usuario']['empresa_id']:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    return render_template('contratos/detalhe.html', contrato=contrato)

@app.route('/contrato/<int:id>/editar', methods=['GET', 'POST'])
@rota_protegida('analista', 'gestor', 'assistente', 'admin_empresa', 'admin_sistema')
def editar_contrato(id):
    """Edita contrato existente"""
    contrato = Contrato.get_by_id(id)
    
    if not contrato or contrato.empresa_id != session['usuario']['empresa_id']:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    if request.method == 'POST':
        contrato.contratante_nome = sanitizar_entrada(request.form.get('contratante_nome', contrato.contratante_nome))
        contrato.contratante_cnpj = apenas_digitos(request.form.get('contratante_cnpj', contrato.contratante_cnpj))
        contrato.contratante_email = sanitizar_entrada(request.form.get('contratante_email', contrato.contratante_email))
        contrato.contratante_telefone = apenas_digitos(request.form.get('contratante_telefone', contrato.contratante_telefone))
        contrato.contratada_nome = sanitizar_entrada(request.form.get('contratada_nome', contrato.contratada_nome))
        contrato.contratada_cnpj = apenas_digitos(request.form.get('contratada_cnpj', contrato.contratada_cnpj))
        contrato.contratada_email = sanitizar_entrada(request.form.get('contratada_email', contrato.contratada_email))
        contrato.valor = float(request.form.get('valor', contrato.valor))
        contrato.prazo_dias = int(request.form.get('prazo_dias', contrato.prazo_dias))
        contrato.descricao = sanitizar_entrada(request.form.get('descricao', contrato.descricao))
        
        contrato.save()
        
        flash('Contrato atualizado com sucesso!', 'success')
        return redirect(url_for('ver_contrato', id=contrato.id))
    
    return render_template('contratos/editar.html', contrato=contrato)

@app.route('/contrato/<int:id>/enviar-aprovacao', methods=['POST'])
@rota_protegida('analista', 'gestor', 'assistente', 'admin_empresa', 'admin_sistema')
def enviar_contrato_aprovacao(id):
    """Envia contrato para aprovação do gestor"""
    contrato = Contrato.get_by_id(id)
    
    if not contrato or contrato.empresa_id != session['usuario']['empresa_id']:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    if contrato.status != 'rascunho':
        flash('Apenas contratos em rascunho podem ser enviados para aprovação.', 'warning')
        return redirect(url_for('ver_contrato', id=contrato.id))
    
    contrato.status = 'aguardando_aprovacao'
    contrato.save()
    
    app.logger.info(f"Contrato {contrato.numero_contrato} enviado para aprovação por {session['usuario']['id']}")
    
    flash(f'Contrato {contrato.numero_contrato} enviado para aprovação!', 'success')
    return redirect(url_for('listar_contratos'))

@app.route('/contrato/<int:id>/aprovar', methods=['POST'])
@rota_protegida('gestor', 'admin_empresa', 'admin_sistema')
def aprovar_contrato(id):
    """Aprova contrato (apenas gestor e admin)"""
    contrato = Contrato.get_by_id(id)
    
    if not contrato or contrato.empresa_id != session['usuario']['empresa_id']:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    if contrato.status != 'aguardando_aprovacao':
        flash('Apenas contratos aguardando aprovação podem ser aprovados.', 'warning')
        return redirect(url_for('ver_contrato', id=contrato.id))
    
    contrato.status = 'ativo'
    contrato.save()
    
    app.logger.info(f"Contrato {contrato.numero_contrato} aprovado por {session['usuario']['id']}")
    
    flash(f'Contrato {contrato.numero_contrato} aprovado com sucesso!', 'success')
    return redirect(url_for('listar_contratos'))

# =====================================================
# ROTAS DE FEEDBACK
# =====================================================

@app.route('/feedback', methods=['POST'])
@rota_protegida()
def enviar_feedback():
    """Envia feedback do usuário"""
    try:
        nota = int(request.form.get('nota', 0))
        recomendaria = request.form.get('recomendaria') == 'true'
        sugestao = sanitizar_entrada(request.form.get('sugestao', ''))
        
        if nota < 1 or nota > 5:
            return jsonify({'sucesso': False, 'erro': 'Nota inválida'}), 400
        
        db = get_db()
        query = """
            INSERT INTO feedbacks (empresa_id, usuario_id, nota, recomendaria, sugestao)
            VALUES (%s, %s, %s, %s, %s)
        """
        db.execute(query, (
            session['usuario']['empresa_id'],
            session['usuario']['id'],
            nota,
            recomendaria,
            sugestao[:500]
        ))
        
        session['feedback_enviado'] = True
        app.logger.info(f"Feedback recebido do usuário {session['usuario']['id']}: {nota} estrelas")
        
        return jsonify({'sucesso': True})
        
    except Exception as e:
        app.logger.error(f"Erro ao processar feedback: {e}")
        return jsonify({'sucesso': False, 'erro': 'Erro interno'}), 500

# =====================================================
# HANDLERS DE ERRO PERSONALIZADOS
# =====================================================

@app.errorhandler(404)
def pagina_nao_encontrada(e):
    """Página 404 personalizada"""
    app.logger.warning(f"Página não encontrada: {request.path} - IP: {request.remote_addr}")
    return render_template('erros/404.html'), 404

@app.errorhandler(403)
def acesso_negado(e):
    """Página 403 personalizada"""
    app.logger.warning(f"Acesso negado: {request.path} - IP: {request.remote_addr}")
    return render_template('erros/403.html'), 403

@app.errorhandler(500)
def erro_interno(e):
    """Página 500 personalizada"""
    app.logger.error(f"Erro interno: {str(e)} - IP: {request.remote_addr}")
    return render_template('erros/500.html'), 500

# =====================================================
# TEARDOWN DO BANCO DE DADOS
# =====================================================

@app.teardown_appcontext
def teardown_db(exception):
    """Fecha conexão com o banco"""
    close_db(exception)

# =====================================================
# INICIALIZAÇÃO
# =====================================================

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=5000)