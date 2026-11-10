# Bike Energy — UPX III

A **versão Simplificada** é a versão atual para demonstração. O aluno registra um treino simulado, recebe pontos e troca o saldo por benefícios. O gestor configura bicicletas e benefícios e confirma a retirada.

## Como executar no Windows

1. Baixe o código ou clone o repositório. Se usar o ZIP do GitHub, extraia os arquivos.
2. Com o Python 3 instalado, abra `INICIAR.bat` ou rode `py -3 server.py` na pasta do projeto.
3. Acesse `http://127.0.0.1:8765` e mantenha o terminal aberto.
4. Abra `ACESSOS_DEMO.txt`, criado na primeira execução, para ver os acessos de aluno e gestor. Os botões da tela de login preenchem o e-mail.

Use o servidor Python para executar o sistema. A extensão Go Live exibe somente a interface e não executa a API. O SQLite grava os registros em `bike_energy.db`. O banco e os acessos gerados são locais.

## Demonstração

Entre como Camila e registre um treino de 80 W por 45 minutos. Na regra inicial, a sessão gera 0,060 kWh e 60 pontos. Somados aos 40 pontos de exemplo, permitem resgatar a bebida esportiva. Entre como gestor para confirmar a retirada e volte ao perfil de aluno para consultar o status.

A interface usa HTML, CSS e JavaScript. O navegador envia requisições HTTP a `server.py`, que valida as operações e consulta ou atualiza o SQLite. A potência é simulada e os pontos são usados para resgatar benefícios, sem equivalência direta em dinheiro.

## Histórico

`app.py`, `energy/`, `static/`, `VER_BANCO.bat` e os documentos e testes da v4 foram preservados como referência. A versão atual usa `server.py`, `index.html`, `style.css` e `app.js` na raiz. O banco da v4 usa outro esquema.

[Acompanhar o projeto no Trello](https://trello.com/b/3DIoUsvE/bike-energy-upx-iii)
