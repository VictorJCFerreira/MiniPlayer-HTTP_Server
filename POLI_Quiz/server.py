import socket
import json
import threading  # NOVO: Importa a biblioteca de threads

# --- Função para carregar as perguntas (sem mudanças) ---
def carregar_perguntas():
    try:
        with open('POLI_Quiz\perguntas.json', 'r', encoding='utf-8') as f:
            perguntas = json.load(f)
        if not perguntas:
            print("Erro: Arquivo 'perguntas.json' está vazio.")
            return None
        return perguntas
    except FileNotFoundError:
        print("Erro: Arquivo 'perguntas.json' não encontrado.")
        return None
    except json.JSONDecodeError:
        print("Erro: Arquivo 'perguntas.json' não é um JSON válido.")
        return None

# --- NOVO: Função para lidar com cada cliente em uma thread ---
def handle_client(conn, addr, perguntas_do_quiz):
    """Esta função executa em uma thread separada para cada cliente."""
    
    # Usa o 'addr' para sabermos quem é este cliente nos logs
    print(f"[{addr}] Cliente conectado. Iniciando quiz...")

    with conn:
        # --- LÓGICA DO QUIZ (Movida para dentro desta função) ---
        pontuacao = 0
        total_perguntas = len(perguntas_do_quiz)

        # 1. Loop através de cada pergunta
        for p in perguntas_do_quiz:
            opcoes_formatadas = []
            for chave, valor in p['opcoes'].items():
                opcoes_formatadas.append(f"{chave}) {valor}")
            
            opcoes_str = "\n".join(opcoes_formatadas)
            mensagem_pergunta = f"\n{p['pergunta']}\n{opcoes_str}\nSua resposta (A, B ou C): "

            try:
                # 3. Envia a pergunta
                conn.sendall(mensagem_pergunta.encode('utf-8'))
                
                # 4. Espera pela resposta do cliente
                data = conn.recv(1024)
                if not data:
                    print(f"[{addr}] Cliente desconectou no meio do quiz.")
                    break # Sai do loop deste cliente
                
                resposta_cliente = data.decode('utf-8').strip().upper()
                
                # 5. Verifica a resposta e envia o feedback
                if resposta_cliente == p['correta']:
                    pontuacao += 1
                    feedback = "Correto!\n"
                else:
                    feedback = f"Errado! A resposta correta era {p['correta']}.\n"
                
                conn.sendall(feedback.encode('utf-8'))
                
            except (ConnectionResetError, BrokenPipeError):
                # Ocorre se o cliente fechar a janela abruptamente
                print(f"[{addr}] Conexão perdida abruptamente.")
                break # Sai do loop deste cliente

        # 6. Fim do quiz: envia a pontuação final (se o cliente não desconectou)
        if data: # Só envia se o loop terminou normalmente
            msg_final = f"\n--- FIM DE JOGO ---\nSua pontuacao final: {pontuacao} de {total_perguntas}"
            try:
                conn.sendall(msg_final.encode('utf-8'))
            except (ConnectionResetError, BrokenPipeError):
                pass # Cliente já pode ter desconectado após a última resposta

        print(f"[{addr}] Quiz finalizado. Pontuacao: {pontuacao}/{total_perguntas}. Fechando conexão.")
        # --- FIM DA LÓGICA DO QUIZ ---

# --- FUNÇÃO PRINCIPAL DO SERVIDOR (MODIFICADA) ---
def start_server():
    HOST = '127.0.0.1'
    PORT = 50000
    
    perguntas_do_quiz = carregar_perguntas()
    if not perguntas_do_quiz:
        print("Servidor não pode iniciar sem as perguntas.")
        return # Finaliza a função

    print(f"Servidor iniciado, {len(perguntas_do_quiz)} perguntas carregadas.")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Servidor escutando em {HOST}:{PORT}. Aguardando conexões...")
        
        # --- NOVO: Loop infinito para aceitar múltiplos clientes ---
        while True:
            # 1. Aceita uma nova conexão (bloqueia aqui até um cliente chegar)
            conn, addr = s.accept()
            
            # 2. Quando um cliente conecta, cria uma thread para ele
            print(f"[NOVA CONEXÃO] Cliente {addr} conectado.")
            
            # 3. Cria a thread
            # target = A função que a thread deve executar
            # args = Os argumentos para passar para a função (precisa ser uma tupla)
            thread = threading.Thread(target=handle_client, 
                                      args=(conn, addr, perguntas_do_quiz))
            
            # 4. Inicia a thread
            thread.start()
            
            # 5. O loop volta imediatamente para o 's.accept()' para esperar o próximo cliente

# Garante que o servidor vai iniciar quando executarmos o script
if __name__ == "__main__":
    start_server()