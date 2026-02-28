"""
Módulo de gerenciamento de contratos 
"""
import fpdf
import os
from datetime import datetime, date
import re
import uuid

class Contrato:
    def __init__(self, db):
        self.db = db
        self.pasta_contratos = "contratos"
        
        # Cria pasta se não existir
        if not os.path.exists(self.pasta_contratos):
            os.makedirs(self.pasta_contratos)
            print(f" Pasta '{self.pasta_contratos}' criada")
    
    def gerar_numero_contrato(self):
        """Gera um número único para o contrato"""
        data_atual = datetime.now().strftime("%Y%m%d")
        codigo = str(uuid.uuid4())[:6].upper()
        return f"CONTR-{data_atual}-{codigo}"
    
    def validar_cnpj(self, cnpj):
        """Valida CNPJ (formato simples)"""
        cnpj = re.sub(r'[^\d]', '', cnpj)
        return len(cnpj) == 14
    
    def formatar_cnpj(self, cnpj):
        """Formata CNPJ para o padrão"""
        cnpj = re.sub(r'[^\d]', '', cnpj)
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    
    def formatar_data(self, data_str):
        """Converte string de data para objeto date"""
        try:
            dia, mes, ano = map(int, data_str.split('/'))
            return date(ano, mes, dia)
        except:
            return None
    
    def coletar_dados(self):
        """Coleta dados do contrato do usuário"""
        print("\n" + "="*60)
        print(" FORMULÁRIO DO CONTRATO")
        print("="*60)
        
        dados = {}
        
        # =============== CONTRATANTE ===============
        print("\n👤 DADOS DO CONTRATANTE:")
        print("-"*40)
        
        dados['empresa_contratante'] = input("Nome da empresa: ").strip()
        
        cnpj = input("CNPJ: ").strip()
        if cnpj and self.validar_cnpj(cnpj):
            dados['cnpj_contratante'] = self.formatar_cnpj(cnpj)
        elif cnpj:
            print("  CNPJ inválido, será omitido")
    
        dados['funcao_contratante'] = input("Função (ex: Cliente): ").strip()
        
        # Mostra ramos disponíveis
        ramos = self.db.buscar_ramos_atividade()
        if ramos:
            print("\n Ramos disponíveis:")
            for i, ramo in enumerate(ramos, 1):
                print(f"  {i}. [{ramo['codigo']}] {ramo['descricao']}")
        
        ramo_input = input("\nEscolha número do ramo ou digite um novo: ").strip()
        if ramo_input.isdigit():
            idx = int(ramo_input) - 1
            if 0 <= idx < len(ramos):
                dados['ramo_contratante'] = ramos[idx]['descricao']
            else:
                dados['ramo_contratante'] = ramo_input
        else:
            dados['ramo_contratante'] = ramo_input
        
        dados['responsavel_contratante'] = input("Responsável legal: ").strip()
        dados['email_contratante'] = input("E-mail (opcional): ").strip()
        dados['telefone_contratante'] = input("Telefone (opcional): ").strip()
        
        # =============== CONTRATADO ===============
        print("\n👤 DADOS DO CONTRATADO:")
        print("-"*40)
        
        dados['empresa_contratada'] = input("Nome da empresa: ").strip()
        
        cnpj = input("CNPJ : ").strip()
        if cnpj and self.validar_cnpj(cnpj):
            dados['cnpj_contratada'] = self.formatar_cnpj(cnpj)
        elif cnpj:
            print("  CNPJ inválido, será omitido")
        
        dados['funcao_contratada'] = input("Função (ex: Prestador): ").strip()
        
        # Escolha do ramo
        ramo_input = input("Escolha número do ramo ou digite um novo: ").strip()
        if ramo_input.isdigit():
            idx = int(ramo_input) - 1
            if 0 <= idx < len(ramos):
                dados['ramo_contratada'] = ramos[idx]['descricao']
            else:
                dados['ramo_contratada'] = ramo_input
        else:
            dados['ramo_contratada'] = ramo_input
        
        dados['responsavel_contratada'] = input("Responsável legal: ").strip()
        dados['email_contratada'] = input("E-mail (opcional): ").strip()
        dados['telefone_contratada'] = input("Telefone (opcional): ").strip()
        
        # =============== DETALHES DO CONTRATO ===============
        print("\n DETALHES DO CONTRATO:")
        print("-"*40)
        
        # Valor
        while True:
            try:
                valor_input = input("Valor do contrato (R$): ").strip()
                valor = float(valor_input.replace(',', '.'))
                dados['valor'] = valor
                break
            except ValueError:
                print(" Valor inválido. Exemplo: 15000.50")
        
        dados['prazo'] = input("Prazo (ex: 12 meses): ").strip()
        
        # Tipos de serviço
        tipos = self.db.buscar_tipos_servico()
        if tipos:
            print("\n  Tipos de serviço disponíveis:")
            for i, tipo in enumerate(tipos, 1):
                print(f"  {i}. [{tipo['codigo']}] {tipo['descricao']}")
        
        tipo_input = input("\nEscolha número do tipo ou digite um novo: ").strip()
        if tipo_input.isdigit():
            idx = int(tipo_input) - 1
            if 0 <= idx < len(tipos):
                dados['tipo_servico'] = tipos[idx]['descricao']
            else:
                dados['tipo_servico'] = tipo_input
        else:
            dados['tipo_servico'] = tipo_input
        
        # Datas
        print("\n DATAS (opcional):")
        data_inicio = input("Data de início (DD/MM/AAAA): ").strip()
        if data_inicio:
            dados['data_inicio'] = self.formatar_data(data_inicio)
        
        data_termino = input("Data de término (DD/MM/AAAA): ").strip()
        if data_termino:
            dados['data_termino'] = self.formatar_data(data_termino)
        
        # Especificação
        print("\n ESPECIFICAÇÃO DOS SERVIÇOS:")
        print("(Digite linha por linha, linha vazia para terminar)")
        dados['especificacao_servico'] = self._coletar_texto_longo()
        
        return dados
    
    def _coletar_texto_longo(self):
        """Coleta texto longo com múltiplas linhas"""
        linhas = []
        print("\nComece a digitar (pressione Enter duas vezes para finalizar):")
        
        while True:
            linha = input()
            if linha == "":
                if len(linhas) == 0:
                    continue  # Ignora primeira linha vazia
                break
            linhas.append(linha)
        
        return "\n".join(linhas)
    
    def criar_pdf(self, dados):
        """Cria o contrato em PDF"""
        numero_contrato = self.gerar_numero_contrato()
        nome_arquivo = f"{numero_contrato}.pdf"
        caminho_arquivo = os.path.join(self.pasta_contratos, nome_arquivo)
        
        pdf = fpdf.FPDF()
        pdf.add_page()
        
        # Configurações
        pdf.set_margins(20, 20, 20)
        
        # Cabeçalho
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "CONTRATO DE PRESTAÇÃO DE SERVIÇOS", ln=1, align='C')
        pdf.ln(5)
        
        # Número do contrato
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Nº: {numero_contrato}", ln=1, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y')}", ln=1, align='C')
        pdf.ln(10)
        
        # =============== PARTES ===============
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "PARTES CONTRATANTES", ln=1)
        pdf.set_font("Arial", '', 11)
        
        # Contratante
        pdf.cell(0, 8, "CONTRATANTE:", ln=1)
        pdf.cell(30, 8, "  Empresa:")
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, dados['empresa_contratante'], ln=1)
        
        pdf.set_font("Arial", '', 11)
        if 'cnpj_contratante' in dados:
            pdf.cell(30, 8, "  CNPJ:")
            pdf.cell(0, 8, dados['cnpj_contratante'], ln=1)
        
        if 'funcao_contratante' in dados:
            pdf.cell(30, 8, "  Função:")
            pdf.cell(0, 8, dados['funcao_contratante'], ln=1)
        
        if 'ramo_contratante' in dados:
            pdf.cell(30, 8, "  Ramo:")
            pdf.cell(0, 8, dados['ramo_contratante'], ln=1)
        
        pdf.cell(30, 8, "  Responsável:")
        pdf.cell(0, 8, dados.get('responsavel_contratante', ''), ln=1)
        
        # Contratado
        pdf.ln(5)
        pdf.cell(0, 8, "CONTRATADA:", ln=1)
        pdf.cell(30, 8, "  Empresa:")
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, dados['empresa_contratada'], ln=1)
        
        pdf.set_font("Arial", '', 11)
        if 'cnpj_contratada' in dados:
            pdf.cell(30, 8, "  CNPJ:")
            pdf.cell(0, 8, dados['cnpj_contratada'], ln=1)
        
        if 'funcao_contratada' in dados:
            pdf.cell(30, 8, "  Função:")
            pdf.cell(0, 8, dados['funcao_contratada'], ln=1)
        
        if 'ramo_contratada' in dados:
            pdf.cell(30, 8, "  Ramo:")
            pdf.cell(0, 8, dados['ramo_contratada'], ln=1)
        
        pdf.cell(30, 8, "  Responsável:")
        pdf.cell(0, 8, dados.get('responsavel_contratada', ''), ln=1)
        
        pdf.ln(10)
        
        # =============== DETALHES ===============
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "DETALHES DO CONTRATO", ln=1)
        pdf.set_font("Arial", '', 11)
        
        # Valor formatado
        valor_formatado = f"R$ {dados['valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        pdf.cell(40, 8, "Valor do contrato:")
        pdf.cell(0, 8, valor_formatado, ln=1)
        
        pdf.cell(40, 8, "Prazo:")
        pdf.cell(0, 8, dados.get('prazo', ''), ln=1)
        
        if 'tipo_servico' in dados:
            pdf.cell(40, 8, "Tipo de serviço:")
            pdf.cell(0, 8, dados['tipo_servico'], ln=1)
        
        if 'data_inicio' in dados and dados['data_inicio']:
            data_str = dados['data_inicio'].strftime('%d/%m/%Y') if isinstance(dados['data_inicio'], date) else dados['data_inicio']
            pdf.cell(40, 8, "Data de início:")
            pdf.cell(0, 8, data_str, ln=1)
        
        if 'data_termino' in dados and dados['data_termino']:
            data_str = dados['data_termino'].strftime('%d/%m/%Y') if isinstance(dados['data_termino'], date) else dados['data_termino']
            pdf.cell(40, 8, "Data de término:")
            pdf.cell(0, 8, data_str, ln=1)
        
        # Especificação
        if 'especificacao_servico' in dados and dados['especificacao_servico']:
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "ESPECIFICAÇÃO DOS SERVIÇOS", ln=1)
            pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 8, dados['especificacao_servico'])
        
        # =============== ASSINATURAS ===============
        pdf.ln(15)
        pdf.cell(90, 1, "", 'T', 0, 'C')
        pdf.cell(10, 1, "")
        pdf.cell(90, 1, "", 'T', 1, 'C')
        pdf.cell(90, 8, "Contratante", 0, 0, 'C')
        pdf.cell(10, 8, "")
        pdf.cell(90, 8, "Data", 0, 1, 'C')
        
        pdf.ln(20)
        
        pdf.cell(90, 1, "", 'T', 0, 'C')
        pdf.cell(10, 1, "")
        pdf.cell(90, 1, "", 'T', 1, 'C')
        pdf.cell(90, 8, "Contratada", 0, 0, 'C')
        pdf.cell(10, 8, "")
        pdf.cell(90, 8, "Data", 0, 1, 'C')
        
        # Rodapé
        pdf.set_y(-30)
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(0, 8, f"Documento gerado automaticamente - Contrato Nº: {numero_contrato}", 0, 0, 'C')
        
        # Salva o PDF
        pdf.output(caminho_arquivo)
        print(f" PDF gerado: {caminho_arquivo}")
        
        return numero_contrato, caminho_arquivo
    
    def salvar_contrato(self, dados):
        """Salva o contrato no banco e gera PDF"""
        try:
            # Gera PDF
            numero_contrato, caminho_pdf = self.criar_pdf(dados)
            
            # Prepara dados para o banco
            dados_db = {
                'numero_contrato': numero_contrato,
                'empresa_contratante': dados['empresa_contratante'],
                'cnpj_contratante': dados.get('cnpj_contratante'),
                'funcao_contratante': dados.get('funcao_contratante'),
                'ramo_contratante': dados.get('ramo_contratante'),
                'responsavel_contratante': dados.get('responsavel_contratante'),
                'email_contratante': dados.get('email_contratante'),
                'telefone_contratante': dados.get('telefone_contratante'),
                'empresa_contratada': dados['empresa_contratada'],
                'cnpj_contratada': dados.get('cnpj_contratada'),
                'funcao_contratada': dados.get('funcao_contratada'),
                'ramo_contratada': dados.get('ramo_contratada'),
                'responsavel_contratada': dados.get('responsavel_contratada'),
                'email_contratada': dados.get('email_contratada'),
                'telefone_contratada': dados.get('telefone_contratada'),
                'valor': dados['valor'],
                'prazo': dados.get('prazo'),
                'tipo_servico': dados.get('tipo_servico'),
                'especificacao_servico': dados.get('especificacao_servico', ''),
                'data_inicio': dados.get('data_inicio'),
                'data_termino': dados.get('data_termino'),
                'arquivo_pdf': caminho_pdf
            }
            
            # Salva no banco
            resultado = self.db.inserir_contrato(dados_db)
            
            if resultado:
                # Registra log
                self.db.registrar_log(
                    "contrato_criado",
                    f"Contrato {numero_contrato} criado para {dados['empresa_contratante']}"
                )
                
                return numero_contrato, caminho_pdf
            else:
                print(" Erro ao salvar no banco de dados")
                return None, None
            
        except Exception as e:
            print(f" Erro ao salvar contrato: {e}")
            return None, None
    
    def listar_contratos(self):
        """Lista todos os contratos"""
        contratos = self.db.buscar_contratos()
        
        if not contratos:
            print("\n Nenhum contrato encontrado!")
            return
        
        print("\n" + "="*120)
        print(" LISTA DE CONTRATOS")
        print("="*120)
        print(f"{'Nº CONTRATO':<20} {'CONTRATANTE':<25} {'CONTRATADO':<25} {'VALOR':<15} {'DATA':<12}")
        print("-"*120)
        
        for contrato in contratos:
            valor_formatado = f"{contrato['valor']:,.2f}"
            valor_formatado = valor_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')
            
            data = contrato['data_criacao'].strftime('%d/%m/%Y') if contrato['data_criacao'] else 'N/A'
            
            print(f"{contrato['numero_contrato']:<20} "
                  f"{contrato['empresa_contratante'][:23]:<25} "
                  f"{contrato['empresa_contratada'][:23]:<25} "
                  f"R$ {valor_formatado:<12} "
                  f"{data:<12}")
        
        print("="*120)
        print(f" Total: {len(contratos)} contrato(s)")
    
    def buscar_contrato(self):
        """Busca contrato por termo"""
        termo = input("\n Digite número, empresa contratante ou contratada: ").strip()
        
        if not termo:
            print("  Termo de busca vazio!")
            return
        
        contratos = self.db.buscar_contratos(termo)
        
        if not contratos:
            print(f"\n Nenhum contrato encontrado para '{termo}'")
            return
        
        print(f"\n Encontrado(s) {len(contratos)} contrato(s):")
        for contrato in contratos:
            print(f"\n CONTRATO: {contrato['numero_contrato']}")
            print(f"    Contratante: {contrato['empresa_contratante']}")
            if contrato.get('ramo_contratante'):
                print(f"    Ramo: {contrato['ramo_contratante']}")
            print(f"    Contratado: {contrato['empresa_contratada']}")
            print(f"    Valor: R$ {contrato['valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            print(f"    Criado em: {contrato['data_criacao']}")
            print(f"    PDF: {contrato.get('arquivo_pdf', 'N/A')}")