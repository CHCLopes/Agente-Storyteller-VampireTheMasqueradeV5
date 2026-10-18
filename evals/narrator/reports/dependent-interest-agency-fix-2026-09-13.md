# Interesse condicional: falso positivo de agência corrigido

O texto GPT-OSS/Oficina do lote 095e7efd foi recusado porque “dependendo do que
você procura” acionou o conceito `inspect`. A expressão qualifica a relevância
dos sinais narrados e não afirma que o jogador já procura algo. O lote histórico
permanece recusado; esta correção vale somente para propostas futuras.

Em `api/scene_director_service.py`, a checagem agora reconhece a construção
terminal `dependendo do que <jogador> procura` e mascara somente `procura` durante
a análise de autoria. O match exige pontuação/fim logo após o verbo. Complemento
como “procura nas bancadas” não recebe exceção; uma ação posterior continua
visível e recusada. A proteção não foi ampliada por modelo, cena ou fala inteira.

O teste de regressão incorpora a narrativa observada e permite local/elenco
parametrizados. Duas contraprovas verificam busca com objeto e ação posterior.
A rodada final combinada executou dez arquivos, com 525 casos distintos aprovados,
zero falhas/skips e três warnings preexistentes. XML SHA
`1db904a8f3c2eb607a60825dafd69261b183071c08f80a68b80650e2b44b65b8`.

Core anterior SHA
`898c7e9134acee08c711196f2ee4230ddf968f767da87d30047a8e6f7aa93953`;
core atual SHA
`30e7635f124698f7e44e52cb586b2470aebfb6415ee2d1f92372991a907e4aa4`.
Teste anterior SHA
`849bc99e60cf9c3b14970693476aae402f11572ad1dfe3d3382fd05516f0a308`;
teste atual SHA
`3a17882d04bfab5fc3857fd9fcbf4c605c1466a90a0cfdac0c40d647ccbd92cd`.

Nenhuma chamada ao provedor, alteração de prompt/corpus/protocolo, banco,
interface, modelo default ou CAP-001 integrou esta correção.
