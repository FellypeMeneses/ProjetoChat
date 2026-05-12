import customtkinter as ctk
from tkinter import messagebox
import interface, crypto_utils, historico, os, threading, json
from rede import ClienteRede

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Parceiro Chat v2.0")
        self.root.geometry("900x650")
        
        self.usuario_logado = None
        self.usuario_tentando_logar = None
        self.contato_atual = None
        self.chave_aes_local = None 
        self.sessao_server = None 
        
        self.container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.container.pack(expand=True, fill="both")
        
        self.contatos_widgets = []
        threading.Thread(target=self.iniciar_conexao, daemon=True).start()

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

    # --- LÓGICA DE AÇÕES ---
    def tentar_login(self):
        user, senha = self.ent_user.get().strip(), self.ent_pass.get().strip()
        if user and senha:
            self.usuario_tentando_logar = user
            self.chave_aes_local, _ = historico.derivar_chave_local(senha)
            pacote = self.sessao_server.cifrar_mensagem({"acao": "login", "usuario": user, "senha": senha})
            self.rede.enviar(pacote)

    def tentar_cadastro(self):
        user, senha = self.ent_user.get().strip(), self.ent_pass.get().strip()
        if user and senha:
            pub = crypto_utils.obter_chave_publica_bytes(self.chave_privada.public_key()).hex()
            pacote = self.sessao_server.cifrar_mensagem({"acao": "registrar", "usuario": user, "senha": senha, "chave_publica": pub})
            self.rede.enviar(pacote)

    def fazer_logout(self):
        """Limpa os dados da sessão e volta para o login."""
        self.usuario_logado = None
        self.contato_atual = None
        self.abrir_login()

    # --- TELA PRINCIPAL MELHORADA ---
    def tela_principal(self):
        for w in self.container.winfo_children(): w.destroy()
        
        # 1. Cabeçalho (Header) com Nome e Botão Sair
        header = ctk.CTkFrame(self.container, height=65, corner_radius=0, fg_color="#008069")
        header.pack(side="top", fill="x")
        
        ctk.CTkLabel(header, text=f"💬 {self.usuario_logado}", text_color="white", font=("Segoe UI", 18, "bold")).pack(side="left", padx=25)
        
        btn_sair = ctk.CTkButton(
            header, text="SAIR", width=80, height=32, corner_radius=8,
            fg_color="#CC3333", hover_color="#990000", font=("Segoe UI", 11, "bold"),
            command=self.fazer_logout
        )
        btn_sair.pack(side="right", padx=25)

        # 2. Painel Lateral (Contatos)
        sidebar = ctk.CTkFrame(self.container, width=280, corner_radius=0, fg_color="#1E1E1E")
        sidebar.pack(side="left", fill="y")
        
        # Título da Lista de Contatos
        ctk.CTkLabel(sidebar, text="CONTATOS DISPONÍVEIS", font=("Segoe UI", 12, "bold"), text_color="#00FF7F").pack(pady=(20, 10))
        
        self.frame_lista = ctk.CTkScrollableFrame(sidebar, fg_color="transparent", corner_radius=0)
        self.frame_lista.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 3. Área de Chat (Direita)
        self.frame_chat = ctk.CTkFrame(self.container, corner_radius=0, fg_color="transparent")
        self.frame_chat.pack(side="right", fill="both", expand=True)
        
        self.chat_display = ctk.CTkTextbox(self.frame_chat, state="disabled", font=("Segoe UI", 14), wrap="word", fg_color="#121212", border_width=1, border_color="#333333")
        self.chat_display.pack(fill="both", expand=True, padx=15, pady=(15, 0))
        self.chat_display.tag_config("eu", justify="right", foreground="#00FF7F")
        self.chat_display.tag_config("outro", justify="left", foreground="#FFFFFF")

        # Entrada de Mensagem
        input_area = ctk.CTkFrame(self.frame_chat, fg_color="transparent")
        input_area.pack(fill="x", side="bottom", padx=15, pady=15)

        self.input_msg = ctk.CTkEntry(input_area, placeholder_text="Escreva aqui...", height=50, corner_radius=15, border_color="#333333")
        self.input_msg.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input_msg.bind("<Return>", lambda e: self.enviar_mensagem_p2p())

        btn_enviar = ctk.CTkButton(input_area, text="ENVIAR", width=100, height=50, corner_radius=15, command=self.enviar_mensagem_p2p)
        btn_enviar.pack(side="right")

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

    def enviar_mensagem_p2p(self):
        texto = self.input_msg.get().strip()
        if not texto or not self.contato_atual: return
        self.input_msg.delete(0, ctk.END)
        self.registrar_e_exibir(self.contato_atual, texto, self.usuario_logado)
        pacote = self.sessao_server.cifrar_mensagem({"acao": "enviar_mensagem", "destinatario": self.contato_atual, "conteudo": texto})
        self.rede.enviar(pacote)

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
            
            # NOVO: Tratamento de Registro com Pop-up
            if acao == "resposta_registro":
                if dados.get("sucesso"):
                    messagebox.showinfo("Sucesso", "🎉 Conta criada com sucesso! Você já pode entrar.")
                    self.root.after(0, self.abrir_login)
                else:
                    messagebox.showerror("Erro", f"Ops! {dados.get('mensagem')}")

            elif acao == "resposta_login" and dados.get("sucesso"):
                self.usuario_logado = self.usuario_tentando_logar
                self.root.after(0, self.tela_principal)
            elif acao == "nova_mensagem":
                self.root.after(0, lambda: self.registrar_e_exibir(dados['remetente'], dados['conteudo'], dados['remetente']))
            elif acao == "resposta_contatos":
                self.root.after(0, lambda: self.atualizar_lista(dados['contatos']))
        except Exception as e: print(f"Erro: {e}")

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
                contact_frame = ctk.CTkFrame(
                    self.frame_lista, 
                    fg_color="transparent", 
                    corner_radius=8,
                    cursor="hand2"
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
                for componente in (contact_frame, status_indicator, user_label):
                    componente.bind("<Button-1>", ao_clicar)  # Botão esquerdo do rato
                    componente.bind("<Enter>", ao_entrar)     # O rato entra na área
                    componente.bind("<Leave>", ao_sair)       # O rato sai da área
if __name__ == "__main__":
    root = ctk.CTk()
    app = ChatApp(root)
    root.mainloop()