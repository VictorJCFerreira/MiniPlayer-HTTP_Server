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
    # Pergunta o IP do servidor ao iniciar
    print("--- CONFIGURAÇÃO DE CONEXÃO ---")
    ip_servidor = input("Digite o IP do servidor (padrão: 127.0.0.1): ").strip()
    if not ip_servidor:
        ip_servidor = '127.0.0.1'
        
    PORT = 9000 # Lembre-se que mudamos a porta para 9000

    print(f"Tentando conectar a {ip_servidor}:{PORT}...")
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Tenta conectar no IP digitado
        s.connect((ip_servidor, PORT))
        print("Conectado! Siga as instruções.")
    except ConnectionRefusedError:
        print("Não foi possível conectar. Verifique:")
        print("1. O servidor está rodando?")
        print("2. O IP está correto?")
        print("3. O Firewall do servidor está bloqueando a porta 9000?")
        return
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        return
    
    # ... (O resto do código continua igual: threads, loops, etc.) ...
    # 1. Inicia a thread receptora
    recv_thread = threading.Thread(target=receive_messages, args=(s,), daemon=True)
    recv_thread.start()

    try:
        while True:
            message = input("> ") 
            if not recv_thread.is_alive(): break
            try:
                s.sendall(message.encode('utf-8'))
            except ConnectionError: break 
    except KeyboardInterrupt:
        print("\nSaindo...")
    finally:
        s.close()

if __name__ == "__main__":
    start_client()