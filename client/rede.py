import socket
import json
import threading
from client.crypto_session import CryptoSession

class ClienteRede:
    def __init__(self, host='127.0.0.1', porta=5000):
        self.host = host
        self.porta = porta
        self.crypto_session = CryptoSession()
        self.socket = None
        self.conectado = False
        self.ao_receber_mensagem = None  # Uma função que a GUI vai fornecer para processar respostas
        self.sessao = None  # Armazena a sessão criptografada ativa (se houver)

    def conectar(self):
        """Tenta conectar ao servidor TCP"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.porta))
            self.conectado = True
            
            # handshake criptográfico (DHE + HKDF) para estabelecer chaves de sessão seguras
            self.sessao = CryptoSession()
            public_key_cliente, salt = self.sessao.iniciar_handshake_cliente()
            
            handshake_msg = {
                "tipo": "handshake_iniciar",
                "public_key": public_key_cliente.hex(),
                "salt": salt.hex()
            }
            self.socket.send(json.dumps(handshake_msg).encode('utf-8'))
            
            #finalizado o handshake, agora a sessão tem as chaves AES e HMAC derivadas e prontas para uso
            
            pub_servidor = bytes.fromhex(dados['public_key_servidor'])
            self.sessao.finalizar_handshake_cliente(pub_servidor, salt)
            
            print("Handshake criptográfico concluído, sessão segura estabelecida!")
            
            # Inicia uma Thread para ouvir o servidor em segundo plano (Requisito Multithread)
            thread_receber = threading.Thread(target=self.ouvir_servidor)
            thread_receber.daemon = True  # A thread morre se você fechar o programa
            thread_receber.start()
            return True, "Conectado ao servidor!"
        except Exception as e:
            return False, f"Falha na conexão: {e}"

    def enviar(self, dicionario_dados):
        """Converte um dicionário Python em JSON e envia pelo Socket"""
        if self.conectado and self.sessao:
            try:
                # Cifra a mensagem
                
                pacote_cifrado = self.sessao.cifrar_mensagem(dicionario_dados)
                self.sessao.contador_mensagens += 1
                
                # Transforma dicionário em texto JSON e depois em Bytes
                mensagem = json.dumps(dicionario_dados)
                self.socket.send(mensagem.encode('utf-8'))
                
                # Verifica se precisa renovar chaves
                if self.sessao.precisa_renovar():
                    self.renovar_sessao()
                                        
            except Exception as e:
                print(f"Erro ao enviar: {e}")

    def ouvir_servidor(self):
        """Loop infinito rodando em paralelo para receber respostas do servidor"""
        while self.conectado:
            try:
                mensagem_bytes = self.socket.recv(8192)
                if not mensagem_bytes:
                    break  # Servidor fechou a conexão
                
                # Converte os Bytes de volta para dicionário Python
                dados = json.loads(mensagem_bytes.decode('utf-8'))
                
                # Se a interface gráfica cadastrou uma função, manda os dados pra ela
                if self.ao_receber_mensagem:
                    self.ao_receber_mensagem(dados)
                    
            except Exception as e:
                print(f"Conexão com o servidor perdida: {e}")
                self.conectado = False
                break
        
        if self.socket:
            self.socket.close()