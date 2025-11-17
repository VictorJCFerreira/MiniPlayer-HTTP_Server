import asyncio
import websockets
import json
import random

# --- CLASSE DO JOGO (Lógica Mantida) ---
class Game:
    def __init__(self, questions):
        self.questions = questions
        self.connected_clients = set() # Armazena os websockets conectados
        self.players = {} # {'websocket': {'name': 'Victor', 'score': 0}}
        self.game_state = "WAITING"
        self.current_question_index = 0
        self.round_answers = {} 
        self.min_players = 2

    async def register(self, websocket):
        self.connected_clients.add(websocket)

    async def unregister(self, websocket):
        self.connected_clients.remove(websocket)
        if websocket in self.players:
            name = self.players[websocket]['name']
            del self.players[websocket]
            await self.broadcast(f"[SYSTEM] {name} saiu do jogo.")

    async def broadcast(self, message):
        if self.connected_clients:
            # Envia a mensagem para todos os sockets conectados
            # websockets requer que a mensagem seja enviada para todos simultaneamente
            await asyncio.gather(*[client.send(message) for client in self.connected_clients])

    async def run_game_loop(self):
        """O Loop Principal do Jogo (Gerenciado pelo Servidor)"""
        print("[MESTRE] Loop do jogo iniciado.")
        while True:
            await asyncio.sleep(1)

            if self.game_state == "WAITING":
                if len(self.players) >= self.min_players:
                    await self.broadcast("START_GAME") # Comando para o Front mudar de tela
                    await asyncio.sleep(1)
                    await self.broadcast("O JOGO VAI COMEÇAR EM 3 SEGUNDOS...")
                    await asyncio.sleep(3)
                    self.game_state = "PLAYING"
                    self.current_question_index = 0
            
            if self.game_state == "PLAYING":
                if self.current_question_index >= len(self.questions):
                    # Fim de jogo
                    winner_msg = "--- FIM DE JOGO ---\n"
                    sorted_players = sorted(self.players.values(), key=lambda x: x['score'], reverse=True)
                    for p in sorted_players:
                        winner_msg += f"{p['name']}: {p['score']} pts<br>"
                    
                    await self.broadcast(f"GAME_OVER|{winner_msg}")
                    self.game_state = "WAITING"
                    self.players = {} # Reinicia jogadores (opcional)
                    self.current_question_index = 0
                    await asyncio.sleep(5)
                    continue

                # Nova Rodada
                p = self.questions[self.current_question_index]
                self.round_answers = {}
                
                # Envia JSON da pergunta para o front montar bonito
                question_data = {
                    "type": "QUESTION",
                    "id": p['id'],
                    "text": p['pergunta'],
                    "options": p['opcoes']
                }
                await self.broadcast(json.dumps(question_data))
                
                # Tempo para responder
                await asyncio.sleep(10)
                
                # Processa pontuação
                correct = p['correta']
                results = "--- RESULTADO ---\n"
                
                for ws, ans in self.round_answers.items():
                    player = self.players.get(ws)
                    if player:
                        if ans == correct:
                            player['score'] += 10
                            results += f"✅ {player['name']} acertou!<br>"
                        else:
                            results += f"❌ {player['name']} errou.<br>"
                
                await self.broadcast(f"FEEDBACK|{results}")
                await asyncio.sleep(4)
                self.current_question_index += 1

# --- CARREGAR PERGUNTAS (Mesma função) ---
def carregar_perguntas():
    try:
        with open('perguntas.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

# --- SERVIDOR WEBSOCKET ---
async def handler(websocket):
    # Esta função roda para cada cliente conectado
    await game.register(websocket)
    try:
        async for message in websocket:
            # Processa mensagens vindas do Javascript
            data = json.loads(message)
            action = data.get('action')
            
            if action == 'JOIN':
                name = data['name']
                game.players[websocket] = {'name': name, 'score': 0}
                await websocket.send("JOIN_OK")
                await game.broadcast(f"[LOBBY] {name} entrou na sala!")
            
            elif action == 'ANSWER':
                if game.game_state == "PLAYING":
                    # Só aceita a primeira resposta
                    if websocket not in game.round_answers:
                        game.round_answers[websocket] = data['value']

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        await game.unregister(websocket)

# --- INICIALIZAÇÃO ---
async def main():
    global game
    perguntas = carregar_perguntas()
    if not perguntas: return
    
    game = Game(perguntas)
    
    # Inicia o loop do jogo em background
    asyncio.create_task(game.run_game_loop())
    
    # Inicia o servidor WebSocket
    # host="0.0.0.0" permite conexões externas
    async with websockets.serve(handler, "0.0.0.0", 9000):
        print("Servidor WEB rodando em ws://0.0.0.0:9000")
        await asyncio.Future()  # Mantém rodando para sempre

if __name__ == "__main__":
    asyncio.run(main())