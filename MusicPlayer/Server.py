import socket

# Passo 1: Configuração Inicial
HOST = '0.0.0.0'  # Escuta em todas as interfaces de rede
PORT = 9000

# Passo 2: Criação e Preparação do Socket Principal
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(5)

print(f"Servidor escutando em http://localhost:{PORT}")
print("Acesse pelo seu navegador. Pressione Ctrl+C para encerrar.")

try:
    # Passo 3: O Loop Principal do Servidor
    while True:
        # Aguarda por uma nova conexão
        client_connection, client_address = server_socket.accept()
        print(f"Nova conexão de {client_address}")

        # Passo 4: Processamento da Requisição do Cliente
        try:
            # Recebe os dados da requisição
            request_data = client_connection.recv(1024).decode('utf-8')
            if not request_data:
                continue

            # Extrai o caminho (path) do arquivo solicitado
            first_line = request_data.split('\n')[0]
            method, path, _ = first_line.split(' ')
            
            print(f"Recurso solicitado: {path}")

            # Se o caminho for a raiz, serve o MiniPlayer.html
            if path == '/':
                path = '/MiniPlayer.html'

            # Monta o caminho completo para o arquivo na pasta 'assets'
            file_path = "MusicPlayer/assets" + path

            # Determina o Content-Type (MIME Type) com base na extensão
            if file_path.endswith('.html'):
                content_type = 'text/html; charset=utf-8'
            elif file_path.endswith('.css'): 
                content_type = 'text/css'
            elif file_path.endswith('.mp3'):
                content_type = 'audio/mpeg'
            else:
                content_type = 'application/octet-stream' # Tipo genérico

            # Tenta abrir e ler o arquivo solicitado em modo binário ('rb')
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Monta a resposta de sucesso 200 OK
            response_line = "HTTP/1.1 200 OK\r\n"
            headers = f"Content-Type: {content_type}\r\n"
            headers += f"Content-Length: {len(file_content)}\r\n"
            blank_line = "\r\n"

            http_response = response_line.encode('utf-8') + headers.encode('utf-8') + blank_line.encode('utf-8') + file_content

        except FileNotFoundError:
            # Passo 5: Tratamento de Erro 404
            body = "<html><body><h1>Erro 404: Arquivo nao encontrado</h1></body></html>".encode('utf-8')
            response_line = "HTTP/1.1 404 Not Found\r\n"
            headers = "Content-Type: text/html; charset=utf-8\r\n"
            headers += f"Content-Length: {len(body)}\r\n"
            blank_line = "\r\n"
            
            http_response = response_line.encode('utf-8') + headers.encode('utf-8') + blank_line.encode('utf-8') + body

        except Exception as e:
            # Tratamento para outros erros
            print(f"Erro ao processar requisição: {e}")
            body = "<html><body><h1>Erro 500: Erro Interno do Servidor</h1></body></html>".encode('utf-8')
            response_line = "HTTP/1.1 500 Internal Server Error\r\n"
            headers = "Content-Type: text/html; charset=utf-8\r\n"
            headers += f"Content-Length: {len(body)}\r\n"
            blank_line = "\r\n"

            http_response = response_line.encode('utf-8') + headers.encode('utf-8') + blank_line.encode('utf-8') + body
            
        finally:
            # Envia a resposta HTTP e fecha a conexão com este cliente
            client_connection.sendall(http_response)
            client_connection.close()

except KeyboardInterrupt:
    print("\nServidor encerrado.")
finally:
    # Fecha o socket principal do servidor
    server_socket.close()