import customtkinter as ctk

class Cores:
    PRIMARIA = "#008069"
    PRIMARIA_HOVER = "#00A884"
    FUNDO_DARK = "#121212"
    CARD_DARK = "#1E1E1E"

def criar_card_central(frame_pai):
    """Cria um cartão centralizado para Login/Cadastro."""
    frame_center = ctk.CTkFrame(frame_pai, fg_color="transparent")
    frame_center.place(relx=0.5, rely=0.5, anchor="center")
    
    card = ctk.CTkFrame(frame_center, corner_radius=15, fg_color=Cores.CARD_DARK, border_width=1, border_color="#333333")
    card.pack(padx=20, pady=20, ipadx=10, ipady=10)
    return card

def criar_input(frame_pai, titulo, is_senha=False):
    """Cria um campo de entrada com rótulo estilizado."""
    label = ctk.CTkLabel(frame_pai, text=titulo, font=("Segoe UI", 12, "bold"), text_color="#AAAAAA")
    label.pack(anchor="w", pady=(10, 2), padx=25)
    
    entry = ctk.CTkEntry(
        frame_pai, 
        show="*" if is_senha else "", 
        font=("Segoe UI", 14), 
        height=45, 
        corner_radius=10,
        fg_color="#2A2A2A",
        border_color="#333333"
    )
    entry.pack(fill="x", pady=(0, 10), padx=25)
    return entry

def criar_botao(frame_pai, texto, cor_bg, comando):
    """Cria um botão de ação principal."""
    btn = ctk.CTkButton(
        frame_pai, 
        text=texto, 
        fg_color=cor_bg, 
        hover_color=Cores.PRIMARIA_HOVER,
        font=("Segoe UI", 14, "bold"), 
        height=45, 
        corner_radius=10,
        command=comando
    )
    btn.pack(fill="x", pady=15, padx=25)
    return btn

def montar_layout_login(frame_pai, comando_login, comando_ir_cadastro):
    """Monta a tela de Login."""
    card = criar_card_central(frame_pai)
    
    ctk.CTkLabel(card, text="Bem-vindo ao Chat", font=("Segoe UI", 24, "bold")).pack(pady=(10, 20))
    
    ent_user = criar_input(card, "Usuário")
    ent_pass = criar_input(card, "Senha", is_senha=True)
    
    criar_botao(card, "ENTRAR", Cores.PRIMARIA, comando_login)
    
    btn_cadastrar = ctk.CTkButton(
        card, 
        text="Ainda não tem conta? Crie uma.", 
        fg_color="transparent", 
        text_color=Cores.PRIMARIA, 
        hover_color="#2B2B2B", 
        command=comando_ir_cadastro
    )
    btn_cadastrar.pack(pady=(5, 10))
    
    return ent_user, ent_pass

def montar_layout_cadastro(frame_pai, acao_registrar, acao_voltar):
    """Monta a tela de Cadastro."""
    card = criar_card_central(frame_pai)
    
    ctk.CTkLabel(card, text="Criar Conta", font=("Segoe UI", 24, "bold")).pack(pady=(10, 20))
    
    ent_user = criar_input(card, "Novo Usuário")
    ent_pass = criar_input(card, "Nova Senha", is_senha=True)
    
    criar_botao(card, "REGISTRAR", Cores.PRIMARIA, acao_registrar)
    
    btn_voltar = ctk.CTkButton(
        card, 
        text="Voltar para o Login", 
        fg_color="transparent", 
        text_color="gray", 
        hover_color="#2B2B2B",
        command=acao_voltar
    )
    btn_voltar.pack(pady=(5, 10))
    
    return ent_user, ent_pass