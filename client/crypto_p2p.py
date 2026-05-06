import os
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
        self.private_key_ecdh = None
        self.handshake_completo = False
    
    # --- PASSO 1: O INICIADOR ---
    def iniciar_handshake_iniciador(self):
        """O Cliente A gera a sua chave efêmera (temporária) e o Salt."""
        self.private_key_ecdh = ec.generate_private_key(ec.SECP256R1(), default_backend())
        self.salt = os.urandom(32)
        
        pub_bytes = self.private_key_ecdh.public_key().public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pub_bytes, self.salt
    
    def finalizar_handshake_iniciador(self, pub_remota_bytes):
        """O Cliente A recebe a chave do Cliente B e cria o segredo matemático."""
        pub_remota = serialization.load_pem_public_key(pub_remota_bytes, backend=default_backend())
        chave_compartilhada = self.private_key_ecdh.exchange(ec.ECDH(), pub_remota)
        
        hkdf = HKDF(algorithm=hashes.SHA256(), length=64, salt=self.salt, info=b"p2p-chat", backend=default_backend())
        chaves = hkdf.derive(chave_compartilhada)
        self.chave_aes, self.chave_hmac = chaves[:32], chaves[32:]
        self.handshake_completo = True

    # --- PASSO 2: O RECEPTOR ---
    def responder_handshake(self, pub_remota_bytes, salt):
        """O Cliente B recebe a chave de A, gera a sua própria chave e cria o segredo."""
        self.salt = salt
        self.private_key_ecdh = ec.generate_private_key(ec.SECP256R1(), default_backend())
        pub_local_bytes = self.private_key_ecdh.public_key().public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        pub_remota = serialization.load_pem_public_key(pub_remota_bytes, backend=default_backend())
        chave_compartilhada = self.private_key_ecdh.exchange(ec.ECDH(), pub_remota)
        
        hkdf = HKDF(algorithm=hashes.SHA256(), length=64, salt=self.salt, info=b"p2p-chat", backend=default_backend())
        chaves = hkdf.derive(chave_compartilhada)
        self.chave_aes, self.chave_hmac = chaves[:32], chaves[32:]
        self.handshake_completo = True
        
        return pub_local_bytes

    # --- CRIPTOGRAFIA ---
    def cifrar_mensagem(self, texto):
        """Cifra a mensagem com AES-GCM e protege-a com HMAC (Confidencialidade + Integridade)."""
        if not self.handshake_completo: raise ValueError("Handshake incompleto")
        iv = os.urandom(12)
        cipher = Cipher(algorithms.AES(self.chave_aes), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        cifrado = encryptor.update(texto.encode('utf-8')) + encryptor.finalize()
        
        h = hmac.HMAC(self.chave_hmac, hashes.SHA256(), backend=default_backend())
        h.update(iv + cifrado)
        
        return {"iv": iv.hex(), "tag": encryptor.tag.hex(), "cifrado": cifrado.hex(), "mac": h.finalize().hex()}

    def decifrar_mensagem(self, pacote):
        """Decifra o pacote recebido verificando se a mensagem foi adulterada."""
        if not self.handshake_completo: raise ValueError("Handshake incompleto")
        iv = bytes.fromhex(pacote["iv"])
        tag = bytes.fromhex(pacote["tag"])
        cifrado = bytes.fromhex(pacote["cifrado"])
        mac_recebido = bytes.fromhex(pacote["mac"])
        
        h = hmac.HMAC(self.chave_hmac, hashes.SHA256(), backend=default_backend())
        h.update(iv + cifrado)
        h.verify(mac_recebido) # Se alguém adulterou a mensagem, o código para aqui com um erro.
        
        cipher = Cipher(algorithms.AES(self.chave_aes), modes.GCM(iv, tag), backend=default_backend())
        return (cipher.decryptor().update(cifrado) + cipher.decryptor().finalize()).decode('utf-8')