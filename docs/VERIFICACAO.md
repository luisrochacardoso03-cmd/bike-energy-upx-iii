# Verificação — 19/10/2026

Windows, Python 3.15.0: `py -3 -m unittest discover -s tests -v` — **24 testes, OK**, 9,139 segundos. Node 24.22: `node tests/test_browser_logic.cjs` — **1 teste, PASS**. Nenhum pacote externo instalado.

Exercitados: cadastro/login, duplicidade, isolamento de perfis, permissões, entradas inválidas, bicicletas/benefícios inativos, cálculo/arredondamento do v3, regra sem alterar passado, metas, relatório, saldo insuficiente, estoque, concorrência, idempotência, histórico do benefício, retirada/reversão, HTTP, origem/host e arquivos públicos.

Um teste inicia servidor real, cadastra aluno, registra sessão, resgata e confirma retirada; encerra o processo, abre outro com o mesmo SQLite e compara registros, saldo e status. Os bancos de teste são isolados.

## Chrome

Executados com dados fictícios: login aluno, nova sessão, consulta, resgate, saída, login gestor, confirmação, atualização da página, retorno para pendente e nova confirmação. Status final observado: Retirado. Consulta de console após o fluxo não retornou erros. O usuário aceitou a confirmação nativa do resgate, pois a ferramenta perdeu acesso enquanto o diálogo estava aberto.

## Revisão e correções

Revisão independente de código encontrou três problemas corrigidos com regressões:

- Repetição após gravar com sucesso e falhar a consulta: manter a chave de idempotência até concluir a consulta.
- Edição de situação com estoque antigo: separar atualização de situação e proteger edição completa com versão.
- Inicialização interrompida: transação única e teste de falha/reexecução para evitar dados parciais.

Também inspecionada a tela do gestor em resolução 390 × 844: página sem transbordamento horizontal global (375 px úteis), navegação adaptada e tabela com rolagem interna. A resolução original foi restaurada.

## Slides

13 slides renderizados e inspecionados individualmente. Validadores de integridade, geometria, fonte Arial, títulos de gráficos e aritmética de tabelas executados diretamente: zero achados. Reimportação no Artifact Tool confirmou 13 slides. O finalizador automático não conseguiu iniciar o Python a partir do Node neste ambiente (EPERM); as verificações foram executadas separadamente e o arquivo validado foi copiado sem alteração.

## Limites

Verificação local, sem certificação de produção, carga massiva, hardware ou todos os navegadores. Treze slides renderizados e inspecionados; Microsoft PowerPoint nativo não testado. Foto só após a apresentação. O código-fonte foi preparado para publicação no GitHub e o Trello atualizado em 19/10/2026.
