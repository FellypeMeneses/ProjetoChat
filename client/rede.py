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

    def responder_desafio(self, usuario, nonce, chave_privada):
        """Assina o desafio do servidor e envia a resposta."""
        nonce_bytes = bytes.fromhex(nonce)
        assinatura = crypto_utils.assinar_mensagem(chave_privada, nonce_bytes)
        self.enviar({
            "acao": "resposta_desafio",
            "usuario": usuario,
            "nonce": nonce,
            "assinatura": assinatura.hex()
        })
        
    def conectar(self):
        """Tenta estabelecer a conexão inicial e o handshake criptográfico com o servidor."""
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
            # Envia a chave pública do cliente para o servidor
            self.socket.send(json.dumps(handshake_msg).encode('utf-8'))
            
            resposta_bytes = self.socket.recv(8192)
            if not resposta_bytes:
                return False, "Servidor não respondeu durante o handshake."
                
            dados_res = json.loads(resposta_bytes.decode('utf-8'))
            if dados_res.get("acao") == "handshake_resposta":
                pub_servidor = bytes.fromhex(dados_res['public_key_servidor'])
                self.sessao.finalizar_handshake_cliente(pub_servidor)
                self.conectado = True
            
            # Inicia uma thread (processo paralelo) para ficar sempre a ouvir o servidor
            thread_receber = threading.Thread(target=self.ouvir_servidor)
            thread_receber.daemon = True
            thread_receber.start()
            
            return True, "Conectado e Seguro!"
        except ConnectionRefusedError:
            return False, "O servidor está offline. Inicia o servidor.py primeiro."
        except Exception as e:
            return False, f"Falha na conexão: {e}"

    def enviar(self, dicionario_dados):
        """Envia pacotes de dados para o servidor, garantindo que a conexão está ativa."""
        # A verificação 'self.socket is not None' previne o erro WinError 10038
        if self.conectado and self.socket is not None:
            try:
                mensagem = json.dumps(dicionario_dados)
                self.socket.send(mensagem.encode('utf-8'))
            except Exception as e:
                print(f"Erro ao enviar dados: {e}")
                self.fechar_conexao() # Se falhar a enviar, fecha de forma segura
        else:
            print("Aviso: Tentativa de envio falhou porque o cliente está desconectado.")

    def ouvir_servidor(self):
        """Fica a escutar o servidor continuamente. Se o servidor cair, lida com o erro."""
        while self.conectado:
            try:
                mensagem_bytes = self.socket.recv(8192)
                # Se receber bytes vazios, significa que o servidor encerrou a conexão
                if not mensagem_bytes: 
                    print("\nA conexão foi encerrada pelo servidor.")
                    break
                
                dados = json.loads(mensagem_bytes.decode('utf-8'))
                if self.ao_receber_mensagem:
                    self.ao_receber_mensagem(dados)
            except Exception as e:
                print(f"\nConexão interrompida de forma inesperada: {e}")
                break
        
        # Garante que as variáveis são limpas quando o loop termina
        self.fechar_conexao()

    def fechar_conexao(self):
        """Limpa o socket de forma segura para evitar o WinError 10038."""
        self.conectado = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None