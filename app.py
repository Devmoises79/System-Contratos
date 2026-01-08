"""
ValidaPy Web - Sistema de Contratos Simplificado
"""
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_file
import os
import sys
from datetime import datetime
import json

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Tenta importar os módulos existentes
try:
    from database import Database
    from contrato import Contrato
    print(" Módulos importados com sucesso!")
except ImportError as e:
    print(f" Erro ao importar módulos: {e}")
    print(" Certifique-se que database.py e contrato.py estão no diretório")

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Inicializa o banco
try:
    db = Database()
    contrato_manager = Contrato(db)
    print(" Banco de dados conectado!")
except Exception as e:
    print(f" Erro ao conectar ao banco: {e}")
    db = None
    contrato_manager = None

# =============== APENAS 2 ROTAS ===============

@app.route('/')
def index():
    """Página inicial/landing page"""
    return render_template('index.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    """Dashboard com todas as funcionalidades"""
    if not db or not contrato_manager:
        flash("Erro na conexão com o banco de dados", "error")
        return render_template('index.html')
    
    # =============== AJAX/API ===============
    # API para dados (usada pelo AJAX)
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        action = request.form.get('action')
        
        if action == 'get_ramos':
            ramos = db.buscar_ramos_atividade()
            return jsonify({'success': True, 'data': ramos})
        
        elif action == 'get_tipos':
            tipos = db.buscar_tipos_servico()
            return jsonify({'success': True, 'data': tipos})
        
        elif action == 'create_contract':
            try:
                # Extrai dados do formulário
                valor_str = request.form.get('valor', '0').replace('R$', '').replace('.', '').replace(',', '.').strip()
                valor = float(valor_str) if valor_str else 0
                
                dados = {
                    'empresa_contratante': request.form.get('empresa_contratante', '').strip(),
                    'cnpj_contratante': request.form.get('cnpj_contratante', '').strip(),
                    'ramo_contratante': request.form.get('ramo_contratante', '').strip(),
                    'responsavel_contratante': request.form.get('responsavel_contratante', '').strip(),
                    'email_contratante': request.form.get('email_contratante', '').strip(),
                    'telefone_contratante': request.form.get('telefone_contratante', '').strip(),
                    
                    'empresa_contratada': request.form.get('empresa_contratada', '').strip(),
                    'cnpj_contratada': request.form.get('cnpj_contratada', '').strip(),
                    'ramo_contratada': request.form.get('ramo_contratada', '').strip(),
                    'responsavel_contratada': request.form.get('responsavel_contratada', '').strip(),
                    'email_contratada': request.form.get('email_contratada', '').strip(),
                    'telefone_contratada': request.form.get('telefone_contratada', '').strip(),
                    
                    'valor': valor,
                    'prazo': request.form.get('prazo', '').strip(),
                    'tipo_servico': request.form.get('tipo_servico', '').strip(),
                    'especificacao_servico': request.form.get('especificacao_servico', '').strip(),
                    'data_inicio': request.form.get('data_inicio', '').strip(),
                    'data_termino': request.form.get('data_termino', '').strip()
                }
                
                # Validação básica
                if not dados['empresa_contratante'] or not dados['empresa_contratada'] or valor <= 0:
                    return jsonify({'success': False, 'message': 'Preencha os campos obrigatórios e insira um valor válido'})
                
                numero, caminho = contrato_manager.salvar_contrato(dados)
                
                if numero and caminho:
                    return jsonify({
                        'success': True,
                        'message': f'Contrato {numero} criado com sucesso!',
                        'numero': numero,
                        'caminho': caminho
                    })
                else:
                    return jsonify({'success': False, 'message': 'Erro ao criar contrato'})
                    
            except Exception as e:
                return jsonify({'success': False, 'message': f'Erro: {str(e)}'})
        
        elif action == 'search_contract':
            termo = request.form.get('termo', '')
            filtro = request.form.get('filtro', 'all')
            
            # Constrói query baseada no filtro
            if filtro == 'numero':
                query = f"%{termo}%"
                result = db.executar_query(
                    "SELECT * FROM contratos WHERE numero_contrato LIKE %s ORDER BY data_criacao DESC",
                    (query,), fetch=True
                )
            elif filtro == 'contratante':
                query = f"%{termo}%"
                result = db.executar_query(
                    "SELECT * FROM contratos WHERE empresa_contratante LIKE %s ORDER BY data_criacao DESC",
                    (query,), fetch=True
                )
            elif filtro == 'contratado':
                query = f"%{termo}%"
                result = db.executar_query(
                    "SELECT * FROM contratos WHERE empresa_contratada LIKE %s ORDER BY data_criacao DESC",
                    (query,), fetch=True
                )
            elif filtro == 'cnpj':
                query = f"%{termo}%"
                result = db.executar_query(
                    "SELECT * FROM contratos WHERE cnpj_contratante LIKE %s OR cnpj_contratada LIKE %s ORDER BY data_criacao DESC",
                    (query, query), fetch=True
                )
            else:
                query = f"%{termo}%"
                result = db.executar_query(
                    "SELECT * FROM contratos WHERE numero_contrato LIKE %s OR empresa_contratante LIKE %s OR empresa_contratada LIKE %s OR cnpj_contratante LIKE %s OR cnpj_contratada LIKE %s ORDER BY data_criacao DESC",
                    (query, query, query, query, query), fetch=True
                )
            
            # Formata os dados para JSON
            contratos_data = []
            for c in (result or []):
                contratos_data.append({
                    'id': c['id'],
                    'numero': c['numero_contrato'],
                    'contratante': c['empresa_contratante'],
                    'contratado': c['empresa_contratada'],
                    'valor': float(c['valor']),
                    'data_criacao': c['data_criacao'].strftime('%d/%m/%Y %H:%M') if c['data_criacao'] else '',
                    'pdf_path': c.get('arquivo_pdf', '')
                })
            
            return jsonify({'success': True, 'data': contratos_data})
        
        elif action == 'get_contract_details':
            numero = request.form.get('numero')
            result = db.executar_query(
                "SELECT * FROM contratos WHERE numero_contrato = %s",
                (numero,), fetch=True
            )
            
            if result and len(result) > 0:
                return jsonify({
                    'success': True,
                    'data': result[0]
                })
            else:
                return jsonify({'success': False, 'message': 'Contrato não encontrado'})
    
    # =============== GET NORMAL ===============
    # Para requisições GET normais
    try:
        # Busca estatísticas
        contratos = db.buscar_contratos()
        total_contratos = len(contratos) if contratos else 0
        valor_total = sum(c['valor'] for c in contratos) if contratos else 0
        
        # Calcula contratos deste mês
        current_month = datetime.now().month
        current_year = datetime.now().year
        month_contracts = 0
        
        for c in contratos:
            if c['data_criacao']:
                if c['data_criacao'].month == current_month and c['data_criacao'].year == current_year:
                    month_contracts += 1
        
        contratos_recentes = contratos[:10] if contratos else []
        
        # Busca dados para formulário
        ramos = db.buscar_ramos_atividade()
        tipos = db.buscar_tipos_servico()
        
        return render_template('dashboard.html',
                             total_contratos=total_contratos,
                             valor_total=valor_total,
                             month_contracts=month_contracts,
                             contratos_recentes=contratos_recentes,
                             ramos=ramos,
                             tipos=tipos,
                             all_contratos=contratos[:100])  # Limita para performance
    except Exception as e:
        flash(f"Erro ao carregar dashboard: {e}", "error")
        return render_template('index.html')

@app.route('/download/<path:numero>')
def download_pdf(numero):
    """Download do PDF"""
    if not db:
        return "Erro no banco", 500
    
    try:
        result = db.executar_query(
            "SELECT * FROM contratos WHERE numero_contrato = %s",
            (numero,), fetch=True
        )
        
        if result and len(result) > 0:
            contrato = result[0]
            caminho_pdf = contrato.get('arquivo_pdf')
            
            if caminho_pdf and os.path.exists(caminho_pdf):
                return send_file(caminho_pdf, as_attachment=True, download_name=f"{numero}.pdf")
        
        return "Arquivo não encontrado", 404
    except Exception as e:
        return f"Erro: {e}", 500

# =============== FILTROS JINJA2 ===============
def format_currency(value):
    """Formata valor para moeda brasileira"""
    try:
        return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return f"R$ {value}"

def format_date(date_obj):
    """Formata data"""
    if date_obj:
        if isinstance(date_obj, str):
            return date_obj
        return date_obj.strftime('%d/%m/%Y')
    return ""

app.jinja_env.filters['currency'] = format_currency
app.jinja_env.filters['date'] = format_date

# =============== INICIALIZAÇÃO ===============
if __name__ == '__main__':
    print("\n" + "="*60)
    print(" VALIDAPY WEB - Sistema Simplificado")
    print("="*60)
    
    # Cria pastas se não existirem
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("\n Sistema pronto!")
    print(" Acesse: http://localhost:5000")
    print("="*60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)