import socket
import json
import threading

class ClienteRede:
    def __init__(self, host='127.0.0.1', porta=5000):
        self.host = host
        self.porta = porta
        self.socket = None
        self.conectado = False
        self.ao_receber_mensagem = None  # Uma função que a GUI vai fornecer para processar respostas

    def conectar(self):
        """Tenta conectar ao servidor TCP"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.porta))
            self.conectado = True
            
            # Inicia uma Thread para ouvir o servidor em segundo plano (Requisito Multithread)
            thread_receber = threading.Thread(target=self.ouvir_servidor)
            thread_receber.daemon = True  # A thread morre se você fechar o programa
            thread_receber.start()
            return True, "Conectado ao servidor!"
        except Exception as e:
            return False, f"Falha na conexão: {e}"

    def enviar(self, dicionario_dados):
        """Converte um dicionário Python em JSON e envia pelo Socket"""
        if self.conectado:
            try:
                # Transforma dicionário em texto JSON e depois em Bytes
                mensagem = json.dumps(dicionario_dados)
                self.socket.send(mensagem.encode('utf-8'))
            except Exception as e:
                print(f"Erro ao enviar: {e}")

    def ouvir_servidor(self):
        """Loop infinito rodando em paralelo para receber respostas do servidor"""
        while self.conectado:
            try:
                mensagem_bytes = self.socket.recv(1024)
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