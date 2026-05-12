import mysql.connector
from argon2 import PasswordHasher

ph = PasswordHasher()

def obter_conexao():
    return mysql.connector.connect(
        host="localhost", user="root", password="", database="chat_db"
    )

def registrar_usuario(nome, senha, chave_publica_hex):
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        hash_senha = ph.hash(senha)
        sql = "INSERT INTO usuarios (nome_usuario, senha, chave_publica, status) VALUES (%s, %s, %s, 'offline')"
        cursor.execute(sql, (nome, hash_senha, chave_publica_hex))
        conn.commit()
        return True, "Usuário registrado!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def login_db(nome, senha):
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT senha FROM usuarios WHERE nome_usuario = %s", (nome,))
        user = cursor.fetchone()
        if user and ph.verify(user['senha'], senha):
            return True, "Sucesso"
        return False, "Credenciais inválidas"
    except:
        return False, "Erro no login"
    finally:
        conn.close()

def atualizar_status(nome_usuario, status):
    """Atualiza o status para online/offline garantindo consistência"""
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        # Converte para lowercase para facilitar a lógica visual
        cursor.execute("UPDATE usuarios SET status = %s WHERE nome_usuario = %s", 
                       (status.lower(), nome_usuario))
        conn.commit()
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def atualizar_status(nome_usuario, status):
    """Atualiza o status para online/offline garantindo consistência"""
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        # Converte para lowercase para facilitar a lógica visual
        cursor.execute("UPDATE usuarios SET status = %s WHERE nome_usuario = %s", 
                       (status.lower(), nome_usuario))
        conn.commit()
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def salvar_offline(remetente, destinatario, conteudo):
    """Guarda mensagem na tabela mensagens_offline"""
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        # O conteúdo aqui já deve estar em JSON/Cifrado vindo do servidor
        sql = "INSERT INTO mensagens_offline (remetente, destinatario, conteudo) VALUES (%s, %s, %s)"
        cursor.execute(sql, (remetente, destinatario, conteudo))
        conn.commit()
    finally:
        conn.close()

def buscar_e_apagar_offline(destinatario):
    """Recupera mensagens pendentes e limpa a fila"""
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT remetente, conteudo FROM mensagens_offline WHERE destinatario = %s", (destinatario,))
        mensagens = cursor.fetchall()
        if mensagens:
            cursor.execute("DELETE FROM mensagens_offline WHERE destinatario = %s", (destinatario,))
            conn.commit()
        return mensagens
    except:
        return []
    finally:
        conn.close()
def obter_lista_contatos(usuario_atual):
    """Busca contatos ordenando pelos Online primeiro para um visual organizado"""
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        # SQL com ORDER BY para colocar quem está online no topo
        cursor.execute("""
            SELECT nome_usuario, status FROM usuarios 
            WHERE nome_usuario != %s 
            ORDER BY status DESC, nome_usuario ASC
        """, (usuario_atual,))
        return True, cursor.fetchall()
    except Exception:
        return False, []
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()