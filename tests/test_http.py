import http.client
import json
import secrets
from scratch import ScratchDirectory
import threading
import unittest
from pathlib import Path
from energy.service import Service
from energy.http import make_server


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = ScratchDirectory()
        cls.service = Service(Path(cls.temp.name)/'http.sqlite3')
        cls.password = secrets.token_urlsafe(12)
        cls.service.create_user('Aluna Teste', 'aluna@example.test', cls.password)
        cls.server = make_server(cls.service, 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, method, path, data=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        body = json.dumps(data) if data is not None else None
        base = {'Origin': f'http://127.0.0.1:{self.port}', 'Content-Type': 'application/json'}
        base.update(headers or {})
        connection.request(method, path, body, base)
        result = connection.getresponse()
        content = result.read()
        response = result.status, dict(result.getheaders()), content
        connection.close()
        return response

    def login(self):
        status, headers, body = self.request('POST', '/api/login', {'email':'aluna@example.test', 'password':self.password})
        self.assertEqual(status, 200)
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        return headers['Set-Cookie'].split(';')[0]

    def test_real_login_state_logout(self):
        cookie = self.login()
        self.assertEqual(self.request('GET','/api/state',headers={'Cookie':cookie})[0], 200)
        self.request('POST','/api/logout',{}, {'Cookie':cookie})
        self.assertEqual(self.request('GET','/api/state',headers={'Cookie':cookie})[0], 401)

    def test_student_cannot_escalate_role_or_edit_bike(self):
        cookie = self.login()
        self.assertEqual(self.request('POST','/api/bikes',{'name':'X','active':True},{'Cookie':cookie})[0],403)
        status, _, content = self.request('POST','/api/register',{'name':'Outro','email':'other@example.test','password':self.password,'role':'gestor'})
        self.assertEqual(status, 201)
        self.assertEqual(json.loads(content)['role'], 'aluno')

    def test_csrf_foreign_host_and_static_allowlist(self):
        self.assertEqual(self.request('POST','/api/login',{}, {'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.request('GET','/',headers={'Host':'evil.example'})[0],403)
        for path in ['/data/bike_energy.sqlite3','/../app.py','/energy/service.py']:
            self.assertEqual(self.request('GET',path)[0],404)

    def test_invalid_body_is_controlled(self):
        self.assertEqual(self.request('POST','/api/login',[])[0],400)
        self.assertEqual(self.request('POST','/api/login',{'x':'a'*20000})[0],413)

    def test_static_headers(self):
        status, headers, body = self.request('GET','/')
        self.assertEqual(status,200)
        self.assertIn('Bike Energy',body.decode())
        self.assertIn("default-src 'self'",headers['Content-Security-Policy'])
