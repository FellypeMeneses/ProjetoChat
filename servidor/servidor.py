import socket
import threading
import json
import database 
from crypto_session import SessaoCriptografada
import os
import crypto_utils

class ServidorChat:
    def __init__(self, host='127.0.0.1', porta=5000):
        self.desafios_login = {} # Guarda os nonces temporários { "nome": "nonce_em_hex" }
        self.clientes_online = {}
        self.host = host
        self.porta = porta
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.porta))

    def enviar_seguro(self, client_sock, sessao, dados):
        """Cifra os dados na Camada 1 (Servidor-Cliente) antes de enviar."""
        pacote = sessao.cifrar_mensagem(dados)
        client_sock.sendall((json.dumps(pacote) + "\n").encode('utf-8'))

    def handle_client(self, client_socket, addr):
        usuario_atual = None
        sessao_server = SessaoCriptografada()
        buffer = ""

        try:
            # === ESTÁGIO 1: HANDSHAKE ECDH ===
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
                        print(f"[*] Handshake de transporte concluído com {addr}")
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

                    # REGISTRO DE USUÁRIO
                    if acao == "registrar":
                        sucesso, msg = database.registrar_usuario(dados['usuario'], dados['senha'], dados['chave_publica'])
                        self.enviar_seguro(client_socket, sessao_server, {
                            "acao": "resposta_registro", "sucesso": sucesso, "mensagem": msg
                        })

                    # 1. PEDIDO DE LOGIN (ENVIA DESAFIO) [cite: 106]
                    elif acao == "login_challenge":
                        nome = dados['usuario']
                        if nome in self.clientes_online:
                            self.enviar_seguro(client_socket, sessao_server, {"acao": "resposta_login", "sucesso": False, "mensagem": "Usuário já logado!"})
                            continue
                        
                        chave_pub_hex = database.obter_chave_publica(nome)
                        if not chave_pub_hex:
                            self.enviar_seguro(client_socket, sessao_server, {"acao": "resposta_login", "sucesso": False, "mensagem": "Usuário não encontrado."})
                            continue
                            
                        nonce = os.urandom(32).hex()
                        self.desafios_login[nome] = nonce
                        self.enviar_seguro(client_socket, sessao_server, {"acao": "login_nonce", "nonce": nonce})

                    # 2. VERIFICAÇÃO DE ASSINATURA [cite: 112]
                    elif acao == "login_verify":
                        nome = dados['usuario']
                        assinatura_hex = dados['assinatura']
                        
                        esperado_nonce_hex = self.desafios_login.get(nome)
                        if not esperado_nonce_hex:
                            self.enviar_seguro(client_socket, sessao_server, {"acao": "resposta_login", "sucesso": False, "mensagem": "Desafio expirado ou inválido."})
                            continue
                            
                        chave_pub_hex = database.obter_chave_publica(nome)
                        pub_key = crypto_utils.carregar_chave_publica_bytes(bytes.fromhex(chave_pub_hex))
                        
                        assinatura_valida = crypto_utils.verificar_assinatura(pub_key, bytes.fromhex(esperado_nonce_hex), bytes.fromhex(assinatura_hex))
                        
                        if assinatura_valida:
                            self.desafios_login.pop(nome, None)
                            usuario_atual = nome
                            self.clientes_online[nome] = {"socket": client_socket, "sessao": sessao_server}
                            database.atualizar_status(nome, 'online')
                            self.enviar_seguro(client_socket, sessao_server, {"acao": "resposta_login", "sucesso": True, "usuario": nome})
                            
                            pendentes = database.buscar_e_apagar_offline(nome)
                            for m in pendentes:
                                self.enviar_seguro(client_socket, sessao_server, {
                                    "acao": "nova_mensagem", "remetente": m['remetente'], "conteudo": m['conteudo']
                                })
                            
                            print(f"[+] {nome} autenticado via Assinatura Ed25519. Status: Online.")
                            self.broadcast_status()
                        else:
                            self.enviar_seguro(client_socket, sessao_server, {"acao": "resposta_login", "sucesso": False, "mensagem": "Assinatura inválida! Possível tentativa de fraude."})

                    # ROTEAMENTO DE CHAVES PÚBLICAS
                    elif acao == "pedir_chave_publica":
                        alvo = dados.get("usuario_alvo")
                        conn = database.obter_conexao()
                        cursor = conn.cursor(dictionary=True)
                        cursor.execute("SELECT chave_publica FROM usuarios WHERE nome_usuario = %s", (alvo,))
                        resultado = cursor.fetchone()
                        conn.close()
                        
                        if resultado:
                            self.enviar_seguro(client_socket, sessao_server, {
                                "acao": "entrega_chave_publica", "usuario_alvo": alvo, "chave_publica": resultado['chave_publica']
                            })

                    # ROTEAMENTO DE MENSAGENS P2P [cite: 167, 168]
                    elif acao == "enviar_mensagem":
                        dest = dados.get("destinatario")
                        conteudo_cifrado_p2p = dados.get("conteudo")
                        
                        if dest in self.clientes_online:
                            self.enviar_seguro(self.clientes_online[dest]["socket"], self.clientes_online[dest]["sessao"], {
                                "acao": "nova_mensagem", "remetente": usuario_atual, "conteudo": conteudo_cifrado_p2p
                            })
                        else:
                            database.salvar_offline(usuario_atual, dest, json.dumps(conteudo_cifrado_p2p))

                    # LISTA DE CONTACTOS
                    elif acao == "obter_contatos":
                        self.enviar_lista(client_socket, sessao_server, usuario_atual)

                    # --- NOVO: LÓGICA DE RENOVAÇÃO DE SESSÃO COM O SERVIDOR (ALAN TURING) [cite: 73, 84] ---
                    elif acao == "renovacao_handshake":
                        # O servidor recebe a nova chave pública do cliente e o novo salt
                        pub_s = sessao_server.iniciar_handshake_servidor(
                            bytes.fromhex(dados['public_key']), 
                            bytes.fromhex(dados['salt'])
                        )
                        # Responde de forma cifrada para esconder o padrão de renovação 
                        self.enviar_seguro(client_socket, sessao_server, {
                            "acao": "handshake_resposta_renovacao",
                            "public_key_servidor": pub_s.hex()
                        })
                        print(f"[*] Sessão renovada com sucesso para {usuario_atual}")

        except Exception as e:
            print(f"[!] Erro na ligação com {addr}: {e}")
        finally:
            if usuario_atual:
                self.clientes_online.pop(usuario_atual, None)
                database.atualizar_status(usuario_atual, 'offline')
                self.broadcast_status()
            client_socket.close()

    def enviar_lista(self, sock, sessao, user):
        _, lista = database.obter_lista_contatos(user)
        self.enviar_seguro(sock, sessao, {"acao": "resposta_contatos", "contatos": lista})

    def broadcast_status(self):
        for u, info in self.clientes_online.items():
            self.enviar_lista(info['socket'], info['sessao'], u)

    def iniciar(self):
        print(f"[*] Servidor a escutar em {self.host}:{self.porta}")
        self.server_socket.listen()
        while True:
            sock, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(sock, addr), daemon=True).start()

if __name__ == "__main__":
    ServidorChat().iniciar()