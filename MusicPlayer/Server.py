import socket
import os
import threading
import urllib.parse

# =====================================================================================
# FUNÇÃO handle_client
# =====================================================================================
# Esta função contém TODA a lógica para atender UM único cliente.
# Cada cliente conectado terá uma destas funções rodando para ele em uma thread separada.
def handle_client(client_connection, client_address):
    print(f"Thread para {client_address} iniciada.")
    try:
        # 1. RECEBER E PARSEAR A REQUISIÇÃO
        # ------------------------------------
        # Recebe os dados da requisição HTTP (até 1024 bytes) e decodifica de bytes para string.
        request_data = client_connection.recv(1024).decode('utf-8')
        if not request_data:
            return

        # "Parseia" a primeira linha da requisição para extrair o método (GET, HEAD) e o caminho/path (/, /music/Starboy.mp3).
        first_line = request_data.split('\n')[0]
        method, path, _ = first_line.split(' ')
        print(f"Recurso solicitado: {path} com o método: {method} por {client_address}")

        # 2. ROTEAMENTO E MAPEAMENTO DE ARQUIVOS
        # ------------------------------------
        # Se o cliente pedir a raiz '/', nós o direcionamos para a página principal.
        if path == '/':
            path = '/MiniPlayer.html'

        # Decodifica URL (por exemplo, espaços codificados como %20)
        path = urllib.parse.unquote(path)

        # Monta o caminho completo do arquivo em relação ao diretório deste script,
        # apontando para a pasta 'assets'. Isso evita problemas quando o servidor é
        # executado a partir de um diretório diferente.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(base_dir, 'assets')
        # Remove a barra inicial para usar os.path.join corretamente
        rel_path = path.lstrip('/')
        file_path = os.path.join(assets_dir, rel_path)

        # Normaliza o caminho e previne directory traversal garantindo que o
        # caminho final esteja dentro de assets_dir.
        normalized_assets = os.path.normpath(assets_dir)
        normalized_target = os.path.normpath(file_path)
        # Usamos commonpath para checar que o arquivo está sob assets_dir
        if os.path.commonpath([normalized_assets, normalized_target]) != normalized_assets:
            raise FileNotFoundError()

        # 3. VERIFICAÇÃO DE MÉTODOS HTTP SUPORTADOS
        # ------------------------------------
        # Nosso servidor só entende GET (me dê o arquivo completo) e HEAD (me dê só os metadados do arquivo).
        if method not in ['GET', 'HEAD']:
            # Se for um método não suportado (como POST), retorna um erro 405 Method Not Allowed.
            response_body = "<html><body><h1>Erro 405: Metodo nao permitido</h1></body></html>".encode('utf-8')
            response_line = "HTTP/1.1 405 Method Not Allowed\r\n"
            headers = "Content-Type: text/html; charset=utf-8\r\n"
            headers += f"Content-Length: {len(response_body)}\r\n"
            blank_line = "\r\n"
            http_response = response_line.encode('utf-8') + headers.encode('utf-8') + blank_line.encode('utf-8') + response_body
            client_connection.sendall(http_response)
        
        else:
            # 4. LÓGICA DE RESPOSTA PARA GET E HEAD
            # ------------------------------------
            # Abre o arquivo em modo de leitura binária ('rb').
            with open(file_path, 'rb') as f:
                # Pega o tamanho total do arquivo para o cabeçalho Content-Length.
                file_size = os.path.getsize(file_path)
                
                # DETERMINAÇÃO DO MIME TYPE (Content-Type): "Etiquetando o arquivo"
                # Isso é crucial para o navegador saber como interpretar o conteúdo.
                if file_path.endswith('.html'): content_type = 'text/html; charset=utf-8'
                elif file_path.endswith('.css'): content_type = 'text/css'
                elif file_path.endswith('.mp3'): content_type = 'audio/mpeg'
                else: content_type = 'application/octet-stream' # Tipo genérico para outros arquivos.

                # Monta a resposta dos cabeçalhos HTTP.
                response_line = "HTTP/1.1 200 OK\r\n"
                headers = f"Content-Type: {content_type}\r\n"
                headers += f"Content-Length: {file_size}\r\n"
                blank_line = "\r\n"
                
                # Envia apenas os cabeçalhos primeiro.
                response_headers = response_line.encode('utf-8') + headers.encode('utf-8') + blank_line.encode('utf-8')
                client_connection.sendall(response_headers)

                # Se o método for GET, nós enviamos o corpo do arquivo.
                # Se for HEAD, o trabalho termina aqui, economizando banda.
                if method == 'GET':
                    # 5. STREAMING DE DADOS (OTIMIZAÇÃO DE MEMÓRIA)
                    # ------------------------------------
                    # Em vez de f.read() que lê tudo de uma vez, lemos em pedaços (chunks).
                    # Isso mantém o consumo de memória baixo e constante.
                    try:
                        while True:
                            chunk = f.read(4096) # Lê 4KB por vez.
                            if not chunk: break # Se não houver mais dados, sai do loop.
                            client_connection.sendall(chunk) # Envia o pedaço para o cliente.
                    except (ConnectionResetError, ConnectionAbortedError):
                        # RESILIÊNCIA: Se o cliente fechar a conexão, o servidor não quebra.
                        # Apenas essa thread para de enviar dados e encerra.
                        print(f"Cliente {client_address} fechou a conexão durante o streaming.")

    except FileNotFoundError:
        # Se o arquivo não existir, envia uma resposta 404 Not Found.
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
        # Garante que a conexão com este cliente seja sempre fechada no final.
        print(f"Conexão com {client_address} fechada.")
        client_connection.close()

# =====================================================================================
# EXECUÇÃO PRINCIPAL
# =====================================================================================

# Configuração do Socket principal do servidor.
HOST = '0.0.0.0'  
PORT = 9000
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # AF_INET = IPv4 e SOCK_STREAM = TCP
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Reutilizar endereço, evitar erro "Address already in use"
server_socket.bind((HOST, PORT)) # Associa o socket a um endereço e porta
server_socket.listen(5) # Permite até 5 conexões pendentes.
print(f"Servidor CONCORRENTE escutando em http://localhost:{PORT}")
print("Pressione Ctrl+C para encerrar.")

try:
    # O Loop Principal agora só aceita conexões e delega para as threads
    while True:
        # A execução bloqueia aqui em .accept() até um novo cliente se conectar.
        client_connection, client_address = server_socket.accept()
        
        # PONTO CHAVE DA CONCORRÊNCIA:
        # Assim que um cliente se conecta, criamos uma Thread para ele.
        # A função 'handle_client' será o "alvo" (target) dessa thread.
        client_thread = threading.Thread(
            target=handle_client,
            args=(client_connection, client_address) # Passamos a conexão e o endereço para a função.
        )
        # .start() inicia a thread, que começa a rodar a função handle_client em paralelo.
        client_thread.start()
        # O loop volta IMEDIATAMENTE para o .accept(), pronto para o próximo cliente,
        # enquanto a thread cuida do cliente anterior.
        
except KeyboardInterrupt:
    print("\nServidor encerrado.")
finally:
    # Fecha o socket principal quando o servidor é encerrado.
    server_socket.close()
