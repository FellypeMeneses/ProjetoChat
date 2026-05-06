from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import os

# ==========================================
# FUNÇÕES DE USO PRINCIPAL PELO SERVIDOR
# ==========================================

def carregar_chave_publica_bytes(public_key_bytes):
    """
    Pega na string/bytes da chave pública (vinda do banco de dados) 
    e transforma num objeto de chave Ed25519 que o Python consegue usar.
    """
    return serialization.load_pem_public_key(
        public_key_bytes,
        backend=default_backend()
    )

def verificar_assinatura(public_key, mensagem_bytes, assinatura):
    """
    Verifica se a assinatura digital enviada pelo cliente é válida para a mensagem (nonce).
    """
    try:
        # Tenta validar. Se a assinatura for falsa ou a mensagem foi alterada, 
        # a biblioteca cryptography gera um erro (Exception).
        public_key.verify(assinatura, mensagem_bytes)
        return True
    except Exception as e:
        print(f"Aviso de Segurança: Falha na verificação da assinatura. Detalhe: {e}")
        return False

# ==========================================
# FUNÇÕES AUXILIARES E DE PADRONIZAÇÃO
# (Mantidas para compatibilidade e caso o servidor precise gerar chaves no futuro)
# ==========================================

def gerar_par_chaves_ed25519():
    """Gera um novo par de chaves usando o algoritmo Ed25519."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key

def obter_chave_publica_bytes(public_key):
    """Converte o objeto da chave pública para o formato PEM (texto/bytes)."""
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

def assinar_mensagem(private_key, mensagem_bytes):
    """Assina uma mensagem usando a chave privada Ed25519."""
    return private_key.sign(mensagem_bytes)

def carregar_chave_privada(arquivo="chave_privada.pem", senha=None):
    """Lê uma chave privada de um arquivo PEM no disco."""
    with open(arquivo, "rb") as f:
        pem_data = f.read()
    return serialization.load_pem_private_key(
        pem_data, 
        password=senha.encode() if senha else None, 
        backend=default_backend()
    )