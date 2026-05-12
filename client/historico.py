import mysql.connector
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import base64

def obter_conexao():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="chat_db"
    )

def derivar_chave_local(senha):
    """Deriva a chave para o banco local (Requisito de segurança)"""
    salt = b'salt_fixo_local' 
    kdf_obj = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf_obj.derive(senha.encode()), salt

def salvar_mensagem_protegida(usuario_dono, contato, remetente, texto, chave_aes):
    """Cifra e salva na tabela historico_cliente"""
    try:
        # Usamos CTR para evitar o erro de 'CFB moved'
        nonce = os.urandom(16)
        cipher = Cipher(algorithms.AES(chave_aes), modes.CTR(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        texto_cifrado = encryptor.update(texto.encode()) + encryptor.finalize()

        # Guarda Nonce + Texto Cifrado
        conteudo_final = base64.b64encode(nonce + texto_cifrado).decode('utf-8')

        conn = obter_conexao()
        cursor = conn.cursor()
        sql = "INSERT INTO historico_cliente (usuario_dono, contato, remetente, conteudo) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (usuario_dono, contato, remetente, conteudo_final))
        conn.commit()
    except Exception as e:
        print(f"Erro ao salvar no banco: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

# Adicione ao historico.py

def carregar_historico_local(usuario_dono, contato, chave_aes):
    """Busca mensagens salvas localmente e decifra para exibição"""
    mensagens = []
    try:
        conn = obter_conexao()
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT remetente, conteudo, data_hora FROM historico_cliente WHERE usuario_dono = %s AND contato = %s ORDER BY data_hora ASC"
        cursor.execute(sql, (usuario_dono, contato))
        
        for linha in cursor.fetchall():
            try:
                import base64
                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                from cryptography.hazmat.backends import default_backend
                
                dados_brutos = base64.b64decode(linha['conteudo'])
                nonce, cifrado = dados_brutos[:16], dados_brutos[16:]
                
                cipher = Cipher(algorithms.AES(chave_aes), modes.CTR(nonce), backend=default_backend())
                decryptor = cipher.decryptor()
                texto = decryptor.update(cifrado) + decryptor.finalize()
                
                mensagens.append({
                    "remetente": linha['remetente'],
                    "texto": texto.decode('utf-8'),
                    "data": linha['data_hora']
                })
            except: continue
    finally:
        if 'conn' in locals() and conn.is_connected(): conn.close()
    return mensagens