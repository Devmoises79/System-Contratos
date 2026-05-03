# routes/contratos.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_file, session
from models.empresa import Empresa
from models.usuario import Usuario
from models.contrato import Contrato
from core.database import Database
from auth.permissoes import login_required, perfil_required, pode_criar_contrato, pode_editar_contrato
from utils.gerador_pdf import gerar_pdf_contrato
from services.contrato_service import ContratoService
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

contratos_bp = Blueprint('contratos', __name__, url_prefix='/contratos')


@contratos_bp.route('/')
@login_required
def listar():
    """Lista contratos do usuário"""
    usuario_perfil = session['usuario']['perfil']
    usuario_empresa_id = session['usuario'].get('empresa_id')
    usuario_id = session['usuario']['id']
    
    if usuario_perfil == 'admin_sistema':
        contratos = Contrato.listar_todos()
    elif usuario_perfil == 'admin_empresa':
        contratos = Contrato.listar_por_empresa(usuario_empresa_id)
    elif usuario_perfil == 'analista':
        # Analista vê contratos em análise e pendentes
        contratos = Contrato.listar_em_analise(usuario_empresa_id)
        contratos += Contrato.listar_pendentes_aprovacao(usuario_empresa_id)
    else:
        # Assistente vê apenas seus rascunhos
        contratos = Contrato.listar_por_criador(usuario_id)
    
    return render_template('contratos/listar.html', contratos=contratos)


@contratos_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    """Criar novo contrato"""
    if not pode_criar_contrato():
        flash('Você não tem permissão para criar contratos.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Pega empresa_id (admin-sistema pode escolher, outros usam a própria)
            empresa_id = session['usuario'].get('empresa_id')
            if session['usuario']['perfil'] == 'admin_sistema' and request.form.get('empresa_id'):
                empresa_id = int(request.form.get('empresa_id'))
            
            # Processa datas
            data_inicio = request.form.get('data_inicio')
            data_fim = request.form.get('data_fim')
            prazo_dias = request.form.get('prazo_dias', type=int)
            
            # Se não tem data_fim mas tem prazo_dias e data_inicio, calcula
            if not data_fim and prazo_dias and data_inicio:
                from datetime import timedelta
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                data_fim = (data_inicio_obj + timedelta(days=prazo_dias)).isoformat()
            
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
                criado_por=session['usuario']['id'],
                status='rascunho'
            )
            
            contrato.save()
            flash('Contrato criado com sucesso!', 'success')
            return redirect(url_for('contratos.detalhe', contrato_id=contrato.id))
            
        except Exception as e:
            logger.error(f"Erro ao criar contrato: {e}")
            flash('Erro ao criar contrato', 'danger')
    
    # Busca empresas para o select (admin-sistema)
    empresas = []
    if session['usuario']['perfil'] == 'admin_sistema':
        empresas = Empresa.listar_todas()
    
    return render_template('contratos/novo.html', empresas=empresas)


@contratos_bp.route('/<int:contrato_id>')
@login_required
def detalhe(contrato_id):
    """Detalhe do contrato"""
    contrato = Contrato.get_by_id(contrato_id)
    
    if not contrato:
        abort(404)
    
    # Verifica permissão
    usuario_perfil = session['usuario']['perfil']
    usuario_empresa_id = session['usuario'].get('empresa_id')
    
    if usuario_perfil != 'admin_sistema' and contrato.empresa_id != usuario_empresa_id:
        abort(403)
    
    # Lógica de transição automática (analista vê rascunho -> vira em análise)
    if usuario_perfil == 'analista' and contrato.status == 'rascunho':
        contrato.status = 'em_analise'
        contrato.atualizado_por = session['usuario']['id']
        contrato.save()
        from models.notificacao import SistemaNotificacoes
        usuario_atual = Usuario.get_by_id(session['usuario']['id'])
        SistemaNotificacoes.notificar_contrato_em_analise(contrato, usuario_atual)
        flash('Contrato agora está em análise!', 'info')
    
    dias_restantes = contrato.get_dias_restantes()
    
    return render_template('contratos/detalhe.html', contrato=contrato, dias_restantes=dias_restantes)


@contratos_bp.route('/<int:contrato_id>/editar', methods=['GET', 'POST'])
@login_required
def editar(contrato_id):
    """Editar contrato"""
    contrato = Contrato.get_by_id(contrato_id)
    
    if not contrato:
        abort(404)
    
    # Verifica permissão
    usuario_perfil = session['usuario']['perfil']
    usuario_empresa_id = session['usuario'].get('empresa_id')
    usuario_id = session['usuario']['id']
    
    if usuario_perfil != 'admin_sistema' and contrato.empresa_id != usuario_empresa_id:
        abort(403)
    
    # Verifica se pode editar baseado no perfil e status
    pode_editar = False
    
    if usuario_perfil in ['admin_sistema', 'admin_empresa']:
        pode_editar = True
    elif usuario_perfil == 'gestor' and contrato.status in ['rascunho', 'em_analise']:
        pode_editar = True
    elif usuario_perfil == 'analista' and contrato.status in ['rascunho', 'em_analise']:
        pode_editar = True
    elif usuario_perfil == 'assistente' and contrato.status == 'rascunho' and contrato.criado_por == usuario_id:
        pode_editar = True
    
    if not pode_editar:
        flash('Você não tem permissão para editar este contrato.', 'danger')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    if request.method == 'POST':
        try:
            contrato.contratante_nome = request.form.get('contratante_nome')
            contrato.contratante_cnpj = request.form.get('contratante_cnpj')
            contrato.contratante_email = request.form.get('contratante_email')
            contrato.contratante_telefone = request.form.get('contratante_telefone')
            contrato.contratada_nome = request.form.get('contratada_nome')
            contrato.contratada_cnpj = request.form.get('contratada_cnpj')
            contrato.contratada_email = request.form.get('contratada_email')
            contrato.valor = request.form.get('valor')
            contrato.prazo_dias = request.form.get('prazo_dias', type=int)
            contrato.data_inicio = request.form.get('data_inicio')
            contrato.data_fim = request.form.get('data_fim')
            contrato.descricao = request.form.get('descricao')
            contrato.atualizado_por = session['usuario']['id']
            
            contrato.save()
            flash('Contrato atualizado com sucesso!', 'success')
            return redirect(url_for('contratos.detalhe', contrato_id=contrato.id))
            
        except Exception as e:
            logger.error(f"Erro ao editar contrato: {e}")
            flash('Erro ao editar contrato', 'danger')
    
    return render_template('contratos/editar.html', contrato=contrato)


@contratos_bp.route('/<int:contrato_id>/enviar-analista', methods=['POST'])
@login_required
def enviar_para_analista(contrato_id):
    """Enviar contrato para análise (Assistente -> Analista)"""
    contrato = Contrato.get_by_id(contrato_id)
    
    if not contrato:
        abort(404)
    
    # Verifica permissão: apenas assistente ou admin
    usuario_perfil = session['usuario']['perfil']
    usuario_id = session['usuario']['id']
    
    if usuario_perfil not in ['assistente', 'admin_empresa', 'admin_sistema']:
        flash('Apenas assistentes podem enviar contratos para análise.', 'danger')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    # Assistente só pode enviar seus próprios contratos
    if usuario_perfil == 'assistente' and contrato.criado_por != usuario_id:
        flash('Você só pode enviar seus próprios contratos.', 'danger')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    if contrato.status != 'rascunho':
        flash('Este contrato não está em rascunho e não pode ser enviado.', 'warning')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    contrato.enviar_para_analista(session['usuario']['id'])
    flash('Contrato enviado para análise!', 'success')
    return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))


@contratos_bp.route('/<int:contrato_id>/enviar-gestor', methods=['POST'])
@login_required
def enviar_para_gestor(contrato_id):
    """Enviar contrato para gestor (Analista -> Gestor)"""
    contrato = Contrato.get_by_id(contrato_id)
    
    if not contrato:
        abort(404)
    
    # Verifica permissão: apenas analista
    usuario_perfil = session['usuario']['perfil']
    
    if usuario_perfil != 'analista':
        flash('Apenas analistas podem enviar contratos para o gestor.', 'danger')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    if contrato.status != 'em_analise':
        flash('Este contrato não está em análise.', 'warning')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    contrato.enviar_para_gestor(session['usuario']['id'])
    flash('Contrato enviado para aprovação do gestor!', 'success')
    return redirect(url_for('dashboard_analista'))


@contratos_bp.route('/<int:contrato_id>/aprovar', methods=['POST'])
@login_required
def aprovar(contrato_id):
    """Aprovar contrato (Gestor -> Ativo)"""
    contrato = Contrato.get_by_id(contrato_id)
    
    if not contrato:
        abort(404)
    
    # Verifica permissão: apenas gestor ou admin
    usuario_perfil = session['usuario']['perfil']
    
    if usuario_perfil not in ['gestor', 'admin_empresa', 'admin_sistema']:
        flash('Apenas gestores podem aprovar contratos.', 'danger')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    if contrato.status != 'aguardando_aprovacao':
        flash('Este contrato não está aguardando aprovação.', 'warning')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    contrato.aprovar(session['usuario']['id'])
    flash('Contrato aprovado com sucesso!', 'success')
    return redirect(url_for('dashboard_gestor'))


@contratos_bp.route('/<int:contrato_id>/devolver-analista', methods=['POST'])
@login_required
def devolver_para_analista(contrato_id):
    """Devolver contrato para análise (Gestor -> Analista)"""
    contrato = Contrato.get_by_id(contrato_id)
    
    if not contrato:
        abort(404)
    
    usuario_perfil = session['usuario']['perfil']
    
    if usuario_perfil not in ['gestor', 'admin_empresa', 'admin_sistema']:
        flash('Apenas gestores podem devolver contratos.', 'danger')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    if contrato.status != 'aguardando_aprovacao':
        flash('Este contrato não está aguardando aprovação.', 'warning')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    motivo = request.form.get('motivo', '')
    if not motivo:
        flash('É obrigatório informar um motivo para a devolução.', 'danger')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    contrato.devolver_para_analista(session['usuario']['id'], motivo)
    flash('Contrato devolvido para análise do analista.', 'warning')
    return redirect(url_for('dashboard_gestor'))


@contratos_bp.route('/<int:contrato_id>/devolver-assistente', methods=['POST'])
@login_required
def devolver_para_assistente(contrato_id):
    """Devolver contrato para assistente (Analista -> Assistente)"""
    contrato = Contrato.get_by_id(contrato_id)
    
    if not contrato:
        abort(404)
    
    usuario_perfil = session['usuario']['perfil']
    
    if usuario_perfil not in ['analista', 'admin_empresa', 'admin_sistema']:
        flash('Apenas analistas podem devolver contratos para assistente.', 'danger')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    if contrato.status != 'em_analise':
        flash('Este contrato não está em análise.', 'warning')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    motivo = request.form.get('motivo', '')
    if not motivo:
        flash('É obrigatório informar um motivo para a devolução.', 'danger')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    contrato.devolver_para_assistente(session['usuario']['id'], motivo)
    flash('Contrato devolvido para o assistente revisar.', 'warning')
    return redirect(url_for('dashboard_analista'))


@contratos_bp.route('/<int:contrato_id>/download')
@login_required
def download_pdf(contrato_id):
    """Download do PDF do contrato"""
    contrato = Contrato.get_by_id(contrato_id)
    
    if not contrato:
        abort(404)
    
    # Verifica permissão
    usuario_perfil = session['usuario']['perfil']
    usuario_empresa_id = session['usuario'].get('empresa_id')
    
    if usuario_perfil != 'admin_sistema' and contrato.empresa_id != usuario_empresa_id:
        abort(403)
    
    pdf_filename = f'contrato_{contrato.numero_contrato}.pdf'
    pdf_path = os.path.join('static', 'uploads', 'contratos', pdf_filename).replace('\\', '/')
    
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True, download_name=pdf_filename, mimetype='application/pdf')
    
    # Tenta gerar o PDF
    try:
        novo_pdf = gerar_pdf_contrato(contrato)
        if novo_pdf and os.path.exists(novo_pdf):
            novo_pdf = novo_pdf.replace('\\', '/')
            contrato.pdf_path = novo_pdf
            contrato.save()
            return send_file(novo_pdf, as_attachment=True, download_name=pdf_filename, mimetype='application/pdf')
        else:
            flash('Erro ao gerar o PDF do contrato.', 'danger')
            return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        flash('Erro ao gerar o PDF do contrato.', 'danger')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))


@contratos_bp.route('/<int:contrato_id>/cancelar', methods=['POST'])
@login_required
def cancelar(contrato_id):
    """Cancelar contrato (apenas admin)"""
    contrato = Contrato.get_by_id(contrato_id)
    
    if not contrato:
        abort(404)
    
    usuario_perfil = session['usuario']['perfil']
    usuario_empresa_id = session['usuario'].get('empresa_id')
    
    if usuario_perfil not in ['admin_sistema', 'admin_empresa']:
        flash('Apenas administradores podem cancelar contratos.', 'danger')
        return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))
    
    if usuario_perfil != 'admin_sistema' and contrato.empresa_id != usuario_empresa_id:
        abort(403)
    
    motivo = request.form.get('motivo', 'Cancelado pelo administrador')
    
    contrato.status = 'cancelado'
    contrato.motivo_cancelamento = motivo
    contrato.atualizado_por = session['usuario']['id']
    contrato.save()
    
    flash('Contrato cancelado com sucesso!', 'warning')
    return redirect(url_for('contratos.detalhe', contrato_id=contrato_id))


@contratos_bp.route('/estatisticas')
@login_required
def estatisticas():
    """Estatísticas de contratos"""
    usuario_perfil = session['usuario']['perfil']
    
    if usuario_perfil == 'admin_sistema':
        empresa_id = request.args.get('empresa_id', type=int)
        if not empresa_id:
            flash('Selecione uma empresa para ver as estatísticas.', 'warning')
            return redirect(url_for('admin_sistema.empresas'))
    else:
        empresa_id = session['usuario'].get('empresa_id')
    
    stats = Contrato.estatisticas(empresa_id)
    
    # Contratos por mês
    db = Database()
    contratos_por_mes = db.fetch_all("""
        SELECT 
            DATE_FORMAT(data_criacao, '%%Y-%%m') as mes,
            COUNT(*) as total
        FROM contratos
        WHERE empresa_id = %s
        GROUP BY DATE_FORMAT(data_criacao, '%%Y-%%m')
        ORDER BY mes DESC
        LIMIT 12
    """, (empresa_id,))
    
    return render_template('contratos/estatisticas.html', 
                         stats=stats, 
                         contratos_por_mes=contratos_por_mes)