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

# CORREÇÃO: Registrar a função, NÃO o resultado da função
app.jinja_env.globals['csrf_token'] = gerar_csrf_token

def validar_csrf_token(token):
    """Valida token CSRF"""
    token_sessao = session.pop('_csrf_token', None)
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

def sanitizar_entrada(dados):
    """Sanitiza entradas para evitar XSS"""
    if isinstance(dados, str):
        return html.escape(dados.strip())
    elif isinstance(dados, dict):
        return {k: sanitizar_entrada(v) for k, v in dados.items()}
    elif isinstance(dados, list):
        return [sanitizar_entrada(item) for item in dados]
    return dados

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
    """Decorator que adiciona camada extra de proteção SQL Injection"""
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
            
            # Aqui você pode salvar no banco se desejar
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
        senha = request.form.get('senha', '')  # Não sanitizar senha
        lembrar = request.form.get('lembrar') == 'on'
        
        # Validação básica
        if not email or not senha:
            flash('Email e senha são obrigatórios.', 'danger')
            return render_template('login.html')
        
        # Valida formato do email
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            flash('Formato de email inválido.', 'danger')
            return render_template('login.html')
        
        sucesso, resultado = LoginManager.login(email, senha, lembrar)
        
        if sucesso:
            # Gera novo CSRF token para a sessão
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
            token = usuario.gerar_token_recuperacao()
            # Aqui você enviaria email com link
            # link = url_for('redefinir_senha', token=token, _external=True)
            app.logger.info(f"Token de recuperação gerado para: {email}")
            flash('Instruções enviadas para seu email.', 'success')
        else:
            # Mensagem genérica por segurança
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
        
        # Validações de senha forte
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


# app.py - Substitua a rota de cadastro existente por esta:

@app.route('/cadastro', methods=['GET', 'POST'])
@ip_bloqueado_verificado
@xss_protegido
@sql_injection_protegido
def cadastro_usuario():
    """Página pública de cadastro de usuário"""
    from models.empresa import Empresa
    from core.database import Database
    
    # Busca ramos de atividade do banco
    db = Database()
    ramos = db.fetch_all("SELECT id, nome, descricao FROM ramos_atividade WHERE ativo = TRUE ORDER BY nome")
    
    if request.method == 'POST':
        nome = sanitizar_entrada(request.form.get('nome', ''))
        email = sanitizar_entrada(request.form.get('email', ''))
        senha = request.form.get('senha', '')
        confirmar_senha = request.form.get('confirmar_senha', '')
        empresa_nome = sanitizar_entrada(request.form.get('empresa_nome', ''))
        empresa_cnpj = apenas_digitos(request.form.get('empresa_cnpj', ''))
        ramo_id = request.form.get('ramo_id', '')
        novo_ramo = sanitizar_entrada(request.form.get('novo_ramo', ''))
        
        # Validações
        if not nome or not email or not senha or not empresa_nome:
            flash('Todos os campos obrigatórios devem ser preenchidos.', 'danger')
            return render_template('admin/empresa/usuario_form.html', cadastro_publico=True, ramos=ramos)
        
        if senha != confirmar_senha:
            flash('As senhas não conferem.', 'danger')
            return render_template('admin/empresa/usuario_form.html', cadastro_publico=True, ramos=ramos)
        
        # Valida força da senha
        if len(senha) < 8:
            flash('A senha deve ter no mínimo 8 caracteres.', 'danger')
            return render_template('admin/empresa/usuario_form.html', cadastro_publico=True, ramos=ramos)
        
        # Verifica se email já existe
        if Usuario.get_by_email(email):
            flash('Este email já está cadastrado.', 'danger')
            return render_template('admin/empresa/usuario_form.html', cadastro_publico=True, ramos=ramos)
        
        try:
            # Se usuário escolheu "Outro" e preencheu novo ramo
            if ramo_id == 'outro' and novo_ramo:
                # Insere novo ramo no banco
                query = "INSERT INTO ramos_atividade (nome, descricao, ativo) VALUES (%s, %s, TRUE)"
                ramo_id = db.execute_return_id(query, (novo_ramo, f"Ramo cadastrado por {empresa_nome}"))
                app.logger.info(f"Novo ramo cadastrado: {novo_ramo}")
            
            # Cria a empresa
            empresa = Empresa(
                nome=empresa_nome,
                cnpj=empresa_cnpj if empresa_cnpj else None,
                email=email,
                status='trial'
            )
            empresa.save()
            
            # Registra o ramo da empresa (se selecionado)
            if ramo_id and ramo_id != 'outro':
                # Aqui você pode criar uma relação empresa-ramo se tiver essa tabela
                # Por enquanto, vamos apenas logar
                app.logger.info(f"Empresa {empresa.id} associada ao ramo {ramo_id}")
            
            # Cria o usuário como admin da empresa
            usuario = Usuario(
                empresa_id=empresa.id,
                nome=nome,
                email=email,
                perfil='admin_empresa',
                ativo=True,
                primeiro_acesso=False  # Já vai definir a senha agora
            )
            usuario.definir_senha(senha)
            usuario.save()
            
            app.logger.info(f"Novo cadastro: {email} - Empresa: {empresa_nome}")
            flash('Cadastro realizado com sucesso! Faça o login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            app.logger.error(f"Erro no cadastro: {str(e)}")
            flash('Erro ao realizar cadastro. Tente novamente.', 'danger')
            return render_template('admin/empresa/usuario_form.html', cadastro_publico=True, ramos=ramos)
    
    # GET - exibe formulário de cadastro com os ramos
    return render_template('admin/empresa/usuario_form.html', cadastro_publico=True, ramos=ramos)
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
    
    # Estatísticas
    stats = Contrato.estatisticas(empresa_id)
    
    # Contratos pendentes de aprovação
    contratos_pendentes = Contrato.listar_por_empresa(empresa_id, 'rascunho')
    
    return render_template('dashboard/gestor.html',
                         stats=stats,
                         contratos_pendentes=contratos_pendentes)

@app.route('/dashboard/assistente')
@rota_protegida('assistente', 'gestor', 'admin_empresa', 'admin_sistema')
def assistente_dashboard():
    """Dashboard do assistente"""
    empresa_id = session['usuario']['empresa_id']
    
    # Meus contratos
    db = get_db()
    meus_contratos = db.fetch_all("""
        SELECT * FROM contratos 
        WHERE empresa_id = %s AND criado_por = %s
        ORDER BY data_criacao DESC
        LIMIT 10
    """, (empresa_id, session['usuario']['id']))
    
    return render_template('dashboard/assistente.html', contratos=meus_contratos)

@app.route('/dashboard/analista')
@rota_protegida('analista', 'gestor', 'admin_empresa', 'admin_sistema')
def analista_dashboard():
    """Dashboard do analista"""
    empresa_id = session['usuario']['empresa_id']
    
    # Estatísticas completas
    stats = Contrato.estatisticas(empresa_id)
    
    return render_template('dashboard/analista.html', stats=stats)

# =====================================================
# ROTAS DE CONTRATOS (PROTEGIDAS)
# =====================================================

@app.route('/contratos')
@rota_protegida('gestor', 'assistente', 'admin_empresa', 'admin_sistema')
def listar_contratos():
    """Lista contratos da empresa"""
    empresa_id = session['usuario']['empresa_id']
    status = sanitizar_entrada(request.args.get('status', ''))
    
    contratos = Contrato.listar_por_empresa(empresa_id, status if status else None)
    
    return render_template('contratos/listar.html', contratos=contratos)

@app.route('/contrato/novo', methods=['GET', 'POST'])
@rota_protegida('gestor', 'assistente', 'admin_empresa', 'admin_sistema')
def contrato_novo():
    """Cria novo contrato"""
    if request.method == 'POST':
        # Sanitiza todas as entradas
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
        
        # Validações
        if not dados['contratante_nome'] or not dados['contratada_nome']:
            flash('Nome do contratante e contratada são obrigatórios.', 'danger')
            return redirect(url_for('contrato_novo'))
        
        if not dados['valor'] or float(dados['valor']) <= 0:
            flash('Valor deve ser maior que zero.', 'danger')
            return redirect(url_for('contrato_novo'))
        
        if not dados['prazo_dias'] or int(dados['prazo_dias']) <= 0:
            flash('Prazo deve ser maior que zero.', 'danger')
            return redirect(url_for('contrato_novo'))
        
        # Cria contrato
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
        
        # Registra log
        app.logger.info(f"Novo contrato criado: {contrato.numero_contrato} por usuário {session['usuario']['id']}")
        
        flash('Contrato criado com sucesso!', 'success')
        return redirect(url_for('listar_contratos'))
    
    return render_template('contratos/novo.html')

@app.route('/contrato/<int:id>')
@rota_protegida('gestor', 'assistente', 'analista', 'admin_empresa', 'admin_sistema')
def ver_contrato(id):
    """Visualiza contrato"""
    contrato = Contrato.get_by_id(id)
    
    if not contrato or contrato.empresa_id != session['usuario']['empresa_id']:
        flash('Contrato não encontrado', 'danger')
        return redirect(url_for('listar_contratos'))
    
    return render_template('contratos/detalhe.html', contrato=contrato)

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
            sugestao[:500]  # Limita tamanho
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

@app.errorhandler(429)
def many_requests(e):
    """Muitas requisições"""
    return render_template('erros/429.html'), 429

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
    # Modo debug apenas em desenvolvimento
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=5000)