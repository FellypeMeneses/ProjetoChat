import tkinter as tk
from tkinter import messagebox, simpledialog
import interface
from rede import ClienteRede
import historico
import json
import crypto_utils
import os
import threading

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Parceiro Chat - Cliente TCP")
        self.root.geometry("450x600")
        
        self.usuario_logado = None
        self.usuario_tentando_logar = None
        self.contato_atual = None
        self.timer_expiracao = None
        self.contador_msgs_sessao = 0
        
        # 1. Cria o container principal da interface
        self.container = tk.Frame(self.root)
        self.container.pack(expand=True, fill="both")
        
        # 2. Carrega as chaves locais (se existirem) para manter a identidade
        self.chave_privada = None
        self.chave_publica_bytes = None
        if os.path.exists("chave_privada.pem"):
            try:
                self.chave_privada = crypto_utils.carregar_chave_privada()
                self.chave_publica_bytes = crypto_utils.obter_chave_publica_bytes(self.chave_privada.public_key())
            except Exception as e:
                print(f"Erro ao carregar chave privada: {e}")

        # 3. Conecta ao servidor e estabelece a sessão segura
        self.rede = ClienteRede()
        sucesso, msg = self.rede.conectar()
        if not sucesso:
            messagebox.showerror("Erro de Rede", msg)
            self.root.destroy()
            return
            
        # 4. Define a função de escuta e abre a tela de login
        self.rede.ao_receber_mensagem = self.processar_resposta_servidor
        self.abrir_login()

    def limpar_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def abrir_login(self):
        self.limpar_container()
        self.ent_login_user, self.ent_login_pass = interface.montar_layout_login(
            self.container, self.solicitar_login, self.abrir_cadastro
        )

    def abrir_cadastro(self):
        self.limpar_container()
        self.ent_cad_user, self.ent_cad_pass = interface.montar_layout_cadastro(
            self.container, self.solicitar_registro, self.abrir_login
        )

    def tela_principal(self):
        self.limpar_container()
        self.contato_atual = None
        self.iniciar_timer_expiracao_sessao()
        
        self.lista_contatos_box = interface.montar_layout_contatos(
            self.container,
            self.usuario_logado,
            self.pedir_contatos_ao_servidor,
            self.abrir_login,
            self.solicitar_excluir_conta
        )
        self.pedir_contatos_ao_servidor()
        self.lista_contatos_box.bind('<Double-1>', self.abrir_tela_chat)

    def abrir_tela_chat(self, event=None):
        selecao = self.lista_contatos_box.curselection()
        if not selecao: return
        
        texto_selecionado = self.lista_contatos_box.get(selecao[0])
        self.contato_atual = texto_selecionado.split(" - ")[0].strip()
        
        self.limpar_container()
        self.list_mensagens, self.ent_mensagem = interface.montar_layout_chat(
            self.container, self.contato_atual, self.enviar_mensagem_texto,
            self.tela_principal, self.solicitar_exclusao, self.solicitar_edicao
        )
        
        mensagens_antigas = historico.carregar_mensagens(self.usuario_logado, self.contato_atual)
        for remetente, msg in mensagens_antigas:
            self.inserir_texto_no_chat(f"{remetente}: {msg}")

    def enviar_mensagem_texto(self):
        texto = self.ent_mensagem.get()
        if texto.strip() and self.contato_atual:
            pacote = {"acao": "enviar_mensagem", "destinatario": self.contato_atual, "conteudo": texto}
            self.rede.enviar(pacote)
            historico.salvar_mensagem(self.usuario_logado, self.contato_atual, "Você", texto)
            self.inserir_texto_no_chat(f"Você: {texto}")
            self.ent_mensagem.delete(0, tk.END)

            self.contador_msgs_sessao += 1
            if self.contador_msgs_sessao >= 90:
                self.root.after(0, lambda: messagebox.showwarning(
                    "Mensagens Restantes",
                    f"Mais {100 - self.contador_msgs_sessao} mensagens até renovação da sessão."
                ))

    def iniciar_timer_expiracao_sessao(self):
        if self.timer_expiracao:
            self.root.after_cancel(self.timer_expiracao)
        self.timer_expiracao = self.root.after(3540000, self.mostrar_aviso_expiracao) # 59 minutos

    def mostrar_aviso_expiracao(self):
        messagebox.showwarning("Sessão Expirando", "A sessão criptográfica vai expirar em breve.")

    def solicitar_excluir_conta(self):
        confirmacao = messagebox.askyesno("Excluir Conta", "Tem certeza que deseja excluir sua conta permanentemente?")
        if confirmacao:
            self.rede.enviar({"acao": "excluir_conta"})

    def solicitar_exclusao(self):
        selecao = self.list_mensagens.curselection()
        if not selecao: return
        indice = selecao[0]
        texto_mensagem = self.list_mensagens.get(indice)
        
        if texto_mensagem.startswith("Você:"):
            texto_limpo = texto_mensagem.replace("Você: ", "", 1).replace(" (editado)", "")
            self.list_mensagens.delete(indice)
            historico.excluir_mensagem_bd(self.usuario_logado, self.contato_atual, "Você", texto_limpo)
            self.rede.enviar({"acao": "excluir_mensagem", "destinatario": self.contato_atual, "conteudo_original": texto_limpo})
        else:
            messagebox.showwarning("Bloqueado", "Você só pode apagar as suas próprias mensagens!")

    def solicitar_edicao(self):
        selecao = self.list_mensagens.curselection()
        if not selecao: return
        indice = selecao[0]
        texto_mensagem = self.list_mensagens.get(indice)
        
        if texto_mensagem.startswith("Você:"):
            texto_original = texto_mensagem.replace("Você: ", "", 1).replace(" (editado)", "")
            novo_texto = simpledialog.askstring("Editar Mensagem", "Digite a nova mensagem:", initialvalue=texto_original)
            
            if novo_texto and novo_texto != texto_original:
                self.list_mensagens.delete(indice)
                self.list_mensagens.insert(indice, f"Você: {novo_texto} (editado)")
                historico.editar_mensagem_bd(self.usuario_logado, self.contato_atual, "Você", texto_original, novo_texto)
                self.rede.enviar({"acao": "editar_mensagem", "destinatario": self.contato_atual, "conteudo_original": texto_original, "conteudo_novo": novo_texto})
        else:
            messagebox.showwarning("Bloqueado", "Você só pode editar as suas próprias mensagens!")

    def inserir_texto_no_chat(self, texto):
        if hasattr(self, 'list_mensagens') and self.list_mensagens.winfo_exists():
            self.list_mensagens.insert(tk.END, texto)
            self.list_mensagens.yview(tk.END)

    def solicitar_registro(self):
        user = self.ent_cad_user.get()
        senha = self.ent_cad_pass.get()
        if user and senha:
            if not self.chave_privada:
                priv, pub = crypto_utils.gerar_par_chaves_ecc()
                self.chave_privada = priv
                self.chave_publica_bytes = crypto_utils.obter_chave_publica_bytes(pub)
                crypto_utils.salvar_chave_privada(priv)
                
            self.rede.enviar({
                "acao": "registrar",
                "usuario": user,
                "senha": senha,
                "chave_publica": self.chave_publica_bytes.hex()
            })

    def solicitar_login(self):
        user = self.ent_login_user.get()
        senha = self.ent_login_pass.get()
        
        if user and senha:
            self.usuario_tentando_logar = user
            self.rede.enviar({"acao": "login", "usuario": user, "senha": senha})

    def pedir_contatos_ao_servidor(self):
        self.rede.enviar({"acao": "pedir_contatos"})

    def processar_resposta_servidor(self, dados):
        acao = dados.get("acao")
        
        if acao == "resposta_registro":
            if dados["sucesso"]:
                messagebox.showinfo("Sucesso", dados["mensagem"])
                self.root.after(0, self.abrir_login)
            else:
                messagebox.showerror("Erro", dados["mensagem"])
                
        elif acao == "resposta_login":
            if dados["sucesso"]:
                self.usuario_logado = self.usuario_tentando_logar
                self.root.after(0, self.tela_principal)
            else:
                messagebox.showerror("Erro", dados["mensagem"])
                
        elif acao == "desafio_login":
            nonce = dados.get("nonce")
            # Responde ao desafio com a assinatura
            
            self.rede.responder_desafio(
                self.usuario_tentando_logar, 
                nonce, 
                self.chave_privada
            )
                
        elif acao == "resposta_exclusao_conta":
            if dados["sucesso"]:
                messagebox.showinfo("Conta Excluída", "Sua conta foi apagada com sucesso.")
                self.root.after(0, self.abrir_login)
            else:
                messagebox.showerror("Erro", dados["mensagem"])
                
        elif acao == "resposta_contatos":
            if dados["sucesso"]:
                def atualizar_lista():
                    self.lista_contatos_box.delete(0, tk.END)
                    for contato in dados["contatos"]:
                        nome = contato['nome_usuario']
                        status_bd = contato['status'].lower()
                        cor = "#00A884" if status_bd == "online" else "#EF4444"
                        self.lista_contatos_box.insert(tk.END, f"{nome} - ● {status_bd.upper()}")
                        self.lista_contatos_box.itemconfig(tk.END, fg=cor)
                self.root.after(0, atualizar_lista)

        elif acao == "nova_mensagem":
            remetente = dados.get("remetente")
            conteudo = dados.get("conteudo")
            historico.salvar_mensagem(self.usuario_logado, remetente, remetente, conteudo)
            def atualizar_chat():
                if self.contato_atual == remetente:
                    self.inserir_texto_no_chat(f"{remetente}: {conteudo}")
                else:
                    messagebox.showinfo("Nova Mensagem", f"Mensagem de {remetente}: {conteudo}")
            self.root.after(0, atualizar_chat)

        elif acao == "apagar_mensagem_tela":
            remetente = dados.get("remetente")
            conteudo_apagado = dados.get("conteudo")
            historico.excluir_mensagem_bd(self.usuario_logado, remetente, remetente, conteudo_apagado)
            def atualizar_exclusao():
                if self.contato_atual == remetente and hasattr(self, 'list_mensagens'):
                    mensagens = self.list_mensagens.get(0, tk.END)
                    for i, msg in enumerate(mensagens):
                        if msg == f"{remetente}: {conteudo_apagado}" or msg == f"{remetente}: {conteudo_apagado} (editado)":
                            self.list_mensagens.delete(i)
                            self.list_mensagens.insert(i, f"🚫 {remetente} apagou uma mensagem.")
                            break
            self.root.after(0, atualizar_exclusao)

        elif acao == "editar_mensagem_tela":
            remetente = dados.get("remetente")
            conteudo_original = dados.get("conteudo_original")
            conteudo_novo = dados.get("conteudo_novo")
            historico.editar_mensagem_bd(self.usuario_logado, remetente, remetente, conteudo_original, conteudo_novo)
            def atualizar_edicao():
                if self.contato_atual == remetente and hasattr(self, 'list_mensagens'):
                    mensagens = self.list_mensagens.get(0, tk.END)
                    for i, msg in enumerate(mensagens):
                        if msg == f"{remetente}: {conteudo_original}" or msg == f"{remetente}: {conteudo_original} (editado)":
                            self.list_mensagens.delete(i)
                            self.list_mensagens.insert(i, f"{remetente}: {conteudo_novo} (editado)")
                            break
            self.root.after(0, atualizar_edicao)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()