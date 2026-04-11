import socket
import threading
import json
import database # O arquivo database.py agora fica do lado do servidor!

class ServidorChat:
    def __init__(self):
        self.host = '127.0.0.1' # Localhost
        self.porta = 5000       # Porta de comunicação
        self.clientes_online = {} # Guarda os sockets conectados: {'nome_usuario': socket}
        
        # Cria o socket TCP/IP conforme exigido no projeto
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.porta))
        self.server_socket.listen()
        
        print(f"[SERVIDOR] Rodando na porta {self.porta} e aguardando conexões...")

    def iniciar(self):
        """Loop principal para aceitar novas conexões"""
        while True:
            # O servidor fica travado aqui até alguém tentar conectar
            client_socket, endereco = self.server_socket.accept()
            print(f"[NOVA CONEXÃO] Cliente {endereco} conectou.")
            
            # Cria uma Thread para atender esse cliente sem travar os outros
            thread = threading.Thread(target=self.lidar_com_cliente, args=(client_socket, endereco))
            thread.start()

    def lidar_com_cliente(self, client_socket, endereco):
        """Função que roda em paralelo para cada cliente conectado"""
        usuario_atual = None
        conectado = True
        
        while conectado:
            try:
                # Recebe a mensagem do cliente (limite de 1024 bytes)
                mensagem_bytes = client_socket.recv(1024)
                if not mensagem_bytes:
                    break
                
                # Converte o JSON recebido para Dicionário Python
                dados = json.loads(mensagem_bytes.decode('utf-8'))
                acao = dados.get("acao")
                
                # --- ROTEAMENTO DE AÇÕES ---
                if acao == "registrar":
                    sucesso, msg = database.registrar_usuario(dados['usuario'], dados['senha'])
                    resposta = {"acao": "resposta_registro", "sucesso": sucesso, "mensagem": msg}
                    client_socket.send(json.dumps(resposta).encode('utf-8'))
                
                elif acao == "login":
                    sucesso, resultado = database.validar_login(dados['usuario'], dados['senha'])
                    if sucesso:
                        usuario_atual = dados['usuario']
                        self.clientes_online[usuario_atual] = client_socket # Guarda como online
                        resposta = {"acao": "resposta_login", "sucesso": True, "mensagem": "Login efetuado!"}
                    else:
                        resposta = {"acao": "resposta_login", "sucesso": False, "mensagem": resultado}
                    
                    client_socket.send(json.dumps(resposta).encode('utf-8'))

                # Aqui futuramente colocaremos a ação "enviar_mensagem"
                
            except Exception as e:
                print(f"[ERRO] Falha com {endereco}: {e}")
                conectado = False

        # Se o loop acabar (cliente fechou o app ou deu erro de internet)
        if usuario_atual:
            print(f"[DESCONECTOU] {usuario_atual} saiu.")
            database.logout_db(usuario_atual) # Muda o status para offline no banco
            del self.clientes_online[usuario_atual] # Remove da lista de online
            
        client_socket.close()

if __name__ == "__main__":
    servidor = ServidorChat()
    servidor.iniciar()