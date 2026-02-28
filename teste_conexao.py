# test_conexao.py
from core.database import Database

db = Database()
if db.connect():
    print(" Conectado ao banco validapy!")
    
    # Testa query
    result = db.fetch_one("SELECT COUNT(*) as total FROM usuarios")
    print(f"Total de usuários: {result['total']}")
    
    db.disconnect()
else:
    print(" Erro na conexão")