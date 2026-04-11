import tkinter as tk

class Cores:
    BG = "#F0F2F5"
    BOTAO_CADASTRO = "#34B7F1"
    BOTAO_LOGIN = "#25D366"
    TEXTO = "#333333"

# --- 1. TELA DE LOGIN ---
def montar_layout_login(frame_pai, comando_login, comando_ir_cadastro):
    frame_pai.configure(bg=Cores.BG)
    
    tk.Label(frame_pai, text="LOGIN DO CHAT", font=("Arial", 16, "bold"), bg=Cores.BG).pack(pady=20)
    
    tk.Label(frame_pai, text="Usuário:", bg=Cores.BG).pack()
    ent_user = tk.Entry(frame_pai)
    ent_user.pack(pady=5)
    
    tk.Label(frame_pai, text="Senha:", bg=Cores.BG).pack()
    ent_pass = tk.Entry(frame_pai, show="*")
    ent_pass.pack(pady=5)
    
    tk.Button(frame_pai, text="ENTRAR", bg=Cores.BOTAO_LOGIN, fg="white", font=("Arial", 10, "bold"), command=comando_login).pack(pady=20, fill="x", padx=50)
    
    tk.Label(frame_pai, text="Não tem conta?", bg=Cores.BG).pack()
    tk.Button(frame_pai, text="Cadastre-se aqui", fg="blue", cursor="hand2", relief="flat", bg=Cores.BG, command=comando_ir_cadastro).pack()
    
    return ent_user, ent_pass

# --- 2. TELA DE CADASTRO ---
def montar_layout_cadastro(frame_pai, acao_registrar, acao_voltar):
    frame_pai.configure(bg=Cores.BG)
    
    tk.Label(frame_pai, text="CRIAR NOVA CONTA", font=("Arial", 16, "bold"), bg=Cores.BG).pack(pady=20)
    
    tk.Label(frame_pai, text="Novo Usuário:", bg=Cores.BG).pack()
    ent_user = tk.Entry(frame_pai)
    ent_user.pack(pady=5)
    
    tk.Label(frame_pai, text="Nova Senha:", bg=Cores.BG).pack()
    ent_pass = tk.Entry(frame_pai, show="*")
    ent_pass.pack(pady=5)
    
    tk.Button(frame_pai, text="REGISTRAR", bg=Cores.BOTAO_CADASTRO, fg="white", font=("Arial", 10, "bold"), command=acao_registrar).pack(pady=10, fill="x", padx=50)
    tk.Button(frame_pai, text="Voltar para Login", relief="flat", bg=Cores.BG, command=acao_voltar).pack()
    
    return ent_user, ent_pass