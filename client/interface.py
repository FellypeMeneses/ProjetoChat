import tkinter as tk

# ==========================================
# PALETA DE CORES MODERNA (Estilo WhatsApp)
# ==========================================
class Cores:
    BG_FUNDO = "#ECE5DD"        # Fundo principal (bege claro)
    BG_CARD = "#FFFFFF"         # Fundo dos formulários (branco)
    PRIMARIA = "#008069"        # Verde escuro clássico do cabeçalho
    PRIMARIA_CLARA = "#00A884"  # Verde mais claro para botões
    TEXTO_ESCURO = "#111B21"    # Quase preto para leitura confortável
    TEXTO_CLARO = "#FFFFFF"     # Texto branco para cabeçalhos
    CINZA_TEXTO = "#667781"     # Cinza para dicas/labels
    BOTAO_VOLTAR = "#8696A0"    # Cinza azulado
    ERRO = "#EF4444"            # Vermelho mais suave

# ==========================================
# FUNÇÕES AUXILIARES DE DESIGN
# ==========================================
def criar_card_central(frame_pai):
    """Cria um 'cartão' branco no centro do ecrã para Login/Cadastro"""
    frame_pai.configure(bg=Cores.BG_FUNDO)
    
    # Um frame invisível para forçar a centralização
    frame_center = tk.Frame(frame_pai, bg=Cores.BG_FUNDO)
    frame_center.place(relx=0.5, rely=0.5, anchor="center")
    
    # O cartão branco com as bordas flat
    card = tk.Frame(frame_center, bg=Cores.BG_CARD, padx=40, pady=40, bd=0, highlightthickness=1, highlightbackground="#D1D7DB")
    card.pack()
    return card

def criar_input(frame_pai, titulo, is_senha=False):
    """Cria um campo de texto estilizado"""
    tk.Label(frame_pai, text=titulo, bg=Cores.BG_CARD, fg=Cores.CINZA_TEXTO, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 2))
    
    entry = tk.Entry(frame_pai, show="*" if is_senha else "", font=("Segoe UI", 12), bg="#F0F2F5", bd=0, highlightthickness=1, highlightbackground="#D1D7DB", relief="flat")
    entry.pack(fill="x", ipady=8, pady=(0, 10)) # ipady deixa o campo mais "gordinho"
    return entry

def criar_botao(frame_pai, texto, cor_bg, comando):
    """Cria um botão flat moderno"""
    btn = tk.Button(frame_pai, text=texto, bg=cor_bg, fg=Cores.TEXTO_CLARO, font=("Segoe UI", 11, "bold"), bd=0, cursor="hand2", relief="flat", activebackground=Cores.TEXTO_ESCURO, activeforeground=Cores.TEXTO_CLARO, command=comando)
    btn.pack(fill="x", pady=10, ipady=8)
    return btn

# ==========================================
# 1. TELA DE LOGIN
# ==========================================
def montar_layout_login(frame_pai, comando_login, comando_ir_cadastro):
    card = criar_card_central(frame_pai)
    
    tk.Label(card, text="Bem-vindo ao Chat", font=("Segoe UI", 18, "bold"), bg=Cores.BG_CARD, fg=Cores.TEXTO_ESCURO).pack(pady=(0, 20))
    
    ent_user = criar_input(card, "Usuário")
    ent_pass = criar_input(card, "Senha", is_senha=True)
    
    criar_botao(card, "ENTRAR", Cores.PRIMARIA, comando_login)
    
    # Botão estilo link
    tk.Button(card, text="Ainda não tem conta? Crie uma.", fg=Cores.PRIMARIA, bg=Cores.BG_CARD, cursor="hand2", relief="flat", activebackground=Cores.BG_CARD, font=("Segoe UI", 10, "underline"), command=comando_ir_cadastro).pack(pady=(10, 0))
    
    return ent_user, ent_pass

# ==========================================
# 2. TELA DE CADASTRO
# ==========================================
def montar_layout_cadastro(frame_pai, acao_registrar, acao_voltar):
    card = criar_card_central(frame_pai)
    
    tk.Label(card, text="Criar Conta", font=("Segoe UI", 18, "bold"), bg=Cores.BG_CARD, fg=Cores.TEXTO_ESCURO).pack(pady=(0, 20))
    
    ent_user = criar_input(card, "Novo Usuário")
    ent_pass = criar_input(card, "Nova Senha", is_senha=True)
    
    criar_botao(card, "REGISTRAR", Cores.PRIMARIA_CLARA, acao_registrar)
    
    tk.Button(card, text="Voltar para o Login", fg=Cores.CINZA_TEXTO, bg=Cores.BG_CARD, cursor="hand2", relief="flat", activebackground=Cores.BG_CARD, font=("Segoe UI", 10), command=acao_voltar).pack(pady=(10, 0))
    
    return ent_user, ent_pass

# ==========================================
# 3. TELA DE CONTATOS (LISTA)
# ==========================================
def montar_layout_contatos(frame_pai, nome_usuario, acao_atualizar, acao_sair):
    frame_pai.configure(bg=Cores.BG_CARD) # Fundo branco para a lista
    
    # Cabeçalho Superior
    header = tk.Frame(frame_pai, bg=Cores.PRIMARIA, height=60)
    header.pack(fill="x")
    header.pack_propagate(False) # Mantém a altura fixa
    
    tk.Label(header, text=f"📱 Olá, {nome_usuario}", fg=Cores.TEXTO_CLARO, bg=Cores.PRIMARIA, font=("Segoe UI", 14, "bold")).pack(side="left", padx=15, pady=15)
    tk.Button(header, text="Sair", command=acao_sair, bg=Cores.PRIMARIA, fg=Cores.TEXTO_CLARO, relief="flat", font=("Segoe UI", 10, "bold", "underline"), cursor="hand2", activebackground=Cores.PRIMARIA).pack(side="right", padx=15)
    
    # Barra de ferramentas com o botão de atualizar
    toolbar = tk.Frame(frame_pai, bg="#F0F2F5", pady=10, padx=15)
    toolbar.pack(fill="x")
    tk.Label(toolbar, text="Conversas", font=("Segoe UI", 12, "bold"), bg="#F0F2F5", fg=Cores.TEXTO_ESCURO).pack(side="left")
    tk.Button(toolbar, text="🔄 Atualizar", bg="#F0F2F5", fg=Cores.PRIMARIA, relief="flat", font=("Segoe UI", 10), cursor="hand2", command=acao_atualizar).pack(side="right")
    
    # Lista de Contatos
    frame_lista = tk.Frame(frame_pai, bg=Cores.BG_CARD)
    frame_lista.pack(fill="both", expand=True)
    
    scrollbar = tk.Scrollbar(frame_lista, bd=0, bg=Cores.BG_CARD)
    scrollbar.pack(side="right", fill="y")
    
    # Listbox super limpa
    lista_box = tk.Listbox(frame_lista, yscrollcommand=scrollbar.set, font=("Segoe UI", 13), bg=Cores.BG_CARD, fg=Cores.TEXTO_ESCURO, bd=0, highlightthickness=0, selectbackground=Cores.PRIMARIA_CLARA, selectforeground=Cores.TEXTO_CLARO, activestyle="none")
    lista_box.pack(side="left", fill="both", expand=True, padx=15, pady=5)
    scrollbar.config(command=lista_box.yview)
    
    return lista_box

# ==========================================
# 4. TELA DE CHAT
# ==========================================
def montar_layout_chat(frame_pai, nome_contato, acao_enviar, acao_voltar, acao_excluir, acao_editar):
    frame_pai.configure(bg=Cores.BG_FUNDO)
    
    # Cabeçalho
    header = tk.Frame(frame_pai, bg=Cores.PRIMARIA, height=60)
    header.pack(fill="x")
    header.pack_propagate(False)
    
    tk.Button(header, text="⬅ Voltar", command=acao_voltar, bg=Cores.PRIMARIA, fg=Cores.TEXTO_CLARO, relief="flat", font=("Segoe UI", 11, "bold"), cursor="hand2", activebackground=Cores.PRIMARIA).pack(side="left", padx=10)
    tk.Label(header, text=nome_contato, fg=Cores.TEXTO_CLARO, bg=Cores.PRIMARIA, font=("Segoe UI", 14, "bold")).pack(side="left", padx=10)

    # Área de Mensagens (Onde fica o histórico)
    frame_chat = tk.Frame(frame_pai, bg=Cores.BG_FUNDO)
    frame_chat.pack(fill="both", expand=True, padx=20, pady=10)
    
    scrollbar = tk.Scrollbar(frame_chat, bd=0)
    scrollbar.pack(side="right", fill="y")
    
    lista_mensagens = tk.Listbox(frame_chat, yscrollcommand=scrollbar.set, font=("Segoe UI", 12), bg=Cores.BG_FUNDO, fg=Cores.TEXTO_ESCURO, bd=0, highlightthickness=0, selectbackground="#D9EBD6", selectforeground=Cores.TEXTO_ESCURO, activestyle="none")
    lista_mensagens.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=lista_mensagens.yview)

    # Menu de Opções (Botão Direito)
    menu_opcoes = tk.Menu(frame_pai, tearoff=0, font=("Segoe UI", 10), bg=Cores.BG_CARD, fg=Cores.TEXTO_ESCURO)
    menu_opcoes.add_command(label="✏️ Editar Mensagem", command=acao_editar)
    menu_opcoes.add_command(label="🗑️ Excluir Mensagem", command=acao_excluir)

    def mostrar_menu(event):
        selecao = lista_mensagens.curselection()
        if selecao:
            menu_opcoes.tk_popup(event.x_root, event.y_root)

    lista_mensagens.bind("<Button-3>", mostrar_menu)

    # Área de Digitar (Rodapé)
    frame_input = tk.Frame(frame_pai, bg="#F0F2F5", pady=10, padx=15)
    frame_input.pack(fill="x", side="bottom")
    
    # Campo de texto arredondado (flat com borda simulada)
    ent_msg = tk.Entry(frame_input, font=("Segoe UI", 12), bg=Cores.BG_CARD, bd=0, highlightthickness=1, highlightbackground="#D1D7DB", relief="flat")
    ent_msg.pack(side="left", fill="x", expand=True, ipady=12, padx=(0, 10))
    
    btn_enviar = tk.Button(frame_input, text="➤", bg=Cores.PRIMARIA_CLARA, fg=Cores.TEXTO_CLARO, font=("Segoe UI", 14), bd=0, relief="flat", cursor="hand2", command=acao_enviar)
    btn_enviar.pack(side="right", ipady=4, ipadx=10)

    ent_msg.bind("<Return>", lambda event: acao_enviar())

    return lista_mensagens, ent_msg