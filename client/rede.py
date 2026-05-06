import socket
import json
import threading
from typing import Self
from client import crypto_utils
from crypto_session import SessaoCriptografada

class ClienteRede:
    def __init__(self, host='127.0.0.1', porta=5000):
        self.host = host
        self.porta = porta
        self.socket = None
        self.conectado = False
        self.ao_receber_mensagem = None 
        self.sessao = None 


    def responder_desafio(self, usuario, nonce, chave_privada):
        """Assina o nonce com a chave privada"""
        nonce_bytes = bytes.fromhex(nonce)
        assinatura = crypto_utils.assinar_mensagem(chave_privada, nonce_bytes)
        
        self.enviar({
            "acao": "resposta_desafio",
            "usuario": usuario,
            "nonce": nonce,
            "assinatura": assinatura.hex()
        })
        
    def conectar(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.porta))
            
            self.sessao = SessaoCriptografada()
            pub_cliente, salt = self.sessao.iniciar_handshake_cliente()
            
            handshake_msg = {
                "tipo": "handshake_iniciar",
                "public_key": pub_cliente.hex(),
                "salt": salt.hex()
            }
            self.socket.send(json.dumps(handshake_msg).encode('utf-8'))
            
            resposta_bytes = self.socket.recv(8192)
            if not resposta_bytes:
                return False, "Servidor não respondeu ao handshake."
                
            dados_res = json.loads(resposta_bytes.decode('utf-8'))
            
            if dados_res.get("acao") == "handshake_resposta":
                pub_servidor = bytes.fromhex(dados_res['public_key_servidor'])
                self.sessao.finalizar_handshake_cliente(pub_servidor)
                self.conectado = True
                print("--- Sessão Segura Estabelecida ---")
            
            thread_receber = threading.Thread(target=self.ouvir_servidor)
            thread_receber.daemon = True
            thread_receber.start()
            
            return True, "Conectado e Seguro!"
        except Exception as e:
            return False, f"Falha na conexão: {e}"

    def enviar(self, dicionario_dados):
        if self.conectado and self.sessao and self.sessao.handshake_completo:
            try:
                # Envia o JSON puro para o servidor poder rotear a mensagem
                pacote_cifrado = self.sessao.cifrar(json.dumps(dicionario_dados))
                self.socket.send(json.dumps(pacote_cifrado).encode('utf-8'))
                mensagem = json.dumps(dicionario_dados)
                self.socket.send(mensagem.encode('utf-8'))
            except Exception as e:
                print(f"Erro ao enviar: {e}")

    def ouvir_servidor(self):
        while self.conectado:
            try:
                mensagem_bytes = self.socket.recv(8192)
                if not mensagem_bytes: break
                
                dados_recebidos = json.loads(mensagem_bytes.decode('utf-8'))
                if "iv" in dados_recebidos and "tag" in dados_recebidos and "cifrado" in dados_recebidos and "mac" in dados_recebidos:
                    texto_decifrado = self.sessao.decifrar(dados_recebidos)
                    dados = json.loads(texto_decifrado)
                else:
                    dados = json.loads(mensagem_bytes.decode('utf-8'))
                if self.ao_receber_mensagem:
                    self.ao_receber_mensagem(dados)
            except:
                print("Conexão perdida com o servidor.")
                self.conectado = False
                break
        if self.socket: self.socket.close()