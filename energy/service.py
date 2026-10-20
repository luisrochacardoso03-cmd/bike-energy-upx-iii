"""Regras de negócio. Nenhuma regra de saldo depende do navegador."""
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from .db import Database

LOCAL_TZ = timezone(timedelta(hours=-3))


class AppError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def now():
    return datetime.now(LOCAL_TZ).isoformat(timespec='seconds')


def text(value, label, maximum=100, minimum=1):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise AppError(f'{label}: informe entre {minimum} e {maximum} caracteres.')
    return value.strip()


def integer(value, label, low, high):
    if type(value) is not int or not low <= value <= high:
        raise AppError(f'{label}: use um inteiro de {low} a {high}.')
    return value


def active(value):
    if type(value) not in (bool, int) or value not in (0, 1):
        raise AppError('Status inválido.')
    return int(value)


def request_key(data):
    key = data.get('request_id')
    if not isinstance(key, str) or not re.fullmatch(r'[a-zA-Z0-9-]{16,80}', key):
        raise AppError('Identificador da operação inválido. Atualize a página.')
    return key


def password_hash(password, salt=None):
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise AppError('A senha precisa ter de 8 a 128 caracteres.')
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 300_000).hex()
    return salt + ':' + digest


def public_user(row):
    return {key: row[key] for key in ('id', 'name', 'email', 'role', 'goal_wh', 'created_at')}


def rows(db, query, params=()):
    return [dict(row) for row in db.execute(query, params)]


class Service:
    def __init__(self, path):
        self.db = Database(path)

    def _user(self, db, user_id, role=None):
        user = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        if not user:
            raise AppError('Entre novamente no sistema.', 401)
        if role and user['role'] != role:
            raise AppError('Seu perfil não permite esta ação.', 403)
        return user

    def create_user(self, name, email, password, role='aluno'):
        name = text(name, 'Nome', 100, 2)
        email = text(email, 'E-mail', 180).lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise AppError('Informe um e-mail válido.')
        if role not in ('aluno', 'gestor'):
            raise AppError('Perfil inválido.')
        hashed = password_hash(password)
        try:
            with self.db.connect(write=True) as db:
                uid = db.execute('INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)',
                                 (name, email, hashed, role, now())).lastrowid
                return public_user(self._user(db, uid))
        except sqlite3.IntegrityError:
            raise AppError('Este e-mail já está cadastrado.', 409) from None

    def login(self, email, password):
        email = text(email, 'E-mail', 180).lower()
        # Invalid credentials return the same message and cost a password derivation.
        with self.db.connect() as db:
            user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        salt = user['password_hash'].split(':')[0] if user else '00' * 16
        try:
            hashed = password_hash(password, salt)
        except AppError:
            raise AppError('E-mail ou senha incorretos.', 401) from None
        if not user or not hmac.compare_digest(hashed, user['password_hash']):
            raise AppError('E-mail ou senha incorretos.', 401)
        token = secrets.token_urlsafe(32)
        with self.db.connect(write=True) as db:
            db.execute('DELETE FROM auth_sessions WHERE expires < ?', (time.time(),))
            db.execute('INSERT INTO auth_sessions VALUES(?,?,?)',
                       (hashlib.sha256(token.encode()).hexdigest(), user['id'], time.time() + 28800))
        return token, public_user(user)

    def authenticate(self, token):
        with self.db.connect() as db:
            row = db.execute('SELECT user_id FROM auth_sessions WHERE token_hash=? AND expires>?',
                             (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
            if not row:
                raise AppError('Entre novamente no sistema.', 401)
            return public_user(self._user(db, row['user_id']))

    def logout(self, token):
        with self.db.connect(write=True) as db:
            db.execute('DELETE FROM auth_sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))

    def save_bike(self, uid, data):
        name, enabled = text(data.get('name'), 'Nome', 80), active(data.get('active', True))
        try:
            with self.db.connect(write=True) as db:
                self._user(db, uid, 'gestor')
                if data.get('id') is not None:
                    bid = integer(data['id'], 'Bicicleta', 1, 2**31)
                    if db.execute('UPDATE bikes SET name=?,active=? WHERE id=?', (name, enabled, bid)).rowcount != 1:
                        raise AppError('Bicicleta não encontrada.', 404)
                else:
                    bid = db.execute('INSERT INTO bikes(name,active) VALUES(?,?)', (name, enabled)).lastrowid
                return dict(db.execute('SELECT * FROM bikes WHERE id=?', (bid,)).fetchone())
        except sqlite3.IntegrityError:
            raise AppError('Já existe uma bicicleta com este nome.', 409) from None

    def save_reward(self, uid, data):
        name = text(data.get('name'), 'Nome', 100)
        description = text(data.get('description', ''), 'Descrição', 300, 0)
        cost = integer(data.get('cost'), 'Pontos', 1, 1_000_000)
        stock = integer(data.get('stock'), 'Estoque', 0, 100_000)
        enabled = active(data.get('active', True))
        with self.db.connect(write=True) as db:
            self._user(db, uid, 'gestor')
            values = (name, description, cost, stock, enabled)
            if data.get('id') is not None:
                rid = integer(data['id'], 'Benefício', 1, 2**31)
                version = integer(data.get('version'), 'Versão do benefício', 1, 2**31)
                if db.execute('UPDATE rewards SET name=?,description=?,cost=?,stock=?,active=?,version=version+1 WHERE id=? AND version=?', values + (rid, version)).rowcount != 1:
                    raise AppError('Este benefício mudou. Abra Benefícios novamente e refaça a edição com os dados atuais.', 409)
            else:
                rid = db.execute('INSERT INTO rewards(name,description,cost,stock,active) VALUES(?,?,?,?,?)', values).lastrowid
            return dict(db.execute('SELECT * FROM rewards WHERE id=?', (rid,)).fetchone())

    def set_reward_status(self, uid, reward_id, enabled):
        integer(reward_id, 'Benefício', 1, 2**31)
        enabled = active(enabled)
        with self.db.connect(write=True) as db:
            self._user(db, uid, 'gestor')
            if db.execute('UPDATE rewards SET active=?,version=version+1 WHERE id=?', (enabled, reward_id)).rowcount != 1:
                raise AppError('Benefício não encontrado.', 404)
        return {'ok': True}

    def set_rate(self, uid, value):
        try:
            rate = Decimal(str(value)) * 10
            if not rate.is_finite() or rate != rate.to_integral_value() or not 1 <= rate <= 1000:
                raise ValueError()
        except (InvalidOperation, ValueError):
            raise AppError('Use pontos por Wh entre 0,1 e 100, em passos de 0,1.') from None
        with self.db.connect(write=True) as db:
            self._user(db, uid, 'gestor')
            db.execute('UPDATE settings SET rate_tenths=? WHERE id=1', (int(rate),))
        return {'points_per_wh': float(rate / 10)}

    def set_goal(self, uid, value):
        goal = integer(value, 'Meta em Wh', 1, 1_000_000)
        with self.db.connect(write=True) as db:
            self._user(db, uid, 'aluno')
            db.execute('UPDATE users SET goal_wh=? WHERE id=?', (goal, uid))
        return {'goal_wh': goal}

    def _ride_dict(self, row):
        result = dict(row)
        result['energy_wh'] = result['energy_wm'] / 60
        result['kwh'] = result['energy_wm'] / 60000
        return result

    def ride(self, uid, data):
        minutes = integer(data.get('minutes'), 'Duração', 1, 180)
        watts = integer(data.get('watts'), 'Potência', 10, 500)
        bid = integer(data.get('bike_id'), 'Bicicleta', 1, 2**31)
        key = request_key(data)
        with self.db.connect(write=True) as db:
            self._user(db, uid, 'aluno')
            previous = db.execute('SELECT * FROM rides WHERE user_id=? AND request_id=?', (uid, key)).fetchone()
            if previous:
                if (previous['minutes'], previous['watts'], previous['bike_id']) != (minutes, watts, bid):
                    raise AppError('Esta operação já foi usada com outros dados.', 409)
                return self._ride_dict(previous)
            bike = db.execute('SELECT * FROM bikes WHERE id=? AND active=1', (bid,)).fetchone()
            if not bike:
                raise AppError('Bicicleta indisponível. Escolha outra.')
            rate = db.execute('SELECT rate_tenths FROM settings WHERE id=1').fetchone()[0]
            energy_wm = watts * minutes
            # Positive round-half-up, matching v3 Math.round, without binary floats.
            points = (energy_wm * rate + 300) // 600
            end = datetime.now(LOCAL_TZ)
            rid = db.execute('''INSERT INTO rides(user_id,bike_id,bike_name,minutes,watts,energy_wm,points,rate_tenths,
                started_at,ended_at,created_at,request_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                (uid, bid, bike['name'], minutes, watts, energy_wm, points, rate,
                 (end - timedelta(minutes=minutes)).isoformat(timespec='seconds'), end.isoformat(timespec='seconds'),
                 end.isoformat(timespec='seconds'), key)).lastrowid
            return self._ride_dict(db.execute('SELECT * FROM rides WHERE id=?', (rid,)).fetchone())

    def _balance(self, db, uid):
        earned = db.execute('SELECT COALESCE(SUM(points),0) FROM rides WHERE user_id=?', (uid,)).fetchone()[0]
        spent = db.execute('SELECT COALESCE(SUM(cost),0) FROM redemptions WHERE user_id=?', (uid,)).fetchone()[0]
        return earned - spent

    def redeem(self, uid, data):
        rid = integer(data.get('reward_id'), 'Benefício', 1, 2**31)
        key = request_key(data)
        with self.db.connect(write=True) as db:
            self._user(db, uid, 'aluno')
            previous = db.execute('SELECT * FROM redemptions WHERE user_id=? AND request_id=?', (uid, key)).fetchone()
            if previous:
                if previous['reward_id'] != rid:
                    raise AppError('Operação já usada com outro benefício.', 409)
                return dict(previous)
            reward = db.execute('SELECT * FROM rewards WHERE id=? AND active=1 AND stock>0', (rid,)).fetchone()
            if not reward:
                raise AppError('Benefício indisponível ou sem estoque.')
            if self._balance(db, uid) < reward['cost']:
                raise AppError('Pontos insuficientes para este benefício.')
            db.execute('UPDATE rewards SET stock=stock-1,version=version+1 WHERE id=?', (rid,))
            result = db.execute('''INSERT INTO redemptions(user_id,reward_id,reward_name,cost,created_at,request_id)
                VALUES(?,?,?,?,?,?)''', (uid, rid, reward['name'], reward['cost'], now(), key)).lastrowid
            return dict(db.execute('SELECT * FROM redemptions WHERE id=?', (result,)).fetchone())

    def set_pickup(self, uid, redemption_id, collected):
        integer(redemption_id, 'Resgate', 1, 2**31)
        if type(collected) is not bool:
            raise AppError('Status inválido.')
        status = 'collected' if collected else 'pending'
        with self.db.connect(write=True) as db:
            self._user(db, uid, 'gestor')
            row = db.execute('SELECT * FROM redemptions WHERE id=?', (redemption_id,)).fetchone()
            if not row:
                raise AppError('Resgate não encontrado.', 404)
            if row['status'] != status:
                stamp = now()
                db.execute('UPDATE redemptions SET status=?,collected_at=?,collected_by=? WHERE id=?',
                           (status, stamp if collected else None, uid if collected else None, redemption_id))
                db.execute('INSERT INTO audit(redemption_id,actor_id,action,created_at) VALUES(?,?,?,?)',
                           (redemption_id, uid, status, stamp))
            return dict(db.execute('SELECT * FROM redemptions WHERE id=?', (redemption_id,)).fetchone())

    def state(self, uid):
        with self.db.connect() as db:
            user = self._user(db, uid)
            manager = user['role'] == 'gestor'
            where, params = ('', ()) if manager else (' WHERE r.user_id=?', (uid,))
            rides = [self._ride_dict(r) for r in rows(db, 'SELECT r.*,u.name AS student FROM rides r JOIN users u ON u.id=r.user_id' + where + ' ORDER BY r.id DESC', params)]
            redemptions = rows(db, 'SELECT r.*,u.name AS student FROM redemptions r JOIN users u ON u.id=r.user_id' + where + ' ORDER BY r.id DESC', params)
            month = now()[:7]
            summary = {'energy_wh': sum(r['energy_wm'] for r in rides)/60,
                       'month_wh': sum(r['energy_wm'] for r in rides if r['created_at'].startswith(month))/60,
                       'points': sum(r['points'] for r in rides), 'minutes': sum(r['minutes'] for r in rides),
                       'sessions': len(rides), 'balance': sum(r['points'] for r in rides)-sum(r['cost'] for r in redemptions),
                       'pending': sum(r['status'] == 'pending' for r in redemptions)}
            result = {'user': public_user(user), 'summary': summary, 'rides': rides, 'redemptions': redemptions,
                      'bikes': rows(db, 'SELECT * FROM bikes ORDER BY id'),
                      'rewards': rows(db, 'SELECT * FROM rewards' + ('' if manager else ' WHERE active=1') + ' ORDER BY id'),
                      'points_per_wh': db.execute('SELECT rate_tenths/10.0 FROM settings WHERE id=1').fetchone()[0]}
            if manager:
                result['students'] = [{**public_user(r), 'balance': self._balance(db, r['id'])}
                                      for r in rows(db, "SELECT * FROM users WHERE role='aluno' ORDER BY name")]
                result['audit'] = rows(db, 'SELECT a.*,u.name AS actor FROM audit a JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC')
            return result

    def report(self, uid, start, end):
        try:
            first = datetime.strptime(start, '%Y-%m-%d').date()
            last = datetime.strptime(end, '%Y-%m-%d').date()
            if first > last:
                raise ValueError()
        except (ValueError, TypeError):
            raise AppError('Informe um período válido (início até fim).') from None
        with self.db.connect() as db:
            self._user(db, uid, 'gestor')
            entries = rows(db, '''SELECT u.id,u.name,COUNT(r.id) AS sessions,COALESCE(SUM(r.energy_wm),0)/60000.0 AS kwh,
                COALESCE(SUM(r.points),0) AS points,COALESCE(SUM(r.minutes),0) AS minutes
                FROM rides r JOIN users u ON u.id=r.user_id WHERE substr(r.created_at,1,10) BETWEEN ? AND ?
                GROUP BY u.id ORDER BY u.name''', (first.isoformat(), last.isoformat()))
        return {'start': start, 'end': end, 'rows': entries}
