from datetime import time

from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend
import os
import json

# Parâmetros DH (usar parâmetros padrão seguros)

def gerar_parametros_dh():
    """Gera parâmetros DH (usar uma vez e reutilizar)"""
    return dh.generate_parameters(generator=2, key_size=2048, backend=default_backend())

# Parâmetros fixos para o servidor (reutilizar)

PARAMETROS_DH = gerar_parametros_dh()

class SessaoCriptografada:
    def __init__(self):
        self.chave_aes = None  # Chave 1 (256 bits)
        self.chave_hmac = None # Chave 2 (256 bits)
        self.salt = None
        self.chave_dh = None
        self.contador_mensagens = 0
        self.inicio_sessao = None
        
    def iniciar_handshake_cliente(self):
        """Cliente inicia DHE com servidor"""
        
        # Gera par de chaves DH (privada + pública)
        
        private_key = PARAMETROS_DH.generate_private_key()
        public_key = private_key.public_key()
        
        # Gera salt aleatório (32 bytes)
        self.salt = os.urandom(32)
        
        # Retorna chave pública e salt para enviar ao servidor
        
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_key_bytes, self.salt
    
    def finalizar_handshake_cliente(self, public_key_servidor_bytes):
        """Cliente finaliza handshake com chave pública do servidor"""
        # Carrega chave pública do servidor
        public_key_servidor = serialization.load_pem_public_key(
            public_key_servidor_bytes,
            backend=default_backend()
        )
        
        # Calcula chave compartilhada DH
        chave_compartilhada = private_key.exchange(public_key_servidor)
        
        # Deriva chaves com HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=64,  # 512 bits (256 para AES + 256 para HMAC)
            salt=self.salt,
            info=b"chat-session",
            backend=default_backend()
        )
        chaves = hkdf.derive(chave_compartilhada)
        
        self.chave_aes = chaves[:32]   # Primeiros 32 bytes = AES-256
        self.chave_hmac = chaves[32:]  # Últimos 32 bytes = HMAC
        self.inicio_sessao = time.time()
        self.contador_mensagens = 0
        
        return True
    
    def iniciar_handshake_servidor(self, public_key_cliente_bytes, salt_cliente):
        """Servidor completa handshake iniciado pelo cliente"""
        self.salt = salt_cliente
        
        # Gera par de chaves DH do servidor
        private_key = PARAMETROS_DH.generate_private_key()
        public_key = private_key.public_key()
        
        # Carrega chave pública do cliente
        public_key_cliente = serialization.load_pem_public_key(
            public_key_cliente_bytes,
            backend=default_backend()
        )
        
        # Calcula chave compartilhada
        chave_compartilhada = private_key.exchange(public_key_cliente)
        
        # Deriva chaves
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=64,
            salt=self.salt,
            info=b"chat-session",
            backend=default_backend()
        )
        chaves = hkdf.derive(chave_compartilhada)
        
        self.chave_aes = chaves[:32]
        self.chave_hmac = chaves[32:]
        self.inicio_sessao = time.time()
        self.contador_mensagens = 0
        
        # Retorna chave pública do servidor
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_key_bytes
    
    def cifrar_mensagem(self, dados_dict):
        """Cifra e autentica mensagem com AES-GCM + HMAC"""
        # Converte dict para JSON
        mensagem_json = json.dumps(dados_dict)
        mensagem_bytes = mensagem_json.encode('utf-8')
        
        # Gera IV aleatório (12 bytes para GCM)
        iv = os.urandom(12)
        
        # Cifra com AES-GCM
        cipher = Cipher(algorithms.AES(self.chave_aes), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        texto_cifrado = encryptor.update(mensagem_bytes) + encryptor.finalize()
        
        # Gera HMAC do texto cifrado + IV
        h = hmac.HMAC(self.chave_hmac, hashes.SHA256(), backend=default_backend())
        h.update(iv + texto_cifrado)
        mac = h.finalize()
        
        # Retorna pacote
        return {
            "iv": iv.hex(),
            "tag": encryptor.tag.hex(),
            "cifrado": texto_cifrado.hex(),
            "mac": mac.hex()
        }
    
    def decifrar_mensagem(self, pacote):
        """Decifra e verifica autenticidade"""
        iv = bytes.fromhex(pacote["iv"])
        tag = bytes.fromhex(pacote["tag"])
        texto_cifrado = bytes.fromhex(pacote["cifrado"])
        mac_recebido = bytes.fromhex(pacote["mac"])
        
        # Verifica HMAC primeiro
        h = hmac.HMAC(self.chave_hmac, hashes.SHA256(), backend=default_backend())
        h.update(iv + texto_cifrado)
        try:
            h.verify(mac_recebido)
        except:
            raise ValueError("HMAC inválido! Mensagem pode ter sido alterada.")
        
        # Decifra AES-GCM
        cipher = Cipher(algorithms.AES(self.chave_aes), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        mensagem_bytes = decryptor.update(texto_cifrado) + decryptor.finalize()
        
        # Converte JSON de volta para dict
        return json.loads(mensagem_bytes.decode('utf-8'))
    
    def precisa_renovar(self):
        """Verifica se precisa renovar chaves (60 min ou 100 msgs)"""
        import time
        tempo_passado = time.time() - self.inicio_sessao
        return tempo_passado > 3600 or self.contador_mensagens > 100
    
    # Adicione este método à classe SessaoCriptografada
def cifrar_evento(self, evento, dados_extra=None):
    """Cifra eventos leves como 'digitando'"""
    msg = {"tipo": evento}
    if dados_extra:
        msg.update(dados_extra)
    return self.cifrar(msg)

def decifrar_evento(self, pacote):
    """Decifra eventos"""
    return self.decifrar(pacote)