# admin/empresa.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session
from auth.permissoes import admin_empresa_required, login_required
from models.empresa import Empresa
from models.usuario import Usuario
from models.contrato import Contrato
from core.database import Database
import os
from werkzeug.utils import secure_filename
from core.utils import gerar_nome_arquivo_seguro

admin_empresa_bp = Blueprint('admin_empresa', __name__, url_prefix='/admin/empresa')

@admin_empresa_bp.route('/')
@admin_empresa_required
def dashboard():
    """Dashboard do admin da empresa"""
    empresa_id = session['usuario']['empresa_id']
    empresa = Empresa.get_by_id(empresa_id)
    
    # Estatísticas da empresa
    stats = Contrato.estatisticas(empresa_id)
    
    # Últimos contratos
    contratos = Contrato.listar_por_empresa(empresa_id)[:10]
    
    # Usuários da empresa
    usuarios = Usuario.listar_por_empresa(empresa_id)
    
    return render_template('admin/empresa/dashboard.html',
                         empresa=empresa,
                         stats=stats,
                         contratos=contratos,
                         usuarios=usuarios)

@admin_empresa_bp.route('/configuracoes', methods=['GET', 'POST'])
@admin_empresa_required
def configuracoes():
    """Configurações da empresa"""
    empresa_id = session['usuario']['empresa_id']
    empresa = Empresa.get_by_id(empresa_id)
    
    if request.method == 'POST':
        # Dados básicos
        empresa.nome = request.form.get('nome', empresa.nome)
        empresa.email = request.form.get('email', empresa.email)
        empresa.telefone = request.form.get('telefone', empresa.telefone)
        empresa.celular = request.form.get('celular', empresa.celular)
        empresa.endereco = request.form.get('endereco', empresa.endereco)
        
        # Cores
        cores = {
            'primaria': request.form.get('cor_primaria', empresa.paleta_cores.get('primaria')),
            'secundaria': request.form.get('cor_secundaria', empresa.paleta_cores.get('secundaria')),
            'destaque': request.form.get('cor_destaque', empresa.paleta_cores.get('destaque')),
            'texto': request.form.get('cor_texto', empresa.paleta_cores.get('texto')),
            'fundo': request.form.get('cor_fundo', empresa.paleta_cores.get('fundo'))
        }
        empresa.paleta_cores = cores
        
        # Upload de logo
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename:
                filename = secure_filename(file.filename)
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                if ext in {'png', 'jpg', 'jpeg', 'gif'}:
                    novo_nome = gerar_nome_arquivo_seguro(filename)
                    os.makedirs('static/uploads/logos', exist_ok=True)
                    file.save(os.path.join('static/uploads/logos', novo_nome))
                    empresa.logo_path = f'static/uploads/logos/{novo_nome}'
        
        empresa.save()
        
        # Atualiza sessão com novas cores
        session['empresa']['cores'] = cores
        session['empresa']['logo'] = empresa.logo_path
        
        flash('Configurações atualizadas com sucesso!', 'success')
        return redirect(url_for('admin_empresa.configuracoes'))
    
    return render_template('admin/empresa/configuracoes.html', empresa=empresa)

@admin_empresa_bp.route('/usuarios')
@admin_empresa_required
def usuarios():
    """Lista usuários da empresa"""
    empresa_id = session['usuario']['empresa_id']
    usuarios = Usuario.listar_por_empresa(empresa_id)
    return render_template('admin/empresa/usuarios.html', usuarios=usuarios)

@admin_empresa_bp.route('/usuario/novo', methods=['GET', 'POST'])
@admin_empresa_required
def usuario_novo():
    """Cria novo usuário"""
    empresa_id = session['usuario']['empresa_id']
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        perfil = request.form.get('perfil')
        senha = request.form.get('senha')
        
        if not nome or not email or not perfil or not senha:
            flash('Todos os campos são obrigatórios', 'danger')
            return redirect(url_for('admin_empresa.usuario_novo'))
        
        # Verifica se email já existe
        if Usuario.get_by_email(email):
            flash('Email já cadastrado', 'danger')
            return redirect(url_for('admin_empresa.usuario_novo'))
        
        usuario = Usuario(
            empresa_id=empresa_id,
            nome=nome,
            email=email,
            perfil=perfil,
            cargo=request.form.get('cargo'),
            telefone=request.form.get('telefone'),
            celular=request.form.get('celular'),
            email_corporativo=request.form.get('email_corporativo'),
            ativo=True,
            primeiro_acesso=True
        )
        
        usuario.definir_senha(senha)
        usuario.save()
        
        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('admin_empresa.usuarios'))
    
    return render_template('admin/empresa/usuario_form.html')

@admin_empresa_bp.route('/usuario/<int:id>/editar', methods=['GET', 'POST'])
@admin_empresa_required
def usuario_editar(id):
    """Edita usuário"""
    empresa_id = session['usuario']['empresa_id']
    usuario = Usuario.get_by_id(id)
    
    if not usuario or usuario.empresa_id != empresa_id:
        flash('Usuário não encontrado', 'danger')
        return redirect(url_for('admin_empresa.usuarios'))
    
    if request.method == 'POST':
        usuario.nome = request.form.get('nome', usuario.nome)
        usuario.cargo = request.form.get('cargo', usuario.cargo)
        usuario.telefone = request.form.get('telefone', usuario.telefone)
        usuario.celular = request.form.get('celular', usuario.celular)
        usuario.email_corporativo = request.form.get('email_corporativo', usuario.email_corporativo)
        
        # Atualiza senha se fornecida
        nova_senha = request.form.get('senha')
        if nova_senha:
            usuario.definir_senha(nova_senha)
        
        usuario.save()
        
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('admin_empresa.usuarios'))
    
    return render_template('admin/empresa/usuario_form.html', usuario=usuario)

@admin_empresa_bp.route('/usuario/<int:id>/toggle-status')
@admin_empresa_required
def usuario_toggle_status(id):
    """Ativa/desativa usuário"""
    empresa_id = session['usuario']['empresa_id']
    usuario = Usuario.get_by_id(id)
    
    if usuario and usuario.empresa_id == empresa_id:
        usuario.ativo = not usuario.ativo
        usuario.save()
        status = 'ativado' if usuario.ativo else 'desativado'
        flash(f'Usuário {status} com sucesso!', 'success')
    else:
        flash('Usuário não encontrado', 'danger')
    
    return redirect(url_for('admin_empresa.usuarios'))

@admin_empresa_bp.route('/estatisticas')
@admin_empresa_required
def estatisticas():
    """Estatísticas detalhadas da empresa"""
    empresa_id = session['usuario']['empresa_id']
    
    stats = Contrato.estatisticas(empresa_id)
    
    # Contratos por status
    db = Database()
    por_status = db.fetch_all("""
        SELECT status, COUNT(*) as quantidade, SUM(valor) as valor_total
        FROM contratos
        WHERE empresa_id = %s
        GROUP BY status
    """, (empresa_id,))
    
    return render_template('admin/empresa/estatisticas.html',
                         stats=stats,
                         por_status=por_status)