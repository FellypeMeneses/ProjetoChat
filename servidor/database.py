import mysql.connector
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Inicializa o gerador de Hash Argon2 para segurança de senhas
ph = PasswordHasher()

def obter_conexao():
    """Cria e retorna a conexão com o banco de dados MySQL."""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="chat_db"
    )

def registrar_usuario(nome, senha, chave_publica_hex):
    """Regista um novo utilizador guardando a senha em hash e a chave pública Ed25519."""
    try:
        conn = obter_conexao()
        cursor = conn.cursor()
        
        # O Argon2 gera o hash da senha automaticamente
        hash_senha = ph.hash(senha)
        
        # Inserimos a chave pública como uma string Hexadecimal
        sql = "INSERT INTO usuarios (nome_usuario, senha, chave_publica) VALUES (%s, %s, %s)"
        cursor.execute(sql, (nome, hash_senha, chave_publica_hex))
        
        conn.commit()
        return True, "Usuário registado com sucesso com chave Ed25519!"
    except mysql.connector.IntegrityError:
        return False, "Esse utilizador já existe! Escolha outro nome."
    except Exception as e:
        return False, f"Erro no banco: {e}"
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def obter_chave_publica(nome_usuario):
    """
    Busca a chave pública de um utilizador no banco de dados.
    Esta é a função que faltava e que causava o erro no servidor.
    """
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT chave_publica FROM usuarios WHERE nome_usuario = %s", (nome_usuario,))
        resultado = cursor.fetchone()
        
        if resultado:
            return resultado['chave_publica']
        return None
    except Exception as e:
        print(f"Erro ao obter chave pública: {e}")
        return None
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def atualizar_chave_publica(nome_usuario, nova_chave_publica, senha):
    """Atualiza chave pública (novo dispositivo) - verifica senha primeiro."""
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
            return True, "Chave pública atualizada."
        return False, "Usuário não encontrado."
    except VerifyMismatchError:
        return False, "Senha incorreta."
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def validar_login(nome, senha):
    """Valida as credenciais do utilizador usando Argon2 e atualiza o status para online."""
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM usuarios WHERE nome_usuario = %s", (nome,))
        usuario = cursor.fetchone()
        
        if usuario:
            # Verifica a senha usando o Argon2
            ph.verify(usuario['senha'], senha)

            # Verifica se o hash precisa de ser fortalecido (re-hash)
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
    """Marca o utilizador como offline no banco de dados."""
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
    """Retorna a lista de todos os utilizadores registados e os seus status."""
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
    """Garante que a tabela de mensagens offline existe ao iniciar o servidor."""
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
    """Guarda uma mensagem cifrada quando o destinatário está offline."""
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
    """Busca as mensagens retidas e apaga-as do banco de dados após a entrega."""
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
    """Remove permanentemente a conta de um utilizador."""
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