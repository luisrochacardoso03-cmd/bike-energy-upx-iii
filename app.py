"""Execute: python app.py. Apenas biblioteca padrão (Python 3.11+)."""
import argparse
import secrets
from pathlib import Path
from energy.service import Service, password_hash, now, LOCAL_TZ
from datetime import datetime, timedelta
from energy.http import make_server


def seed(service, directory):
    # All demo rows commit together; credentials are published before that commit.
    with service.db.connect(write=True) as db:
        if db.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
            return
        passwords = [secrets.token_urlsafe(10), secrets.token_urlsafe(10)]
        user_ids = []
        for (name, email, role), password in zip([
            ('Marcos Andrade', 'gestor@bike.local', 'gestor'),
            ('Camila Duarte', 'aluno@bike.local', 'aluno')], passwords):
            user_ids.append(db.execute('INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)',
                                      (name,email,password_hash(password),role,now())).lastrowid)
        for name, enabled in [('Bike 01',1),('Bike 02',1),('Bike 03',0)]:
            db.execute('INSERT INTO bikes(name,active) VALUES(?,?)',(name,enabled))
        bike_id = db.execute('SELECT id FROM bikes ORDER BY id LIMIT 1').fetchone()[0]
        for name, cost in [('Bebida esportiva',100),('Avaliação física',250),('5% de benefício na mensalidade',500)]:
            db.execute('INSERT INTO rewards(name,description,cost,stock,active) VALUES(?,?,?,?,1)',
                       (name,'Benefício demonstrativo definido pela academia.',cost,20))
        for minutes, watts in [(30,80),(35,90)]:
            end = datetime.now(LOCAL_TZ)
            db.execute('INSERT INTO rides(user_id,bike_id,bike_name,minutes,watts,energy_wm,points,rate_tenths,started_at,ended_at,created_at,request_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (user_ids[1],bike_id,'Bike 01',minutes,watts,minutes*watts,(minutes*watts*10+300)//600,10,
                        (end-timedelta(minutes=minutes)).isoformat(timespec='seconds'),end.isoformat(timespec='seconds'),now(),secrets.token_hex(16)))
        content = ('BIKE ENERGY — CONTAS LOCAIS DE DEMONSTRAÇÃO\n\n'
                   f'Gestor: gestor@bike.local\nSenha: {passwords[0]}\n\n'
                   f'Aluna: aluno@bike.local\nSenha: {passwords[1]}\n\n'
                   'Dados fictícios. Senhas geradas nesta instalação. Não publique este arquivo nem o banco.\n')
        staging = directory/'ACESSOS_DEMO.tmp'
        staging.write_text(content,encoding='utf-8')
        staging.replace(directory/'ACESSOS_DEMO.txt')


def main():
    parser = argparse.ArgumentParser(description='Bike Energy local com SQLite')
    parser.add_argument('--port', type=int, default=8040)
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).resolve().parent/'data')
    parser.add_argument('--no-demo', action='store_true', help='Não criar dados de demonstração')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('A porta deve estar entre 1 e 65535.')
    directory = args.data_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    service = Service(directory/'bike_energy.sqlite3')
    try:
        server = make_server(service, args.port)
    except OSError:
        parser.exit(1, f'Porta {args.port} indisponível. Feche outra instância ou use --port 8041.\n')
    try:
        if not args.no_demo:
            seed(service, directory)
        print(f'Bike Energy: http://127.0.0.1:{args.port}', flush=True)
        print(f'Banco SQLite: {service.db.path}', flush=True)
        print(f'Acessos de demonstração: {directory / "ACESSOS_DEMO.txt"}', flush=True)
        print('Mantenha este terminal aberto. Ctrl+C encerra o servidor.', flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor encerrado. Dados preservados.')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
