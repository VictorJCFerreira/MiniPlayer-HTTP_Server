import socket
import os
import threading

# Esta função contém TODA a lógica para atender UM cliente
def handle_client(client_connection, client_address):
    print(f"Thread para {client_address} iniciada.")
    try:
        # Recebe os dados da requisição
        request_data = client_connection.recv(1024).decode('utf-8')
        if not request_data:
            return

        # Extrai o método e o caminho
        first_line = request_data.split('\n')[0]
        method, path, _ = first_line.split(' ')
        print(f"Recurso solicitado: {path} com o método: {method} por {client_address}")

        # Se o caminho for a raiz, serve o MiniPlayer.html
        if path == '/':
            path = '/MiniPlayer.html'

        # Monta o caminho completo para o arquivo na pasta 'assets'
        file_path = "MusicPlayer/assets" + path

        # Verifica se o método é suportado
        if method not in ['GET', 'HEAD']:
            response_body = "<html><body><h1>Erro 405: Metodo nao permitido</h1></body></html>".encode('utf-8')
            response_line = "HTTP/1.1 405 Method Not Allowed\r\n"
            headers = "Content-Type: text/html; charset=utf-8\r\n"
            headers += f"Content-Length: {len(response_body)}\r\n"
            blank_line = "\r\n"
            http_response = response_line.encode('utf-8') + headers.encode('utf-8') + blank_line.encode('utf-8') + response_body
            client_connection.sendall(http_response)
        
        else:
            # Lógica para GET e HEAD com STREAMING
            with open(file_path, 'rb') as f:
                file_size = os.path.getsize(file_path)
                
                if file_path.endswith('.html'): content_type = 'text/html; charset=utf-8'
                elif file_path.endswith('.css'): content_type = 'text/css'
                elif file_path.endswith('.mp3'): content_type = 'audio/mpeg'
                else: content_type = 'application/octet-stream'

                response_line = "HTTP/1.1 200 OK\r\n"
                headers = f"Content-Type: {content_type}\r\n"
                headers += f"Content-Length: {file_size}\r\n"
                blank_line = "\r\n"
                response_headers = response_line.encode('utf-8') + headers.encode('utf-8') + blank_line.encode('utf-8')
                client_connection.sendall(response_headers)

                if method == 'GET':
                    try:
                        while True:
                            chunk = f.read(4096)
                            if not chunk: break
                            client_connection.sendall(chunk)
                    except (ConnectionResetError, ConnectionAbortedError):
                        print(f"Cliente {client_address} fechou a conexão durante o streaming.")

    except FileNotFoundError:
        body = "<html><body><h1>Erro 404: Arquivo nao encontrado</h1></body></html>".encode('utf-8')
        response_line = "HTTP/1.1 404 Not Found\r\n"
        headers = "Content-Type: text/html; charset=utf-8\r\n"
        headers += f"Content-Length: {len(body)}\r\n"
        blank_line = "\r\n"
        http_response = response_line.encode('utf-8') + headers.encode('utf-8') + blank_line.encode('utf-8') + body
        client_connection.sendall(http_response)
    except Exception as e:
        print(f"Erro ao processar requisição de {client_address}: {e}")
    finally:
        print(f"Conexão com {client_address} fechada.")
        client_connection.close()

# --- INÍCIO DA EXECUÇÃO PRINCIPAL ---

# Configuração do Servidor
HOST = '0.0.0.0'
PORT = 9000
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(5)
print(f"Servidor CONCORRENTE escutando em http://localhost:{PORT}")
print("Pressione Ctrl+C para encerrar.")

try:
    # O Loop Principal agora só aceita conexões e delega para as threads
    while True:
        client_connection, client_address = server_socket.accept()
        client_thread = threading.Thread(
            target=handle_client,
            args=(client_connection, client_address)
        )
        client_thread.start()
except KeyboardInterrupt:
    print("\nServidor encerrado.")
finally:
    server_socket.close()