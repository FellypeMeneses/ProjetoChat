import os
import json
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.backends import default_backend

class SessaoP2P:
    def __init__(self):
        self.chave_aes = None
        self.chave_hmac = None
        self.salt = None
        self.chave_privada_ecdh = None
        self.handshake_completo = False
    
    def iniciar_handshake(self, chave_publica_remota_bytes):
        self.chave_privada_ecdh = ec.generate_private_key(ec.SECP256R1(), default_backend())
        chave_publica_local = self.chave_privada_ecdh.public_key()
        self.salt = os.urandom(32)
        
        chave_publica_remota = serialization.load_pem_public_key(
            chave_publica_remota_bytes, backend=default_backend()
        )
        
        chave_compartilhada = self.chave_privada_ecdh.exchange(ec.ECDH(), chave_publica_remota)
        
        hkdf = HKDF(algorithm=hashes.SHA256(), length=64, salt=self.salt, info=b"p2p-chat")
        chaves = hkdf.derive(chave_compartilhada)
        
        self.chave_aes = chaves[:32]
        self.chave_hmac = chaves[32:]
        self.handshake_completo = True
        
        return chave_publica_local, self.salt
    
    def finalizar_handshake(self, chave_publica_remota_bytes, salt):
        self.salt = salt
        self.chave_privada_ecdh = ec.generate_private_key(ec.SECP256R1(), default_backend())
        chave_publica_local = self.chave_privada_ecdh.public_key()
        
        chave_publica_remota = serialization.load_pem_public_key(
            chave_publica_remota_bytes, backend=default_backend()
        )
        
        chave_compartilhada = self.chave_privada_ecdh.exchange(ec.ECDH(), chave_publica_remota)
        
        hkdf = HKDF(algorithm=hashes.SHA256(), length=64, salt=self.salt, info=b"p2p-chat")
        chaves = hkdf.derive(chave_compartilhada)
        
        self.chave_aes = chaves[:32]
        self.chave_hmac = chaves[32:]
        self.handshake_completo = True
        
        return chave_publica_local
    
    def cifrar(self, texto):
        if not self.handshake_completo:
            raise ValueError("Handshake não completo")
        
        iv = os.urandom(12)
        cipher = Cipher(algorithms.AES(self.chave_aes), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        cifrado = encryptor.update(texto.encode()) + encryptor.finalize()
        
        h = hmac.HMAC(self.chave_hmac, hashes.SHA256(), backend=default_backend())
        h.update(iv + cifrado)
        
        return {
            "iv": iv.hex(),
            "tag": encryptor.tag.hex(),
            "cifrado": cifrado.hex(),
            "mac": h.finalize().hex()
        }
    
    def decifrar(self, pacote):
        if not self.handshake_completo:
            raise ValueError("Handshake não completo")
        
        iv = bytes.fromhex(pacote["iv"])
        tag = bytes.fromhex(pacote["tag"])
        cifrado = bytes.fromhex(pacote["cifrado"])
        mac = bytes.fromhex(pacote["mac"])
        
        h = hmac.HMAC(self.chave_hmac, hashes.SHA256(), backend=default_backend())
        h.update(iv + cifrado)
        h.verify(mac)
        
        cipher = Cipher(algorithms.AES(self.chave_aes), modes.GCM(iv, tag), backend=default_backend())
        return cipher.decryptor().update(cifrado).decode()