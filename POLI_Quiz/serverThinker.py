import socket
import threading
import json
import time
import os

# --- CONFIGURAÇÕES ---
HOST = '0.0.0.0'
PORT = 9000

# --- CARREGAR PERGUNTAS ---
def carregar_perguntas():
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'perguntas.json')
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        print("ERRO: 'perguntas.json' não encontrado.")
        return []

PERGUNTAS = carregar_perguntas()

class GameServer:
    def __init__(self):
        self.clients = {} # {socket: {'nome': 'Bob', 'pontos': 0}}
        self.respostas_rodada = {}
        self.estado = "ESPERANDO"
        self.lock = threading.Lock()

    def broadcast(self, mensagem):
        """Envia mensagem para todos. Se for dict, converte para JSON bytes."""
        with self.lock:
            conexoes = list(self.clients.keys())
        
        if isinstance(mensagem, dict):
            msg_str = json.dumps(mensagem)
        else:
            msg_str = json.dumps({"tipo": "INFO", "conteudo": mensagem})

        for conn in conexoes:
            try:
                conn.sendall(msg_str.encode('utf-8'))
            except:
                pass

    def processar_jogo(self):
        print("[JOGO] Loop iniciado. Aguardando jogadores...")
        while True:
            time.sleep(1)
            
            if self.estado == "ESPERANDO":
                with self.lock:
                    qtd = len([c for c in self.clients.values() if c['nome']])
                
                if qtd >= 2:
                    self.broadcast({"tipo": "LOBBY", "conteudo": "O jogo começa em 5 segundos..."})
                    time.sleep(5)
                    self.estado = "JOGANDO"

            elif self.estado == "JOGANDO":
                for q in PERGUNTAS:
                    self.respostas_rodada = {}
                    
                    # 1. Envia Pergunta
                    msg_pergunta = {
                        "tipo": "PERGUNTA",
                        "pergunta": q['pergunta'],
                        "opcoes": q['opcoes']
                    }
                    self.broadcast(msg_pergunta)
                    
                    # 2. Tempo para responder
                    time.sleep(10)
                    
                    # 3. Corrige
                    texto_res = "Fim da rodada!\n"
                    correta = q['correta']
                    
                    with self.lock:
                        for sock, resp in self.respostas_rodada.items():
                            nome = self.clients[sock]['nome']
                            if resp == correta:
                                self.clients[sock]['pontos'] += 10
                                texto_res += f"✅ {nome} acertou!\n"
                            else:
                                texto_res += f"❌ {nome} errou.\n"
                    
                    self.broadcast({"tipo": "RESULTADO", "conteudo": texto_res})
                    time.sleep(4)
                
                # Fim do Jogo
                with self.lock:
                    ranking = sorted(self.clients.values(), key=lambda x: x['pontos'], reverse=True)
                
                txt_rank = "FIM DE JOGO\n\n" + "\n".join([f"{p['nome']}: {p['pontos']} pts" for p in ranking])
                self.broadcast({"tipo": "FIM", "conteudo": txt_rank})
                
                # Reseta
                self.estado = "ESPERANDO"
                with self.lock:
                    for c in self.clients.values(): c['pontos'] = 0
                time.sleep(5)

game = GameServer()

def handle_client(conn, addr):
    print(f"Nova conexão: {addr}")
    with game.lock:
        game.clients[conn] = {'nome': None, 'pontos': 0}
    
    try:
        while True:
            data = conn.recv(1024)
            if not data: break
            
            msg = json.loads(data.decode('utf-8'))
            
            if msg['acao'] == 'ENTRAR':
                with game.lock:
                    game.clients[conn]['nome'] = msg['nome']
                game.broadcast({"tipo": "LOBBY", "conteudo": f"{msg['nome']} entrou!"})
            
            elif msg['acao'] == 'RESPONDER':
                if game.estado == "JOGANDO":
                    game.respostas_rodada[conn] = msg['valor']
                    
    except Exception as e:
        print(f"Erro cliente {addr}: {e}")
    finally:
        with game.lock:
            if conn in game.clients:
                del game.clients[conn]
        conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Servidor TCP Puro rodando em {HOST}:{PORT}")
    
    threading.Thread(target=game.processar_jogo, daemon=True).start()
    
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()