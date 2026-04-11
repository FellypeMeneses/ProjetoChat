import mysql.connector

def obter_conexao():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="chat_db"
    )

# --- FUNÇÕES DE USUÁRIO ---

def registrar_usuario(nome, senha):
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        # Usamos LOWER para evitar "Admin" e "admin" como usuários diferentes
        cursor.execute("SELECT id FROM usuarios WHERE LOWER(nome_usuario) = LOWER(%s)", (nome,))
        if cursor.fetchone():
            return False, "Usuário já existe!"
        
        cursor.execute("INSERT INTO usuarios (nome_usuario, senha, status) VALUES (%s, %s, 'offline')", (nome, senha))
        conn.commit()
        return True, "Cadastro realizado com sucesso!"
    except Exception as e:
        return False, f"Erro no banco: {e}"
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def validar_login(nome, senha):
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True) 
        cursor.execute("SELECT * FROM usuarios WHERE nome_usuario = %s AND senha = %s", (nome, senha))
        usuario = cursor.fetchone()
        if usuario:
            cursor.execute("UPDATE usuarios SET status = 'online' WHERE id = %s", (usuario['id'],))
            conn.commit()
            return True, usuario
        return False, "Usuário ou senha incorretos."
    except Exception as e:
        return False, str(e)
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def logout_db(nome_usuario):
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET status = 'offline' WHERE nome_usuario = %s", (nome_usuario,))
        conn.commit()
    except Exception as e:
        pass
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def obter_lista_contatos(usuario_atual):
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        # Seleciona apenas usuários que existem na tabela de usuários
        cursor.execute("SELECT nome_usuario, status FROM usuarios WHERE nome_usuario != %s", (usuario_atual,))
        contatos = cursor.fetchall()
        return True, contatos
    except Exception as e:
        return False, str(e)
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

# --- FUNÇÕES DE MENSAGENS OFFLINE ---

def criar_tabela_offline():
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mensagens_offline (
                id INT AUTO_INCREMENT PRIMARY KEY,
                remetente VARCHAR(50),
                destinatario VARCHAR(50),
                conteudo TEXT
            )
        ''')
        conn.commit()
    except Exception as e:
        pass
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def salvar_offline(remetente, destinatario, conteudo):
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        # SÓ salva se o destinatário ainda existir no banco de dados
        cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (destinatario,))
        if cursor.fetchone():
            cursor.execute("INSERT INTO mensagens_offline (remetente, destinatario, conteudo) VALUES (%s, %s, %s)", 
                           (remetente, destinatario, conteudo))
            conn.commit()
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def buscar_e_apagar_offline(destinatario):
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        
        # BUSCA REFINADA: Só pega mensagens de remetentes que ainda existem!
        # Isso evita que mensagens de "fantasmas" (excluídos) apareçam no chat
        query = """
            SELECT m.* FROM mensagens_offline m
            JOIN usuarios u ON m.remetente = u.nome_usuario
            WHERE m.destinatario = %s
        """
        cursor.execute(query, (destinatario,))
        mensagens = cursor.fetchall()
        
        if mensagens:
            cursor.execute("DELETE FROM mensagens_offline WHERE destinatario = %s", (destinatario,))
            conn.commit()
        return mensagens
    except Exception as e:
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

# --- NOVA FUNÇÃO: DELETAR USUÁRIO COMPLETAMENTE ---
def excluir_usuario_total(nome_usuario):
    """ Use esta função para apagar um usuário e limpar tudo dele """
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        # 1. Apaga mensagens offline dele ou para ele
        cursor.execute("DELETE FROM mensagens_offline WHERE remetente = %s OR destinatario = %s", (nome_usuario, nome_usuario))
        # 2. Apaga o usuário
        cursor.execute("DELETE FROM usuarios WHERE nome_usuario = %s", (nome_usuario,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao excluir: {e}")
        return False
    finally:
        conn.close()
    # Linha 151 aprox.
def excluir_conta_db(nome_usuario):
    try: # <--- O código abaixo deste try DEVE estar indentado
        conn = obter_conexao()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios WHERE nome_usuario = %s", (nome_usuario,))
        conn.commit()
        return True, "Conta excluída com sucesso."
    except Exception as e: # <--- O except deve estar alinhado com o try
        return False, f"Erro ao excluir conta: {e}"
    finally: # <--- O finally também alinhado com o try
        if 'conn' in locals() and conn.is_connected():
            conn.close()