from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth.permissoes import admin_empresa_required, login_required, get_empresa_id
from models.cliente import Cliente
from core.logging_config import logger

clientes_bp = Blueprint('admin_clientes', __name__, url_prefix='/admin/empresa/clientes')


@clientes_bp.route('/')
@login_required
@admin_empresa_required
def index():
    """Lista de clientes"""
    empresa_id = get_empresa_id()
    
    ativo = request.args.get('ativo')
    if ativo == 'inativos':
        clientes = Cliente.listar_por_empresa(empresa_id, ativo=False)
        titulo = "Clientes Inativos"
    else:
        clientes = Cliente.listar_por_empresa(empresa_id, ativo=True)
        titulo = "Clientes Ativos"
    
    return render_template('admin/empresa/clientes/index.html', 
                         clientes=clientes,
                         titulo=titulo,
                         filtro_ativo=ativo)


@clientes_bp.route('/novo', methods=['GET', 'POST'])
@login_required
@admin_empresa_required
def novo():
    """Cadastrar novo cliente"""
    empresa_id = get_empresa_id()
    
    if request.method == 'POST':
        try:
            cliente = Cliente(
                empresa_id=empresa_id,
                nome=request.form.get('nome'),
                documento=request.form.get('documento'),
                email=request.form.get('email'),
                telefone=request.form.get('telefone'),
                endereco=request.form.get('endereco'),
                contato_nome=request.form.get('contato_nome'),
                contato_telefone=request.form.get('contato_telefone'),
                contato_email=request.form.get('contato_email'),
                ativo=1 if request.form.get('ativo') == 'on' else 1,
                observacoes=request.form.get('observacoes')
            )
            cliente.save()
            flash('Cliente cadastrado com sucesso!', 'success')
            return redirect(url_for('admin_clientes.index'))
        except Exception as e:
            logger.error(f"Erro ao cadastrar cliente: {e}")
            flash('Erro ao cadastrar cliente.', 'danger')
    
    return render_template('admin/empresa/clientes/form.html', cliente=None)


@clientes_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_empresa_required
def editar(id):
    """Editar cliente"""
    empresa_id = get_empresa_id()
    cliente = Cliente.get_by_id(id, empresa_id)
    
    if not cliente:
        flash('Cliente não encontrado.', 'danger')
        return redirect(url_for('admin_clientes.index'))
    
    if request.method == 'POST':
        try:
            cliente.nome = request.form.get('nome')
            cliente.documento = request.form.get('documento')
            cliente.email = request.form.get('email')
            cliente.telefone = request.form.get('telefone')
            cliente.endereco = request.form.get('endereco')
            cliente.contato_nome = request.form.get('contato_nome')
            cliente.contato_telefone = request.form.get('contato_telefone')
            cliente.contato_email = request.form.get('contato_email')
            cliente.ativo = 1 if request.form.get('ativo') == 'on' else 0
            cliente.observacoes = request.form.get('observacoes')
            cliente.save()
            flash('Cliente atualizado com sucesso!', 'success')
            return redirect(url_for('admin_clientes.detalhe', id=cliente.id))
        except Exception as e:
            logger.error(f"Erro ao atualizar cliente: {e}")
            flash('Erro ao atualizar cliente.', 'danger')
    
    return render_template('admin/empresa/clientes/form.html', cliente=cliente)


@clientes_bp.route('/detalhe/<int:id>')
@login_required
@admin_empresa_required
def detalhe(id):
    """Detalhes do cliente"""
    empresa_id = get_empresa_id()
    cliente = Cliente.get_by_id(id, empresa_id)
    
    if not cliente:
        flash('Cliente não encontrado.', 'danger')
        return redirect(url_for('admin_clientes.index'))
    
    # Buscar contratos do cliente
    contratos = Cliente.get_contratos(id, empresa_id)
    total_contratos = cliente.get_contratos_count()
    valor_total = cliente.get_valor_total_contratos()
    
    return render_template('admin/empresa/clientes/detalhe.html', 
                         cliente=cliente,
                         contratos=contratos,
                         total_contratos=total_contratos,
                         valor_total=valor_total)


@clientes_bp.route('/ativar/<int:id>')
@login_required
@admin_empresa_required
def ativar(id):
    """Ativar cliente"""
    empresa_id = get_empresa_id()
    cliente = Cliente.get_by_id(id, empresa_id)
    
    if not cliente:
        flash('Cliente não encontrado.', 'danger')
    else:
        cliente.ativar()
        flash(f'Cliente {cliente.nome} ativado com sucesso!', 'success')
    
    return redirect(url_for('admin_clientes.index'))


@clientes_bp.route('/desativar/<int:id>')
@login_required
@admin_empresa_required
def desativar(id):
    """Desativar cliente"""
    empresa_id = get_empresa_id()
    cliente = Cliente.get_by_id(id, empresa_id)
    
    if not cliente:
        flash('Cliente não encontrado.', 'danger')
    else:
        if cliente.get_contratos_count() > 0:
            flash(f'Não é possível desativar o cliente {cliente.nome} pois ele possui contratos vinculados.', 'warning')
        else:
            cliente.delete()
            flash(f'Cliente {cliente.nome} desativado com sucesso!', 'success')
    
    return redirect(url_for('admin_clientes.index'))


@clientes_bp.route('/buscar')
@login_required
@admin_empresa_required
def buscar():
    """API de busca de clientes (para autocomplete)"""
    empresa_id = get_empresa_id()
    termo = request.args.get('term', '')
    
    if len(termo) < 2:
        return []
    
    clientes = Cliente.buscar(empresa_id, termo)
    
    return [{
        'id': c.id,
        'nome': c.nome,
        'documento': c.documento,
        'email': c.email,
        'telefone': c.telefone
    } for c in clientes]