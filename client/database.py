import mysql.connector
from mysql.connector import Error

def conectar_banco():
    """Faz a ponte entre o Python e o XAMPP"""
    try:
        conexao = mysql.connector.connect(
            host='localhost',
            user='root',      # Padrão XAMPP
            password='',      # Padrão XAMPP (vazio)
            database='chat_db'
        )
        if conexao.is_connected():
            return conexao
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        return None

def registrar_usuario_db(nome, senha):
    """Exemplo de função para salvar novo usuário"""
    conn = conectar_banco()
    if conn:
        try:
            cursor = conn.cursor()
            query = "INSERT INTO usuarios (nome_usuario, senha) VALUES (%s, %s)"
            cursor.execute(query, (nome, senha))
            conn.commit()
            print(f"Usuário {nome} registrado com sucesso!")
        except Error as e:
            print(f"Erro no registro: {e}")
        finally:
            conn.close()

def salvar_historico_local(usuario, msg):
    """Salva a conversa na tabela historico_local"""
    conn = conectar_banco()
    if conn:
        cursor = conn.cursor()
        query = "INSERT INTO historico_local (usuario, mensagem) VALUES (%s, %s)"
        cursor.execute(query, (usuario, msg))
        conn.commit()
        conn.close()