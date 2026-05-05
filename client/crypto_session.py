import time
import os
import json
from cryptography.hazmat.primitives.asymmetric import ec # Mudou de 'dh' para 'ec' (Elliptic Curve)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.backends import default_backend

class SessaoCriptografada:
    def __init__(self):
        self.chave_aes = None  # Chave 1 (256 bits)
        self.chave_hmac = None # Chave 2 (256 bits)
        self.salt = None
        self.private_key_dh = None 
        self.contador_mensagens = 0
        self.inicio_sessao = None
        
    def iniciar_handshake_cliente(self):
        """Cliente inicia ECDH com servidor"""
        
        # Gera par de chaves usando a Curva Elíptica P-256 (padrão e ultra segura)
        self.private_key_dh = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key = self.private_key_dh.public_key()
        
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
        
        # Calcula chave compartilhada usando o algoritmo ECDH
        chave_compartilhada = self.private_key_dh.exchange(ec.ECDH(), public_key_servidor)
        
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
        
        # Gera par de chaves ECDH do servidor
        self.private_key_dh = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key = self.private_key_dh.public_key()
        
        # Carrega chave pública do cliente
        public_key_cliente = serialization.load_pem_public_key(
            public_key_cliente_bytes,
            backend=default_backend()
        )
        
        # Calcula chave compartilhada usando ECDH
        chave_compartilhada = self.private_key_dh.exchange(ec.ECDH(), public_key_cliente)
        
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
        mensagem_json = json.dumps(dados_dict)
        mensagem_bytes = mensagem_json.encode('utf-8')
        
        iv = os.urandom(12)
        
        cipher = Cipher(algorithms.AES(self.chave_aes), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        texto_cifrado = encryptor.update(mensagem_bytes) + encryptor.finalize()
        
        h = hmac.HMAC(self.chave_hmac, hashes.SHA256(), backend=default_backend())
        h.update(iv + texto_cifrado)
        mac = h.finalize()
        
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
        
        h = hmac.HMAC(self.chave_hmac, hashes.SHA256(), backend=default_backend())
        h.update(iv + texto_cifrado)
        try:
            h.verify(mac_recebido)
        except:
            raise ValueError("HMAC inválido! Mensagem pode ter sido alterada.")
        
        cipher = Cipher(algorithms.AES(self.chave_aes), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        mensagem_bytes = decryptor.update(texto_cifrado) + decryptor.finalize()
        
        return json.loads(mensagem_bytes.decode('utf-8'))
    
    def precisa_renovar(self):
        """Verifica se precisa renovar chaves (60 min ou 100 msgs)"""
        tempo_passado = time.time() - self.inicio_sessao
        return tempo_passado > 3600 or self.contador_mensagens > 100
    
    def cifrar_evento(self, evento, dados_extra=None):
        """Cifra eventos leves como 'digitando'"""
        msg = {"tipo": evento}
        if dados_extra:
            msg.update(dados_extra)
        return self.cifrar_mensagem(msg)

    def decifrar_evento(self, pacote):
        """Decifra eventos"""
        return self.decifrar_mensagem(pacote)