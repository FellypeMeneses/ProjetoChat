import tkinter as tk
from tkinter import messagebox
import interface, crypto_utils, crypto_p2p, historico, os, threading, json
from rede import ClienteRede
from crypto_session import SessaoCriptografada

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Parceiro Chat - Seguro")
        self.root.geometry("650x700")
        
        self.usuario_logado = None
        self.usuario_tentando_logar = None
        self.contato_atual = None
        self.chave_aes_local = None 
        self.sessao_server = None 
        
        self.container = tk.Frame(self.root)
        self.container.pack(expand=True, fill="both")
        
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

    def tentar_login(self):
        user, senha = self.ent_user.get(), self.ent_pass.get()
        if user and senha:
            self.usuario_tentando_logar = user
            self.chave_aes_local, _ = historico.derivar_chave_local(senha)
            pacote = self.sessao_server.cifrar_mensagem({"acao": "login", "usuario": user, "senha": senha})
            self.rede.enviar(pacote)

    def tentar_cadastro(self):
        user, senha = self.ent_user.get(), self.ent_pass.get()
        if user and senha:
            pub = crypto_utils.obter_chave_publica_bytes(self.chave_privada.public_key()).hex()
            pacote = self.sessao_server.cifrar_mensagem({"acao": "registrar", "usuario": user, "senha": senha, "chave_publica": pub})
            self.rede.enviar(pacote)

    # --- TELA PRINCIPAL (CORRIGIDA) ---
    def tela_principal(self):
        for w in self.container.winfo_children(): w.destroy()
        
        # 1. Header (Laranja)
        header = tk.Frame(self.container, bg="#FF8C00", height=60)
        header.pack(side="top", fill="x")
        tk.Label(header, text=f"👤 {self.usuario_logado}", fg="white", bg="#FF8C00", font=("Arial", 12, "bold")).pack(side="left", padx=20)

        # 2. Barra Lateral de Contatos (Esquerda)
        self.frame_lista = tk.Frame(self.container, width=200, bg="#F0F2F5")
        self.frame_lista.pack(side="left", fill="y")
        self.lista_contatos = tk.Listbox(self.frame_lista, bd=0, bg="#F0F2F5", font=("Arial", 10))
        self.lista_contatos.pack(fill="both", expand=True, padx=5, pady=5)
        self.lista_contatos.bind('<<ListboxSelect>>', self.selecionar_contato)

        # 3. Frame do Chat (Direita) - Definir PRIMEIRO para evitar AttributeError
        self.frame_chat = tk.Frame(self.container, bg="#121212")
        self.frame_chat.pack(side="right", fill="both", expand=True)
        
        # IMPORTANTE: Definir self.chat_display ANTES de qualquer comando que o use
        self.chat_display = tk.Text(self.frame_chat, state="disabled", bg="#121212", fg="white", font=("Arial", 11), padx=10, pady=10, bd=0)
        self.chat_display.pack(fill="both", expand=True)
        
        # Tags de Bolha
        self.chat_display.tag_config("eu", justify="right", foreground="#DCF8C6")
        self.chat_display.tag_config("outro", justify="left", foreground="#FFFFFF")

        self.input_msg = tk.Entry(self.frame_chat, bg="#2c2c2c", fg="white", insertbackground="white", bd=0)
        self.input_msg.pack(fill="x", side="bottom", padx=10, pady=10, ipady=8)
        self.input_msg.bind("<Return>", lambda e: self.enviar_mensagem_p2p())

        # Solicita contatos ao servidor
        self.rede.enviar(self.sessao_server.cifrar_mensagem({"acao": "obter_contatos"}))

    def selecionar_contato(self, event):
        selecao = self.lista_contatos.curselection()
        if selecao:
            # Pegar o nome limpando o ícone ●
            nome_raw = self.lista_contatos.get(selecao[0])
            self.contato_atual = nome_raw[4:].split(" - ")[0].strip()
            
            # Carregar Histórico
            self.chat_display.config(state="normal")
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.insert(tk.END, f"--- Conversa com {self.contato_atual} ---\n\n")
            
            mensagens = historico.carregar_historico_local(self.usuario_logado, self.contato_atual, self.chave_aes_local)
            for m in mensagens:
                tag = "eu" if m['remetente'] == self.usuario_logado else "outro"
                self.chat_display.insert(tk.END, f"{m['remetente']}: {m['texto']}\n\n", tag)
            
            self.chat_display.config(state="disabled")
            self.chat_display.see(tk.END)

    def enviar_mensagem_p2p(self):
        texto = self.input_msg.get().strip()
        if not texto or not self.contato_atual: return
        self.input_msg.delete(0, tk.END)

        # Exibe e Salva
        self.registrar_e_exibir(self.contato_atual, texto, self.usuario_logado)

        # Camada 1 para o servidor
        pacote = self.sessao_server.cifrar_mensagem({
            "acao": "enviar_mensagem", "destinatario": self.contato_atual, "conteudo": texto
        })
        self.rede.enviar(pacote)

    def registrar_e_exibir(self, contato, texto, remetente):
        historico.salvar_mensagem_protegida(self.usuario_logado, contato, remetente, texto, self.chave_aes_local)
        
        # Garante que o componente existe antes de atualizar
        if hasattr(self, 'chat_display'):
            self.chat_display.config(state="normal")
            tag = "eu" if remetente == self.usuario_logado else "outro"
            self.chat_display.insert(tk.END, f"{remetente}: {texto}\n\n", tag)
            self.chat_display.config(state="disabled")
            self.chat_display.see(tk.END)

    def processar_resposta_servidor(self, pacote):
        try:
            dados = self.sessao_server.decifrar_mensagem(pacote)
            acao = dados.get("acao")
            if acao == "resposta_login" and dados.get("sucesso"):
                self.usuario_logado = self.usuario_tentando_logar
                self.root.after(0, self.tela_principal)
            elif acao == "nova_mensagem":
                self.root.after(0, lambda: self.registrar_e_exibir(dados['remetente'], dados['conteudo'], dados['remetente']))
            elif acao == "resposta_contatos":
                self.root.after(0, lambda: self.atualizar_lista(dados['contatos']))
        except Exception as e: print(f"Erro: {e}")

    def atualizar_lista(self, contatos):
        self.lista_contatos.delete(0, tk.END)
        for c in contatos:
            if c['nome_usuario'] != self.usuario_logado:
                status = "●" if c['status'].lower() == 'online' else "○"
                cor = "#00FF7F" if status == "●" else "#808080"
                self.lista_contatos.insert(tk.END, f" {status}  {c['nome_usuario'].upper()}")
                self.lista_contatos.itemconfig(tk.END, fg=cor)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()