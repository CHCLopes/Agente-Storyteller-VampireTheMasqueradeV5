# Correção de interesse hipotético — 11/09/2026

**Concluída e revisada: 1.097 testes finais aprovados**, zero falhas, erros ou skips,
em 23,32 segundos. São 48 casos novos e 1.049 regressões relacionadas, em 21 arquivos.
O aviso preexistente de python_multipart permanece sem falha associada.

O detector tratava a fala condicional “se houver algo específico que você procura,
talvez seja melhor seguir o índice” como busca e deslocamento executados. A causa
foi reproduzida no validador real; 16 diagnósticos/ablações locais separaram os dois
verbos, as aspas e as explicações causais. O teste literal falhou antes do ajuste.

O diff adiciona somente 17 linhas em api/scene_director_service.py. Uma expressão
delimitada reconhece o interesse hipotético ligado à recomendação modal; só os
verbos procura/seguir recebem espaços no texto auxiliar de análise. O texto n/q,
sujeitos, posições, pontuação e autorizações da declaração original ficam intactos.
Não há regra especial por modelo, dispensa geral de aspas ou de cláusulas inteiras.

As contraprovas preservam recusas de ações anteriores/posteriores, coordenação,
coerção, aliases, afirmações diretas, formas não equivalentes, segredos, material
interno, emoções impostas e limite de 150 palavras. O ator NPC ainda pode agir.
Revisão independente encerrada sem bloqueadores antes da suíte conjunta; hashes
dos 22 arquivos verificados permaneceram estáveis durante essa execução.

O lote 61b83a2f permanece encerrado com código 1 e nenhum candidato qualificado.
A correção é prospectiva e não preenche seus cinco skips, refaz inferências ou
reclassifica sua recusa. Summary, JSONL, bancos e snapshot da versão antiga foram
preservados. Só scene_director_service.py difere entre os 29 arquivos de implementação
do preflight antigo; os demais continuam idênticos. Nenhuma chamada real adicional.

Há uma limitação preexistente registrada somente por inspeção: certas famílias de
ação ainda são extraídas do input integral, incluindo citações. Este ajuste não
modifica essa leitura nem demonstra que toda citação de input seja inerte. Uma
expectativa do primeiro rascunho, não executada, extrapolava esse comportamento;
foi substituída por prova de ausência de novas autorizações com a entrada original.
Não é um defeito introduzido pelo diff nem foi corrigido neste escopo.

Checkpoint: `eval-results/checkpoints/hypothetical-interest-fix-20260911/`, com o
teste vermelho literal, 48 casos novos, suíte final, diagnóstico, diff e versões
antes/depois. JSON lista hashes e resultados. Próximo trabalho independente:
seleção local B inativa prevista no plano de transporte, sem montar rota/handler/UI.
