import socket
import threading
import json
import tkinter as tk
from tkinter import messagebox, simpledialog

# Cores e Estilo
COR_FUNDO = "#222222"
COR_TEXTO = "#ffffff"
COR_BTN = "#e94560"
COR_BTN_TXT = "#ffffff"
FONT_PADRAO = ("Helvetica", 12)

class QuizClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Quiz Multiplayer TCP")
        self.master.geometry("400x500")
        self.master.configure(bg=COR_FUNDO)
        
        self.sock = None
        self.nome = ""
        
        self.setup_tela_login()

    def limpar_tela(self):
        for widget in self.master.winfo_children():
            widget.destroy()

    # --- TELA 1: LOGIN ---
    def setup_tela_login(self):
        self.limpar_tela()
        
        lbl_titulo = tk.Label(self.master, text="🚀 SUPER QUIZ", bg=COR_FUNDO, fg="#bb86fc", font=("Helvetica", 20, "bold"))
        lbl_titulo.pack(pady=40)
        
        tk.Label(self.master, text="IP do Servidor:", bg=COR_FUNDO, fg=COR_TEXTO).pack()
        self.entry_ip = tk.Entry(self.master, font=FONT_PADRAO)
        self.entry_ip.pack(pady=5)
        self.entry_ip.insert(0, "127.0.0.1") # IP Padrão
        
        tk.Label(self.master, text="Seu Nome:", bg=COR_FUNDO, fg=COR_TEXTO).pack()
        self.entry_nome = tk.Entry(self.master, font=FONT_PADRAO)
        self.entry_nome.pack(pady=5)
        
        btn_conectar = tk.Button(self.master, text="CONECTAR", bg=COR_BTN, fg=COR_BTN_TXT, font=FONT_PADRAO, command=self.conectar)
        btn_conectar.pack(pady=20, fill='x', padx=40)

    # --- TELA 2: LOBBY / MENSAGENS ---
    def setup_tela_mensagem(self, titulo, texto):
        self.limpar_tela()
        
        lbl_tit = tk.Label(self.master, text=titulo, bg=COR_FUNDO, fg="#bb86fc", font=("Helvetica", 16, "bold"))
        lbl_tit.pack(pady=20)
        
        lbl_msg = tk.Label(self.master, text=texto, bg=COR_FUNDO, fg=COR_TEXTO, font=("Helvetica", 12), wraplength=350)
        lbl_msg.pack(pady=10)

    # --- TELA 3: PERGUNTA ---
    def setup_tela_jogo(self, dados_pergunta):
        self.limpar_tela()
        
        lbl_p = tk.Label(self.master, text=dados_pergunta['pergunta'], bg=COR_FUNDO, fg=COR_TEXTO, font=("Helvetica", 14, "bold"), wraplength=380)
        lbl_p.pack(pady=20)
        
        # Botões das Opções
        opcoes = dados_pergunta['opcoes']
        for letra, texto in opcoes.items():
            btn = tk.Button(self.master, text=f"{letra}) {texto}", 
                            bg="#333", fg="white", font=FONT_PADRAO, anchor="w", padx=20,
                            command=lambda l=letra: self.enviar_resposta(l))
            btn.pack(fill='x', pady=5, padx=20)

    # --- LÓGICA DE REDE ---
    def conectar(self):
        ip = self.entry_ip.get()
        self.nome = self.entry_nome.get()
        
        if not self.nome:
            messagebox.showwarning("Erro", "Digite um nome!")
            return
            
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((ip, 9000))
            
            # Envia o nome (Protocolo JSON)
            msg_login = json.dumps({"acao": "ENTRAR", "nome": self.nome})
            self.sock.sendall(msg_login.encode('utf-8'))
            
            # Inicia thread para escutar o servidor
            threading.Thread(target=self.escutar_servidor, daemon=True).start()
            
            self.setup_tela_mensagem("Aguardando...", "Conectado! Esperando o jogo começar.")
            
        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar a {ip}\nErro: {e}")

    def escutar_servidor(self):
        while True:
            try:
                data = self.sock.recv(4096) # Buffer maior para JSON
                if not data: break
                
                # O servidor pode mandar varios jsons colados, mas vamos assumir um por vez por simplicidade
                # Num cenário real, precisariamos de um buffer delimiter
                try:
                    msg = json.loads(data.decode('utf-8'))
                    self.processar_mensagem(msg)
                except json.JSONDecodeError:
                    pass # Ignora pacotes quebrados (raro em localhost/LAN pequena)
                    
            except:
                break
        
        # Se sair do loop, caiu a conexão
        self.master.after(0, lambda: messagebox.showerror("Desconectado", "Conexão perdida com o servidor."))
        self.master.after(0, self.master.destroy)

    def processar_mensagem(self, msg):
        tipo = msg.get('tipo')
        conteudo = msg.get('conteudo')
        
        # Tkinter não é thread-safe, use .after ou chamadas diretas com cuidado
        # Como estamos apenas atualizando widgets, costuma funcionar, mas o ideal seria uma Queue.
        
        if tipo == "LOBBY" or tipo == "INFO":
            self.master.after(0, lambda: self.setup_tela_mensagem("Lobby", conteudo))
            
        elif tipo == "PERGUNTA":
            self.master.after(0, lambda: self.setup_tela_jogo(msg))
            
        elif tipo == "RESULTADO":
            self.master.after(0, lambda: self.setup_tela_mensagem("Resultado", conteudo))
            
        elif tipo == "FIM":
            self.master.after(0, lambda: self.setup_tela_mensagem("Fim de Jogo", conteudo))

    def enviar_resposta(self, letra):
        msg = json.dumps({"acao": "RESPONDER", "valor": letra})
        try:
            self.sock.sendall(msg.encode('utf-8'))
            # Feedback visual simples
            self.setup_tela_mensagem("Enviado", f"Você escolheu: {letra}\nAguarde o resultado...")
        except:
            messagebox.showerror("Erro", "Falha ao enviar resposta.")

if __name__ == "__main__":
    root = tk.Tk()
    app = QuizClient(root)
    root.mainloop()