import http.client
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from scratch import ScratchDirectory


class ProcessPersistenceTests(unittest.TestCase):
    def test_register_ride_redeem_pickup_survive_server_restart(self):
        root = Path(__file__).resolve().parents[1]
        with ScratchDirectory() as folder:
            with socket.socket() as available:
                available.bind(('127.0.0.1', 0))
                port = available.getsockname()[1]
            def request(method, path, body=None, cookie=''):
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
                headers = {'Origin':f'http://127.0.0.1:{port}','Content-Type':'application/json','Cookie':cookie}
                connection.request(method,path,json.dumps(body) if body is not None else None,headers)
                response=connection.getresponse()
                data=json.loads(response.read())
                headers=dict(response.getheaders())
                self.assertLess(response.status,400,data)
                connection.close()
                return data,headers
            def launch():
                process=subprocess.Popen([sys.executable,str(root/'app.py'),'--port',str(port),'--data-dir',folder],
                    cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                try:
                    for _ in range(100):
                        if process.poll() is not None:
                            self.fail('Servidor encerrou durante inicialização')
                        try:
                            request('GET','/api/health')
                            return process
                        except (OSError,http.client.HTTPException):
                            time.sleep(0.05)
                    self.fail('Servidor não iniciou em 5 segundos')
                except BaseException:
                    process.terminate();process.wait(timeout=5)
                    raise
            process=launch()
            try:
                password=secrets.token_urlsafe(12)
                request('POST','/api/register',{'name':'Aluno da apresentação','email':'novo@example.test','password':password})
                _,headers=request('POST','/api/login',{'email':'novo@example.test','password':password})
                cookie=headers['Set-Cookie'].split(';')[0]
                request('POST','/api/rides',{'bike_id':1,'watts':150,'minutes':60,'request_id':secrets.token_hex(16)},cookie)
                redemption,_=request('POST','/api/redemptions',{'reward_id':1,'request_id':secrets.token_hex(16)},cookie)
                lines=(Path(folder)/'ACESSOS_DEMO.txt').read_text(encoding='utf-8').splitlines()
                manager_password=next(line.removeprefix('Senha: ') for line in lines if line.startswith('Senha: '))
                _,headers=request('POST','/api/login',{'email':'gestor@bike.local','password':manager_password})
                manager_cookie=headers['Set-Cookie'].split(';')[0]
                request('POST','/api/pickup',{'id':redemption['id'],'collected':True},manager_cookie)
                before,_=request('GET','/api/state',cookie=cookie)
                process.terminate();process.wait(timeout=5)
                process=launch()
                after,_=request('GET','/api/state',cookie=cookie)
                self.assertEqual(after,before)
                self.assertEqual(after['summary']['balance'],50)
                self.assertEqual(after['redemptions'][0]['status'],'collected')
                self.assertEqual(len(after['rides']),1)
            finally:
                process.terminate();process.wait(timeout=5)
