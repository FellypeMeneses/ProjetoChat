import mysql.connector

# Configuração direta para testar se o XAMPP responde
try:
    conexao = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='chat_db'
    )
    
    if conexao.is_connected():
        cursor = conexao.cursor()
        # Tenta inserir um usuário de teste (usando um nome diferente para evitar erro de UNIQUE)
        nome_teste = "usuario_novo_123"
        cursor.execute("INSERT INTO usuarios (nome_usuario, senha) VALUES (%s, %s)", (nome_teste, 'senha123'))
        
        conexao.commit()
        print("SUCESSO: Conectado ao XAMPP e dado inserido no banco!")
        
    conexao.close()

except Exception as e:
    print(f"ERRO DE CONEXAO OU SQL: {e}")