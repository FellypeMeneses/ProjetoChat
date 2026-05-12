import os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.backends import default_backend
import time
import random

class SessaoP2P:
    def __init__(self):
        self.contador_mensagens = 0
        self.inicio_sessao = None
        self.limite_tempo = 3600 
        self.limite_msgs = 100
        self.chave_aes = None
        self.chave_hmac = None
        self.salt = None
        self.private_key_ecdh = None
        self.handshake_completo = False
        self.id_sessao = None
        # CORREÇÃO CRÍTICA: Variável de estado adicionada para sincronizar o handshake
        self.aguardando = False 

    # --- PASSO 1: O INICIADOR ---
    def configurar_limites_aleatorios(self):
        """Requisito: Aleatório entre 30-60 min e 50-100 msgs [cite: 81, 82]"""
        self.limite_tempo = random.randint(1800, 3600)
        self.limite_msgs = random.randint(50, 100)
        self.inicio_sessao = time.time()
        self.contador_mensagens = 0

    def precisa_renovar(self):
        """Verifica se a sessão P2P atingiu os limites efêmeros [cite: 74, 146]"""
        if not self.handshake_completo or self.inicio_sessao is None: return False
        tempo_passado = time.time() - self.inicio_sessao
        return tempo_passado > self.limite_tempo or self.contador_mensagens >= self.limite_msgs
    def iniciar_handshake_iniciador(self):
        """O Cliente A gera a sua chave efêmera e cria um Token Único."""
        self.id_sessao = os.urandom(8).hex() 
        self.private_key_ecdh = ec.generate_private_key(ec.SECP256R1(), default_backend())
        self.salt = os.urandom(32)
        
        # Bloqueia a sessão enquanto aguarda a resposta do destinatário
        self.aguardando = True 
        
        pub_bytes = self.private_key_ecdh.public_key().public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return self.id_sessao, pub_bytes, self.salt
    
    def finalizar_handshake_iniciador(self, pub_remota_bytes, id_sessao_recebido):
        """Verifica o Token antes de concluir a matemática."""
        if self.id_sessao and id_sessao_recebido != self.id_sessao:
            raise ValueError("ID de sessão incompatível. Ignorando pacote atrasado.")
            
        pub_remota = serialization.load_pem_public_key(pub_remota_bytes, backend=default_backend())
        chave_compartilhada = self.private_key_ecdh.exchange(ec.ECDH(), pub_remota)
        
        hkdf = HKDF(algorithm=hashes.SHA256(), length=64, salt=self.salt, info=b"p2p-chat", backend=default_backend())
        chaves = hkdf.derive(chave_compartilhada)
        self.chave_aes, self.chave_hmac = chaves[:32], chaves[32:]
        
        self.handshake_completo = True
        self.aguardando = False # Liberta o estado para permitir o envio de mensagens

    # --- PASSO 2: O RECEPTOR ---
    def responder_handshake(self, pub_remota_bytes, salt, id_sessao_recebido):
        """O Cliente B adota o Token de A e gera a resposta."""
        self.id_sessao = id_sessao_recebido
        self.salt = salt
        self.private_key_ecdh = ec.generate_private_key(ec.SECP256R1(), default_backend())
        
        # O recetor não aguarda, pois finaliza a sua parte no ato
        self.aguardando = False 
        
        pub_local_bytes = self.private_key_ecdh.public_key().public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        pub_remota = serialization.load_pem_public_key(pub_remota_bytes, backend=default_backend())
        chave_compartilhada = self.private_key_ecdh.exchange(ec.ECDH(), pub_remota)
        
        hkdf = HKDF(algorithm=hashes.SHA256(), length=64, salt=self.salt, info=b"p2p-chat", backend=default_backend())
        chaves = hkdf.derive(chave_compartilhada)
        self.chave_aes, self.chave_hmac = chaves[:32], chaves[32:]
        self.handshake_completo = True
        
        return self.id_sessao, pub_local_bytes

    # --- CRIPTOGRAFIA ---
    def cifrar_mensagem(self, texto):
        if not self.handshake_completo: raise ValueError("Handshake incompleto")
        iv = os.urandom(12)
        cipher = Cipher(algorithms.AES(self.chave_aes), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        cifrado = encryptor.update(texto.encode('utf-8')) + encryptor.finalize()
        
        h = hmac.HMAC(self.chave_hmac, hashes.SHA256(), backend=default_backend())
        h.update(iv + cifrado)
        
        return {"iv": iv.hex(), "tag": encryptor.tag.hex(), "cifrado": cifrado.hex(), "mac": h.finalize().hex()}

    def decifrar_mensagem(self, pacote):
        if not self.handshake_completo: raise ValueError("Handshake incompleto")
        try:
            # Converte as strings hexadecimais de volta para bytes
            iv = bytes.fromhex(pacote["iv"])
            tag = bytes.fromhex(pacote["tag"])
            cifrado = bytes.fromhex(pacote["cifrado"])
            mac_recebido = bytes.fromhex(pacote["mac"])
            
            # Verificação do MAC (Integridade e Autenticidade) [cite: 18, 48]
            h = hmac.HMAC(self.chave_hmac, hashes.SHA256(), backend=default_backend())
            h.update(iv + cifrado)
            h.verify(mac_recebido) # Se falhar aqui, gera a exceção que você viu no terminal
            
            # Decifragem AES-256 GCM [cite: 12, 52]
            cipher = Cipher(algorithms.AES(self.chave_aes), modes.GCM(iv, tag), backend=default_backend())
            decryptor = cipher.decryptor()
            return (decryptor.update(cifrado) + decryptor.finalize()).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Falha na integridade: {str(e)}")