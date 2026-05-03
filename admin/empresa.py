from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth.permissoes import admin_empresa_required, login_required, get_empresa_id
from core.database import Database
from core.logging_config import logger
from models.contrato import Contrato
from models.usuario import Usuario
from core.hash_utils import hash_manager

empresa_bp = Blueprint('admin_empresa', __name__, url_prefix='/admin/empresa')


@empresa_bp.route('/dashboard')
@login_required
@admin_empresa_required
def dashboard():
    """Dashboard da empresa com métricas da empresa e pessoais do admin"""
    empresa_id = get_empresa_id()
    usuario_id = session.get('usuario_id')
    
    # ==================== MÉTRICAS DA EMPRESA ====================
    
    # Total de contratos da empresa
    total_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s", (empresa_id,))
    total_contratos = total_result['total'] if total_result else 0
    
    # Contratos Ativos
    ativos_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'ativo'", (empresa_id,))
    contratos_ativos = ativos_result['total'] if ativos_result else 0
    
    # Contratos em Análise
    analise_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'em_analise'", (empresa_id,))
    contratos_analise = analise_result['total'] if analise_result else 0
    
    # Contratos Aguardando Aprovação
    aguardando_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'aguardando_aprovacao'", (empresa_id,))
    contratos_aguardando = aguardando_result['total'] if aguardando_result else 0
    
    # Contratos Rascunho
    rascunho_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'rascunho'", (empresa_id,))
    contratos_rascunho = rascunho_result['total'] if rascunho_result else 0
    
    # Contratos Encerrados
    encerrados_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'encerrado'", (empresa_id,))
    contratos_encerrados = encerrados_result['total'] if encerrados_result else 0
    
    # Contratos Cancelados
    cancelados_result = Database.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE empresa_id = %s AND status = 'cancelado'", (empresa_id,))
    contratos_cancelados = cancelados_result['total'] if cancelados_result else 0
    
    # Contratos Vencidos
    vencidos_result = Database.fetch_one("""
        SELECT COUNT(*) as total FROM contratos 
        WHERE empresa_id = %s AND status = 'ativo' AND data_fim < CURDATE()
    """, (empresa_id,))
    contratos_vencidos = vencidos_result['total'] if vencidos_result else 0
    
    # Contratos vencendo nos próximos 30 dias
    vencendo_result = Database.fetch_one("""
        SELECT COUNT(*) as total FROM contratos 
        WHERE empresa_id = %s AND status = 'ativo' 
        AND data_fim BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
    """, (empresa_id,))
    contratos_vencendo = vencendo_result['total'] if vencendo_result else 0
    
    # Valor total de TODOS os contratos
    valor_total_result = Database.fetch_one("SELECT SUM(valor) as total FROM contratos WHERE empresa_id = %s", (empresa_id,))
    valor_total = float(valor_total_result['total']) if valor_total_result and valor_total_result['total'] else 0
    
    # Valor total de contratos ATIVOS apenas
    valor_total_ativos_result = Database.fetch_one("SELECT SUM(valor) as total FROM contratos WHERE empresa_id = %s AND status = 'ativo'", (empresa_id,))
    valor_total_ativos = float(valor_total_ativos_result['total']) if valor_total_ativos_result and valor_total_ativos_result['total'] else 0
    
    # Ticket médio (apenas contratos ATIVOS)
    ticket_medio = valor_total_ativos / contratos_ativos if contratos_ativos > 0 else 0
    
    # ==================== MÉTRICAS PESSOAIS DO ADMIN ====================
    
    # Contratos que o admin criou
    meus_contratos = Database.fetch_one("""
        SELECT COUNT(*) as total FROM contratos 
        WHERE empresa_id = %s AND criado_por = %s
    """, (empresa_id, usuario_id))
    meus_contratos_total = meus_contratos['total'] if meus_contratos else 0
    
    # Contratos que o admin editou
    editei_contratos = Database.fetch_one("""
        SELECT COUNT(*) as total FROM contratos 
        WHERE empresa_id = %s AND atualizado_por = %s
    """, (empresa_id, usuario_id))
    editei_contratos_total = editei_contratos['total'] if editei_contratos else 0
    
    # Valor total dos contratos que o admin criou
    meu_valor_total = Database.fetch_one("""
        SELECT SUM(valor) as total FROM contratos 
        WHERE empresa_id = %s AND criado_por = %s
    """, (empresa_id, usuario_id))
    meu_valor_total = float(meu_valor_total['total']) if meu_valor_total and meu_valor_total['total'] else 0
    
    # Contratos ativos que o admin criou
    meus_ativos = Database.fetch_one("""
        SELECT COUNT(*) as total FROM contratos 
        WHERE empresa_id = %s AND criado_por = %s AND status = 'ativo'
    """, (empresa_id, usuario_id))
    meus_ativos_total = meus_ativos['total'] if meus_ativos else 0
    
    # ==================== ÚLTIMOS CONTRATOS ====================
    contratos_raw = Database.fetch_all(
        """SELECT id, numero_contrato, contratante_nome, contratada_nome, 
           valor, status, data_criacao, data_inicio, data_fim
           FROM contratos 
           WHERE empresa_id = %s 
           ORDER BY id DESC 
           LIMIT 10""",
        (empresa_id,)
    )
    
    ultimos_contratos = []
    if contratos_raw:
        for c in contratos_raw:
            ultimos_contratos.append({
                'id': c.get('id'),
                'numero': c.get('numero_contrato') or f"CT-{c.get('id')}",
                'contratante': c.get('contratante_nome') or 'Não informado',
                'contratada': c.get('contratada_nome') or 'Não informado',
                'valor': float(c.get('valor', 0)),
                'status': c.get('status', 'pendente'),
                'data_criacao': c.get('data_criacao'),
                'data_inicio': c.get('data_inicio'),
                'data_fim': c.get('data_fim')
            })
    
    # ==================== NOTIFICAÇÕES ====================
    notificacoes = []
    notificacoes_sidebar = []
    
    # Contratos vencendo nos próximos 7 dias (urgente)
    urgentes = Database.fetch_one("""
        SELECT COUNT(*) as total FROM contratos 
        WHERE empresa_id = %s AND status = 'ativo' 
        AND data_fim BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
    """, (empresa_id,))
    if urgentes and urgentes['total'] > 0:
        notificacoes.append({
            'tipo': 'warning',
            'titulo': 'Contratos a vencer em 7 dias',
            'mensagem': f"{urgentes['total']} contrato(s) vence(m) nos próximos 7 dias",
            'icone': 'fa-clock',
            'cor': '#f59e0b'
        })
        notificacoes_sidebar.append({
            'titulo': 'Vencimento Próximo',
            'mensagem_curta': f'{urgentes["total"]} contrato(s) vencem em 7 dias',
            'icone': 'fa-clock',
            'cor': '#f59e0b',
            'link': url_for('admin_empresa.listar_contratos', status='ativo')
        })
    
    # Contratos vencidos
    if contratos_vencidos > 0:
        notificacoes.append({
            'tipo': 'danger',
            'titulo': 'Contratos Vencidos',
            'mensagem': f"{contratos_vencidos} contrato(s) está(ão) vencido(s)",
            'icone': 'fa-exclamation-triangle',
            'cor': '#ef4444'
        })
        notificacoes_sidebar.append({
            'titulo': 'Contratos Vencidos',
            'mensagem_curta': f'{contratos_vencidos} contrato(s) estão vencidos',
            'icone': 'fa-exclamation-triangle',
            'cor': '#ef4444',
            'link': url_for('admin_empresa.listar_contratos', status='ativo')
        })
    
    # Contratos aguardando aprovação
    if contratos_aguardando > 0:
        notificacoes.append({
            'tipo': 'info',
            'titulo': 'Contratos Aguardando Aprovação',
            'mensagem': f"{contratos_aguardando} contrato(s) aguardando aprovação",
            'icone': 'fa-hourglass-half',
            'cor': '#3b82f6'
        })
        notificacoes_sidebar.append({
            'titulo': 'Aguardando Aprovação',
            'mensagem_curta': f'{contratos_aguardando} contrato(s) aguardam aprovação',
            'icone': 'fa-hourglass-half',
            'cor': '#3b82f6',
            'link': url_for('admin_empresa.listar_contratos', status='aguardando_aprovacao')
        })
    
    # Contratos em análise
    if contratos_analise > 0:
        notificacoes.append({
            'tipo': 'secondary',
            'titulo': 'Contratos em Análise',
            'mensagem': f"{contratos_analise} contrato(s) em análise",
            'icone': 'fa-search',
            'cor': '#6B46C1'
        })
        notificacoes_sidebar.append({
            'titulo': 'Em Análise',
            'mensagem_curta': f'{contratos_analise} contrato(s) em análise',
            'icone': 'fa-search',
            'cor': '#6B46C1',
            'link': url_for('admin_empresa.listar_contratos', status='em_analise')
        })
    
    # Notificação pessoal: contratos que o admin criou pendentes
    meus_pendentes = Database.fetch_one("""
        SELECT COUNT(*) as total FROM contratos 
        WHERE empresa_id = %s AND criado_por = %s 
        AND status IN ('rascunho', 'em_analise')
    """, (empresa_id, usuario_id))
    if meus_pendentes and meus_pendentes['total'] > 0:
        notificacoes.append({
            'tipo': 'personal',
            'titulo': 'Seus contratos pendentes',
            'mensagem': f"Você tem {meus_pendentes['total']} contrato(s) que precisam de ação",
            'icone': 'fa-user-check',
            'cor': '#10b981'
        })
        notificacoes_sidebar.append({
            'titulo': 'Meus Pendentes',
            'mensagem_curta': f'{meus_pendentes["total"]} contrato(s) que criei precisam de ação',
            'icone': 'fa-user-check',
            'cor': '#10b981',
            'link': url_for('admin_empresa.listar_contratos')
        })
    
    # Salvar notificações na sessão para usar na sidebar
    session['notificacoes_sidebar'] = notificacoes_sidebar
    session['contratos_pendentes_count'] = contratos_aguardando + contratos_analise
    
    return render_template('admin/empresa/dashboard.html',
                         # Métricas da empresa
                         total_contratos=total_contratos,
                         contratos_ativos=contratos_ativos,
                         contratos_vencidos=contratos_vencidos,
                         contratos_vencendo=contratos_vencendo,
                         contratos_analise=contratos_analise,
                         contratos_aguardando=contratos_aguardando,
                         contratos_rascunho=contratos_rascunho,
                         contratos_encerrados=contratos_encerrados,
                         contratos_cancelados=contratos_cancelados,
                         valor_total=valor_total,
                         valor_total_ativos=valor_total_ativos,
                         ticket_medio=ticket_medio,
                         # Métricas pessoais
                         meus_contratos_total=meus_contratos_total,
                         editei_contratos_total=editei_contratos_total,
                         meu_valor_total=meu_valor_total,
                         meus_ativos_total=meus_ativos_total,
                         meus_pendentes=meus_pendentes['total'] if meus_pendentes else 0,
                         # Lista e notificações
                         ultimos_contratos=ultimos_contratos,
                         notificacoes=notificacoes)


@empresa_bp.route('/contratos')
@login_required
@admin_empresa_required
def listar_contratos():
    """Lista todos os contratos da empresa"""
    empresa_id = get_empresa_id()
    
    status = request.args.get('status')
    if status:
        contratos = Contrato.listar_por_empresa(empresa_id, status)
    else:
        contratos = Contrato.listar_por_empresa(empresa_id)
    
    return render_template('admin/empresa/contratos.html', 
                         contratos=contratos or [],
                         status_atual=status)
    

@empresa_bp.route('/contrato/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_empresa_required
def editar_contrato(id):
    """Editar um contrato específico"""
    empresa_id = get_empresa_id()
    
    # Buscar o contrato
    contrato = Database.fetch_one(
        "SELECT * FROM contratos WHERE id = %s AND empresa_id = %s",
        (id, empresa_id)
    )
    
    if not contrato:
        flash('Contrato não encontrado.', 'danger')
        return redirect(url_for('admin_empresa.listar_contratos'))
    
    if request.method == 'POST':
        try:
            # Pegar dados do formulário
            contratante_nome = request.form.get('contratante_nome')
            contratante_cnpj = request.form.get('contratante_cnpj')
            contratante_email = request.form.get('contratante_email')
            contratante_telefone = request.form.get('contratante_telefone')
            contratada_nome = request.form.get('contratada_nome')
            contratada_cnpj = request.form.get('contratada_cnpj')
            contratada_email = request.form.get('contratada_email')
            valor = request.form.get('valor')
            prazo_dias = request.form.get('prazo_dias')
            data_inicio = request.form.get('data_inicio')
            data_fim = request.form.get('data_fim')
            descricao = request.form.get('descricao')
            status = request.form.get('status')
            
            # Usar o session para usuario_id
            usuario_id = session.get('usuario_id', 1)
            
            # Atualizar o contrato
            Database.execute("""
                UPDATE contratos SET
                    contratante_nome = %s,
                    contratante_cnpj = %s,
                    contratante_email = %s,
                    contratante_telefone = %s,
                    contratada_nome = %s,
                    contratada_cnpj = %s,
                    contratada_email = %s,
                    valor = %s,
                    prazo_dias = %s,
                    data_inicio = %s,
                    data_fim = %s,
                    descricao = %s,
                    status = %s,
                    atualizado_por = %s,
                    data_atualizacao = NOW()
                WHERE id = %s
            """, (contratante_nome, contratante_cnpj, contratante_email, contratante_telefone,
                  contratada_nome, contratada_cnpj, contratada_email,
                  valor, prazo_dias, data_inicio, data_fim, descricao, status,
                  usuario_id, id))
            
            flash('Contrato atualizado com sucesso!', 'success')
            return redirect(url_for('admin_empresa.ver_contrato', id=id))
            
        except Exception as e:
            print(f"Erro ao atualizar contrato: {e}")
            flash('Erro ao atualizar contrato.', 'danger')
    
    return render_template('admin/empresa/editar_contrato.html', contrato=contrato)


@empresa_bp.route('/contrato/novo', methods=['GET', 'POST'])
@login_required
@admin_empresa_required
def novo_contrato():
    """Criar novo contrato - Redireciona para o formulário principal"""
    # Redirecionar para a rota principal de criação de contratos
    return redirect(url_for('contrato_novo'))


@empresa_bp.route('/contrato/<int:id>')
@login_required
@admin_empresa_required
def ver_contrato(id):
    """Visualiza um contrato específico"""
    empresa_id = get_empresa_id()
    contrato = Contrato.get_by_id(id)
    
    if not contrato or contrato.empresa_id != empresa_id:
        flash('Contrato não encontrado.', 'danger')
        return redirect(url_for('admin_empresa.listar_contratos'))
    
    return render_template('admin/empresa/contrato_detalhe.html', contrato=contrato)


@empresa_bp.route('/usuarios')
@login_required
@admin_empresa_required
def cadastro_usuario():
    """Lista usuários da empresa"""
    empresa_id = get_empresa_id()
    usuarios = Usuario.listar_por_empresa(empresa_id, apenas_ativos=False)
    
    logger.info(f"Usuários encontrados para empresa {empresa_id}: {len(usuarios)}")
    
    return render_template('admin/empresa/usuarios.html', usuarios=usuarios or [])


@empresa_bp.route('/usuario/novo', methods=['GET', 'POST'])
@login_required
@admin_empresa_required
def novo_usuario():
    """Cria novo usuário"""
    empresa_id = get_empresa_id()
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        perfil = request.form.get('perfil')
        senha = request.form.get('senha')
        
        if not senha:
            senha = "123456"
        
        senha_hash = hash_manager.hash_senha(senha)
        
        # Verificar se email já existe
        existing = Database.fetch_one("SELECT id FROM usuarios WHERE email = %s", (email,))
        if existing:
            flash('Este email já está cadastrado.', 'danger')
            return redirect(url_for('admin_empresa.novo_usuario'))
        
        try:
            Database.execute("""
                INSERT INTO usuarios (empresa_id, nome, email, senha_hash, perfil, ativo)
                VALUES (%s, %s, %s, %s, %s, 1)
            """, (empresa_id, nome, email, senha_hash, perfil))
            
            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('admin_empresa.cadastro_usuario'))
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {e}")
            flash('Erro ao criar usuário.', 'danger')
    
    return render_template('admin/empresa/usuario_form.html')


@empresa_bp.route('/usuario/editar/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
@admin_empresa_required
def editar_usuario(usuario_id):
    """Edita usuário"""
    empresa_id = get_empresa_id()
    
    usuario = Database.fetch_one(
        "SELECT * FROM usuarios WHERE id = %s AND empresa_id = %s",
        (usuario_id, empresa_id)
    )
    
    if not usuario:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('admin_empresa.cadastro_usuario'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        perfil = request.form.get('perfil')
        ativo = 1 if request.form.get('ativo') == 'on' else 0
        
        # Verificar se email já existe (exceto o próprio)
        existing = Database.fetch_one(
            "SELECT id FROM usuarios WHERE email = %s AND id != %s",
            (email, usuario_id)
        )
        if existing:
            flash('Este email já está cadastrado para outro usuário.', 'danger')
            return redirect(url_for('admin_empresa.editar_usuario', usuario_id=usuario_id))
        
        Database.execute("""
            UPDATE usuarios SET nome=%s, email=%s, perfil=%s, ativo=%s
            WHERE id=%s AND empresa_id=%s
        """, (nome, email, perfil, ativo, usuario_id, empresa_id))
        
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('admin_empresa.cadastro_usuario'))
    
    return render_template('admin/empresa/usuario_form.html', usuario=usuario)


@empresa_bp.route('/usuario/ativar/<int:usuario_id>')
@login_required
@admin_empresa_required
def ativar_usuario(usuario_id):
    """Ativa/desativa usuário"""
    empresa_id = get_empresa_id()
    
    usuario = Database.fetch_one(
        "SELECT ativo FROM usuarios WHERE id = %s AND empresa_id = %s",
        (usuario_id, empresa_id)
    )
    
    if usuario:
        novo_status = 0 if usuario['ativo'] else 1
        Database.execute(
            "UPDATE usuarios SET ativo=%s WHERE id=%s",
            (novo_status, usuario_id)
        )
        flash('Status do usuário alterado com sucesso!', 'success')
    else:
        flash('Usuário não encontrado.', 'danger')
    
    return redirect(url_for('admin_empresa.cadastro_usuario'))


@empresa_bp.route('/configuracoes')
@login_required
@admin_empresa_required
def configuracoes():
    """Página de configurações da empresa"""
    empresa_id = get_empresa_id()
    
    empresa = Database.fetch_one(
        "SELECT * FROM empresas WHERE id = %s",
        (empresa_id,)
    )
    
    return render_template('admin/empresa/configuracoes.html', empresa=empresa)


@empresa_bp.route('/estatisticas')
@login_required
@admin_empresa_required
def estatisticas():
    """Página de estatísticas da empresa"""
    empresa_id = get_empresa_id()
    
    # Estatísticas mensais
    estatisticas_mensais = Database.fetch_all("""
        SELECT 
            DATE_FORMAT(data_criacao, '%Y-%m') as mes,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'ativo' THEN 1 ELSE 0 END) as ativos,
            SUM(valor) as valor_total
        FROM contratos 
        WHERE empresa_id = %s 
        GROUP BY DATE_FORMAT(data_criacao, '%Y-%m')
        ORDER BY mes DESC
        LIMIT 12
    """, (empresa_id,))
    
    return render_template('admin/empresa/estatisticas.html', 
                         estatisticas_mensais=estatisticas_mensais or [])