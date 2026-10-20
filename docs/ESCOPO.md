# Cobertura do escopo original — 19/10/2026

Base: `Bike_Energy_UPX_III_Escopo_Desenvolvimento.pdf`, recuperado da biblioteca da conversa, seções 3.1 e 3.2. Peso igual por funcionalidade, sem contar implementação parcial. Não representa esforço nem garantia de nota.

| # | Funcionalidade | Situação / evidência |
|---|---|---|
| 1 | Cadastro/login e perfis | Concluída: cadastro aluno, login e permissões |
| 2 | Cadastro de bicicletas | Concluída: identificação e ativação/desativação |
| 3 | Sessões com início/fim/duração | Concluída: registro simulado com datas e minutos |
| 4 | Registro/simulação de energia | Concluída: potência e duração calculam kWh persistidos |
| 5 | Histórico individual | Concluída: consulta privada do aluno |
| 6 | Créditos por regra configurável | Concluída: pontos/Wh e histórico preservado |
| 7 | Painel aluno | Concluída: energia do mês, pontos, histórico e benefícios |
| 8 | Painel gestor | Concluída: energia, uso, créditos, bicicletas e alunos |
| 9 | Faixas de energia/benefício | Pendente: taxa simples e catálogo não equivalem a faixas |
| 10 | Ranking mensal | Pendente |
| 11 | Metas pessoais mensais | Concluída: meta editável e progresso por energia mensal |
| 12 | Relatório por período | Concluída: consulta por datas e CSV |

**Essenciais: 8/8. Complementares: 2/4. Total: 10/12 = 83,3%.**

Resgate, estoque, confirmação e reversão de retirada também foram implementados, sem ampliar artificialmente o denominador. Hardware, aplicativo nativo, integração financeira, desafios/notificações e monitoramento real aparecem como futuro no escopo e ficam fora desta medição do MVP.

## Continuidade

| Período | Próxima etapa |
|---|---|
| 20/10 | Demonstração, feedback e foto real da equipe |
| 21/10–02/11 | Validar regras e ajustar fluxo |
| 03/11–16/11 | Ranking mensal e faixas |
| 17/11–30/11 | Testes ampliados, acessibilidade e correções |
| 01/12–14/12 | Documentação, evidências e entrega final |

Janelas baseadas nas sprints originais, com funcionalidades antecipadas. O código da versão local foi preparado para publicação no repositório; o andamento do Trello foi atualizado em 19/10/2026.

## Equipe e fontes

Nomes conferidos no PPTX original e na capa do escopo:

- Ana Clara dos Reis Bauer Cesar — RA252578
- Luís Otavio Rocha Cardoso — RA252730
- Mateo Pinto de Araujo — RA252674
- Nathan Lima Fonseca — RA210407
- Nickolas Alves de Queiroz — RA252547
- Iago Luís de Carvalho Santos — RA252541

Facens, ADS, UPX III, Prof. Rodrigo Diver.

Fontes: `Bike_Energy_MVP_Programa_v3.zip`, `Bike_Energy_Apresentacao_UPX_III.pptx`, PDF do escopo e links verificados https://github.com/luisrochacardoso03-cmd/bike-energy-upx-iii e https://trello.com/b/3DIoUsvE/bike-energy-upx-iii.
