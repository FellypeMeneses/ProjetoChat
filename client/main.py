import tkinter as tk
from tkinter import messagebox
import database    # Conexão MySQL
import interface   # Design das telas

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Parceiro Chat v1.0")
        self.root.geometry("400x500")
        self.usuario_logado = None
        self.container = tk.Frame(self.root)
        self.container.pack(expand=True, fill="both")
        
        self.abrir_login()

    def limpar_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def abrir_login(self):
        self.limpar_container()
        # Aqui você pode usar a função que já tínhamos ou criar uma no interface.py
        tk.Label(self.container, text="LOGIN", font=("Arial", 16, "bold")).pack(pady=20)
        
        self.ent_login_user = tk.Entry(self.container)
        self.ent_login_user.pack(pady=5)
        self.ent_login_pass = tk.Entry(self.container, show="*")
        self.ent_login_pass.pack(pady=5)
        
        tk.Button(self.container, text="ENTRAR", command=self.logar).pack(pady=10)
        tk.Button(self.container, text="Criar nova conta", command=self.abrir_cadastro).pack()

    def abrir_cadastro(self):
        self.limpar_container()
        # Usando a função do interface.py que acabamos de criar!
        self.ent_cad_user, self.ent_cad_pass = interface.montar_layout_cadastro(
            self.container, self.registrar, self.abrir_login
        )

    def registrar(self):
        user = self.ent_cad_user.get()
        senha = self.ent_cad_pass.get()
        if user and senha:
            sucesso, msg = database.registrar_usuario(user, senha)
            if sucesso:
                messagebox.showinfo("Sucesso", msg)
                self.abrir_login()
            else:
                messagebox.showerror("Erro", msg)
        else:
            messagebox.showwarning("Aviso", "Preencha tudo!")

    def logar(self):
        user = self.ent_login_user.get()
        senha = self.ent_login_pass.get()
        sucesso, resultado = database.validar_login(user, senha)
        if sucesso:
            self.usuario_logado = resultado
            self.tela_principal()
        else:
            messagebox.showerror("Erro", resultado)

    def tela_principal(self):
        self.limpar_container()
        tk.Label(self.container, text=f"Olá, {self.usuario_logado['nome_usuario']}!", font=("Arial", 14)).pack(pady=50)
        tk.Button(self.container, text="Sair", command=self.abrir_login).pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()