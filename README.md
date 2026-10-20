# Bike Energy — versão local v4

Entrega para 20/10/2026, derivada do MVP v3. Interface em português, servidor Python e banco SQLite persistente em arquivo. Sem hardware, internet, pacotes Python externos ou compilação do frontend.

## Executar no Windows / VS Code

1. Extraia todo o ZIP; não execute de dentro do arquivo compactado.
2. É necessário Python 3.11 ou superior. Testado neste Windows com Python 3.15.
3. Abra `INICIAR.bat` na pasta `bike-energy`. Alternativa no terminal do VS Code: `py -3 app.py`.
4. Mantenha o terminal aberto e acesse **http://127.0.0.1:8040**.
5. Abra `data/ACESSOS_DEMO.txt`: os acessos aluno/gestor e as senhas aleatórias são gerados na primeira execução.

Ctrl+C encerra o servidor. Os dados permanecem em `data/bike_energy.sqlite3`. Se a porta estiver ocupada, encerre a outra instância ou use `py -3 app.py --port 8041` e acesse essa porta.

O HTML isolado não executa o sistema. O navegador consulta a API; não guarda registros de negócio no localStorage.

## Mostrar o banco de dados na apresentação

Com o site aberto, dê dois cliques em `VER_BANCO.bat`. Ele executa consultas SQL em modo somente leitura e mostra alunos, bicicletas, sessões, energia, pontos, benefícios e resgates salvos no arquivo `data/bike_energy.sqlite3`. Senhas e tokens não aparecem. O mesmo comando no terminal do VS Code é `py -3 ver_banco.py`. Após cadastrar um aluno ou concluir uma sessão no site, execute novamente para mostrar o novo registro. A tela **Gestor → Alunos/Resgates/Relatórios** também consulta esse mesmo banco.

## Funcionalidades e demonstração

A primeira execução cria dados fictícios: gestor Marcos, aluna Camila, três bicicletas (duas ativas), três benefícios e duas sessões da aluna, totalizando 93 pontos.

- Aluno: cadastro, login, painel, meta mensal, simulação, histórico, benefícios e acompanhamento da retirada.
- Gestor: indicadores, bicicletas, catálogo/estoque, alunos, regra de pontos, resgates, confirmação/reversão de retirada e relatório por período com CSV.
- Regra inicial: 1 ponto por Wh. 150 W durante 60 minutos = 0,150 kWh = 150 pontos.
- A simulação registra início/fim calculados pela duração informada; não exige esperar o treino e não mede energia real.
- Voltar para pendente corrige a entrega: não cancela o resgate nem devolve pontos/estoque.

Leia `docs/ROTEIRO.md`, `docs/ARQUITETURA.md`, `docs/ESCOPO.md` e `docs/VERIFICACAO.md` para apresentar o projeto.

## Testes e dados

Execute `py -3 -m unittest discover -s tests -v`. O teste JavaScript opcional usa `node tests/test_browser_logic.cjs`; Node não é necessário para usar o sistema. Os testes criam bancos isolados. No PowerShell, a variável `BIKE_TEST_ROOT` permite escolher uma pasta temporária.

Para backup, encerre o servidor e copie a pasta `data` para um local privado. Para restaurar, preserve uma cópia dos dados atuais antes de substituir a pasta, com o servidor parado. Não apague o banco para reiniciar o programa. Outra demonstração independente: `py -3 app.py --data-dir data-outra-demo --port 8041`.

Não publique dados ou senhas; o `.gitignore` exclui `data`. MVP destinado à execução local, sem servidor de produção, recuperação de senha, hardware ou integração financeira.

GitHub: https://github.com/luisrochacardoso03-cmd/bike-energy-upx-iii

Trello: https://trello.com/b/3DIoUsvE/bike-energy-upx-iii

O código-fonte desta versão está no repositório indicado acima. Para executar, baixe ou clone o repositório; os dados de cada instalação são gerados localmente na primeira execução. O andamento do Trello foi atualizado em 19/10/2026.
