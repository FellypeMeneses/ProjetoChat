import tkinter as tk
from tkinter import messagebox
import interface
from rede import ClienteRede  # Importamos nossa nova classe de rede

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Parceiro Chat - Cliente TCP")
        self.root.geometry("400x500")
        self.usuario_logado = None
        
        # Inicia a rede e tenta conectar ao servidor
        self.rede = ClienteRede()
        sucesso, msg = self.rede.conectar()
        if not sucesso:
            messagebox.showerror("Erro de Rede", msg)
            self.root.destroy()
            return
            
        # Diz para a rede qual função deve ser chamada quando chegar mensagem
        self.rede.ao_receber_mensagem = self.processar_resposta_servidor

        self.container = tk.Frame(self.root)
        self.container.pack(expand=True, fill="both")
        
        self.abrir_login()

    def limpar_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # --- TELAS (Usando o interface.py) ---
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
        tk.Label(self.container, text=f"Logado como: {self.usuario_logado}", font=("Arial", 14)).pack(pady=50)
        # Futuramente aqui ficará a lista de contatos e chat
        tk.Button(self.container, text="Sair", command=self.abrir_login).pack()

    # --- AÇÕES DE REDE (Enviando JSON) ---
    def solicitar_registro(self):
        user = self.ent_cad_user.get()
        senha = self.ent_cad_pass.get()
        if user and senha:
            # Envia o pacote para o servidor via Socket
            pacote = {"acao": "registrar", "usuario": user, "senha": senha}
            self.rede.enviar(pacote)
        else:
            messagebox.showwarning("Aviso", "Preencha tudo!")

    def solicitar_login(self):
        user = self.ent_login_user.get()
        senha = self.ent_login_pass.get()
        if user and senha:
            # Envia o pacote para o servidor via Socket
            self.usuario_tentando_logar = user # Guarda temporariamente
            pacote = {"acao": "login", "usuario": user, "senha": senha}
            self.rede.enviar(pacote)

    # --- PROCESSANDO RESPOSTAS DO SERVIDOR ---
    def processar_resposta_servidor(self, dados):
        """Esta função é chamada pela Thread da rede quando o servidor responde"""
        acao = dados.get("acao")
        
        if acao == "resposta_registro":
            if dados["sucesso"]:
                # messagebox não se dá bem fora da thread principal, mas funciona na maioria dos sistemas
                messagebox.showinfo("Sucesso", dados["mensagem"])
                # Pede para o Tkinter rodar a mudança de tela com segurança
                self.root.after(0, self.abrir_login)
            else:
                messagebox.showerror("Erro", dados["mensagem"])
                
        elif acao == "resposta_login":
            if dados["sucesso"]:
                self.usuario_logado = self.usuario_tentando_logar
                messagebox.showinfo("Sucesso", "Bem-vindo ao Chat!")
                self.root.after(0, self.tela_principal)
            else:
                messagebox.showerror("Erro", dados["mensagem"])

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()