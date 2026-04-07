import mysql.connector

def obter_conexao():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="chat_db"
    )

def registrar_usuario(nome, senha):
    try:
        conn = obter_conexao()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (nome,))
        if cursor.fetchone():
            return False, "Usuário já existe!"
        
        cursor.execute("INSERT INTO usuarios (nome_usuario, senha) VALUES (%s, %s)", (nome, senha))
        conn.commit()
        return True, "Cadastro realizado com sucesso!"
    except Exception as e:
        return False, f"Erro no banco: {e}"
    finally:
        conn.close()

def validar_login(nome, senha):
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE nome_usuario = %s AND senha = %s", (nome, senha))
        usuario = cursor.fetchone()
        if usuario:
            # Atualiza status para online
            cursor.execute("UPDATE usuarios SET status = 'online' WHERE id = %s", (usuario['id'],))
            conn.commit()
            return True, usuario
        return False, "Usuário ou senha incorretos."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def logout_db(usuario_id):
    conn = obter_conexao()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET status = 'offline' WHERE id = %s", (usuario_id,))
    conn.commit()
    conn.close()