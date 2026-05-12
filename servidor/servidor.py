import socket
import threading
import json
import database 
from crypto_session import SessaoCriptografada

class ServidorChat:
    def __init__(self, host='127.0.0.1', porta=5000):
        self.host = host
        self.porta = porta
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.porta))
        self.clientes_online = {} # {nome_usuario: {"socket": sock, "sessao": sessao_obj}}

    def enviar_seguro(self, client_sock, sessao, dados):
        """Cifra os dados na Camada 1 (Servidor-Cliente) antes de enviar."""
        pacote = sessao.cifrar_mensagem(dados)
        client_sock.sendall((json.dumps(pacote) + "\n").encode('utf-8'))

    def handle_client(self, client_socket, addr):
        usuario_atual = None
        sessao_server = SessaoCriptografada()
        buffer = ""

        try:
            # === ESTÁGIO 1: HANDSHAKE ECDH (Criptografia de Sessão) ===
            while True:
                chunk = client_socket.recv(4096).decode('utf-8')
                if not chunk: return
                buffer += chunk
                if "\n" in buffer:
                    linha, buffer = buffer.split("\n", 1)
                    msg = json.loads(linha)
                    if msg.get("tipo") == "handshake_iniciar":
                        pub_s = sessao_server.iniciar_handshake_servidor(
                            bytes.fromhex(msg['public_key']), 
                            bytes.fromhex(msg['salt'])
                        )
                        res = {"acao": "handshake_resposta", "public_key_servidor": pub_s.hex()}
                        client_socket.sendall((json.dumps(res) + "\n").encode('utf-8'))
                        print(f"[*] Handshake concluído com {addr}")
                        break

            # === ESTÁGIO 2: LOOP DE COMANDOS CIFRADOS ===
            while True:
                chunk = client_socket.recv(8192).decode('utf-8')
                if not chunk: break
                buffer += chunk
                while "\n" in buffer:
                    linha, buffer = buffer.split("\n", 1)
                    pacote_cifrado = json.loads(linha)
                    dados = sessao_server.decifrar_mensagem(pacote_cifrado)
                    acao = dados.get("acao")

                    # LÓGICA DE REGISTRO
                    if acao == "registrar":
                        sucesso, msg = database.registrar_usuario(dados['usuario'], dados['senha'], dados['chave_publica'])
                        self.enviar_seguro(client_socket, sessao_server, {"acao": "resposta_registro", "sucesso": sucesso, "mensagem": msg})

                    # LÓGICA DE LOGIN COM TRAVA E MENSAGENS OFFLINE
                    elif acao == "login":
                        nome = dados['usuario']
                        if nome in self.clientes_online:
                            self.enviar_seguro(client_socket, sessao_server, {"acao": "resposta_login", "sucesso": False, "mensagem": "Usuário já logado!"})
                            continue
                        
                        sucesso, msg = database.login_db(nome, dados['senha'])
                        if sucesso:
                            usuario_atual = nome
                            self.clientes_online[nome] = {"socket": client_socket, "sessao": sessao_server}
                            database.atualizar_status(nome, 'online')
                            self.enviar_seguro(client_socket, sessao_server, {"acao": "resposta_login", "sucesso": True, "usuario": nome})
                            
                            # ENTREGA DE MENSAGENS OFFLINE (Aguardam o login seguro)
                            pendentes = database.buscar_e_apagar_offline(nome)
                            for m in pendentes:
                                self.enviar_seguro(client_socket, sessao_server, {
                                    "acao": "nova_mensagem",
                                    "remetente": m['remetente'],
                                    "conteudo": m['conteudo']
                                })
                            
                            print(f"[+] {nome} entrou. Mensagens offline entregues.")
                            self.broadcast_status()
                        else:
                            self.enviar_seguro(client_socket, sessao_server, {"acao": "resposta_login", "sucesso": False, "mensagem": msg})

                    # ROTEAMENTO DE MENSAGENS (P2P OU OFFLINE)
                    elif acao == "enviar_mensagem":
                        dest = dados.get("destinatario")
                        if dest in self.clientes_online:
                            # Destinatário Online: Roteia em tempo real
                            dados["remetente"] = usuario_atual
                            self.enviar_seguro(self.clientes_online[dest]["socket"], self.clientes_online[dest]["sessao"], {
                                "acao": "nova_mensagem",
                                "remetente": usuario_atual,
                                "conteudo": dados["conteudo"]
                            })
                        else:
                            # Destinatário Offline: Armazena no Banco de Dados
                            database.salvar_offline(usuario_atual, dest, dados["conteudo"])

                    elif acao == "obter_contatos":
                        self.enviar_lista(client_socket, sessao_server, usuario_atual)

        except Exception as e:
            print(f"[!] Erro no atendimento de {addr}: {e}")
        finally:
            if usuario_atual:
                self.clientes_online.pop(usuario_atual, None)
                database.atualizar_status(usuario_atual, 'offline')
                self.broadcast_status()
            client_socket.close()

    def enviar_lista(self, sock, sessao, user):
        """Envia a lista de contatos atualizada para um usuário específico."""
        _, lista = database.obter_lista_contatos(user)
        self.enviar_seguro(sock, sessao, {"acao": "resposta_contatos", "contatos": lista})

    def broadcast_status(self):
        """Notifica todos os usuários online sobre mudanças de status (Online/Offline)."""
        for u, info in self.clientes_online.items():
            self.enviar_lista(info['socket'], info['sessao'], u)

    def iniciar(self):
        print(f"[*] Servidor rodando em {self.host}:{self.porta}")
        self.server_socket.listen()
        while True:
            sock, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(sock, addr), daemon=True).start()

if __name__ == "__main__":
    ServidorChat().iniciar()