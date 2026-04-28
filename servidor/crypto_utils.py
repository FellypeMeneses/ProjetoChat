from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import os

#ECC (usar por ser mais leve e rápido que RSA para chat)

def gerar_par_chaves_ecc():
    
    #Gera par de chaves ECC (Curve25519)
    
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()
    return private_key, public_key

def salvar_chave_privada(private_key, arquivo="chave_privada.pem", senha=None):
    
    #Salva chave privada criptografada (opcional)
    if senha:
        encryption = serialization.BestAvailableEncryption(senha.encode())
    else:
        encryption = serialization.NoEncryption()
    
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption
    )
    with open(arquivo, "wb") as f:
        f.write(pem)

def carregar_chave_privada(arquivo="chave_privada.pem", senha=None):
    
    """Carrega chave privada do arquivo"""
    with open(arquivo, "rb") as f:
        pem_data = f.read()
    
    if senha:
        return serialization.load_pem_private_key(pem_data, password=senha.encode(), backend=default_backend())
    else:
        return serialization.load_pem_private_key(pem_data, password=None, backend=default_backend())

def obter_chave_publica_bytes(public_key):
    """Converte chave pública para bytes (para enviar ao servidor)"""
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

def assinar_mensagem(private_key, mensagem_bytes):
    """Assina uma mensagem com a chave privada (ECDSA)"""
    signature = private_key.sign(
        mensagem_bytes,
        ec.ECDSA(hashes.SHA256())
    )
    return signature

def verificar_assinatura(public_key, mensagem_bytes, assinatura):
    """Verifica assinatura com chave pública"""
    try:
        public_key.verify(
            assinatura,
            mensagem_bytes,
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except:
        return False