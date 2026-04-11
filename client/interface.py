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
def montar_layout_contatos(frame_pai, nome_usuario, acao_atualizar, acao_sair):
    frame_pai.configure(bg=Cores.BG)
    
    # Cabeçalho
    header = tk.Frame(frame_pai, bg="#075E54", pady=10)
    header.pack(fill="x")
    tk.Label(header, text=f"Bem-vindo, {nome_usuario}", fg="white", bg="#075E54", font=("Arial", 12, "bold")).pack(side="left", padx=10)
    tk.Button(header, text="Sair", command=acao_sair, bg="red", fg="white", relief="flat").pack(side="right", padx=10)
    
    # Título da Lista
    tk.Label(frame_pai, text="Seus Contatos", font=("Arial", 14, "bold"), bg=Cores.BG).pack(pady=10)
    
    # Lista de Contatos (Listbox)
    frame_lista = tk.Frame(frame_pai)
    frame_lista.pack(fill="both", expand=True, padx=20, pady=5)
    
    scrollbar = tk.Scrollbar(frame_lista)
    scrollbar.pack(side="right", fill="y")
    
    lista_box = tk.Listbox(frame_lista, yscrollcommand=scrollbar.set, font=("Arial", 12), height=15)
    lista_box.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=lista_box.yview)
    
    # Botão para atualizar manualmente
    tk.Button(frame_pai, text="Atualizar Lista", bg=Cores.BOTAO_LOGIN, fg="white", command=acao_atualizar).pack(pady=10)
    
    return lista_box
# --- 3. TELA DE CHAT ---
# --- 3. TELA DE CHAT (ATUALIZADA PARA EDIÇÃO/EXCLUSÃO) ---
# --- 3. TELA DE CHAT (ATUALIZADA PARA EDIÇÃO/EXCLUSÃO) ---
def montar_layout_chat(frame_pai, nome_contato, acao_enviar, acao_voltar, acao_excluir, acao_editar):
    frame_pai.configure(bg=Cores.BG)
    
    header = tk.Frame(frame_pai, bg="#075E54", pady=10)
    header.pack(fill="x")
    tk.Button(header, text="< Voltar", command=acao_voltar, bg="#075E54", fg="white", relief="flat", font=("Arial", 10, "bold")).pack(side="left", padx=5)
    tk.Label(header, text=nome_contato, fg="white", bg="#075E54", font=("Arial", 14, "bold")).pack(side="left", padx=10)

    frame_chat = tk.Frame(frame_pai)
    frame_chat.pack(fill="both", expand=True, padx=10, pady=10)
    
    scrollbar = tk.Scrollbar(frame_chat)
    scrollbar.pack(side="right", fill="y")
    
    lista_mensagens = tk.Listbox(frame_chat, yscrollcommand=scrollbar.set, font=("Arial", 12), bg="#ECE5DD")
    lista_mensagens.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=lista_mensagens.yview)

    # Menu de Opções (Botão Direito)
    menu_opcoes = tk.Menu(frame_pai, tearoff=0)
    menu_opcoes.add_command(label="Editar Mensagem", command=acao_editar)
    menu_opcoes.add_command(label="Excluir Mensagem", command=acao_excluir)

    def mostrar_menu(event):
        selecao = lista_mensagens.curselection()
        if selecao:
            menu_opcoes.tk_popup(event.x_root, event.y_root)

    lista_mensagens.bind("<Button-3>", mostrar_menu)

    frame_input = tk.Frame(frame_pai, bg=Cores.BG, pady=10)
    frame_input.pack(fill="x", side="bottom", padx=10)
    
    ent_msg = tk.Entry(frame_input, font=("Arial", 12))
    ent_msg.pack(side="left", fill="x", expand=True, padx=5, ipady=8)
    
    btn_enviar = tk.Button(frame_input, text="Enviar", bg=Cores.BOTAO_LOGIN, fg="white", font=("Arial", 10, "bold"), command=acao_enviar)
    btn_enviar.pack(side="right", padx=5)

    ent_msg.bind("<Return>", lambda event: acao_enviar())

    return lista_mensagens, ent_msg

    def mostrar_menu(event):
        """Mostra o menu onde o rato clicou, se houver uma mensagem selecionada"""
        selecao = lista_mensagens.curselection()
        if selecao:
            menu_opcoes.tk_popup(event.x_root, event.y_root)

    # Vincula o botão direito do rato (Button-3 no Windows/Linux) à Listbox
    lista_mensagens.bind("<Button-3>", mostrar_menu)

    # Área de Digitar
    frame_input = tk.Frame(frame_pai, bg=Cores.BG, pady=10)
    frame_input.pack(fill="x", side="bottom", padx=10)
    
    ent_msg = tk.Entry(frame_input, font=("Arial", 12))
    ent_msg.pack(side="left", fill="x", expand=True, padx=5, ipady=8)
    
    btn_enviar = tk.Button(frame_input, text="Enviar", bg=Cores.BOTAO_LOGIN, fg="white", font=("Arial", 10, "bold"), command=acao_enviar)
    btn_enviar.pack(side="right", padx=5)

    ent_msg.bind("<Return>", lambda event: acao_enviar())

    return lista_mensagens, ent_msg

    # Permite enviar pressionando a tecla "Enter"
    ent_msg.bind("<Return>", lambda event: acao_enviar())

    return txt_mensagens, ent_msg