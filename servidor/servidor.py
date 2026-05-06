import os
import socket
import threading
import json
import traceback  
import database      
import crypto_utils  
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
        self.nonces_pendentes = {}
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
                acao = dados.get("acao")

                # (Código de handshake com servidor e registo permanecem iguais)
                if dados.get("tipo") == "handshake_iniciar":
                    sessao_segura = SessaoCriptografada()
                    pub_cliente, salt_cliente = bytes.fromhex(dados['public_key']), bytes.fromhex(dados['salt'])
                    pub_servidor_bytes = sessao_segura.iniciar_handshake_servidor(pub_cliente, salt_cliente)
                    client_socket.send(json.dumps({"acao": "handshake_resposta", "public_key_servidor": pub_servidor_bytes.hex()}).encode('utf-8'))
                    continue

                if acao == "registrar":
                    chave_pub = dados.get('chave_publica')
                    sucesso, msg = database.registrar_usuario(dados['usuario'].strip(), dados['senha'], chave_pub)
                    client_socket.send(json.dumps({"acao": "resposta_registro", "sucesso": sucesso, "mensagem": msg}).encode('utf-8'))

                elif acao == "login_desafio":
                    usuario = dados.get('usuario')
                    nonce = os.urandom(32).hex()
                    self.nonces_pendentes[usuario] = nonce
                    client_socket.send(json.dumps({"acao": "desafio_login", "nonce": nonce}).encode('utf-8'))

                elif acao == "resposta_desafio":
                    usuario, nonce_recebido, assinatura = dados.get('usuario'), dados.get('nonce'), bytes.fromhex(dados.get('assinatura'))
                    nonce_esperado = self.nonces_pendentes.get(usuario)
                    if not nonce_esperado or nonce_esperado != nonce_recebido:
                        client_socket.send(json.dumps({"acao": "resposta_login", "sucesso": False, "mensagem": "Desafio inválido"}).encode('utf-8'))
                        continue
                    
                    chave_pub_hex = database.obter_chave_publica(usuario)
                    chave_pub = crypto_utils.carregar_chave_publica_bytes(bytes.fromhex(chave_pub_hex))
                    if crypto_utils.verificar_assinatura(chave_pub, bytes.fromhex(nonce_recebido), assinatura):
                        usuario_atual = usuario
                        self.clientes_online[usuario_atual] = client_socket
                        self.nonces_pendentes.pop(usuario, None)
                        client_socket.send(json.dumps({"acao": "resposta_login", "sucesso": True}).encode('utf-8'))
                        
                        # Mensagens offline (enviadas cifradas pelo P2P)
                        for msg in database.buscar_e_apagar_offline(usuario_atual):
                            client_socket.send(json.dumps({"acao": "nova_mensagem", "remetente": msg['remetente'], "conteudo": json.loads(msg['conteudo'])}).encode('utf-8'))
                    else:
                        client_socket.send(json.dumps({"acao": "resposta_login", "sucesso": False, "mensagem": "Assinatura inválida"}).encode('utf-8'))

                # --- NOVO: ROTEAMENTO P2P ---
                elif acao in ["p2p_handshake", "p2p_handshake_resposta"]:
                    destinatario = dados.get("destinatario")
                    dest_socket = self.clientes_online.get(destinatario)
                    if dest_socket:
                        dados["remetente"] = usuario_atual
                        dest_socket.send(json.dumps(dados).encode('utf-8'))
                    else:
                        # Exigência do PDF: Não entregar offline se não houver chave
                        client_socket.send(json.dumps({"acao": "erro_p2p", "mensagem": f"{destinatario} está offline. Impossível negociar chave segura."}).encode('utf-8'))

                elif acao == "enviar_mensagem":
                    destinatario, conteudo = dados.get("destinatario"), dados.get("conteudo") 
                    dest_socket = self.clientes_online.get(destinatario)
                    if dest_socket:
                        try:
                            dest_socket.send(json.dumps({"acao": "nova_mensagem", "remetente": usuario_atual, "conteudo": conteudo}).encode('utf-8'))
                        except:
                            del self.clientes_online[destinatario]
                            database.salvar_offline(usuario_atual, destinatario, json.dumps(conteudo))
                    else:
                        database.salvar_offline(usuario_atual, destinatario, json.dumps(conteudo))

                elif acao == "pedir_contatos":
                    sucesso, contatos = database.obter_lista_contatos(usuario_atual)
                    client_socket.send(json.dumps({"acao": "resposta_contatos", "sucesso": sucesso, "contatos": contatos}).encode('utf-8'))

            except Exception as e:
                print("\n" + "="*50 + f"\n❌ ERRO AO LIDAR COM CLIENTE: {e}\n" + "="*50)
                conectado = False

        if usuario_atual:
            database.logout_db(usuario_atual)
            self.clientes_online.pop(usuario_atual, None)
        client_socket.close()

if __name__ == "__main__":
    ServidorChat().iniciar()