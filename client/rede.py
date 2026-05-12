import socket
import json
import threading
import crypto_utils
from crypto_session import SessaoCriptografada

class ClienteRede:
    def __init__(self, host='127.0.0.1', porta=5000):
        self.host = host
        self.porta = porta
        self.socket = None
        self.conectado = False
        self.ao_receber_mensagem = None 
        self.sessao = None 

    def conectar(self):
        """Estabelece a conexão inicial e o handshake DHE"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.porta))
            
            self.sessao = SessaoCriptografada()
            # Passo 1: Inicia negociação Diffie-Hellman
            pub_cliente, salt = self.sessao.iniciar_handshake_cliente()
            
            handshake_msg = {
                "tipo": "handshake_iniciar",
                "public_key": pub_cliente.hex(),
                "salt": salt.hex()
            }
            # Envia com delimitador \n para o servidor identificar o fim do pacote
            self.socket.sendall((json.dumps(handshake_msg) + "\n").encode('utf-8'))
            
            # Recebe resposta do servidor
            resposta_bytes = self.socket.recv(8192)
            if not resposta_bytes:
                return False, "Servidor não respondeu."
                
            # Decodifica removendo possíveis espaços ou quebras de linha
            resposta_texto = resposta_bytes.decode('utf-8').strip()
            if not resposta_texto:
                 return False, "Resposta vazia do servidor."

            dados_res = json.loads(resposta_texto)
            if dados_res.get("acao") == "handshake_resposta":
                pub_servidor = bytes.fromhex(dados_res['public_key_servidor'])
                # Finaliza a derivação das Chaves 1 e 2 via HKDF
                self.sessao.finalizar_handshake_cliente(pub_servidor)
                self.conectado = True
                
                threading.Thread(target=self.ouvir_servidor, daemon=True).start()
                return True, "Conectado!"
            
            return False, "Falha no protocolo de Handshake."
        except Exception as e:
            return False, f"Falha: {str(e)}"

    def enviar(self, dados):
        """Envia pacotes cifrados com Chave 1 e Chave 2"""
        if self.conectado and self.socket:
            try:
                mensagem = json.dumps(dados) + "\n"
                self.socket.sendall(mensagem.encode('utf-8'))
            except:
                self.fechar_conexao()

    def ouvir_servidor(self):
        buffer = ""
        while self.conectado:
            try:
                chunk = self.socket.recv(8192).decode('utf-8')
                if not chunk: break
                buffer += chunk
                while "\n" in buffer:
                    linha, buffer = buffer.split("\n", 1)
                    if linha.strip() and self.ao_receber_mensagem:
                        self.ao_receber_mensagem(json.loads(linha))
            except:
                break
        self.fechar_conexao()

    def fechar_conexao(self):
        self.conectado = False
        if self.socket:
            self.socket.close()
            self.socket = None