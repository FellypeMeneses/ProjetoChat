from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import os

def gerar_par_chaves_ed25519():
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key

def salvar_chave_privada(private_key, arquivo="chave_privada.pem", senha=None):
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
    with open(arquivo, "rb") as f:
        pem_data = f.read()
    return serialization.load_pem_private_key(
        pem_data, 
        password=senha.encode() if senha else None, 
        backend=default_backend()
    )

def obter_chave_publica_bytes(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

def carregar_chave_publica_bytes(public_key_bytes):
    return serialization.load_pem_public_key(
        public_key_bytes,
        backend=default_backend()
    )

def assinar_mensagem(private_key, mensagem_bytes):
    return private_key.sign(mensagem_bytes)

def verificar_assinatura(public_key, mensagem_bytes, assinatura):
    try:
        public_key.verify(assinatura, mensagem_bytes)
        return True
    except Exception:
        return False