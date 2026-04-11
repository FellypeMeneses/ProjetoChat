import mysql.connector

def obter_conexao():
    """Cria a ponte de conexão com o MySQL do XAMPP"""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="chat_db"
    )

def registrar_usuario(nome, senha):
    """Verifica se o usuário existe e insere no banco"""
    try:
        conn = obter_conexao()
        cursor = conn.cursor()

        # Verifica se o nome de usuário já está em uso
        cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (nome,))
        if cursor.fetchone():
            return False, "Usuário já existe!"
        
        # Se não existir, cadastra
        cursor.execute("INSERT INTO usuarios (nome_usuario, senha) VALUES (%s, %s)", (nome, senha))
        conn.commit()
        return True, "Cadastro realizado com sucesso!"
    except Exception as e:
        return False, f"Erro no banco: {e}"
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def validar_login(nome, senha):
    """Verifica credenciais e muda o status para ONLINE"""
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True) # dictionary=True faz o banco devolver os dados com os nomes das colunas
        
        cursor.execute("SELECT * FROM usuarios WHERE nome_usuario = %s AND senha = %s", (nome, senha))
        usuario = cursor.fetchone()
        
        if usuario:
            # Atualiza status para online no banco
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
    """Muda o status do usuário para OFFLINE quando ele fecha o app ou sai"""
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET status = 'offline' WHERE nome_usuario = %s", (nome_usuario,))
        conn.commit()
    except Exception as e:
        print(f"Erro ao atualizar status offline: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def obter_lista_contatos(usuario_atual):
    """Busca todos os usuários do banco, ignorando o próprio usuário logado"""
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        
        # Seleciona nome e status, ignorando quem fez o pedido
        cursor.execute("SELECT nome_usuario, status FROM usuarios WHERE nome_usuario != %s", (usuario_atual,))
        contatos = cursor.fetchall()
        
        return True, contatos
    except Exception as e:
        return False, str(e)
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()