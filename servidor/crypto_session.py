import time
import os
import json
import random
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.backends import default_backend

class SessaoCriptografada:
    def __init__(self):
        self.chave_aes = None  # Chave 1 (256 bits) para AES-256
        self.chave_hmac = None # Chave 2 (256 bits) para HMAC
        self.salt = None
        self.private_key_dh = None 
        self.contador_mensagens = 0
        self.inicio_sessao = None
        
        # Atributos para limites de renovação (Requisito Alan Turing)
        self.limite_tempo = 3600  # Padrão 60 min
        self.limite_msgs = 100   # Padrão 100 mensagens
        
    def configurar_limites_aleatorios(self):
        """
        Define limites variáveis para a expiração da sessão.
        Requisito: Aleatório entre 30 e 60 min, e entre 50 e 100 msgs.
        """
        self.limite_tempo = random.randint(1800, 3600)
        self.limite_msgs = random.randint(50, 100)
        print(f"[*] Segurança: Sessão expirará em {self.limite_tempo//60}min ou {self.limite_msgs} mensagens.")

    def iniciar_handshake_cliente(self):
        """Cliente inicia ECDH (Diffie-Hellman Efêmero) com servidor"""
        self.private_key_dh = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key = self.private_key_dh.public_key()
        self.salt = os.urandom(32)
        
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_key_bytes, self.salt
    
    def finalizar_handshake_cliente(self, public_key_servidor_bytes):
        """Cliente finaliza handshake e deriva as chaves usando HKDF"""
        public_key_servidor = serialization.load_pem_public_key(
            public_key_servidor_bytes,
            backend=default_backend()
        )
        
        chave_compartilhada = self.private_key_dh.exchange(ec.ECDH(), public_key_servidor)
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=64,  # 512 bits (256 para AES + 256 para HMAC)
            salt=self.salt,
            info=b"chat-session",
            backend=default_backend()
        )
        chaves = hkdf.derive(chave_compartilhada)
        
        self.chave_aes = chaves[:32]   # Chave 1: AES-256
        self.chave_hmac = chaves[32:]  # Chave 2: HMAC-256
        self.inicio_sessao = time.time()
        self.contador_mensagens = 0
        return True
    
    def iniciar_handshake_servidor(self, public_key_cliente_bytes, salt_cliente):
        """Servidor completa handshake iniciado pelo cliente"""
        self.salt = salt_cliente
        self.private_key_dh = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key = self.private_key_dh.public_key()
        
        public_key_cliente = serialization.load_pem_public_key(
            public_key_cliente_bytes,
            backend=default_backend()
        )
        
        chave_compartilhada = self.private_key_dh.exchange(ec.ECDH(), public_key_cliente)
        
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
        
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_key_bytes
    
    def cifrar_mensagem(self, dados_dict):
        """Cifra e autentica mensagem com AES-256 + HMAC"""
        mensagem_json = json.dumps(dados_dict)
        mensagem_bytes = mensagem_json.encode('utf-8')
        
        iv = os.urandom(12) 
        
        cipher = Cipher(algorithms.AES(self.chave_aes), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        texto_cifrado = encryptor.update(mensagem_bytes) + encryptor.finalize()
        
        h = hmac.HMAC(self.chave_hmac, hashes.SHA256(), backend=default_backend())
        h.update(iv + texto_cifrado)
        mac = h.finalize() 
        
        self.contador_mensagens += 1
        return {
            "iv": iv.hex(),
            "tag": encryptor.tag.hex(),
            "cifrado": texto_cifrado.hex(),
            "mac": mac.hex()
        }
    
    def decifrar_mensagem(self, pacote):
        """Decifra e verifica integridade/autenticidade"""
        iv = bytes.fromhex(pacote["iv"])
        tag = bytes.fromhex(pacote["tag"])
        texto_cifrado = bytes.fromhex(pacote["cifrado"])
        mac_recebido = bytes.fromhex(pacote["mac"])
        
        h = hmac.HMAC(self.chave_hmac, hashes.SHA256(), backend=default_backend())
        h.update(iv + texto_cifrado)
        try:
            h.verify(mac_recebido)
        except:
            raise ValueError("HMAC inválido! Mensagem descartada por segurança.")
        
        cipher = Cipher(algorithms.AES(self.chave_aes), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        mensagem_bytes = decryptor.update(texto_cifrado) + decryptor.finalize()
        
        return json.loads(mensagem_bytes.decode('utf-8'))
    
    def precisa_renovar(self):
        """Verifica se os limites da sessão efêmera foram atingidos"""
        if self.inicio_sessao is None: return False
        tempo_passado = time.time() - self.inicio_sessao
        return tempo_passado > self.limite_tempo or self.contador_mensagens >= self.limite_msgs