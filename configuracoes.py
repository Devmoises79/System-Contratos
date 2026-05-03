from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth.permissoes import login_required
from models.usuario import Usuario
from core.database import Database
from core.hash_utils import hash_manager

config_bp = Blueprint('configuracoes', __name__, url_prefix='/configuracoes')


@config_bp.route('/')
@login_required
def index():
    """Página principal de configurações"""
    usuario_id = session['usuario']['id']
    usuario = Usuario.get_by_id(usuario_id)
    
    # Buscar preferências do usuário
    prefs = Database.fetch_one(
        "SELECT notificacao_som, tema FROM usuarios WHERE id = %s",
        (usuario_id,)
    )
    
    return render_template('configuracoes/index.html', 
                         usuario=usuario,
                         notificacao_som=prefs.get('notificacao_som', 1) if prefs else 1,
                         tema=prefs.get('tema', 'claro') if prefs else 'claro')


@config_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    """Edição de perfil do usuário"""
    usuario_id = session['usuario']['id']
    usuario = Usuario.get_by_id(usuario_id)
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        
        # Verificar se email já existe para outro usuário
        existing = Database.fetch_one(
            "SELECT id FROM usuarios WHERE email = %s AND id != %s",
            (email, usuario_id)
        )
        if existing:
            flash('Este email já está cadastrado para outro usuário.', 'danger')
            return redirect(url_for('configuracoes.perfil'))
        
        Database.execute(
            "UPDATE usuarios SET nome = %s, email = %s WHERE id = %s",
            (nome, email, usuario_id)
        )
        
        # Atualizar sessão
        session['usuario']['nome'] = nome
        session['usuario']['email'] = email
        
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('configuracoes.perfil'))
    
    return render_template('configuracoes/perfil.html', usuario=usuario)


@config_bp.route('/seguranca', methods=['GET', 'POST'])
@login_required
def seguranca():
    """Alteração de senha e segurança"""
    usuario_id = session['usuario']['id']
    
    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        # Validar senha atual
        usuario = Usuario.get_by_id(usuario_id)
        if not usuario.verificar_senha(senha_atual):
            flash('Senha atual incorreta.', 'danger')
            return redirect(url_for('configuracoes.seguranca'))
        
        # Validar nova senha
        if len(nova_senha) < 8:
            flash('A nova senha deve ter no mínimo 8 caracteres.', 'danger')
            return redirect(url_for('configuracoes.seguranca'))
        
        if nova_senha != confirmar_senha:
            flash('As senhas não conferem.', 'danger')
            return redirect(url_for('configuracoes.seguranca'))
        
        # Atualizar senha
        usuario.set_senha(nova_senha)
        usuario.save()
        
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('configuracoes.seguranca'))
    
    return render_template('configuracoes/seguranca.html')


@config_bp.route('/preferencias', methods=['GET', 'POST'])
@login_required
def preferencias():
    """Preferências de notificações"""
    usuario_id = session['usuario']['id']
    
    if request.method == 'POST':
        som_ativado = 1 if request.form.get('som_ativado') == 'on' else 0
        email_notif = 1 if request.form.get('email_notif') == 'on' else 0
        
        Database.execute("""
            UPDATE usuarios 
            SET notificacao_som = %s, notificacao_email = %s 
            WHERE id = %s
        """, (som_ativado, email_notif, usuario_id))
        
        flash('Preferências salvas com sucesso!', 'success')
        return redirect(url_for('configuracoes.preferencias'))
    
    prefs = Database.fetch_one(
        "SELECT notificacao_som, notificacao_email FROM usuarios WHERE id = %s",
        (usuario_id,)
    )
    
    return render_template('configuracoes/preferencias.html', 
                         som_ativado=prefs.get('notificacao_som', 1) if prefs else 1,
                         email_notif=prefs.get('notificacao_email', 1) if prefs else 1)


@config_bp.route('/aparencia', methods=['GET', 'POST'])
@login_required
def aparencia():
    """Configurações de aparência e tema"""
    usuario_id = session['usuario']['id']
    
    if request.method == 'POST':
        tema = request.form.get('tema', 'claro')
        
        Database.execute(
            "UPDATE usuarios SET tema = %s WHERE id = %s",
            (tema, usuario_id)
        )
        
        flash('Aparência atualizada com sucesso!', 'success')
        return redirect(url_for('configuracoes.aparencia'))
    
    prefs = Database.fetch_one("SELECT tema FROM usuarios WHERE id = %s", (usuario_id,))
    tema_atual = prefs.get('tema', 'claro') if prefs else 'claro'
    
    return render_template('configuracoes/aparencia.html', tema_atual=tema_atual)