import socket

HOST = '127.0.0.1'
PORT = 50000

print("Tentando conectar ao servidor do Quiz...")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        s.connect((HOST, PORT))
        print(f"Conectado ao servidor em {HOST}:{PORT}")
        
        # Loop principal do cliente
        while True:
            data = s.recv(1024)
            if not data:
                print("Conexão perdida com o servidor.")
                break
                
            msg_servidor = data.decode('utf-8')
            
            if "FIM DE JOGO" in msg_servidor:
                print(msg_servidor)
                break
            
            if "Sua resposta" in msg_servidor:
                resposta = input(msg_servidor)
                s.sendall(resposta.encode('utf-8'))
            else:
                print(msg_servidor)
        
    except ConnectionRefusedError:
        print("Não foi possível conectar ao servidor.")
        print("Verifique se o 'server.py' está em execução.")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

print("Encerrando cliente.")