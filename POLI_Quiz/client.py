import socket
import threading
import sys

# --- NOVO: Thread para Receber Mensagens ---
def receive_messages(s):
    """Esta função roda em uma thread separada.
    Apenas recebe e imprime mensagens do servidor."""
    while True:
        try:
            data = s.recv(1024)
            if not data:
                print("\n[Conexão perdida com o servidor. Aperte ENTER para sair.]")
                break
            
            # Imprime a mensagem do servidor
            # O '\n' e o '\n> ' garantem que a mensagem
            # apareça corretamente, sem bagunçar o 'input()' do usuário
            print(f"\n{data.decode('utf-8')}", end="")
            
        except ConnectionError:
            print("\n[Conexão perdida. Aperte ENTER para sair.]")
            break
        except Exception as e:
            # Captura outros erros (ex: quando o programa fecha)
            # print(f"Erro no receive: {e}")
            break

# --- Thread Principal (Envia Mensagens) ---
def start_client():
    HOST = '127.0.0.1'
    PORT = 50000

    print("Tentando conectar ao servidor do Quiz...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        print("Conectado! Siga as instruções.")
    except ConnectionRefusedError:
        print("Não foi possível conectar. O servidor está offline?")
        return
    
    # 1. Inicia a thread receptora
    # daemon=True faz ela fechar quando a thread principal fechar
    recv_thread = threading.Thread(target=receive_messages, args=(s,), daemon=True)
    recv_thread.start()

    # 2. A thread principal fica em loop lendo o input do usuário
    try:
        while True:
            # O 'input()' bloqueia a thread principal (o que é bom)
            message = input("> ") # Mostra o prompt '>'
            
            # Se a thread receptora morreu (conexão caiu), sai do loop
            if not recv_thread.is_alive():
                break
            
            # Envia a mensagem do usuário (JOIN, ANSWER, etc.)
            try:
                s.sendall(message.encode('utf-8'))
            except ConnectionError:
                break # Sai se não puder enviar

    except KeyboardInterrupt:
        print("\nSaindo do chat...")
    finally:
        s.close()
        print("Conexão fechada.")

if __name__ == "__main__":
    start_client()