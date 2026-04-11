import mysql.connector

def conectar():
    """Conecta ao MySQL e garante que a tabela de histórico do cliente existe"""
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="chat_db"
    )
    cursor = conn.cursor()
    
    # Cria a tabela no XAMPP se ela não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_cliente (
            id INT AUTO_INCREMENT PRIMARY KEY,
            dono_do_app VARCHAR(50),
            contato VARCHAR(50),
            remetente VARCHAR(50),
            mensagem TEXT,
            data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn, cursor

def salvar_mensagem(dono_do_app, contato, remetente, mensagem):
    """Guarda a mensagem no MySQL (Tabela de Histórico do Cliente)"""
    try:
        conn, cursor = conectar()
        query = "INSERT INTO historico_cliente (dono_do_app, contato, remetente, mensagem) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (dono_do_app, contato, remetente, mensagem))
        conn.commit()
    except Exception as e:
        print(f"Erro ao salvar histórico no MySQL: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def carregar_mensagens(dono_do_app, contato):
    """Busca o histórico no MySQL quando o chat é aberto"""
    try:
        conn, cursor = conectar()
        # Busca as mensagens e ordena pelo ID (da mais antiga para a mais nova)
        query = "SELECT remetente, mensagem FROM historico_cliente WHERE dono_do_app = %s AND contato = %s ORDER BY id ASC"
        cursor.execute(query, (dono_do_app, contato))
        resultados = cursor.fetchall()
        return resultados
    except Exception as e:
        print(f"Erro ao carregar histórico do MySQL: {e}")
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
    # ... (mantenha as funções conectar, salvar_mensagem e carregar_mensagens que já estão lá) ...

def excluir_mensagem_bd(dono_do_app, contato, remetente, mensagem):
    """Apaga a mensagem do MySQL permanentemente"""
    try:
        conn, cursor = conectar()
        # O LIMIT 1 garante que, se houver mensagens repetidas, apague apenas uma por vez
        query = "DELETE FROM historico_cliente WHERE dono_do_app = %s AND contato = %s AND remetente = %s AND mensagem = %s LIMIT 1"
        cursor.execute(query, (dono_do_app, contato, remetente, mensagem))
        conn.commit()
    except Exception as e:
        print(f"Erro ao excluir no BD: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def editar_mensagem_bd(dono_do_app, contato, remetente, mensagem_antiga, mensagem_nova):
    """Atualiza o texto da mensagem no MySQL permanentemente"""
    try:
        conn, cursor = conectar()
        query = "UPDATE historico_cliente SET mensagem = %s WHERE dono_do_app = %s AND contato = %s AND remetente = %s AND mensagem = %s LIMIT 1"
        cursor.execute(query, (mensagem_nova, dono_do_app, contato, remetente, mensagem_antiga))
        conn.commit()
    except Exception as e:
        print(f"Erro ao editar no BD: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()