"""
Script para gerar PDF fisicamente no disco
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.contrato import Contrato
from utils.gerador_pdf import gerar_pdf_contrato

print("=" * 60)
print("GERANDO PDF FISICAMENTE NO DISCO")
print("=" * 60)

# ID do contrato
CONTRATO_ID = 4

# Busca o contrato
contrato = Contrato.get_by_id(CONTRATO_ID)

if not contrato:
    print(f"❌ Contrato ID {CONTRATO_ID} não encontrado!")
    print("Listando contratos disponíveis:")
    
    # Lista todos os contratos
    db = Database()
    contratos = db.fetch_all("SELECT id, numero_contrato, contratante_nome FROM contratos LIMIT 10")
    for c in contratos:
        print(f"   ID: {c['id']} - Nº: {c['numero_contrato']} - {c['contratante_nome']}")
    sys.exit(1)

print(f"\n✅ Contrato encontrado:")
print(f"   ID: {contrato.id}")
print(f"   Número: {contrato.numero_contrato}")
print(f"   Contratante: {contrato.contratante_nome}")
print(f"   Status: {contrato.status}")

# Verifica se o diretório existe
pdf_dir = os.path.abspath('static/uploads/contratos')
os.makedirs(pdf_dir, exist_ok=True)
print(f"\n📁 Diretório de PDFs: {pdf_dir}")
print(f"   Diretório existe: {os.path.exists(pdf_dir)}")

# Gera o PDF
print(f"\n📄 Gerando PDF...")
pdf_path = gerar_pdf_contrato(contrato)

if pdf_path:
    print(f"\n✅ PDF gerado com sucesso!")
    print(f"   Caminho: {pdf_path}")
    
    if os.path.exists(pdf_path):
        tamanho = os.path.getsize(pdf_path)
        print(f"   Tamanho: {tamanho} bytes")
        print(f"   Arquivo existe: SIM")
        
        # Atualiza o caminho no banco
        contrato.pdf_path = pdf_path
        contrato.save()
        print(f"\n✅ Caminho salvo no banco de dados!")
    else:
        print(f"   ❌ Arquivo não encontrado mesmo após geração!")
else:
    print(f"\n❌ Falha ao gerar o PDF!")

print("\n" + "=" * 60)
print("🔗 Para testar o download, acesse:")
print(f"   http://localhost:5000/contratos/{CONTRATO_ID}/download")
print("=" * 60)