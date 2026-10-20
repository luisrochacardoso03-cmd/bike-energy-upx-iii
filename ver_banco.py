"""Consulta de demonstração ao SQLite, sem alterar dados nem mostrar senhas."""

import argparse
import sqlite3
import sys
from pathlib import Path


def show(connection, title, sql):
    print(f'\n{title}\nSQL: {sql}')
    rows = connection.execute(sql).fetchall()
    if not rows:
        print('(nenhum registro)')
        return
    print(' | '.join(rows[0].keys()))
    for row in rows:
        print(' | '.join(str(value) if value is not None else '-' for value in row))


def main():
    parser = argparse.ArgumentParser(description='Consultar o banco SQLite do Bike Energy em modo somente leitura')
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).resolve().parent / 'data')
    args = parser.parse_args()
    db_path = (args.data_dir / 'bike_energy.sqlite3').resolve()
    if not db_path.is_file():
        print(f'Banco ainda não encontrado: {db_path}\nInicie o site com INICIAR.bat primeiro.', file=sys.stderr)
        return 1

    print(f'BANCO SQLITE: {db_path}')
    print('Consulta somente leitura. Senhas e tokens não são exibidos.')
    try:
        with sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True, timeout=5) as db:
            db.row_factory = sqlite3.Row
            show(db, 'ALUNOS E GESTORES',
                 'SELECT id, name, email, role FROM users ORDER BY id LIMIT 20')
            show(db, 'BICICLETAS',
                 'SELECT id, name, active FROM bikes ORDER BY id LIMIT 20')
            show(db, 'SESSÕES E PONTOS',
                 'SELECT rides.id, users.name AS aluno, rides.bike_name AS bicicleta, '
                 'rides.minutes AS minutos, ROUND(rides.energy_wm / 60000.0, 4) AS kWh, '
                 'rides.points AS pontos FROM rides JOIN users ON users.id = rides.user_id '
                 'ORDER BY rides.id DESC LIMIT 20')
            show(db, 'BENEFÍCIOS',
                 'SELECT id, name, cost AS pontos_necessarios, stock AS estoque, active '
                 'FROM rewards ORDER BY id LIMIT 20')
            show(db, 'RESGATES E RETIRADAS',
                 'SELECT redemptions.id, users.name AS aluno, redemptions.reward_name AS beneficio, '
                 'redemptions.cost AS pontos_usados, redemptions.status AS situacao, '
                 'redemptions.collected_at AS retirada_em FROM redemptions '
                 'JOIN users ON users.id = redemptions.user_id '
                 'ORDER BY redemptions.id DESC LIMIT 20')
    except sqlite3.Error as exc:
        print(f'Não foi possível consultar o banco: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
