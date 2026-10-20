import concurrent.futures
import secrets
from scratch import ScratchDirectory
import unittest
from pathlib import Path

from energy.service import Service, AppError


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = ScratchDirectory()
        self.path = Path(self.temp.name) / 'test.sqlite3'
        self.s = Service(self.path)
        self.password = secrets.token_urlsafe(12)
        self.manager = self.s.create_user('Gestor', 'gestor@example.test', self.password, role='gestor')
        self.student = self.s.create_user('Ana', 'ana@example.test', self.password)
        self.other = self.s.create_user('Bruno', 'bruno@example.test', self.password)
        self.bike = self.s.save_bike(self.manager['id'], {'name': 'Bike 01', 'active': True})
        self.reward = self.s.save_reward(self.manager['id'], {'name': 'Garrafa', 'description': 'Retirar na recepção', 'cost': 50, 'stock': 2, 'active': True})

    def tearDown(self):
        self.temp.cleanup()

    def ride(self, user=None, key=None, minutes=60, watts=100):
        return self.s.ride((user or self.student)['id'], {'bike_id': self.bike['id'], 'minutes': minutes, 'watts': watts, 'request_id': key or secrets.token_hex(16)})

    def redeem(self, user=None, key=None):
        return self.s.redeem((user or self.student)['id'], {'reward_id': self.reward['id'], 'request_id': key or secrets.token_hex(16)})

    def test_register_login_and_duplicate_email(self):
        token, user = self.s.login(' ANA@example.test ', self.password)
        self.assertEqual(self.s.authenticate(token)['id'], self.student['id'])
        self.assertNotIn('password_hash', user)
        with self.assertRaises(AppError):
            self.s.create_user('Outra Ana', 'ana@example.test', self.password)
        with self.assertRaises(AppError):
            self.s.login('ana@example.test', 'incorrect')
        self.s.logout(token)
        with self.assertRaises(AppError):
            self.s.authenticate(token)

    def test_exact_energy_points_and_persistence(self):
        ride = self.ride(minutes=30, watts=150)
        self.assertEqual(ride['energy_wh'], 75)
        self.assertEqual(ride['points'], 75)
        new = Service(self.path)
        state = new.state(self.student['id'])
        self.assertEqual(state['summary']['balance'], 75)
        self.assertEqual(len(state['rides']), 1)

    def test_rounding_matches_original_v3(self):
        self.assertEqual(self.ride(minutes=1, watts=100)['points'], 2)
        self.assertEqual(self.ride(minutes=35, watts=90)['points'], 53)

    def test_rate_change_only_affects_future_rides(self):
        self.ride()
        self.s.set_rate(self.manager['id'], 2.5)
        self.assertEqual(self.ride()['points'], 250)
        self.assertEqual(self.s.state(self.student['id'])['summary']['points'], 350)
        with self.assertRaises(AppError):
            self.s.set_rate(self.student['id'], 100)

    def test_goal_and_report_period(self):
        self.s.set_goal(self.student['id'], 750)
        self.ride()
        self.assertEqual(self.s.state(self.student['id'])['user']['goal_wh'], 750)
        self.assertEqual(self.s.report(self.manager['id'], '2000-01-01', '2099-12-31')['rows'][0]['kwh'], 0.1)
        self.assertEqual(self.s.report(self.manager['id'], '2000-01-01', '2000-01-02')['rows'], [])
        with self.assertRaises(AppError):
            self.s.report(self.student['id'], '2000-01-01', '2099-12-31')

    def test_redeem_pickup_and_revert_preserve_balance_and_history(self):
        self.ride()
        result = self.redeem()
        self.assertEqual(result['status'], 'pending')
        self.s.set_pickup(self.manager['id'], result['id'], True)
        self.assertEqual(self.s.state(self.student['id'])['redemptions'][0]['status'], 'collected')
        self.s.set_pickup(self.manager['id'], result['id'], False)
        state = self.s.state(self.student['id'])
        self.assertEqual(state['summary']['balance'], 50)
        self.assertEqual(state['rewards'][0]['stock'], 1)
        self.assertEqual(state['redemptions'][0]['status'], 'pending')
        self.assertEqual(len(self.s.state(self.manager['id'])['audit']), 2)

    def test_insufficient_balance_rolls_back(self):
        with self.assertRaises(AppError):
            self.redeem()
        self.assertEqual(self.s.state(self.student['id'])['rewards'][0]['stock'], 2)
        self.assertEqual(self.s.state(self.student['id'])['redemptions'], [])

    def test_repeat_request_is_idempotent(self):
        key = secrets.token_hex(16)
        self.assertEqual(self.ride(key=key)['id'], self.ride(key=key)['id'])
        key = secrets.token_hex(16)
        self.assertEqual(self.redeem(key=key)['id'], self.redeem(key=key)['id'])
        self.assertEqual(self.s.state(self.student['id'])['summary']['balance'], 50)

    def test_conflicting_idempotency_payload_rejected(self):
        key = secrets.token_hex(16)
        self.ride(key=key)
        with self.assertRaises(AppError):
            self.ride(key=key, minutes=30)

    def test_permissions_and_private_consultation(self):
        self.ride()
        result = self.redeem()
        with self.assertRaises(AppError):
            self.s.set_pickup(self.student['id'], result['id'], True)
        with self.assertRaises(AppError):
            self.s.save_reward(self.student['id'], {'name': 'Fraude', 'cost': 1, 'stock': 100, 'active': True})
        self.assertEqual(self.s.state(self.other['id'])['rides'], [])
        self.assertEqual(self.s.state(self.other['id'])['redemptions'], [])
        self.assertNotIn('students', self.s.state(self.other['id']))

    def test_concurrent_redemptions_do_not_overspend(self):
        self.ride(minutes=30)
        def attempt(_):
            try:
                self.redeem()
                return True
            except AppError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(attempt, range(4))), 1)
        self.assertEqual(self.s.state(self.student['id'])['summary']['balance'], 0)

    def test_stock_and_inactive_reward(self):
        self.ride()
        self.s.save_reward(self.manager['id'], {**self.reward, 'stock': 0})
        with self.assertRaises(AppError):
            self.redeem()
        latest = self.s.state(self.manager['id'])['rewards'][0]
        self.s.save_reward(self.manager['id'], {**latest, 'active': False})
        with self.assertRaises(AppError):
            self.redeem()

    def test_validation_blocks_invalid_numbers_and_inactive_bike(self):
        for minutes in [-1, 0, 181, True, '30', 1.5]:
            with self.subTest(minutes=minutes), self.assertRaises(AppError):
                self.ride(minutes=minutes)
        self.s.save_bike(self.manager['id'], {**self.bike, 'active': False})
        with self.assertRaises(AppError):
            self.ride()

    def test_reward_snapshot_survives_catalog_edit(self):
        self.ride()
        self.redeem()
        latest = self.s.state(self.manager['id'])['rewards'][0]
        self.s.save_reward(self.manager['id'], {**latest, 'name': 'Outro nome', 'cost': 999})
        record = self.s.state(self.student['id'])['redemptions'][0]
        self.assertEqual((record['reward_name'], record['cost']), ('Garrafa', 50))

    def test_stale_catalog_edit_cannot_restore_consumed_stock(self):
        self.ride()
        self.redeem()
        with self.assertRaises(AppError):
            self.s.save_reward(self.manager['id'], {**self.reward, 'name':'Nome novo'})
        self.assertEqual(self.s.state(self.manager['id'])['rewards'][0]['stock'], 1)

    def test_status_update_does_not_overwrite_stock(self):
        self.ride()
        self.redeem()
        self.s.set_reward_status(self.manager['id'], self.reward['id'], False)
        reward = self.s.state(self.manager['id'])['rewards'][0]
        self.assertEqual((reward['stock'], reward['active']), (1,0))

    def test_sql_special_characters_are_data(self):
        user = self.s.create_user("Ana '); DROP TABLE users; --", 'safe@example.test', self.password)
        self.assertIn('DROP TABLE', self.s.state(user['id'])['user']['name'])
        self.assertEqual(self.s.state(self.student['id'])['user']['name'], 'Ana')


if __name__ == '__main__':
    unittest.main()
