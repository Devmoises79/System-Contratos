"""
Script para testar a conexão com o MySQL
Testa diferentes métodos e configurações
"""

import sys
import time

print("=" * 60)
print("🔍 TESTE DE CONEXÃO COM MYSQL")
print("=" * 60)

# Configurações do banco (mesmas do seu config.py)
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Mo!ses@2004',
    'database': 'validapy',
    'port': 3306
}

print(f"\n📋 Configurações:")
print(f"   Host: {MYSQL_CONFIG['host']}")
print(f"   Porta: {MYSQL_CONFIG['port']}")
print(f"   Usuário: {MYSQL_CONFIG['user']}")
print(f"   Banco: {MYSQL_CONFIG['database']}")
print(f"   Senha: {'*' * len(MYSQL_CONFIG['password'])}")

# ============================================================
# TESTE 1: mysql-connector-python com SSL desabilitado
# ============================================================
print("\n" + "=" * 60)
print("📦 TESTE 1: mysql-connector-python (com SSL desabilitado)")
print("=" * 60)

try:
    import mysql.connector
    from mysql.connector import Error
    
    print("   Conectando...")
    conn = mysql.connector.connect(
        host=MYSQL_CONFIG['host'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        database=MYSQL_CONFIG['database'],
        port=MYSQL_CONFIG['port'],
        ssl_disabled=True,  # Desabilitar SSL
        use_pure=True,       # Forçar implementação Python pura
        connection_timeout=10
    )
    
    if conn.is_connected():
        print("   ✅ CONEXÃO OK!")
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT 1 as test, NOW() as data_hora, VERSION() as versao")
        result = cursor.fetchone()
        print(f"   ✅ Query executada: {result}")
        
        cursor.close()
        conn.close()
        print("   ✅ Conexão fechada")
        
except ImportError:
    print("   ❌ mysql-connector-python não instalado")
    print("   Instale com: pip install mysql-connector-python")
    
except Error as e:
    print(f"   ❌ Erro MySQL: {e}")
    
except Exception as e:
    print(f"   ❌ Erro: {e}")


# ============================================================
# TESTE 2: PyMySQL
# ============================================================
print("\n" + "=" * 60)
print("📦 TESTE 2: PyMySQL")
print("=" * 60)

try:
    import pymysql
    from pymysql import Error
    
    print("   Conectando...")
    conn = pymysql.connect(
        host=MYSQL_CONFIG['host'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        database=MYSQL_CONFIG['database'],
        port=MYSQL_CONFIG['port'],
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10
    )
    
    print("   ✅ CONEXÃO OK!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT 1 as test, NOW() as data_hora, VERSION() as versao")
    result = cursor.fetchone()
    print(f"   ✅ Query executada: {result}")
    
    cursor.close()
    conn.close()
    print("   ✅ Conexão fechada")
    
except ImportError:
    print("   ❌ PyMySQL não instalado")
    print("   Instale com: pip install pymysql")
    
except Error as e:
    print(f"   ❌ Erro MySQL: {e}")
    
except Exception as e:
    print(f"   ❌ Erro: {e}")


# ============================================================
# TESTE 3: Teste de tabela notificacoes
# ============================================================
print("\n" + "=" * 60)
print("📦 TESTE 3: Verificar tabela notificacoes")
print("=" * 60)

try:
    import pymysql
    
    conn = pymysql.connect(
        host=MYSQL_CONFIG['host'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        database=MYSQL_CONFIG['database'],
        port=MYSQL_CONFIG['port'],
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    cursor = conn.cursor()
    
    # Verificar se a tabela existe
    cursor.execute("""
        SELECT COUNT(*) as total 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = 'notificacoes'
    """, (MYSQL_CONFIG['database'],))
    
    result = cursor.fetchone()
    
    if result['total'] > 0:
        print("   ✅ Tabela 'notificacoes' existe")
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) as total FROM notificacoes")
        count = cursor.fetchone()
        print(f"   📊 Total de registros: {count['total']}")
        
        # Verificar estrutura
        cursor.execute("DESCRIBE notificacoes")
        columns = cursor.fetchall()
        print(f"   📋 Colunas: {len(columns)}")
        
    else:
        print("   ⚠️ Tabela 'notificacoes' NÃO existe")
        print("   Será necessário criar a tabela")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"   ❌ Erro: {e}")


# ============================================================
# TESTE 4: Conexão com socket (telnet)
# ============================================================
print("\n" + "=" * 60)
print("📦 TESTE 4: Teste de socket (conexão básica)")
print("=" * 60)

try:
    import socket
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((MYSQL_CONFIG['host'], MYSQL_CONFIG['port']))
    
    if result == 0:
        print(f"   ✅ Porta {MYSQL_CONFIG['port']} está ABERTA")
        
        # Tentar ler banner do MySQL
        banner = sock.recv(1024)
        print(f"   📡 Banner: {banner[:50]}...")
    else:
        print(f"   ❌ Porta {MYSQL_CONFIG['port']} está FECHADA (código: {result})")
    
    sock.close()
    
except Exception as e:
    print(f"   ❌ Erro: {e}")


# ============================================================
# TESTE 5: Ping no servidor
# ============================================================
print("\n" + "=" * 60)
print("📦 TESTE 5: Ping no servidor")
print("=" * 60)

try:
    import subprocess
    import platform
    
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    
    result = subprocess.run(
        ['ping', param, '1', MYSQL_CONFIG['host']],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    if result.returncode == 0:
        print(f"   ✅ Servidor {MYSQL_CONFIG['host']} está RESPONDENDO")
    else:
        print(f"   ⚠️ Servidor {MYSQL_CONFIG['host']} NÃO respondeu")
        
except Exception as e:
    print(f"   ❌ Erro: {e}")


# ============================================================
# TESTE 6: Recomendação final
# ============================================================
print("\n" + "=" * 60)
print("📋 RECOMENDAÇÃO FINAL")
print("=" * 60)

# Verificar qual teste funcionou
pymysql_ok = False
mysql_connector_ok = False

try:
    import pymysql
    conn = pymysql.connect(
        host=MYSQL_CONFIG['host'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        database=MYSQL_CONFIG['database'],
        port=MYSQL_CONFIG['port']
    )
    conn.close()
    pymysql_ok = True
except:
    pass

try:
    import mysql.connector
    conn = mysql.connector.connect(
        host=MYSQL_CONFIG['host'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        database=MYSQL_CONFIG['database'],
        port=MYSQL_CONFIG['port'],
        ssl_disabled=True
    )
    conn.close()
    mysql_connector_ok = True
except:
    pass

if pymysql_ok:
    print("\n   ✅ RECOMENDAÇÃO: USAR PyMySQL")
    print("   pip install pymysql")
    print("   E usar o database.py com PyMySQL")
    
elif mysql_connector_ok:
    print("\n   ✅ RECOMENDAÇÃO: USAR mysql-connector-python com ssl_disabled=True")
    
else:
    print("\n   ❌ NENHUMA CONEXÃO FUNCIONOU")
    print("   Verifique:")
    print("   1. Se o MySQL está rodando (Services.msc)")
    print("   2. Se o usuário e senha estão corretos")
    print("   3. Se o banco de dados 'validapy' existe")
    print("   4. Se o firewall está permitindo a porta 3306")

print("\n" + "=" * 60)
print("🏁 TESTE FINALIZADO")
print("=" * 60)