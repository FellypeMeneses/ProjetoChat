import mysql.connector
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Inicializa o gerador de Hash Argon2
ph = PasswordHasher()

def obter_conexao():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="chat_db"
    )

def registrar_usuario(nome, senha, chave_publica):
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        
        # 1. Verifica se o utilizador já existe (ignorando maiúsculas/minúsculas)
        cursor.execute("SELECT id FROM usuarios WHERE LOWER(nome_usuario) = LOWER(%s)", (nome,))
        if cursor.fetchone():
            return False, "Esse utilizador já existe! Tente outro nome."
        
        # 2. Gera o hash seguro da senha com Argon2
        hash_senha = ph.hash(senha)
        
        # 3. Salva no banco de dados na coluna 'senha'
        cursor.execute("INSERT INTO usuarios (nome_usuario, senha, status, chave_publica) VALUES (%s, %s, 'offline', %s)", (nome, hash_senha, chave_publica))
        conn.commit()
        return True, "Cadastro realizado com sucesso!"
    except Exception as e:
        return False, f"Erro ao registrar no banco: {e}"
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def atualizar_chave_publica(nome_usuario, nova_chave_publica, senha):
    """Atualiza chave pública (novo dispositivo) - verifica senha primeiro"""
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT senha FROM usuarios WHERE nome_usuario = %s", (nome_usuario,))
        usuario = cursor.fetchone()
        
        if usuario:
            ph.verify(usuario['senha'], senha)
            cursor.execute("UPDATE usuarios SET chave_publica = %s WHERE nome_usuario = %s",
                        (nova_chave_publica, nome_usuario))
            conn.commit()
            return True, "Chave pública atualizada"
        return False, "Usuário não encontrado"
    except VerifyMismatchError:
        return False, "Senha incorreta"
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def validar_login(nome, senha):
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM usuarios WHERE nome_usuario = %s", (nome,))
        usuario = cursor.fetchone()
        
        if usuario:
            # Verifica a senha usando o Argon2
            ph.verify(usuario['senha'], senha)

            # Verifica se precisa de re-hash
            if ph.check_needs_rehash(usuario['senha']):
                novo_hash = ph.hash(senha)
                cursor.execute("UPDATE usuarios SET senha = %s WHERE id = %s", (novo_hash, usuario['id']))
                conn.commit()

            cursor.execute("UPDATE usuarios SET status = 'online' WHERE id = %s", (usuario['id'],))
            conn.commit()
            return True, usuario
        else:
            return False, "Utilizador não encontrado. Verifique o nome introduzido."
    except VerifyMismatchError:
        return False, "Palavra-passe incorreta."
    except Exception as e:
        return False, f"Erro interno: {e}"
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def logout_db(nome_usuario):
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET status = 'offline' WHERE nome_usuario = %s", (nome_usuario,))
        conn.commit()
    except Exception:
        pass
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def obter_lista_contatos(usuario_atual):
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nome_usuario, status FROM usuarios WHERE nome_usuario != %s", (usuario_atual,))
        contatos = cursor.fetchall()
        return True, contatos
    except Exception as e:
        return False, str(e)
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

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
    except Exception:
        pass
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def salvar_offline(remetente, destinatario, conteudo):
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
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
    except Exception:
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def excluir_conta_db(nome_usuario):
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios WHERE nome_usuario = %s", (nome_usuario,))
        conn.commit()
        return True, "Conta excluída com sucesso."
    except Exception as e:
        return False, f"Erro ao excluir conta: {e}"
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()