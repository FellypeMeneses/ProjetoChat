import socket
import threading
import json
import database

class ServidorChat:
    def __init__(self):
        self.host = '127.0.0.1'
        self.porta = 5000
        self.clientes_online = {}
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.porta))
        self.server_socket.listen()
        
        print(f"[SERVIDOR] Rodando na porta {self.porta} e aguardando conexões...")

    def iniciar(self):
        while True:
            client_socket, endereco = self.server_socket.accept()
            print(f"[NOVA CONEXÃO] Cliente {endereco} conectou.")
            thread = threading.Thread(target=self.lidar_com_cliente, args=(client_socket, endereco))
            thread.start()

    def lidar_com_cliente(self, client_socket, endereco):
        usuario_atual = None
        conectado = True
        
        while conectado:
            try:
                mensagem_bytes = client_socket.recv(8192)
                if not mensagem_bytes:
                    break
                
                dados = json.loads(mensagem_bytes.decode('utf-8'))
                acao = dados.get("acao")
                
                # ==========================================
                # ROTEAMENTO DE AÇÕES
                # ==========================================
                if acao == "registrar":
                    sucesso, msg = database.registrar_usuario(dados['usuario'], dados['senha'])
                    resposta = {"acao": "resposta_registro", "sucesso": sucesso, "mensagem": msg}
                    client_socket.send(json.dumps(resposta).encode('utf-8'))
                
                elif acao == "login":
                    sucesso, resultado = database.validar_login(dados['usuario'], dados['senha'])
                    if sucesso:
                        usuario_atual = dados['usuario']
                        self.clientes_online[usuario_atual] = client_socket
                        resposta = {"acao": "resposta_login", "sucesso": True, "mensagem": "Login efetuado!"}
                    else:
                        resposta = {"acao": "resposta_login", "sucesso": False, "mensagem": resultado}
                    client_socket.send(json.dumps(resposta).encode('utf-8'))

                elif acao == "pedir_contatos":
                    sucesso, contatos = database.obter_lista_contatos(usuario_atual)
                    resposta = {"acao": "resposta_contatos", "sucesso": sucesso, "contatos": contatos if sucesso else []}
                    client_socket.send(json.dumps(resposta).encode('utf-8'))
                
                elif acao == "enviar_mensagem":
                    destinatario = dados.get("destinatario")
                    conteudo = dados.get("conteudo")
                    if destinatario in self.clientes_online:
                        pacote_envio = {"acao": "nova_mensagem", "remetente": usuario_atual, "conteudo": conteudo}
                        self.clientes_online[destinatario].send(json.dumps(pacote_envio).encode('utf-8'))
                    else:
                        print(f"[AVISO] {destinatario} está offline.")

                elif acao == "excluir_mensagem":
                    destinatario = dados.get("destinatario")
                    conteudo_original = dados.get("conteudo_original")
                    if destinatario in self.clientes_online:
                        pacote_exclusao = {"acao": "apagar_mensagem_tela", "remetente": usuario_atual, "conteudo": conteudo_original}
                        self.clientes_online[destinatario].send(json.dumps(pacote_exclusao).encode('utf-8'))

                # 6. EDITAR MENSAGEM (NOVA FUNCIONALIDADE)
                elif acao == "editar_mensagem":
                    destinatario = dados.get("destinatario")
                    conteudo_original = dados.get("conteudo_original")
                    conteudo_novo = dados.get("conteudo_novo")
                    print(f"[AÇÃO] {usuario_atual} editou uma mensagem enviada para {destinatario}.")
                    
                    if destinatario in self.clientes_online:
                        pacote_edicao = {
                            "acao": "editar_mensagem_tela",
                            "remetente": usuario_atual,
                            "conteudo_original": conteudo_original,
                            "conteudo_novo": conteudo_novo
                        }
                        self.clientes_online[destinatario].send(json.dumps(pacote_edicao).encode('utf-8'))
                
            except Exception as e:
                print(f"[ERRO] Falha com {endereco}: {e}")
                conectado = False

        if usuario_atual:
            print(f"[DESCONECTOU] {usuario_atual} saiu.")
            database.logout_db(usuario_atual)
            if usuario_atual in self.clientes_online:
                del self.clientes_online[usuario_atual]
            
        client_socket.close()

if __name__ == "__main__":
    servidor = ServidorChat()
    servidor.iniciar()