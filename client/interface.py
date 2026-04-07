import tkinter as tk

class Cores:
    BG = "#F0F2F5"
    BOTAO_CADASTRO = "#34B7F1"
    BOTAO_LOGIN = "#25D366"
    TEXTO = "#333333"

def montar_layout_cadastro(frame_pai, acao_registrar, acao_voltar):
    frame_pai.configure(bg=Cores.BG)
    
    tk.Label(frame_pai, text="CRIAR CONTA", font=("Arial", 16, "bold"), bg=Cores.BG).pack(pady=20)
    
    tk.Label(frame_pai, text="Usuário:", bg=Cores.BG).pack()
    ent_user = tk.Entry(frame_pai)
    ent_user.pack(pady=5)
    
    tk.Label(frame_pai, text="Senha:", bg=Cores.BG).pack()
    ent_pass = tk.Entry(frame_pai, show="*")
    ent_pass.pack(pady=5)
    
    tk.Button(frame_pai, text="REGISTRAR", bg=Cores.BOTAO_CADASTRO, fg="white", command=acao_registrar).pack(pady=10, fill="x")
    tk.Button(frame_pai, text="Voltar para Login", relief="flat", bg=Cores.BG, command=acao_voltar).pack()
    
    return ent_user, ent_pass