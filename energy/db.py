import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('aluno','gestor')),
 goal_wh INTEGER NOT NULL DEFAULT 500 CHECK(goal_wh > 0), created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_sessions (
 token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), rate_tenths INTEGER NOT NULL CHECK(rate_tenths BETWEEN 1 AND 1000));
INSERT OR IGNORE INTO settings VALUES (1,10);
CREATE TABLE IF NOT EXISTS bikes (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, active INTEGER NOT NULL CHECK(active IN (0,1))
);
CREATE TABLE IF NOT EXISTS rewards (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
 cost INTEGER NOT NULL CHECK(cost>0), stock INTEGER NOT NULL CHECK(stock>=0),
 active INTEGER NOT NULL CHECK(active IN (0,1)), version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS rides (
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), bike_id INTEGER NOT NULL REFERENCES bikes(id),
 bike_name TEXT NOT NULL, minutes INTEGER NOT NULL CHECK(minutes BETWEEN 1 AND 180),
 watts INTEGER NOT NULL CHECK(watts BETWEEN 10 AND 500), energy_wm INTEGER NOT NULL CHECK(energy_wm>0),
 points INTEGER NOT NULL CHECK(points>=0), rate_tenths INTEGER NOT NULL,
 started_at TEXT NOT NULL, ended_at TEXT NOT NULL, created_at TEXT NOT NULL,
 request_id TEXT NOT NULL, UNIQUE(user_id,request_id)
);
CREATE TABLE IF NOT EXISTS redemptions (
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), reward_id INTEGER NOT NULL REFERENCES rewards(id),
 reward_name TEXT NOT NULL, cost INTEGER NOT NULL CHECK(cost>0), created_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','collected')),
 collected_at TEXT, collected_by INTEGER REFERENCES users(id), request_id TEXT NOT NULL, UNIQUE(user_id,request_id)
);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY, redemption_id INTEGER NOT NULL REFERENCES redemptions(id),
 actor_id INTEGER NOT NULL REFERENCES users(id), action TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS rides_user_date ON rides(user_id,created_at);
CREATE INDEX IF NOT EXISTS redemptions_user ON redemptions(user_id);
PRAGMA user_version=1;
"""


class Database:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(SCHEMA)
            if 'version' not in {r['name'] for r in db.execute('PRAGMA table_info(rewards)')}:
                db.execute('ALTER TABLE rewards ADD COLUMN version INTEGER NOT NULL DEFAULT 1')

    @contextmanager
    def connect(self, write=False):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            # A consistent snapshot for reads; serialize balance/stock writes.
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
