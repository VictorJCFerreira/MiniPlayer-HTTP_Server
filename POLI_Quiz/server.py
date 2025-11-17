import socket
import json
import threading
import time

# --- (A função carregar_perguntas() é a mesma do Passo 4) ---
def carregar_perguntas():
    try:
        with open('POLI_Quiz\perguntas.json', 'r', encoding='utf-8') as f:
            perguntas = json.load(f)
        if not perguntas: raise Exception("Arquivo 'perguntas.json' está vazio.")
        return perguntas
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Erro crítico ao carregar perguntas: {e}")
        return None

# --- NOVO: A Classe que gerencia o estado do Jogo ---
class Game:
    """Gerencia o estado centralizado do quiz multiplayer."""
    
    def __init__(self, questions):
        self.questions = questions
        self.players = {}  # {'nome': {'score': 0, 'conn': socket_cliente}}
        self.game_state = "WAITING" # WAITING | PLAYING | FINISHED
        self.current_question_index = 0
        self.round_answers = {}  # {'nome_player': 'resposta'}
        # O 'Lock' é essencial para evitar que duas threads mexam no placar ao mesmo tempo
        self.lock = threading.Lock()
        self.min_players = 2 # Mínimo para começar

    def add_player(self, name, conn):
        """Adiciona um novo jogador ao jogo."""
        
        # Bloco para verificar e adicionar o jogador
        with self.lock:
            if self.game_state != "WAITING":
                conn.sendall("O jogo já está em andamento. Tente mais tarde.\n".encode('utf-8'))
                return False
            if name in self.players:
                conn.sendall("Este nome já está em uso. Tente outro.\n".encode('utf-8'))
                return False
            
            self.players[name] = {'score': 0, 'conn': conn}
            player_count = len(self.players) # Pega o número de jogadores
            print(f"[JOGO] {name} entrou. Total de jogadores: {player_count}")
            
            # Envia a mensagem de boas-vindas APENAS para o jogador que entrou
            conn.sendall(f"Bem-vindo, {name}! Aguardando mais jogadores...\n> ".encode('utf-8'))
        
        # --- CORREÇÃO: Movido para FORA do 'with self.lock:' ---
        # Agora que soltamos a chave, podemos avisar a todos.
        self.broadcast(f"\n[JOGO] {name} entrou! Temos {player_count} jogador(es).\n> ", 
                       exclude_name=name) 
        
        return True

    def remove_player(self, name):
        """Remove um jogador que desconectou."""
        player_exists = False
        with self.lock:
            if name in self.players:
                del self.players[name]
                player_exists = True
                print(f"[JOGO] {name} saiu.")
        
        # --- CORREÇÃO: Movido para FORA do 'with self.lock:' ---
        if player_exists:
            self.broadcast(f"\n[JOGO] {name} saiu do jogo.\n> ")

    def submit_answer(self, name, answer):
        """Registra a resposta de um jogador para a rodada atual."""
        with self.lock:
            # Só aceita resposta se o jogo estiver rolando e se ele ainda não respondeu
            if self.game_state == "PLAYING" and name not in self.round_answers:
                self.round_answers[name] = answer.upper()
                print(f"[JOGO] Resposta de {name} recebida: {answer}")
                self.players[name]['conn'].sendall("Resposta recebida! Aguarde o fim da rodada.\n> ".encode('utf-8'))

    def broadcast(self, message, exclude_name=None):
        """Envia uma mensagem para todos os jogadores conectados."""
        # Não precisamos do lock para *enviar* dados, mas precisamos dele
        # para ler a lista de jogadores de forma segura.
        with self.lock:
            players_list = list(self.players.items())
            
        for name, player_data in players_list:
            if name == exclude_name:
                continue
            try:
                player_data['conn'].sendall(message.encode('utf-8'))
            except (ConnectionError, BrokenPipeError):
                # Se falhar, o handle_client vai cuidar da remoção
                pass

    def run_game_loop(self):
        """A THREAD 'MESTRE DO JOGO'. Controla o fluxo."""
        while True:
            time.sleep(1) # Roda o loop 1 vez por segundo
            
            # --- FASE 1: ESPERANDO JOGADORES ---
            if self.game_state == "WAITING":
                iniciar_agora = False
                
                # Bloco Crítico: Apenas verifica e muda o estado
                with self.lock:
                    if len(self.players) >= self.min_players:
                        self.game_state = "PLAYING"
                        self.current_question_index = 0
                        iniciar_agora = True
                
                # FORA DO BLOCO CRÍTICO (Sem a chave):
                if iniciar_agora:
                    print("[MESTRE] Mínimo de jogadores atingido. Iniciando o jogo...")
                    self.broadcast("\n--- O JOGO VAI COMEÇAR! ---\n> ")
                    time.sleep(2) # Pequena pausa
                
                continue # Volta ao início do 'while True'

            # --- FASE 2: JOGO EM ANDAMENTO ---
            if self.game_state == "PLAYING":
                # Verifica se o jogo acabou
                if self.current_question_index >= len(self.questions):
                    print("[MESTRE] Fim de jogo. Reiniciando...")
                    self.broadcast("\n--- FIM DE JOGO ---\nAguarde o reinício...\n> ")
                    
                    # Reinicia o estado do jogo com segurança
                    with self.lock:
                        self.game_state = "WAITING"
                        self.current_question_index = 0
                        for p in self.players.values(): p['score'] = 0
                        # Limpa respostas antigas para evitar bugs no reinício
                        self.round_answers = {} 
                    
                    time.sleep(3)
                    self.broadcast("O jogo reiniciou! Aguardando novos jogadores...\n> ")
                    continue
                
                # --- JOGO NÃO ACABOU: PRÓXIMA RODADA ---
                print(f"[MESTRE] Iniciando Rodada {self.current_question_index + 1}")
                
                # 1. Prepara a pergunta (Precisamos do lock para ler a pergunta com segurança? 
                # Na verdade não, pois 'questions' é somente leitura, mas vamos manter simples)
                p = self.questions[self.current_question_index]
                
                # Limpa respostas da rodada anterior
                with self.lock:
                     self.round_answers = {}

                # 2. Formata e envia a pergunta
                opcoes_formatadas = []
                for chave, valor in p['opcoes'].items():
                    opcoes_formatadas.append(f"{chave}) {valor}")
                opcoes_str = "\n".join(opcoes_formatadas)
                msg_pergunta = f"\n--- PERGUNTA {p['id']} ---\n{p['pergunta']}\n{opcoes_str}\nResponda com (ex: RESP A): \n> "
                
                # O broadcast já cuida do lock internamente, então chamamos ele solto aqui
                self.broadcast(msg_pergunta)
                
                # 3. Espera 20 segundos pelas respostas
                print("[MESTRE] Pergunta enviada. Aguardando 20s...")
                time.sleep(20)
                
                # 4. Processa as respostas
                print("[MESTRE] Tempo esgotado. Processando respostas...")
                correct_answer = p['correta']
                feedback = f"\n--- FIM DA RODADA {p['id']} ---\nA resposta correta era: {correct_answer}\n"
                
                # Bloco Crítico: Calcular pontuação e ler respostas
                with self.lock:
                    for name, answer in self.round_answers.items():
                        # Verifica se jogador ainda está conectado
                        if name in self.players: 
                            if answer == correct_answer:
                                self.players[name]['score'] += 10
                                feedback += f"  - {name} acertou! (+10 pontos)\n"
                            else:
                                feedback += f"  - {name} errou. (Respondeu: {answer})\n"
                    
                    feedback += "\n--- PLACAR ATUAL ---\n"
                    placar_ordenado = sorted(self.players.items(), 
                                           key=lambda item: item[1]['score'], 
                                           reverse=True)
                    
                    for name, data in placar_ordenado:
                        feedback += f"  {name}: {data['score']} pontos\n"
                    
                    feedback += "> "
                    self.current_question_index += 1

                # 5. Envia feedback (Fora do lock)
                self.broadcast(feedback)
                
                print("[MESTRE] Fim da rodada. Pausando 10s...")
                time.sleep(10)

# --- THREAD DE CLIENTE ---
def handle_client(conn, addr, game):
    """Uma thread para cada cliente. Apenas 'ouve' e repassa."""
    print(f"[{addr}] Nova conexão. Aguardando nome...")
    player_name = None
    try:
        # 1. Loop para pegar o nome
        while True:
            conn.sendall("Digite seu nome (ex: JOIN <seu_nome>):\n> ".encode('utf-8'))
            data = conn.recv(1024)
            if not data: return # Cliente desistiu
            
            cmd = data.decode('utf-8').strip()
            if cmd.startswith("JOIN "):
                name = cmd.split(" ", 1)[1]
                if name: # Se o nome não for vazio
                    if game.add_player(name, conn):
                        player_name = name # Conseguiu entrar
                        break
                    # Se add_player() retornou False, o loop continua e pede o nome de novo
            else:
                conn.sendall("Comando inválido. Use 'JOIN <seu_nome>'.\n> ".encode('utf-8'))
        
        # 2. Loop principal: apenas ouve por respostas
        print(f"[{addr}] Jogador {player_name} autenticado. Ouvindo por respostas...")
        while True:
            data = conn.recv(1024)
            if not data: break # Cliente desconectou
            
            cmd = data.decode('utf-8').strip()
            if cmd.startswith("RESP "):
                answer = cmd.split(" ", 1)[1]
                game.submit_answer(player_name, answer)
            else:
                conn.sendall("Comando inválido. Para responder, use 'RESP <letra>'.\n> ".encode('utf-8'))

    except (ConnectionResetError, BrokenPipeError):
        print(f"[{addr}] Conexão perdida com {player_name}.")
    finally:
        if player_name:
            game.remove_player(player_name)
        conn.close()


# --- THREAD PRINCIPAL ---
def start_server():
    # Configurações de Rede
    HOST = '0.0.0.0'  # Escuta em todas as interfaces de rede
    PORT = 9000       # Porta alterada conforme solicitado
    
    perguntas = carregar_perguntas()
    if not perguntas: return
    
    # 1. Cria a instância ÚNICA do jogo
    game = Game(perguntas)

    # 2. Inicia a thread 'MESTRE DO JOGO'
    game_thread = threading.Thread(target=game.run_game_loop, daemon=True)
    game_thread.start()
    print("[SERVIDOR] Thread Mestre do Jogo iniciada.")

    # 3. Configuração do Socket Principal (Atualizada)
    # Usamos AF_INET (IPv4) e SOCK_STREAM (TCP)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Permite reusar o endereço imediatamente se o servidor cair
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5) # Aceita até 5 conexões na fila de espera
        print(f"[SERVIDOR] CONCORRENTE escutando em todas as interfaces na porta {PORT}")
        print(f"[DICA] Para conectar de outro PC, descubra o IP desta maquina (ipconfig/ifconfig).")
        print("Pressione Ctrl+C para encerrar.")
        
        while True:
            # Aceita conexão
            conn, addr = server_socket.accept()
            
            # Cria thread para o cliente
            client_thread = threading.Thread(target=handle_client, 
                                             args=(conn, addr, game))
            client_thread.start()
            
    except Exception as e:
        print(f"\n[ERRO FATAL] Não foi possível iniciar o servidor: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()