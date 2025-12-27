"""
ValidaPy - Sistema de Gerenciamento de Contratos
"""


import sys
import os

print("="*60)
print(" VALIDAPY - SISTEMA DE CONTRATOS")
print("="*60)
print("Versão Primária")
print("="*60)

# Testa se os módulos estão disponíveis
try:
    from database import Database
    from contrato import Contrato
    print(" Módulos importados com sucesso!")
    
except ImportError as e:
    print(f" Erro ao importar: {e}")
    print("\n Instale as dependências:")
    print("pip install mysql-connector-python fpdf2")
    input("\nPressione Enter para sair...")
    sys.exit(1)

def mostrar_menu():
    """Exibe o menu principal"""
    print("\n" + "="*60)
    print(" MENU PRINCIPAL")
    print("="*60)
    print("1.  Criar novo contrato")
    print("2.  Listar todos os contratos")
    print("3.  Buscar contrato")
    print("4.  Ver ramos de atividade")
    print("5.   Ver tipos de serviço")
    print("6.   Verificar arquivos PDF")
    print("7.  Configurar sistema")
    print("8.  Sair")
    print("="*60)

def ver_ramos_atividade(db):
    """Mostra ramos de atividade"""
    ramos = db.buscar_ramos_atividade()
    
    if not ramos:
        print("\n Nenhum ramo cadastrado")
        return
    
    print(f"\n RAMOS DE ATIVIDADE ({len(ramos)}):")
    print("-"*60)
    
    # Agrupa por categoria
    categorias = {}
    for ramo in ramos:
        categoria = ramo['categoria'] or 'Outros'
        if categoria not in categorias:
            categorias[categoria] = []
        categorias[categoria].append(ramo)
    
    for categoria, itens in categorias.items():
        print(f"\n {categoria}:")
        for i, ramo in enumerate(itens, 1):
            print(f"  {i:2}. [{ramo['codigo']}] {ramo['descricao']}")

def ver_tipos_servico(db):
    """Mostra tipos de serviço"""
    tipos = db.buscar_tipos_servico()
    
    if not tipos:
        print("\n Nenhum tipo de serviço cadastrado")
        return
    
    print(f"\n  TIPOS DE SERVIÇO ({len(tipos)}):")
    print("-"*60)
    
    # Agrupa por categoria
    categorias = {}
    for tipo in tipos:
        categoria = tipo['categoria'] or 'Outros'
        if categoria not in categorias:
            categorias[categoria] = []
        categorias[categoria].append(tipo)
    
    for categoria, itens in categorias.items():
        print(f"\n {categoria}:")
        for i, tipo in enumerate(itens, 1):
            print(f"  {i:2}. [{tipo['codigo']}] {tipo['descricao']}")

def verificar_pdfs(contrato_manager):
    """Verifica se os PDFs existem"""
    contratos = contrato_manager.db.buscar_contratos()
    
    if not contratos:
        print("\n Nenhum contrato para verificar")
        return
    
    print(f"\n Verificando {len(contratos)} PDF(s)...")
    problemas = 0
    
    for contrato in contratos:
        caminho = contrato.get('arquivo_pdf')
        if caminho:
            if os.path.exists(caminho):
                tamanho = os.path.getsize(caminho) / 1024  # KB
                print(f" {contrato['numero_contrato']}: OK ({tamanho:.1f} KB)")
            else:
                print(f" {contrato['numero_contrato']}: ARQUIVO NÃO ENCONTRADO")
                problemas += 1
        else:
            print(f"  {contrato['numero_contrato']}: SEM CAMINHO")
            problemas += 1
    
    if problemas == 0:
        print(f"\n Todos os {len(contratos)} PDFs estão acessíveis!")
    else:
        print(f"\n  {problemas} problema(s) encontrado(s)")

def estatisticas(db):
    """Mostra estatísticas"""
    try:
        contratos = db.buscar_contratos()
        
        if not contratos:
            print("\n Nenhum contrato para estatísticas")
            return
        
        print("\n ESTATÍSTICAS DO SISTEMA")
        print("="*60)
        print(f" Total de contratos: {len(contratos)}")
        
        # Soma dos valores
        valor_total = sum(contrato['valor'] for contrato in contratos)
        print(f" Valor total: R$ {valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        # Valor médio
        valor_medio = valor_total / len(contratos) if contratos else 0
        print(f" Valor médio: R$ {valor_medio:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        # Contratos por mês
        from collections import defaultdict
        contratos_por_mes = defaultdict(int)
        
        for contrato in contratos:
            if contrato['data_criacao']:
                mes = contrato['data_criacao'].strftime('%Y-%m')
                contratos_por_mes[mes] += 1
        
        if contratos_por_mes:
            print("\n Contratos por mês:")
            for mes in sorted(contratos_por_mes.keys(), reverse=True)[:6]:  # Últimos 6 meses
                print(f"  • {mes}: {contratos_por_mes[mes]} contrato(s)")
        
        print("="*60)
        
    except Exception as e:
        print(f" Erro ao gerar estatísticas: {e}")

def configurar_sistema(db):
    """Menu de configurações"""
    print("\n CONFIGURAÇÕES DO SISTEMA")
    print("="*60)
    print("1.  Recriar tabelas do banco")
    print("2.  Ver estatísticas do banco")
    print("3.  Limpar dados de teste")
    print("4.  Voltar")
    print("="*60)
    
    opcao = input("\nEscolha: ").strip()
    
    if opcao == "1":
        confirmar = input("\n  Tem certeza? Isso recriará todas as tabelas (S/N): ").strip().upper()
        if confirmar == "S":
            print("\n🔄 Recriando tabelas...")
            db._verificar_tabelas()
            print(" Tabelas recriadas!")
    
    elif opcao == "2":
        print("\n ESTATÍSTICAS DO BANCO:")
        try:
            cursor = db.connection.cursor(dictionary=True)
            cursor.execute("SHOW TABLES")
            tabelas = cursor.fetchall()
            
            print(f"\n Total de tabelas: {len(tabelas)}")
            for tabela in tabelas:
                nome = list(tabela.values())[0]
                cursor.execute(f"SELECT COUNT(*) as total FROM {nome}")
                total = cursor.fetchone()['total']
                print(f"  • {nome}: {total} registro(s)")
            
            cursor.close()
            
        except Exception as e:
            print(f" Erro: {e}")
    
    elif opcao == "3":
        confirmar = input("\n  Limpar todos os contratos? (S/N): ").strip().upper()
        if confirmar == "S":
            try:
                cursor = db.connection.cursor()
                cursor.execute("DELETE FROM contratos")
                cursor.execute("DELETE FROM logs")
                db.connection.commit()
                cursor.close()
                print(" Dados limpos!")
            except Exception as e:
                print(f" Erro: {e}")

def main():
    """Função principal"""
    print("\n Iniciando conexão com o banco de dados...")
    
    try:
        db = Database()
        
        if not db.connection or not db.connection.is_connected():
            print(" Não foi possível conectar ao banco")
            print("\n Soluções:")
            print("1. Execute o script SQL para criar o banco")
            print("2. Verifique as credenciais no config.json")
            print("3. Confirme se o MySQL está rodando")
            return
        
        contrato_manager = Contrato(db)
        
        print("\n" + "="*60)
        print(" SISTEMA PRONTO PARA USO!")
        print("="*60)
        
        while True:
            mostrar_menu()
            
            try:
                opcao = input("\n Escolha uma opção (1-8): ").strip()
                
                if opcao == "1":
                    print("\n CRIANDO NOVO CONTRATO")
                    
                    dados = contrato_manager.coletar_dados()
                    
                    # Mostra resumo
                    print("\n" + "="*50)
                    print(" RESUMO DO CONTRATO")
                    print("="*50)
                    print(f"Contratante: {dados['empresa_contratante']}")
                    if 'ramo_contratante' in dados:
                        print(f"Ramo: {dados['ramo_contratante']}")
                    print(f"Contratado: {dados['empresa_contratada']}")
                    if 'ramo_contratada' in dados:
                        print(f"Ramo: {dados['ramo_contratada']}")
                    print(f"Valor: R$ {dados['valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                    if 'tipo_servico' in dados:
                        print(f"Serviço: {dados['tipo_servico']}")
                    print("="*50)
                    
                    confirmar = input("\n Confirmar criação? (S/N): ").strip().upper()
                    
                    if confirmar == "S":
                        print("\n Criando contrato...")
                        numero, caminho = contrato_manager.salvar_contrato(dados)
                        
                        if numero and caminho:
                            print(f"\n CONTRATO CRIADO COM SUCESSO!")
                            print(f" Número: {numero}")
                            print(f" Arquivo: {caminho}")
                        else:
                            print("\n Erro ao criar contrato")
                    else:
                        print("\n  Operação cancelada")
                
                elif opcao == "2":
                    contrato_manager.listar_contratos()
                
                elif opcao == "3":
                    contrato_manager.buscar_contrato()
                
                elif opcao == "4":
                    ver_ramos_atividade(db)
                
                elif opcao == "5":
                    ver_tipos_servico(db)
                
                elif opcao == "6":
                    verificar_pdfs(contrato_manager)
                
                elif opcao == "7":
                    configurar_sistema(db)
                
                elif opcao == "8":
                    print("\n Obrigado por usar o ValidaPy!")
                    db.fechar_conexao()
                    break
                
                else:
                    print(" Opção inválida! Escolha de 1 a 8.")
                
                input("\n Pressione Enter para continuar...")
                
            except KeyboardInterrupt:
                print("\n\n  Operação interrompida pelo usuário")
                continue
            except Exception as e:
                print(f"\n Erro: {e}")
                continue
    
    except Exception as e:
        print(f"\n Erro fatal: {e}")
    
    finally:
        print("\n Programa encerrado.")

if __name__ == "__main__":
    main()
