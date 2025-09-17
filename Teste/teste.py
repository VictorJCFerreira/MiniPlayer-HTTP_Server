import socket

# Configurações do servidor
# Aceita conexões de qualquer endereço IP quando o HOST é ''
# Colocando o IPv4 da rede WiFI da máquina, deixa ela visivel na rede local para 
# qualquer dispositivo conectado na mesma rede
HOST = '0.0.0.0'  
PORT = 9000

# Cria o socket principal do servidor

# AF_INET = IPv4 e SOCK_STREAM = TCP
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Reutilizar endereço, evitar erro "Address already in use"
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Associa o socket a um endereço e porta
server_socket.bind((HOST, PORT))

# O número indica o máximo de conexões pendentes
server_socket.listen(5) 

print(f"Servidor escutando em http://{HOST}:{PORT}")
print("Pressione Ctrl+C para encerrar.")

try:
    while True:
        # Aguarda por uma nova conexão
        client_connection, client_address = server_socket.accept()
        print(f"Nova conexão de {client_address}")

        try:
            # Recebe os dados da requisição (até 1024 bytes)
            request_data = client_connection.recv(1024).decode('utf-8')

            # Caso a requisição seja vazia, ignora
            if not request_data:
                continue

            #print("--- Requisição Recebida ---")
            #print(request_data)
            #print("--------------------------")

            # Extrai o caminho (path) do arquivo solicitado
            first_line = request_data.split('\n')[0]
            method, path, _ = first_line.split(' ')
            
            print(f"Recurso solicitado: {path}")

            # Se o caminho for a raiz, serve o index.html
            if path == '/':

                # Caminho para o arquivo index.html na pasta
                path = '/Teste/index.html'

            # Tenta abrir e ler o arquivo solicitado
            file_path = path.strip('/')
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Monta a resposta de sucesso 200 OK
            response_line = "HTTP/1.1 200 OK\r\n"
            headers = "Content-Type: text/html; charset=utf-8\r\n"
            headers += f"Content-Length: {len(file_content)}\r\n"
            blank_line = "\r\n"

            http_response = response_line.encode('utf-8') + headers.encode('utf-8') + blank_line.encode('utf-8') + file_content

        except FileNotFoundError:
            # Monta uma resposta de erro 404 Not Found
            body = "<html><body><h1>Erro 404: Pagina nao encontrada</h1></body></html>".encode('utf-8')
            response_line = "HTTP/1.1 404 Not Found\r\n"
            headers = "Content-Type: text/html; charset=utf-8\r\n"
            headers += f"Content-Length: {len(body)}\r\n"
            blank_line = "\r\n"
            
            http_response = response_line.encode('utf-8') + headers.encode('utf-8') + blank_line.encode('utf-8') + body

        except Exception as e:
            # Em caso de outros erros, envia uma resposta 500 Internal Server Error
            print(f"Erro ao processar requisição: {e}")
            body = "<html><body><h1>Erro 500: Erro Interno do Servidor</h1></body></html>".encode('utf-8')
            response_line = "HTTP/1.1 500 Internal Server Error\r\n"
            headers = "Content-Type: text/html; charset=utf-8\r\n"
            headers += f"Content-Length: {len(body)}\r\n"
            blank_line = "\r\n"

            http_response = response_line.encode('utf-8') + headers.encode('utf-8') + blank_line.encode('utf-8') + body
            
        finally:
            # Envia a resposta HTTP para o cliente
            client_connection.sendall(http_response)
            # Fecha a conexão com o cliente
            client_connection.close()

except KeyboardInterrupt:
    print("\nServidor encerrado.")
finally:
    # Fecha o socket principal do servidor
    server_socket.close()