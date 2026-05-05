import socket
import threading
import json
import database
from crypto_session import SessaoCriptografada

class ServidorChat:
    def __init__(self):
        self.host = '127.0.0.1'
        self.porta = 5000
        self.clientes_online = {}
        database.criar_tabela_offline()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.porta))
        self.server_socket.listen()
        print(f"--- [SERVIDOR] Ativo em {self.host}:{self.porta} ---")

    def iniciar(self):
        while True:
            client_socket, endereco = self.server_socket.accept()
            thread = threading.Thread(target=self.lidar_com_cliente, args=(client_socket, endereco))
            thread.start()

    def lidar_com_cliente(self, client_socket, endereco):
        usuario_atual = None
        conectado = True
        
        while conectado:
            try:
                mensagem_bytes = client_socket.recv(8192)
                if not mensagem_bytes: break
                
                dados = json.loads(mensagem_bytes.decode('utf-8'))
                
                # --- HANDSHAKE ---
                if dados.get("tipo") == "handshake_iniciar":
                    sessao_segura = SessaoCriptografada()
                    pub_cliente = bytes.fromhex(dados['public_key'])
                    salt_cliente = bytes.fromhex(dados['salt'])
                    pub_servidor_bytes = sessao_segura.iniciar_handshake_servidor(pub_cliente, salt_cliente)
                    
                    resposta = {"acao": "handshake_resposta", "public_key_servidor": pub_servidor_bytes.hex()}
                    client_socket.send(json.dumps(resposta).encode('utf-8'))
                    continue

                acao = dados.get("acao")
                
                if acao == "registrar":
                    sucesso, msg = database.registrar_usuario(dados['usuario'].strip(), dados['senha'])
                    client_socket.send(json.dumps({"acao": "resposta_registro", "sucesso": sucesso, "mensagem": msg}).encode('utf-8'))
                
                elif acao == "login":
                    usuario_req = dados['usuario'].strip()
                    senha_req = dados['senha']
                    if usuario_req in self.clientes_online:
                        try: self.clientes_online[usuario_req].close()
                        except: pass
                        del self.clientes_online[usuario_req]

                    sucesso, resultado = database.validar_login(usuario_req, senha_req)
                    if sucesso:
                        usuario_atual = usuario_req
                        self.clientes_online[usuario_atual] = client_socket
                        client_socket.send(json.dumps({"acao": "resposta_login", "sucesso": True}).encode('utf-8'))
                        msgs_offline = database.buscar_e_apagar_offline(usuario_atual)
                        for msg in msgs_offline:
                            pacote = {"acao": "nova_mensagem", "remetente": msg['remetente'], "conteudo": msg['conteudo']}
                            client_socket.send(json.dumps(pacote).encode('utf-8'))
                    else:
                        client_socket.send(json.dumps({"acao": "resposta_login", "sucesso": False, "mensagem": resultado}).encode('utf-8'))

                elif acao == "pedir_contatos":
                    sucesso, contatos = database.obter_lista_contatos(usuario_atual)
                    contatos_validos = [c for c in contatos if c.get('nome_usuario')]
                    client_socket.send(json.dumps({"acao": "resposta_contatos", "sucesso": sucesso, "contatos": contatos_validos}).encode('utf-8'))
                
                elif acao == "enviar_mensagem":
                    destinatario = dados.get("destinatario")
                    conteudo = dados.get("conteudo")
                    dest_socket = self.clientes_online.get(destinatario)
                    if dest_socket:
                        try: dest_socket.send(json.dumps({"acao": "nova_mensagem", "remetente": usuario_atual, "conteudo": conteudo}).encode('utf-8'))
                        except:
                            del self.clientes_online[destinatario]
                            database.salvar_offline(usuario_atual, destinatario, conteudo)
                    else:
                        database.salvar_offline(usuario_atual, destinatario, conteudo)

                elif acao == "excluir_mensagem":
                    dest_socket = self.clientes_online.get(dados.get("destinatario"))
                    if dest_socket: dest_socket.send(json.dumps({"acao": "apagar_mensagem_tela", "remetente": usuario_atual, "conteudo": dados.get("conteudo_original")}).encode('utf-8'))

                elif acao == "editar_mensagem":
                    dest_socket = self.clientes_online.get(dados.get("destinatario"))
                    if dest_socket: dest_socket.send(json.dumps({"acao": "editar_mensagem_tela", "remetente": usuario_atual, "conteudo_original": dados.get("conteudo_original"), "conteudo_novo": dados.get("conteudo_novo")}).encode('utf-8'))

                elif acao == "excluir_conta":
                    sucesso, msg = database.excluir_conta_db(usuario_atual)
                    client_socket.send(json.dumps({"acao": "resposta_exclusao_conta", "sucesso": sucesso, "mensagem": msg}).encode('utf-8'))
                    if sucesso: conectado = False

            except Exception as e:
                conectado = False

        if usuario_atual:
            database.logout_db(usuario_atual)
            self.clientes_online.pop(usuario_atual, None)
        client_socket.close()

if __name__ == "__main__":
    ServidorChat().iniciar()