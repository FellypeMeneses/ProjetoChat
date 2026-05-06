import tkinter as tk
from tkinter import messagebox, simpledialog
import interface
from rede import ClienteRede
import historico
import crypto_utils
import crypto_p2p # Importamos a nova lógica de Ponta-a-Ponta
import os
import sys
import traceback

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Parceiro Chat - Cliente Seguro")
        self.root.geometry("450x600")
        
        self.usuario_logado = None
        self.usuario_tentando_logar = None
        self.contato_atual = None
        
        # Dicionário que guarda os segredos matemáticos com cada amigo
        self.sessoes_p2p = {} 
        
        self.container = tk.Frame(self.root)
        self.container.pack(expand=True, fill="both")
        
        self.chave_privada = None
        self.carregar_identidade()

        self.rede = ClienteRede()
        sucesso, msg = self.rede.conectar()
        
        if not sucesso:
            print(f"\n❌ ERRO DE REDE: {msg}") 
            self.root.withdraw()
            messagebox.showerror("Erro de Conexão", f"Falha ao conectar.\nDetalhe: {msg}")
            self.root.destroy()
            sys.exit(1)
            
        self.rede.ao_receber_mensagem = self.processar_resposta_servidor
        self.abrir_login()

    def carregar_identidade(self):
        if os.path.exists("chave_privada.pem"):
            try: self.chave_privada = crypto_utils.carregar_chave_privada()
            except Exception as e: print(f"Aviso: {e}")

    # (Funções de Layout omitidas aqui para focar na lógica de Criptografia)
    def abrir_login(self):
        for widget in self.container.winfo_children(): widget.destroy()
        self.ent_login_user, self.ent_login_pass = interface.montar_layout_login(self.container, self.solicitar_login, self.abrir_cadastro)

    def abrir_cadastro(self):
        for widget in self.container.winfo_children(): widget.destroy()
        self.ent_cad_user, self.ent_cad_pass = interface.montar_layout_cadastro(self.container, self.solicitar_registro, self.abrir_login)

    def tela_principal(self):
        for widget in self.container.winfo_children(): widget.destroy()
        self.lista_contatos_box = interface.montar_layout_contatos(
            self.container, self.usuario_logado, 
            lambda: self.rede.enviar({"acao": "pedir_contatos"}),
            self.abrir_login, lambda: self.rede.enviar({"acao": "excluir_conta"})
        )
        self.rede.enviar({"acao": "pedir_contatos"})
        self.lista_contatos_box.bind('<Double-1>', self.abrir_tela_chat)

    def abrir_tela_chat(self, event=None):
        selecao = self.lista_contatos_box.curselection()
        if not selecao: return
        self.contato_atual = self.lista_contatos_box.get(selecao[0]).split(" - ")[0].strip()
        
        for widget in self.container.winfo_children(): widget.destroy()
        self.list_mensagens, self.ent_mensagem = interface.montar_layout_chat(
            self.container, self.contato_atual, self.enviar_mensagem_texto,
            self.tela_principal, lambda: print("Excluir"), lambda: print("Editar")
        )
        
        for rem, msg in historico.carregar_mensagens(self.usuario_logado, self.contato_atual):
            self.list_mensagens.insert(tk.END, f"{rem}: {msg}")

    # --- LÓGICA DE REGISTO E LOGIN ---
    def solicitar_login(self):
        user, senha = self.ent_login_user.get(), self.ent_login_pass.get()
        if user and senha:
            self.usuario_tentando_logar = user
            self.rede.enviar({"acao": "login_desafio", "usuario": user})

    def solicitar_registro(self):
        user, senha = self.ent_cad_user.get(), self.ent_cad_pass.get()
        if user and senha:
            priv, pub = crypto_utils.gerar_par_chaves_ed25519()
            self.chave_privada = priv
            crypto_utils.salvar_chave_privada(priv)
            self.rede.enviar({"acao": "registrar", "usuario": user, "senha": senha, "chave_publica": crypto_utils.obter_chave_publica_bytes(pub).hex()})

    # --- LÓGICA DE MENSAGENS COM P2P ---
    def enviar_mensagem_texto(self):
        texto = self.ent_mensagem.get()
        if texto.strip() and self.contato_atual:
            
            # Verifica se já temos o segredo matemático com este contato
            if self.contato_atual not in self.sessoes_p2p or not self.sessoes_p2p[self.contato_atual].handshake_completo:
                # Se não temos, cria a sessão e inicia o aperto de mão
                sessao = crypto_p2p.SessaoP2P()
                self.sessoes_p2p[self.contato_atual] = sessao
                pub_bytes, salt = sessao.iniciar_handshake_iniciador()
                
                self.rede.enviar({
                    "acao": "p2p_handshake",
                    "destinatario": self.contato_atual,
                    "public_key": pub_bytes.hex(),
                    "salt": salt.hex()
                })
                self.list_mensagens.insert(tk.END, "🔒 Negociando chaves seguras... Aguarde 1 segundo e envie novamente.")
                return

            # Se já temos o segredo, ciframos o texto e enviamos ao servidor
            pacote_cifrado = self.sessoes_p2p[self.contato_atual].cifrar_mensagem(texto)
            self.rede.enviar({"acao": "enviar_mensagem", "destinatario": self.contato_atual, "conteudo": pacote_cifrado})
            
            historico.salvar_mensagem(self.usuario_logado, self.contato_atual, "Você", texto)
            self.list_mensagens.insert(tk.END, f"Você: {texto}")
            self.ent_mensagem.delete(0, tk.END)

    def tratar_chegada_mensagem(self, dados):
        remetente = dados.get("remetente")
        pacote_cifrado = dados.get("conteudo")
        
        # Desempacota e decifra o texto usando o segredo partilhado
        if remetente in self.sessoes_p2p and self.sessoes_p2p[remetente].handshake_completo:
            try:
                texto_decifrado = self.sessoes_p2p[remetente].decifrar_mensagem(pacote_cifrado)
                historico.salvar_mensagem(self.usuario_logado, remetente, remetente, texto_decifrado)
                if self.contato_atual == remetente:
                    self.root.after(0, lambda: self.list_mensagens.insert(tk.END, f"{remetente}: {texto_decifrado}"))
            except Exception as e:
                print(f"Erro de Segurança: Mensagem de {remetente} foi adulterada. Erro: {e}")
        else:
            print(f"Aviso: Mensagem recebida de {remetente} sem handshake P2P anterior.")

    # --- RESPOSTAS DO SERVIDOR ---
    def processar_resposta_servidor(self, dados):
        acao = dados.get("acao")
        
        # --- ROTEAMENTO DO HANDSHAKE P2P ---
        if acao == "p2p_handshake":
            # Passo 2: Recebemos o pedido de handshake, geramos resposta
            remetente = dados.get("remetente")
            pub_remota = bytes.fromhex(dados.get("public_key"))
            salt = bytes.fromhex(dados.get("salt"))
            
            sessao = crypto_p2p.SessaoP2P()
            self.sessoes_p2p[remetente] = sessao
            pub_local = sessao.responder_handshake(pub_remota, salt)
            
            self.rede.enviar({
                "acao": "p2p_handshake_resposta",
                "destinatario": remetente,
                "public_key": pub_local.hex()
            })

        elif acao == "p2p_handshake_resposta":
            # Passo 3: O iniciador recebe a resposta e finaliza a matemática
            remetente = dados.get("remetente")
            pub_remota = bytes.fromhex(dados.get("public_key"))
            if remetente in self.sessoes_p2p:
                self.sessoes_p2p[remetente].finalizar_handshake_iniciador(pub_remota)
                if self.contato_atual == remetente:
                    self.root.after(0, lambda: self.list_mensagens.insert(tk.END, "✅ Chat Seguro estabelecido! Pode enviar."))

        elif acao == "erro_p2p":
            self.root.after(0, lambda: messagebox.showwarning("Aviso de Segurança", dados.get("mensagem")))

        # --- EVENTOS GERAIS ---
        elif acao == "desafio_login":
            nonce = dados.get("nonce")
            if self.chave_privada: self.rede.responder_desafio(self.usuario_tentando_logar, nonce, self.chave_privada)
            
        elif acao == "resposta_login":
            if dados["sucesso"]:
                self.usuario_logado = self.usuario_tentando_logar
                self.root.after(0, self.tela_principal)
            else:
                self.root.after(0, lambda: messagebox.showerror("Erro de Login", dados.get("mensagem")))

        elif acao == "resposta_registro":
            if dados["sucesso"]: self.root.after(0, self.abrir_login)
            self.root.after(0, lambda: messagebox.showinfo("Registro", dados["mensagem"]))

        elif acao == "nova_mensagem":
            self.tratar_chegada_mensagem(dados)
            
        elif acao == "resposta_contatos":
            if dados.get("sucesso") and hasattr(self, 'lista_contatos_box'):
                def atualizar_lista():
                    self.lista_contatos_box.delete(0, tk.END)
                    for contato in dados["contatos"]:
                        nome = contato['nome_usuario']
                        status_bd = contato.get('status', 'offline').lower()
                        cor = "#00A884" if status_bd == "online" else "#EF4444"
                        self.lista_contatos_box.insert(tk.END, f"{nome} - ● {status_bd.upper()}")
                        self.lista_contatos_box.itemconfig(tk.END, fg=cor)
                self.root.after(0, atualizar_lista)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ChatApp(root)
        root.mainloop()
    except Exception as e:
        print("\n" + "="*50)
        traceback.print_exc()
        input("Pressione ENTER para fechar o terminal...")