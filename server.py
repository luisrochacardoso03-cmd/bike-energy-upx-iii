# Bike Energy - trabalho de faculdade
# Este arquivo recebe os dados das telas e salva no SQLite.
# Nao precisa instalar bibliotecas: usamos as que ja vem com Python.

import sqlite3
import json
import hashlib
import hmac
import secrets
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse
from http.cookies import SimpleCookie

PASTA = Path(__file__).parent
BANCO = PASTA / "bike_energy.db"
LOGINS = {}  # Guarda quem fez login enquanto o programa estiver aberto.


def agora():
    return datetime.now().isoformat(timespec="seconds")


def conectar():
    banco = sqlite3.connect(BANCO)
    banco.row_factory = sqlite3.Row
    banco.execute("PRAGMA foreign_keys = ON")
    return banco


def senha_hash(senha, sal):
    # A senha nao fica salva em texto no banco.
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), 220000).hex()


def criar_usuario(banco, nome, email, senha, perfil="ALUNO"):
    sal = secrets.token_hex(16)
    banco.execute(
        "INSERT INTO users(name,email,password_salt,password_hash,role,created_at) VALUES(?,?,?,?,?,?)",
        (nome, email.lower(), sal, senha_hash(senha, sal), perfil, agora())
    )


def iniciar_banco():
    banco = conectar()
    # As tabelas sao criadas apenas se ainda nao existem.
    banco.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bikes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ATIVA'
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bike_id INTEGER NOT NULL,
            duration_minutes INTEGER NOT NULL,
            avg_watts INTEGER NOT NULL,
            energy_kwh REAL NOT NULL,
            points INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(bike_id) REFERENCES bikes(id)
        );
        CREATE TABLE IF NOT EXISTS benefits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            points_cost INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            benefit_id INTEGER NOT NULL,
            benefit_name TEXT NOT NULL,
            points_spent INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDENTE',
            created_at TEXT NOT NULL,
            delivered_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(benefit_id) REFERENCES benefits(id)
        );
        CREATE TABLE IF NOT EXISTS config (name TEXT PRIMARY KEY, value TEXT NOT NULL);
    """)
    banco.execute("INSERT OR IGNORE INTO config(name,value) VALUES('points_per_wh','1')")

    acessos_demo = None
    if banco.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        senha_aluno = secrets.token_urlsafe(12)
        senha_gestor = secrets.token_urlsafe(12)
        criar_usuario(banco, "Camila Duarte", "camila@bikeenergy.com", senha_aluno)
        criar_usuario(banco, "Marcos Andrade", "gestor@bikeenergy.com", senha_gestor, "GESTOR")
        acessos_demo = (
            f"Aluno: camila@bikeenergy.com\nSenha: {senha_aluno}\n\n"
            f"Gestor: gestor@bikeenergy.com\nSenha: {senha_gestor}\n"
        )

    if banco.execute("SELECT COUNT(*) FROM bikes").fetchone()[0] == 0:
        banco.executemany("INSERT INTO bikes(code,name,status) VALUES(?,?,?)", [
            ("BK-01", "Bike 01", "ATIVA"),
            ("BK-02", "Bike 02", "ATIVA"),
            ("BK-03", "Bike 03", "MANUTENCAO")
        ])

    if banco.execute("SELECT COUNT(*) FROM benefits").fetchone()[0] == 0:
        banco.executemany("INSERT INTO benefits(name,points_cost,active,created_at) VALUES(?,?,1,?)", [
            ("Bebida esportiva", 100, agora()),
            ("Avaliação física", 250, agora()),
            ("5% de desconto na mensalidade", 500, agora())
        ])

    if banco.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0:
        aluno = banco.execute("SELECT id FROM users WHERE email='camila@bikeenergy.com'").fetchone()
        bike = banco.execute("SELECT id FROM bikes ORDER BY id LIMIT 1").fetchone()
        if aluno and bike:
            banco.execute("""INSERT INTO sessions
                (user_id,bike_id,duration_minutes,avg_watts,energy_kwh,points,created_at)
                VALUES(?,?,?,?,?,?,?)""", (aluno["id"], bike["id"], 30, 80, 0.040, 40, agora()))
    try:
        if acessos_demo is not None:
            BANCO.with_name("ACESSOS_DEMO.txt").write_text(acessos_demo, encoding="utf-8")
        banco.commit()
    finally:
        banco.close()


def lista(banco, sql, params=()):
    return [dict(linha) for linha in banco.execute(sql, params).fetchall()]


def saldo(banco, usuario):
    ganhos = banco.execute("SELECT COALESCE(SUM(points),0) FROM sessions WHERE user_id=?", (usuario,)).fetchone()[0]
    gastos = banco.execute("SELECT COALESCE(SUM(points_spent),0) FROM redemptions WHERE user_id=?", (usuario,)).fetchone()[0]
    return ganhos - gastos


def dados_usuario(banco, usuario):
    # Consultas que abastecem as telas do aluno e do gestor.
    gestor = usuario["role"] == "GESTOR"
    filtro = "" if gestor else " WHERE s.user_id=?"
    params = () if gestor else (usuario["id"],)
    sessoes = lista(banco, """SELECT s.*, u.name AS user_name, b.name AS bike_name
        FROM sessions s JOIN users u ON u.id=s.user_id JOIN bikes b ON b.id=s.bike_id"""
        + filtro + " ORDER BY s.id DESC", params)
    filtro_r = "" if gestor else " WHERE r.user_id=?"
    resgates = lista(banco, """SELECT r.*, u.name AS user_name FROM redemptions r
        JOIN users u ON u.id=r.user_id""" + filtro_r + " ORDER BY r.id DESC", params)
    return {
        "user": dict(usuario),
        "wallet": None if gestor else saldo(banco, usuario["id"]),
        "users": lista(banco, "SELECT id,name,email,role,created_at FROM users") if gestor else [],
        "bikes": lista(banco, "SELECT * FROM bikes ORDER BY id"),
        "sessions": sessoes,
        "benefits": lista(banco, "SELECT * FROM benefits ORDER BY points_cost"),
        "redemptions": resgates,
        "points_per_wh": float(banco.execute("SELECT value FROM config WHERE name='points_per_wh'").fetchone()[0])
    }


class Erro(Exception):
    pass


class Servidor(BaseHTTPRequestHandler):
    def responder(self, dados, status=200, cookie=None):
        texto = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(texto))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(texto)

    def arquivo(self, caminho):
        arquivos = {"/": "index.html", "/index.html": "index.html", "/style.css": "style.css", "/app.js": "app.js"}
        nome = arquivos.get(caminho)
        if not nome:
            self.send_error(404)
            return
        tipos = {".html": "text/html", ".css": "text/css", ".js": "text/javascript"}
        conteudo = (PASTA / nome).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", tipos[Path(nome).suffix] + "; charset=utf-8")
        self.send_header("Content-Length", len(conteudo))
        self.end_headers()
        self.wfile.write(conteudo)

    def receber(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        if tamanho < 0 or tamanho > 20000:
            raise Erro("Dados muito grandes")
        dados = json.loads(self.rfile.read(tamanho)) if tamanho else {}
        if not isinstance(dados, dict):
            raise Erro("Dados inválidos")
        return dados

    def token(self):
        cookies = SimpleCookie()
        cookies.load(self.headers.get("Cookie", ""))
        return cookies["bike"].value if "bike" in cookies else ""

    def usuario_logado(self, banco):
        id_usuario = LOGINS.get(self.token())
        if id_usuario:
            return banco.execute("SELECT id,name,email,role FROM users WHERE id=?", (id_usuario,)).fetchone()
        return None

    def processar(self, metodo):
        caminho = urlparse(self.path).path
        if metodo == "GET" and not caminho.startswith("/api/"):
            return self.arquivo(caminho)
        if not caminho.startswith("/api/"):
            return self.responder({"erro": "Endereço não encontrado"}, 404)
        banco = conectar()
        try:
            dados = self.receber() if metodo == "POST" else {}
            usuario = self.usuario_logado(banco)
            resposta, cookie = self.executar(banco, caminho, metodo, dados, usuario)
            banco.commit()
            self.responder(resposta, 200, cookie)
        except (Erro, ValueError, TypeError, sqlite3.IntegrityError, json.JSONDecodeError) as erro:
            banco.rollback()
            self.responder({"erro": str(erro)}, 400)
        except Exception as erro:
            banco.rollback()
            print("Erro do servidor:", erro)
            self.responder({"erro": "Erro no servidor. Veja o terminal."}, 500)
        finally:
            banco.close()

    def executar(self, banco, caminho, metodo, d, usuario):
        if caminho == "/api/me" and metodo == "GET":
            return ({"user": dict(usuario) if usuario else None}, None)

        if caminho == "/api/login" and metodo == "POST":
            conta = banco.execute("SELECT * FROM users WHERE email=?", (str(d.get("email", "")).lower(),)).fetchone()
            senha = str(d.get("password", ""))
            if not conta or not hmac.compare_digest(senha_hash(senha, conta["password_salt"]), conta["password_hash"]):
                raise Erro("Email ou senha incorretos")
            token = secrets.token_urlsafe(24)
            LOGINS[token] = conta["id"]
            return ({"ok": True}, f"bike={token}; HttpOnly; SameSite=Strict; Path=/")

        if caminho == "/api/register" and metodo == "POST":
            nome = str(d.get("name", "")).strip()
            email = str(d.get("email", "")).strip().lower()
            senha = str(d.get("password", ""))
            if len(nome) < 3 or "@" not in email or len(senha) < 8:
                raise Erro("Informe nome, email e senha com 8 caracteres")
            if banco.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
                raise Erro("Email já cadastrado")
            criar_usuario(banco, nome, email, senha)
            return ({"ok": True}, None)

        if caminho == "/api/logout" and metodo == "POST":
            LOGINS.pop(self.token(), None)
            return ({"ok": True}, "bike=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")

        if not usuario:
            raise Erro("Faça login primeiro")
        gestor = usuario["role"] == "GESTOR"

        if caminho == "/api/data" and metodo == "GET":
            return (dados_usuario(banco, usuario), None)

        if caminho == "/api/sessions" and metodo == "POST" and not gestor:
            bike_id = int(d.get("bike_id"))
            watts = int(d.get("watts"))
            minutos = int(d.get("minutes"))
            if watts < 1 or watts > 300 or minutos < 1 or minutos > 180:
                raise Erro("Potência ou duração fora do limite")
            bike = banco.execute("SELECT * FROM bikes WHERE id=? AND status='ATIVA'", (bike_id,)).fetchone()
            if not bike:
                raise Erro("Bicicleta indisponível")
            # kWh = watts x horas / 1000. Pontos = Wh x fator da academia.
            kwh = round(watts * minutos / 60000, 6)
            fator = float(banco.execute("SELECT value FROM config WHERE name='points_per_wh'").fetchone()[0])
            pontos = int(watts * minutos / 60 * fator + 0.5)
            banco.execute("""INSERT INTO sessions
                (user_id,bike_id,duration_minutes,avg_watts,energy_kwh,points,created_at)
                VALUES(?,?,?,?,?,?,?)""", (usuario["id"], bike_id, minutos, watts, kwh, pontos, agora()))
            return ({"ok": True, "kwh": kwh, "points": pontos}, None)

        # Os comandos daqui em diante sao apenas do gestor, exceto o resgate.
        if caminho == "/api/redeem" and metodo == "POST" and not gestor:
            beneficio = banco.execute("SELECT * FROM benefits WHERE id=? AND active=1", (int(d.get("id")),)).fetchone()
            if not beneficio:
                raise Erro("Benefício não encontrado")
            # Bloqueia o saldo enquanto registra o resgate.
            banco.execute("BEGIN IMMEDIATE")
            if saldo(banco, usuario["id"]) < beneficio["points_cost"]:
                raise Erro("Pontos insuficientes")
            banco.execute("""INSERT INTO redemptions
                (user_id,benefit_id,benefit_name,points_spent,status,created_at)
                VALUES(?,?,?,?,'PENDENTE',?)""",
                (usuario["id"], beneficio["id"], beneficio["name"], beneficio["points_cost"], agora()))
            return ({"ok": True}, None)

        if not gestor:
            raise Erro("Esta opção é apenas do gestor")

        if caminho == "/api/bikes" and metodo == "POST":
            nome = str(d.get("name", "")).strip()
            codigo = str(d.get("code", "")).strip().upper()
            if not nome or not codigo:
                raise Erro("Informe nome e código da bicicleta")
            banco.execute("INSERT INTO bikes(code,name,status) VALUES(?,?,'ATIVA')", (codigo, nome))
            return ({"ok": True}, None)

        if caminho == "/api/bike-status" and metodo == "POST":
            status = str(d.get("status", ""))
            if status not in ("ATIVA", "MANUTENCAO"):
                raise Erro("Status inválido")
            banco.execute("UPDATE bikes SET status=? WHERE id=?", (status, int(d.get("id"))))
            return ({"ok": True}, None)

        if caminho == "/api/benefits" and metodo == "POST":
            nome = str(d.get("name", "")).strip()
            custo = int(d.get("points_cost"))
            if not nome or custo <= 0:
                raise Erro("Informe nome e pontos do benefício")
            banco.execute("INSERT INTO benefits(name,points_cost,active,created_at) VALUES(?,?,1,?)", (nome, custo, agora()))
            return ({"ok": True}, None)

        if caminho == "/api/benefit-status" and metodo == "POST":
            ativo = int(d.get("active"))
            if ativo not in (0, 1):
                raise Erro("Status inválido")
            banco.execute("UPDATE benefits SET active=? WHERE id=?", (ativo, int(d.get("id"))))
            return ({"ok": True}, None)

        if caminho == "/api/redemption-status" and metodo == "POST":
            status = str(d.get("status", ""))
            if status not in ("PENDENTE", "RETIRADO"):
                raise Erro("Status inválido")
            retirada = agora() if status == "RETIRADO" else None
            banco.execute("UPDATE redemptions SET status=?,delivered_at=? WHERE id=?", (status, retirada, int(d.get("id"))))
            return ({"ok": True}, None)

        if caminho == "/api/rule" and metodo == "POST":
            fator = float(d.get("points_per_wh"))
            if not 0.1 <= fator <= 100:
                raise Erro("Valor deve ficar entre 0,1 e 100")
            banco.execute("UPDATE config SET value=? WHERE name='points_per_wh'", (str(fator),))
            return ({"ok": True}, None)

        raise Erro("Comando não encontrado ou sem permissão")

    def do_GET(self):
        self.processar("GET")

    def do_POST(self):
        self.processar("POST")

    def log_message(self, formato, *args):
        pass  # Evita encher o terminal de mensagens.


def main():
    iniciar_banco()
    try:
        servidor = HTTPServer(("127.0.0.1", 8765), Servidor)
    except OSError:
        print("A porta 8765 ja esta em uso. Feche o programa antigo antes.")
        input("Pressione Enter para fechar...")
        return
    endereco = "http://127.0.0.1:8765"
    print("BIKE ENERGY - SISTEMA SIMPLES")
    print("Aberto em:", endereco)
    print("Banco de dados:", BANCO)
    if BANCO.with_name("ACESSOS_DEMO.txt").is_file():
        print("Acessos de demonstração:", BANCO.with_name("ACESSOS_DEMO.txt"))
    print("Para fechar: Ctrl + C")
    threading.Timer(1, lambda: webbrowser.open(endereco)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        servidor.server_close()


if __name__ == "__main__":
    main()
