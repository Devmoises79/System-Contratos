# test_filtro.py
from flask import Flask
from config import Config
from models.contrato import Contrato
from core.database import Database

app = Flask(__name__)
app.config.from_object(Config)

with app.app_context():
    print("\n=== TESTE DE FILTRO ===\n")
    
    # Buscar contratos da empresa 5
    contratos = Contrato.listar_por_empresa(5)
    print(f"Total de contratos: {len(contratos)}")
    for c in contratos:
        print(f"  {c.id}: {c.numero_contrato} - Status: {c.status}")
    
    print("\n--- Filtrando por status 'ativo' ---")
    ativos = [c for c in contratos if c.status == 'ativo']
    print(f"Contratos ativos: {len(ativos)}")
    for c in ativos:
        print(f"  {c.id}: {c.numero_contrato} - Status: {c.status}")
    
    print("\n--- Filtrando por status 'em_analise' ---")
    em_analise = [c for c in contratos if c.status == 'em_analise']
    print(f"Contratos em análise: {len(em_analise)}")
    for c in em_analise:
        print(f"  {c.id}: {c.numero_contrato} - Status: {c.status}")
    
    print("\n--- Filtrando por status 'rascunho' ---")
    rascunhos = [c for c in contratos if c.status == 'rascunho']
    print(f"Contratos rascunho: {len(rascunhos)}")