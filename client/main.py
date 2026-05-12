import customtkinter as ctk
from tkinter import messagebox
import interface, crypto_utils, historico, os, threading, json, time
from rede import ClienteRede
from crypto_p2p import SessaoP2P 

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Parceiro Chat v2.0 - Segurança Ativa")
        self.root.geometry("900x650")
        
        self.usuario_logado = None
        self.usuario_tentando_logar = None
        self.contato_atual = None
        self.chave_aes_local = None 
        self.sessao_server = None 
        self.sessoes_p2p = {} 
        
        self.container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.container.pack(expand=True, fill="both")
        
        self.contatos_widgets = []
        
        # Inicia a conexão e o monitor de expiração das chaves efêmeras
        threading.Thread(target=self.iniciar_conexao, daemon=True).start()
        threading.Thread(target=self.monitor_de_expiracao, daemon=True).start()

    def monitor_de_expiracao(self):
        """Verifica a cada 30 segundos se alguma sessão precisa de renovação (Requisito Alan Turing)"""
        while True:
            time.sleep(30)
            # Verifica sessão de transporte com o servidor
            if self.sessao_server and self.sessao_server.precisa_renovar():
                self.renovar_sessao_servidor()
            
            # Verifica sessões ponta-a-ponta com os contatos
            for contato, sessao in list(self.sessoes_p2p.items()):
                if sessao.precisa_renovar():
                    self.renovar_sessao_p2p(contato)

    def renovar_sessao_servidor(self):
        """Inicia um novo handshake DHE cifrado com o servidor para trocar a chave de transporte"""
        pub, salt = self.sessao_server.iniciar_handshake_cliente()
        pacote = self.sessao_server.cifrar_mensagem({
            "acao": "renovacao_handshake", 
            "public_key": pub.hex(), 
            "salt": salt.hex()
        })
        self.rede.enviar(pacote)

    def renovar_sessao_p2p(self, contato):
        """Renova a chave P2P enviando o novo DHE de forma cifrada (escondendo o padrão)"""
        sessao = self.sessoes_p2p[contato]
        id_s, pub_a, salt = sessao.iniciar_handshake_iniciador()
        
        conteudo_p2p = {"tipo_p2p": "init", "id_sessao": id_s, "pub_key": pub_a.hex(), "salt": salt.hex()}
        pacote_cifrado_p2p = sessao.cifrar_mensagem(json.dumps(conteudo_p2p))
        
        self.rede.enviar(self.sessao_server.cifrar_mensagem({
            "acao": "enviar_mensagem", "destinatario": contato, "conteudo": pacote_cifrado_p2p
        }))

    def iniciar_conexao(self):
        self.carregar_identidade()
        self.rede = ClienteRede()
        self.rede.ao_receber_mensagem = self.processar_resposta_servidor
        sucesso, _ = self.rede.conectar()
        if sucesso:
            self.sessao_server = self.rede.sessao
            self.root.after(0, self.abrir_login)

    def carregar_identidade(self):
        if not os.path.exists("chave_privada.pem"):
            priv, _ = crypto_utils.gerar_par_chaves_ed25519()
            crypto_utils.salvar_chave_privada(priv, "chave_privada.pem")
        self.chave_privada = crypto_utils.carregar_chave_privada("chave_privada.pem")

    def abrir_login(self):
        for w in self.container.winfo_children(): w.destroy()
        self.ent_user, self.ent_pass = interface.montar_layout_login(self.container, self.tentar_login, self.abrir_cadastro)

    def abrir_cadastro(self):
        for w in self.container.winfo_children(): w.destroy()
        self.ent_user, self.ent_pass = interface.montar_layout_cadastro(self.container, self.tentar_cadastro, self.abrir_login)

    def tentar_login(self):
        user, senha = self.ent_user.get().strip(), self.ent_pass.get().strip()
        if user and senha:
            self.usuario_tentando_logar = user
            self.chave_aes_local, _ = historico.derivar_chave_local(senha)
            pacote = self.sessao_server.cifrar_mensagem({"acao": "login_challenge", "usuario": user})
            self.rede.enviar(pacote)

    def tentar_cadastro(self):
        user, senha = self.ent_user.get().strip(), self.ent_pass.get().strip()
        if user and senha:
            pub = crypto_utils.obter_chave_publica_bytes(self.chave_privada.public_key()).hex()
            pacote = self.sessao_server.cifrar_mensagem({"acao": "registrar", "usuario": user, "senha": senha, "chave_publica": pub})
            self.rede.enviar(pacote)

    def fazer_logout(self):
        self.usuario_logado = None
        self.contato_atual = None
        self.sessoes_p2p.clear() 
        self.abrir_login()

    def tela_principal(self):
        for w in self.container.winfo_children(): w.destroy()
        
        header = ctk.CTkFrame(self.container, height=65, corner_radius=0, fg_color="#008069")
        header.pack(side="top", fill="x")
        ctk.CTkLabel(header, text=f"💬 {self.usuario_logado}", text_color="white", font=("Segoe UI", 18, "bold")).pack(side="left", padx=25)
        
        ctk.CTkButton(header, text="SAIR", width=80, height=32, corner_radius=8, fg_color="#CC3333", command=self.fazer_logout).pack(side="right", padx=25)

        sidebar = ctk.CTkFrame(self.container, width=280, corner_radius=0, fg_color="#1E1E1E")
        sidebar.pack(side="left", fill="y")
        ctk.CTkLabel(sidebar, text="CONTATOS DISPONÍVEIS", font=("Segoe UI", 12, "bold"), text_color="#00FF7F").pack(pady=(20, 10))
        
        self.frame_lista = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.frame_lista.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.frame_chat = ctk.CTkFrame(self.container, corner_radius=0, fg_color="transparent")
        self.frame_chat.pack(side="right", fill="both", expand=True)
        
        self.chat_display = ctk.CTkTextbox(self.frame_chat, state="disabled", font=("Segoe UI", 14), wrap="word", fg_color="#121212")
        self.chat_display.pack(fill="both", expand=True, padx=15, pady=(15, 0))
        self.chat_display.tag_config("eu", justify="right", foreground="#00FF7F")
        self.chat_display.tag_config("outro", justify="left", foreground="#FFFFFF")

        input_area = ctk.CTkFrame(self.frame_chat, fg_color="transparent")
        input_area.pack(fill="x", side="bottom", padx=15, pady=15)
        self.input_msg = ctk.CTkEntry(input_area, placeholder_text="Escreva aqui...", height=50, corner_radius=15)
        self.input_msg.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input_msg.bind("<Return>", lambda e: self.enviar_mensagem_p2p())
        ctk.CTkButton(input_area, text="ENVIAR", width=100, height=50, command=self.enviar_mensagem_p2p).pack(side="right")

        self.rede.enviar(self.sessao_server.cifrar_mensagem({"acao": "obter_contatos"}))

    def selecionar_contato(self, nome_contato):
        self.contato_atual = nome_contato
        self.chat_display.configure(state="normal")
        self.chat_display.delete(1.0, ctk.END)
        self.chat_display.insert(ctk.END, f"--- Conversa com {self.contato_atual} ---\n\n", "outro")
        
        mensagens = historico.carregar_historico_local(self.usuario_logado, self.contato_atual, self.chave_aes_local)
        for m in mensagens:
            tag = "eu" if m['remetente'] == self.usuario_logado else "outro"
            self.chat_display.insert(ctk.END, f"{m['remetente']}: {m['texto']}\n\n", tag)
        
        self.chat_display.configure(state="disabled")
        self.chat_display.see(ctk.END)

        if nome_contato not in self.sessoes_p2p:
            self.rede.enviar(self.sessao_server.cifrar_mensagem({
                "acao": "pedir_chave_publica", "usuario_alvo": nome_contato
            }))

    def enviar_mensagem_p2p(self):
        texto = self.input_msg.get().strip()
        if not texto or not self.contato_atual: return
        
        sessao_p2p = self.sessoes_p2p.get(self.contato_atual)
        if not sessao_p2p or not sessao_p2p.handshake_completo:
            messagebox.showwarning("Segurança", "A estabelecer ligação segura... Tente novamente.")
            return

        if not getattr(sessao_p2p, 'autenticado', False):
            messagebox.showwarning("Segurança", "A verificar a identidade do contato. Aguarde um instante...")
            return

        self.input_msg.delete(0, ctk.END)
        self.registrar_e_exibir(self.contato_atual, texto, self.usuario_logado)

        pacote_p2p = sessao_p2p.cifrar_mensagem(texto)
        self.rede.enviar(self.sessao_server.cifrar_mensagem({
            "acao": "enviar_mensagem", "destinatario": self.contato_atual, "conteudo": pacote_p2p
        }))
        
        # Incrementa contador para forçar renovação futura
        self.sessao_server.contador_mensagens += 1
        sessao_p2p.contador_mensagens += 1

    def registrar_e_exibir(self, contato, texto, remetente):
        historico.salvar_mensagem_protegida(self.usuario_logado, contato, remetente, texto, self.chave_aes_local)
        if hasattr(self, 'chat_display'):
            self.chat_display.configure(state="normal")
            tag = "eu" if remetente == self.usuario_logado else "outro"
            self.chat_display.insert(ctk.END, f"{remetente}: {texto}\n\n", tag)
            self.chat_display.configure(state="disabled")
            self.chat_display.see(ctk.END)

    def processar_resposta_servidor(self, pacote):
        try:
            dados = self.sessao_server.decifrar_mensagem(pacote)
            acao = dados.get("acao")
            
            # --- RESPOSTA DE RENOVAÇÃO DA CHAVE COM O SERVIDOR ---
            if acao == "handshake_resposta_renovacao":
                self.sessao_server.finalizar_handshake_cliente(bytes.fromhex(dados['public_key_servidor']))
                self.sessao_server.configurar_limites_aleatorios()
                print("[*] Chaves de transporte renovadas com sucesso.")

            elif acao == "login_nonce":
                nonce_hex = dados.get("nonce")
                assinatura = crypto_utils.assinar_mensagem(self.chave_privada, bytes.fromhex(nonce_hex))
                
                pacote_verifica = self.sessao_server.cifrar_mensagem({
                    "acao": "login_verify", "usuario": self.usuario_tentando_logar, "assinatura": assinatura.hex()
                })
                self.rede.enviar(pacote_verifica)

            elif acao == "entrega_chave_publica":
                alvo = dados['usuario_alvo']
                nova_sessao = SessaoP2P()
                id_s, pub_a, salt = nova_sessao.iniciar_handshake_iniciador()
                self.sessoes_p2p[alvo] = nova_sessao
                self.rede.enviar(self.sessao_server.cifrar_mensagem({
                    "acao": "enviar_mensagem", "destinatario": alvo,
                    "conteudo": {"tipo_p2p": "init", "id_sessao": id_s, "pub_key": pub_a.hex(), "salt": salt.hex()}
                }))

            elif acao == "nova_mensagem":
                remetente = dados['remetente']
                conteudo = dados['conteudo']
                
                if isinstance(conteudo, dict) and "tipo_p2p" in conteudo:
                    if conteudo["tipo_p2p"] == "init":
                        sessao = SessaoP2P()
                        id_s, pub_b = sessao.responder_handshake(bytes.fromhex(conteudo["pub_key"]), bytes.fromhex(conteudo["salt"]), conteudo["id_sessao"])
                        self.sessoes_p2p[remetente] = sessao
                        self.rede.enviar(self.sessao_server.cifrar_mensagem({
                            "acao": "enviar_mensagem", "destinatario": remetente,
                            "conteudo": {"tipo_p2p": "res", "id_sessao": id_s, "pub_key": pub_b.hex()}
                        }))
                    elif conteudo["tipo_p2p"] == "res" and remetente in self.sessoes_p2p:
                        sessao = self.sessoes_p2p[remetente]
                        sessao.finalizar_handshake_iniciador(bytes.fromhex(conteudo["pub_key"]), conteudo["id_sessao"])
                        sessao.configurar_limites_aleatorios() # Define expiração da sessão P2P
                        
                        sessao.autenticado = False
                        sessao.meu_nonce = os.urandom(16).hex()
                        minha_pub = crypto_utils.obter_chave_publica_bytes(self.chave_privada.public_key()).hex()
                        
                        auth_msg = json.dumps({"tipo_auth": "req", "nonce": sessao.meu_nonce, "pub_key": minha_pub})
                        pacote_p2p = sessao.cifrar_mensagem(auth_msg)
                        self.rede.enviar(self.sessao_server.cifrar_mensagem({
                            "acao": "enviar_mensagem", "destinatario": remetente, "conteudo": pacote_p2p
                        }))
                else: 
                    if remetente in self.sessoes_p2p:
                        texto_claro = self.sessoes_p2p[remetente].decifrar_mensagem(conteudo)
                        self.sessoes_p2p[remetente].contador_mensagens += 1
                        
                        is_auth_protocol = False
                        try:
                            msg_obj = json.loads(texto_claro)
                            if isinstance(msg_obj, dict) and "tipo_auth" in msg_obj:
                                is_auth_protocol = True
                                sessao = self.sessoes_p2p[remetente]
                                
                                if msg_obj["tipo_auth"] == "req":
                                    sessao.pub_key_identidade_remota = bytes.fromhex(msg_obj["pub_key"])
                                    assinatura_a = crypto_utils.assinar_mensagem(self.chave_privada, bytes.fromhex(msg_obj["nonce"]))
                                    
                                    sessao.meu_nonce = os.urandom(16).hex()
                                    sessao.autenticado = False
                                    minha_pub = crypto_utils.obter_chave_publica_bytes(self.chave_privada.public_key()).hex()
                                    
                                    auth_msg = json.dumps({
                                        "tipo_auth": "res", "assinatura": assinatura_a.hex(),
                                        "nonce": sessao.meu_nonce, "pub_key": minha_pub
                                    })
                                    pacote_p2p = sessao.cifrar_mensagem(auth_msg)
                                    self.rede.enviar(self.sessao_server.cifrar_mensagem({"acao": "enviar_mensagem", "destinatario": remetente, "conteudo": pacote_p2p}))

                                elif msg_obj["tipo_auth"] == "res":
                                    sessao.pub_key_identidade_remota = bytes.fromhex(msg_obj["pub_key"])
                                    pub_key_b = crypto_utils.carregar_chave_publica_bytes(sessao.pub_key_identidade_remota)
                                    
                                    if crypto_utils.verificar_assinatura(pub_key_b, bytes.fromhex(sessao.meu_nonce), bytes.fromhex(msg_obj["assinatura"])):
                                        sessao.autenticado = True
                                        assinatura_b = crypto_utils.assinar_mensagem(self.chave_privada, bytes.fromhex(msg_obj["nonce"]))
                                        
                                        auth_msg = json.dumps({"tipo_auth": "ack", "assinatura": assinatura_b.hex()})
                                        pacote_p2p = sessao.cifrar_mensagem(auth_msg)
                                        self.rede.enviar(self.sessao_server.cifrar_mensagem({"acao": "enviar_mensagem", "destinatario": remetente, "conteudo": pacote_p2p}))
                                        print(f"[+] Identidade de {remetente} verificada.")

                                elif msg_obj["tipo_auth"] == "ack":
                                    pub_key_a = crypto_utils.carregar_chave_publica_bytes(sessao.pub_key_identidade_remota)
                                    if crypto_utils.verificar_assinatura(pub_key_a, bytes.fromhex(sessao.meu_nonce), bytes.fromhex(msg_obj["assinatura"])):
                                        sessao.autenticado = True
                                        print(f"[+] Autenticação mútua com {remetente} concluída.")
                        except Exception:
                            pass 

                        if not is_auth_protocol and getattr(self.sessoes_p2p[remetente], 'autenticado', False):
                            self.root.after(0, lambda r=remetente, t=texto_claro: self.registrar_e_exibir(r, t, r))

            elif acao == "resposta_registro":
                if dados.get("sucesso"):
                    messagebox.showinfo("Sucesso", "🎉 Conta criada com sucesso!")
                    self.root.after(0, self.abrir_login)
                else: messagebox.showerror("Erro", f"Falha: {dados.get('mensagem')}")

            elif acao == "resposta_login":
                if dados.get("sucesso"):
                    self.usuario_logado = self.usuario_tentando_logar
                    self.root.after(0, self.tela_principal)
                else:
                    messagebox.showerror("Erro de Login", dados.get("mensagem"))

            elif acao == "resposta_contatos":
                self.root.after(0, lambda: self.atualizar_lista(dados['contatos']))
                
        except Exception as e:
            print(f"Erro no processamento: {e}")

    def atualizar_lista(self, contatos):
        """
        Atualiza a lista de contatos na barra lateral com indicadores de status visuais,
        resolvendo o bug de sobreposição.
        """
        # Limpa os widgets antigos da lista
        for widget in self.contatos_widgets:
            widget.destroy()
        self.contatos_widgets.clear()

        # Definição de cores para o status
        COR_ONLINE = "#00E676"  # Verde vibrante
        COR_OFFLINE = "#757575" # Cinza médio

        for c in contatos:
            if c['nome_usuario'] != self.usuario_logado:
                nome_contato = c['nome_usuario']
                esta_online = c['status'].lower() == 'online'
                
                cor_status = COR_ONLINE if esta_online else COR_OFFLINE
                borda_width = 0 if esta_online else 1 

                # 1. Container Principal do Contato
                # Criamos um frame para segurar todos os elementos do contacto
                contact_frame = ctk.CTkFrame(
                    self.frame_lista, 
                    fg_color="transparent", 
                    corner_radius=8,
                    cursor="hand2" # Muda o cursor para mãozinha ao passar o mouse
                )
                contact_frame.pack(fill="x", pady=3, padx=5)
                self.contatos_widgets.append(contact_frame)

                # 2. Indicador de Status (A bolinha colorida)
                status_indicator = ctk.CTkFrame(
                    contact_frame,
                    width=12,
                    height=12,
                    corner_radius=6,
                    fg_color=cor_status,
                    border_width=borda_width,
                    border_color="#404040",
                    cursor="hand2"
                )
                status_indicator.pack(side="left", padx=(15, 10), pady=12)

                # 3. Nome do Usuário
                user_label = ctk.CTkLabel(
                    contact_frame, 
                    text=nome_contato.upper(),
                    font=("Segoe UI", 13, "bold"),
                    text_color="#FFFFFF" if esta_online else "#AAAAAA", 
                    anchor="w",
                    cursor="hand2"
                )
                user_label.pack(side="left", fill="x", expand=True)

                # 4. Lógica de Eventos (Substitui o botão invisível)
                # Funções criadas para responder às ações do rato
                def ao_clicar(event, n=nome_contato):
                    self.selecionar_contato(n)
                
                def ao_entrar(event, f=contact_frame):
                    f.configure(fg_color="#2B2B2B") # Cor de destaque (hover)
                
                def ao_sair(event, f=contact_frame):
                    f.configure(fg_color="transparent") # Volta ao normal

                # Associamos os eventos a todos os componentes do contacto
                # Assim, clicar em qualquer parte (bolinha, nome ou frame) funciona.
                for componente in (contact_frame, status_indicator, user_label):
                    componente.bind("<Button-1>", ao_clicar)  # Botão esquerdo do rato
                    componente.bind("<Enter>", ao_entrar)     # O rato entra na área
                    componente.bind("<Leave>", ao_sair)       # O rato sai da área
if __name__ == "__main__":
    root = ctk.CTk()
    app = ChatApp(root)
    root.mainloop()