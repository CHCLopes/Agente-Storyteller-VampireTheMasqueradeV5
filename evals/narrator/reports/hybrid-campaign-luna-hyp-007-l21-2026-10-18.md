# HYP-007-L21 — aviso R-03 não reconhecido lexicalmente

Data: 18/10/2026. Batch afc50a96-706c-4f44-ba6b-f8fcf2a2858f.
Luna low/v5, até 17 chamadas/USD 0,15 estimados autorizados; sem retry/fallback.

## Observado

Três chamadas/dois turnos concluídos. CAMP-EVAL-01 completo, registro intacto,
q terminal vazio. Parada campaign_source_policy_failed no primeiro R-03 de
CAMP-EVAL-02. Demais percursos não alcançados. Nenhum narrador admitido.
Geração das respostas: 3.440/4.131/3.054 ms; duração dos turnos: 3.581/4.475/3.171 ms.
Sem HTTP 429 neste lote; não comprova disponibilidade futura do provedor.

Custo final estimado USD 0,0022768, não cobrança confirmada. 7.934 tokens de
entrada/575 saída, três chamadas precificadas, zero sem usage; reporter --settled
reproduzido. Não inclui ajustes de cache, tarifas ou impostos.

Diretório: eval-results/hybrid-campaign-luna-l21-afc50a96-706c-4f44-ba6b-f8fcf2a2858f/.

- records.jsonl SHA256: 47cfdad1e3f6389f378a4f07e5e965c49f55d4ca5d2972c1d68b61b9e04a2e4e
- summary.json SHA256: a90468d3dbc6205bca0bd3ca490d99428d0e73d70c761f9f7acda614efe1e48e
- Manifesto fechado SHA256: aa316ad04169198727c8ed6ffdf332b7b4bc03c0aa3dad3b314f570b7007e552

## Reprodução e correção

Validação genérica de agência aceitou a resposta exata. _realizes_rule rejeitou
R-03 por ausência de avisa/alerta/risco/aproxima, embora a resposta afirme
“a ameaça agora é evidente”, preserve registro seco e apresente aviso direto
de Mara. Duas regressões falharam antes da correção (equivalência/commit).
Adicionada somente a expressão normalizada a ameaca agora e evidente ao grupo
de aviso R-03 em api/campaign_source_profile.py. Não generalizar para toda ameaça
ou alterar prompt/cânone. O verificador continua lexical, não prova semântica geral.

Oito testes novos: equivalência exata, negação/ausência da ameaça, dano antecipado,
negação do aviso, ausência de Mara e dois casos integrados seguros/inseguros.
39 focados aprovados/um aviso preexistente python_multipart; XML
eval-results/hyp-007-l21-correction-2026-10-18.xml. Commit/rejeição atômica,
reinício/replay sem nova geração/RNG verificados. Resposta live não reclassificada.

## Fechamento e próximo checkpoint

Gate paid/live L21 fechado, trava e artefatos preservados. Sem retry ou chamadas
adicionais. L20 já aceito por Prossiga. TASK-013/CAMP-24/MVP abertos.
L22 separado/fechado, mesmo v5/alvo/limites; 22 hashes válidos, 17 sintéticos/
zero chamadas ao provedor, payload máximo 13.952 bytes e AST válido.
30 testes focados de preparação/integração aprovados/um aviso preexistente; XML
eval-results/hyp-007-l22-readiness-2026-10-18.xml.
Suíte integral não repetida: alteração lexical unitária, cobertura focada de
contradições/integração; não declarar ausência de falhas fora dessa cobertura.

Proposta delimitada: aceitar L21 inconclusivo para campanha integral, um percurso
completo, e autorizar L22 até 17 chamadas/USD 0,15 estimados adicionais, Luna low,
mesmo v5/768 tokens/20.000 bytes/60s, sem retry/fallback/admissão. Continue/prossiga
aprova ambos. Até lá L22 fechado, sem terminal/chave/inferência. Não transferir
slots ou orçamento não consumidos de L21. Nenhum narrador admitido.
