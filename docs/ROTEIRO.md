# Apresentação de 20/10/2026

Extraia o programa, execute INICIAR.bat e abra http://127.0.0.1:8040. Confira os acessos em data/ACESSOS_DEMO.txt sem projetar as senhas. Tenha os slides e este roteiro offline.

## Demonstração ao vivo — aproximadamente 7 minutos

1. Cadastre um aluno fictício com e-mail novo e senha de pelo menos oito caracteres. Entre. Explique a gravação no SQLite.
   Em outra janela, abra `VER_BANCO.bat` e mostre a consulta SQL `SELECT id, name, email, role FROM users`. O aluno recém-cadastrado deve aparecer. Não projete `ACESSOS_DEMO.txt`.
2. Em Nova sessão, escolha bicicleta ativa, 150 W e 60 minutos. Finalize. Mostre 0,150 kWh e 150 pontos com a regra padrão. A duração é simulada, sem esperar uma hora.
3. Consulte Histórico e painel. Edite a meta mensal e mostre o progresso.
4. Resgate Bebida esportiva por 100 pontos e confirme. Mostre saldo de 50 e Aguardando retirada.
   Execute `VER_BANCO.bat` novamente e mostre as seções SESSÕES E PONTOS e RESGATES E RETIRADAS. Depois da confirmação do gestor, repita a consulta para mostrar a mudança do status no SQLite.
5. Saia e entre como gestor. Em Alunos, consulte o novo cadastro. Em Bicicletas, cadastre uma identificação nova e veja a lista.
6. Em Resgates, confirme a retirada do novo aluno. Mostre Retirado. Voltar para pendente corrige o status, sem cancelar o débito.
7. Em Relatórios, consulte um período que inclua hoje e mostre o CSV.
8. Encerre com Ctrl+C, reinicie usando a mesma pasta e atualize o navegador. Consulte o resgate salvo: os dados sobreviveram ao processo.
9. Explique arquitetura e andamento nos slides: navegador → Python → SQLite; 10/12 funcionalidades; ranking/faixas pendentes.

Use uma conta nova para repetir os números acima. Camila inicia com 93 pontos e testes anteriores na mesma pasta alteram o saldo. Para uma demonstração isolada, consulte o comando --data-dir no README.

Mostre os links reais do GitHub/Trello, informando o que está publicado. Registre a foto da equipe em sala no dia 20/10 e insira no último slide. Não apresente dados de navegador como banco, nem energia simulada como medição física.
