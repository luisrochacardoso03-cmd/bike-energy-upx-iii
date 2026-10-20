"""Servidor HTTP restrito ao computador local, sem dependências externas."""
import csv
import io
import json
import logging
import sqlite3
import threading
import time
from collections import deque
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from .service import AppError

STATIC = Path(__file__).resolve().parent.parent / 'static'
PUBLIC = {'/': ('index.html', 'text/html'), '/styles.css': ('styles.css', 'text/css'),
          '/app.js': ('app.js', 'text/javascript')}


def make_server(service, port=8040):
    failures = deque()
    failure_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = 'BikeEnergy/4'
        sys_version = ''

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *_):
            pass  # Do not log credentials, cookies or student data.

        def send(self, status, value, content_type='application/json', extra=None):
            body = json.dumps(value, ensure_ascii=False).encode() if content_type == 'application/json' else value
            self.send_response(status)
            self.send_header('Content-Type', content_type + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            for key, val in (extra or {}).items():
                self.send_header(key, val)
            self.end_headers()
            self.wfile.write(body)

        def cookie(self):
            try:
                parsed = SimpleCookie(self.headers.get('Cookie', ''))
                return parsed['bike_session'].value if 'bike_session' in parsed else ''
            except CookieError:
                return ''

        def check_origin(self, write=False):
            port = self.server.server_address[1]
            hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
            if self.headers.get('Host') not in hosts:
                raise AppError('Host não autorizado.', 403)
            if write and self.headers.get('Origin') != 'http://' + self.headers.get('Host'):
                raise AppError('Origem não autorizada. Abra o sistema pelo endereço local.', 403)

        def data(self):
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise AppError('Envie os dados em JSON.', 415)
            lengths = self.headers.get_all('Content-Length', [])
            if len(lengths) != 1 or self.headers.get('Transfer-Encoding'):
                raise AppError('Tamanho da requisição inválido.')
            try:
                length = int(lengths[0])
            except ValueError:
                raise AppError('Tamanho da requisição inválido.') from None
            if not 0 <= length <= 16384:
                raise AppError('Dados muito grandes.', 413)
            try:
                data = json.loads(self.rfile.read(length))
            except (ValueError, UnicodeError):
                raise AppError('JSON inválido.') from None
            if not isinstance(data, dict):
                raise AppError('Os dados devem ser um objeto JSON.')
            return data

        def handle_error(self, action):
            try:
                action()
            except AppError as error:
                self.send(error.status, {'error': str(error)})
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                self.close_connection = True
            except sqlite3.OperationalError:
                logging.exception('Falha de acesso ao banco local')
                self.send(503, {'error': 'Banco ocupado ou indisponível. Tente novamente.'})
            except Exception:
                logging.exception('Falha interna')
                self.send(500, {'error': 'Falha interna. Consulte o terminal do servidor.'})

        def do_GET(self):
            self.handle_error(self.get)

        def get(self):
            self.check_origin()
            path = urlsplit(self.path).path
            if path in PUBLIC:
                filename, mime = PUBLIC[path]
                return self.send(200, (STATIC / filename).read_bytes(), mime)
            if path == '/api/health':
                return self.send(200, {'ok': True, 'database': 'SQLite', 'version': '4.0'})
            if path not in ('/api/state', '/api/report', '/api/report.csv'):
                raise AppError('Recurso não encontrado.', 404)
            uid = service.authenticate(self.cookie())['id']
            if path == '/api/state':
                return self.send(200, service.state(uid))
            query = parse_qs(urlsplit(self.path).query)
            report = service.report(uid, query.get('start', [''])[0], query.get('end', [''])[0])
            if path == '/api/report':
                return self.send(200, report)
            output = io.StringIO(newline='')
            writer = csv.writer(output, delimiter=';')
            writer.writerow(['Aluno', 'Sessões', 'Minutos', 'kWh simulados', 'Pontos gerados'])
            for row in report['rows']:
                name = row['name']
                if name.lstrip().startswith(('=', '+', '-', '@')):
                    name = "'" + name
                writer.writerow([name, row['sessions'], row['minutes'], f"{row['kwh']:.6f}".replace('.', ','), row['points']])
            self.send(200, ('\ufeff' + output.getvalue()).encode(), 'text/csv', {'Content-Disposition': 'attachment; filename="bike-energy-relatorio.csv"'})

        def do_POST(self):
            self.handle_error(self.post)

        def post(self):
            self.check_origin(write=True)
            data, path = self.data(), urlsplit(self.path).path
            if path in ('/api/login', '/api/register'):
                with failure_lock:
                    while failures and failures[0] < time.monotonic()-60:
                        failures.popleft()
                    if len(failures) >= 30:
                        raise AppError('Muitas tentativas. Aguarde um minuto.', 429)
                    failures.append(time.monotonic())
                if path == '/api/register':
                    return self.send(201, service.create_user(data.get('name'), data.get('email'), data.get('password')))
                token, user = service.login(data.get('email'), data.get('password'))
                return self.send(200, user, extra={'Set-Cookie': f'bike_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'})
            token = self.cookie()
            uid = service.authenticate(token)['id']
            if path == '/api/logout':
                service.logout(token)
                return self.send(200, {'ok': True}, extra={'Set-Cookie':'bike_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
            actions = {
                '/api/rides': lambda: service.ride(uid, data),
                '/api/redemptions': lambda: service.redeem(uid, data),
                '/api/pickup': lambda: service.set_pickup(uid, data.get('id'), data.get('collected')),
                '/api/bikes': lambda: service.save_bike(uid, data),
                '/api/rewards': lambda: service.save_reward(uid, data),
                '/api/reward-status': lambda: service.set_reward_status(uid, data.get('id'), data.get('active')),
                '/api/rate': lambda: service.set_rate(uid, data.get('points_per_wh')),
                '/api/goal': lambda: service.set_goal(uid, data.get('goal_wh')),
            }
            if path not in actions:
                raise AppError('Recurso não encontrado.', 404)
            self.send(200, actions[path]())

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server
