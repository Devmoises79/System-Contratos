# admin/sistema.py
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from auth.permissoes import admin_sistema_required
from auth.ip_blocker import IPBlocker
from models.empresa import Empresa
from models.usuario import Usuario
from models.contrato import Contrato
from core.database import Database
import os
from datetime import datetime
import secrets
from werkzeug.utils import secure_filename

admin_sistema_bp = Blueprint('admin_sistema', __name__, url_prefix='/admin/sistema')

@admin_sistema_bp.route('/')
@admin_sistema_required
def dashboard():
    """Dashboard do admin do sistema"""
    db = Database()
    
    # Estatísticas gerais
    stats = {
        'total_empresas': db.fetch_one("SELECT COUNT(*) as total FROM empresas")['total'],
        'empresas_ativas': db.fetch_one("SELECT COUNT(*) as total FROM empresas WHERE status = 'ativo'")['total'],
        'total_usuarios': db.fetch_one("SELECT COUNT(*) as total FROM usuarios")['total'],
        'usuarios_ativos': db.fetch_one("SELECT COUNT(*) as total FROM usuarios WHERE ativo = TRUE")['total'],
        'total_contratos': db.fetch_one("SELECT COUNT(*) as total FROM contratos")['total'],
        'contratos_ativos': db.fetch_one("SELECT COUNT(*) as total FROM contratos WHERE status = 'ativo'")['total'],
        'ips_bloqueados': db.fetch_one("SELECT COUNT(*) as total FROM ips_bloqueados WHERE ativo = TRUE")['total']
    }
    
    # Valor total contratado
    valor_total = db.fetch_one("SELECT SUM(valor) as total FROM contratos")
    stats['valor_total'] = float(valor_total['total']) if valor_total and valor_total['total'] else 0
    
    # Últimos logs
    logs = db.fetch_all("""
        SELECT l.*, u.nome as usuario_nome, e.nome as empresa_nome
        FROM logs l
        LEFT JOIN usuarios u ON l.usuario_id = u.id
        LEFT JOIN empresas e ON l.empresa_id = e.id
        ORDER BY l.data_criacao DESC
        LIMIT 20
    """)
    
    # Estatísticas de IPs
    ip_stats = IPBlocker.estatisticas()
    
    # Últimas empresas para o dashboard
    empresas_rapidas = db.fetch_all("""
        SELECT e.*, 
               (SELECT COUNT(*) FROM usuarios WHERE empresa_id = e.id) as total_usuarios
        FROM empresas e
        ORDER BY e.data_criacao DESC
        LIMIT 5
    """)
    
    # Últimos feedbacks
    feedbacks = db.fetch_all("""
        SELECT f.*, u.nome as usuario_nome, e.nome as empresa_nome
        FROM feedbacks f
        JOIN usuarios u ON f.usuario_id = u.id
        JOIN empresas e ON f.empresa_id = e.id
        ORDER BY f.data_criacao DESC
        LIMIT 5
    """)
    
    return render_template('admin/sistema/dashboard.html', 
                         stats=stats, 
                         logs=logs,
                         ip_stats=ip_stats,
                         empresas_rapidas=empresas_rapidas,
                         feedbacks=feedbacks)


@admin_sistema_bp.route('/ips')
@admin_sistema_required
def ips_bloqueados():
    """Lista IPs bloqueados"""
    ips = IPBlocker.listar_bloqueados()
    ip_stats = IPBlocker.estatisticas()
    
    return render_template('admin/sistema/ips.html', ips=ips, ip_stats=ip_stats)


@admin_sistema_bp.route('/ips/desbloquear', methods=['POST'])
@admin_sistema_required
def desbloquear_ip():
    """Desbloqueia um IP manualmente"""
    ip = request.json.get('ip')
    if ip:
        IPBlocker.desbloquear(ip)
        return jsonify({'sucesso': True, 'mensagem': 'IP desbloqueado com sucesso!'})
    return jsonify({'sucesso': False, 'mensagem': 'IP não informado'}), 400


@admin_sistema_bp.route('/logs')
@admin_sistema_required
def logs():
    """Visualiza logs do sistema"""
    db = Database()
    
    # Parâmetros de filtro
    modulo = request.args.get('modulo', '')
    usuario = request.args.get('usuario', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 50
    offset = (pagina - 1) * por_pagina
    
    # Estatísticas de logs
    logs_hoje = db.fetch_one("SELECT COUNT(*) as total FROM logs WHERE DATE(data_criacao) = CURDATE()")['total']
    logs_semana = db.fetch_one("SELECT COUNT(*) as total FROM logs WHERE data_criacao > DATE_SUB(NOW(), INTERVAL 7 DAY)")['total']
    logs_mes = db.fetch_one("SELECT COUNT(*) as total FROM logs WHERE data_criacao > DATE_SUB(NOW(), INTERVAL 30 DAY)")['total']
    
    # Query base
    query = """
        SELECT l.*, u.nome as usuario_nome, u.email as usuario_email, e.nome as empresa_nome
        FROM logs l
        LEFT JOIN usuarios u ON l.usuario_id = u.id
        LEFT JOIN empresas e ON l.empresa_id = e.id
        WHERE 1=1
    """
    params = []
    
    if modulo:
        query += " AND l.modulo = %s"
        params.append(modulo)
    
    if usuario:
        query += " AND u.nome LIKE %s"
        params.append(f"%{usuario}%")
    
    if data_inicio:
        query += " AND DATE(l.data_criacao) >= %s"
        params.append(data_inicio)
    
    if data_fim:
        query += " AND DATE(l.data_criacao) <= %s"
        params.append(data_fim)
    
    # Contagem total
    count_query = f"SELECT COUNT(*) as total FROM ({query}) as temp"
    total = db.fetch_one(count_query, params)['total']
    
    # Query com paginação
    query += " ORDER BY l.data_criacao DESC LIMIT %s OFFSET %s"
    params.extend([por_pagina, offset])
    
    logs = db.fetch_all(query, params)
    
    # Módulos disponíveis para filtro
    modulos = db.fetch_all("SELECT DISTINCT modulo FROM logs ORDER BY modulo")
    
    return render_template('admin/sistema/logs.html', 
                         logs=logs,
                         modulos=modulos,
                         pagina=pagina,
                         total_paginas=(total + por_pagina - 1) // por_pagina,
                         total_registros=total,
                         logs_hoje=logs_hoje,
                         logs_semana=logs_semana,
                         logs_mes=logs_mes,
                         filtros={
                             'modulo': modulo,
                             'usuario': usuario,
                             'data_inicio': data_inicio,
                             'data_fim': data_fim
                         })


@admin_sistema_bp.route('/empresas')
@admin_sistema_required
def empresas():
    """Lista todas as empresas"""
    empresas = Empresa.listar_todas()
    
    # Adicionar contagem de usuários para cada empresa
    db = Database()
    for empresa in empresas:
        count = db.fetch_one("SELECT COUNT(*) as total FROM usuarios WHERE empresa_id = %s", (empresa.id,))
        empresa.total_usuarios = count['total'] if count else 0
    
    return render_template('admin/sistema/empresas.html', empresas=empresas)


@admin_sistema_bp.route('/empresa/nova', methods=['POST'])
@admin_sistema_required
def nova_empresa():
    """Cria uma nova empresa"""
    from core.utils import sanitizar_entrada, apenas_digitos
    
    if request.method == 'POST':
        nome = sanitizar_entrada(request.form.get('nome', ''))
        cnpj = apenas_digitos(request.form.get('cnpj', ''))
        email = sanitizar_entrada(request.form.get('email', ''))
        telefone = apenas_digitos(request.form.get('telefone', ''))
        celular = apenas_digitos(request.form.get('celular', ''))
        endereco = sanitizar_entrada(request.form.get('endereco', ''))
        status = request.form.get('status', 'trial')
        data_expiracao = request.form.get('data_expiracao')
        
        if not nome or not cnpj:
            flash('Nome e CNPJ são obrigatórios.', 'danger')
            return redirect(url_for('admin_sistema.empresas'))
        
        # Verifica se CNPJ já existe
        if Empresa.get_by_cnpj(cnpj):
            flash('CNPJ já cadastrado.', 'danger')
            return redirect(url_for('admin_sistema.empresas'))
        
        # Upload de logo
        logo_path = None
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename:
                filename = secure_filename(file.filename)
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                if ext in {'png', 'jpg', 'jpeg', 'gif'}:
                    novo_nome = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}.{ext}"
                    os.makedirs('static/uploads/logos', exist_ok=True)
                    file.save(os.path.join('static/uploads/logos', novo_nome))
                    logo_path = f'uploads/logos/{novo_nome}'
        
        empresa = Empresa(
            nome=nome,
            cnpj=cnpj,
            email=email,
            telefone=telefone,
            celular=celular,
            endereco=endereco,
            logo_path=logo_path,
            status=status,
            data_expiracao=data_expiracao
        )
        
        empresa.save()
        flash('Empresa criada com sucesso!', 'success')
        
    return redirect(url_for('admin_sistema.empresas'))


@admin_sistema_bp.route('/empresa/<int:id>')
@admin_sistema_required
def empresa_detalhe(id):
    """Detalhe de uma empresa"""
    empresa = Empresa.get_by_id(id)
    if not empresa:
        flash('Empresa não encontrada', 'danger')
        return redirect(url_for('admin_sistema.empresas'))
    
    usuarios = empresa.get_usuarios()
    contratos = empresa.get_contratos()
    stats = Contrato.estatisticas(empresa.id)
    
    return render_template('admin/sistema/empresa_detalhe.html',
                         empresa=empresa,
                         usuarios=usuarios,
                         contratos=contratos,
                         stats=stats)


@admin_sistema_bp.route('/feedbacks')
@admin_sistema_required
def feedbacks():
    """Lista feedbacks dos usuários"""
    db = Database()
    
    # Estatísticas gerais
    stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            AVG(nota) as media_nota,
            SUM(CASE WHEN recomendaria = TRUE THEN 1 ELSE 0 END) as recomendariam
        FROM feedbacks
    """) or {'total': 0, 'media_nota': 0, 'recomendariam': 0}
    
    # Distribuição das notas
    distribuicao = {}
    for i in range(1, 6):
        count = db.fetch_one("SELECT COUNT(*) as total FROM feedbacks WHERE nota = %s", (i,))
        distribuicao[str(i)] = count['total'] if count else 0
    
    # Evolução mensal (últimos 6 meses)
    evolucao = db.fetch_all("""
        SELECT 
            DATE_FORMAT(data_criacao, '%%Y-%%m') as mes,
            COUNT(*) as total
        FROM feedbacks
        WHERE data_criacao > DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(data_criacao, '%%Y-%%m')
        ORDER BY mes ASC
    """)
    
    evolucao_labels = []
    evolucao_dados = []
    for item in evolucao:
        ano, mes = item['mes'].split('-')
        meses = {
            '01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr',
            '05': 'Mai', '06': 'Jun', '07': 'Jul', '08': 'Ago',
            '09': 'Set', '10': 'Out', '11': 'Nov', '12': 'Dez'
        }
        evolucao_labels.append(f"{meses[mes]}/{ano}")
        evolucao_dados.append(item['total'])
    
    # Lista de empresas para filtro
    empresas = db.fetch_all("SELECT id, nome FROM empresas ORDER BY nome")
    
    # Feedbacks com joins
    query = """
        SELECT f.*, 
               u.nome as usuario_nome, 
               u.email as usuario_email,
               e.nome as empresa_nome
        FROM feedbacks f
        JOIN usuarios u ON f.usuario_id = u.id
        JOIN empresas e ON f.empresa_id = e.id
        ORDER BY f.data_criacao DESC
        LIMIT 500
    """
    feedbacks = db.fetch_all(query)
    
    return render_template('admin/sistema/feedbacks.html',
                         stats=stats,
                         feedbacks=feedbacks,
                         empresas=empresas,
                         distribuicao_notas=distribuicao,
                         evolucao_labels=evolucao_labels,
                         evolucao_dados=evolucao_dados)


@admin_sistema_bp.route('/estatisticas')
@admin_sistema_required
def estatisticas_api():
    """API de estatísticas para gráficos"""
    db = Database()
    
    # Empresas por mês (últimos 12 meses)
    empresas_mes = db.fetch_all("""
        SELECT 
            DATE_FORMAT(data_criacao, '%%Y-%%m') as mes,
            COUNT(*) as total
        FROM empresas
        WHERE data_criacao > DATE_SUB(NOW(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(data_criacao, '%%Y-%%m')
        ORDER BY mes ASC
    """)
    
    # Contratos por status
    contratos_status = db.fetch_all("""
        SELECT status, COUNT(*) as total
        FROM contratos
        GROUP BY status
    """)
    
    # Usuários por perfil
    usuarios_perfil = db.fetch_all("""
        SELECT perfil, COUNT(*) as total
        FROM usuarios
        GROUP BY perfil
    """)
    
    return jsonify({
        'empresas_mes': empresas_mes,
        'contratos_status': contratos_status,
        'usuarios_perfil': usuarios_perfil
    })