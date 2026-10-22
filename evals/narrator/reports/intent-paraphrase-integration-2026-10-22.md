# Opção E — integração exata das seis paráfrases no A2

Data: 22/10/2026. Resultado: escopo técnico concluído; aguardar as resoluções
humanas do brainstorm em outro chat. Não é aceite de produto ou de arquitetura.

## Autorização e hipótese

Humano delegou a opção mais recomendada de E/F, a conclusão da bateria, o registro
e o push, seguidos de espera por suas instruções do brainstorm. E era a opção
recomendada: conectar as seis strings exatas do catálogo C ao executor A2 existente.
Protocolo prospectivo registrado em
`plan/proposal-intent-paraphrase-integration-2026-10-22.md` antes dos testes.

Hipótese testada: cada frase admitida produz o efeito de sua intenção canônica,
conservando replay/retomada e recusando os seis controles C sem avanço.

## Implementação delimitada

- `scripts/run_expression_selection_browser_trial.py`: flag opt-in
  `--exact-paraphrases` e parâmetro `create_app(..., exact_paraphrases=True)`.
  O modo anterior permanece padrão e foi incluído na regressão.
- `api/experiments/intent_paraphrase_boundary.py`: correspondência exata e recibo
  persistido com sessão, operação, texto original, frase canônica e versão C.
- Banco A2 novo e exclusivo; recibos em arquivo companheiro
  `<db>.paraphrases.sqlite3`, validado por application_id e tabela própria.
  Nenhuma migração do banco A2 congelado ou do produto.
- Recibo precede claim/preparação do A2. O núcleo recebe a frase canônica;
  histórico e ação pendente exibem o texto original após validar sua correspondência.
  O mesmo ID não aceita outra frase, inclusive outra frase da mesma intenção.
- Sem comparação aproximada, normalização ou remoção de espaços no modo E.
  Armazenamento local do navegador usa chaves próprias para esse modo.

| Texto exato | Intenção | Entrada encaminhada ao A2 |
|---|---|---|
| Quero saber qual é a tarefa. | task | Como posso ajudar? |
| Mara, o que eu posso fazer para ajudar? | task | Como posso ajudar? |
| Fico esperando. | wait | Aguardo |
| Vou retirar o registro da bancada. | rescue | Retiro o registro |
| Analiso o registro. | inspect | Examino o registro |
| Não participarei do resgate. | withdraw | Desisto |

E aceita SOMENTE essas seis entradas. As frases canônicas são encaminhamento
interno e referência de comparação em outra sessão baseline. Isso evita adicionar
uma união implícita de reconhecedores: o controle C `Digo a Mara: "Leve o registro".`
é recusado em E, embora a baseline o reconheça legitimamente como pedido de ajuda.
O resultado C não demonstrava que a baseline executava um resgate por essa frase.

## Evidência dos testes

Primeira execução focada: **39 passaram**, zero falhas/erros/skips. São 32 casos
parametrizados novos E e sete do harness anterior. Regressão conjunta posterior:
**245 passaram**, zero falhas/erros/skips, em 72,75 s reportados pelo pytest.
Essa regressão contém os mesmos 39; não somar as contagens como testes distintos.
Inclui os 213 casos da bateria anterior e os 32 novos E.

Cobertura observada:

- Seis pares paráfrase/canônica comparados em sessões independentes: mesmo estado,
  regra, efeitos, texto e resolução mecânica. Investigação usa resultado simulado
  fixo de sucesso e falha; cada execução nova inspeciona uma vez, replay não rola.
- Seis controles C recusados: negação, fala dirigida a outro ator, ação composta,
  frase sem pontuação aprovada, método novo e injeção de cânone. Turno/histórico,
  operações A2 e recibos permanecem sem alteração nesses casos.
- Espaço inicial/final e alteração de maiúsculas recusados; nenhuma ampliação
  silenciosa do catálogo pela interface.
- Quatro desfechos conservados: preservado, parcial, perdido e abandonado; ação
  nova após encerramento recusada sem alterar o resultado.
- Reload via GET, nova instância do aplicativo, replay e retomada explícita
  conservam texto original, preparação e seleção; não refazem decisão/rolagem.
- Interrupção entre recibo e claim é recuperável; falha na preparação não permite
  rolar outra vez com o mesmo ID. Recibo ausente ou corrompido é recusado.
- Reuso de ID com outra frase é recusado, mesmo que a intenção seja igual;
  sessões distintas permanecem isoladas.
- Sem token, origem externa ou host externo: recusados. Sessão ausente: 404.
- Regressão anterior de persistência, A1/A2, seleção, parser e isolamento passou.

Rede externa permanece bloqueada pelo conftest. Pares E também bloqueiam a
construção de request de seleção; o modo é determinístico. **Zero chamadas a
provedor; custo de inferência USD 0.** Sem leitura de chave ou `.env`.
Aviso preexistente: `PendingDeprecationWarning` recomenda `python_multipart`.
Nenhuma dependência alterada.

XMLs locais (ignorados no Git; totais e hashes publicados neste relatório):

| Artefato | Testes | SHA-256 |
|---|---:|---|
| eval-results/intent-paraphrase-integration-focused-2026-10-22.xml | 39 | 8563833edc76a1797b57dd70adcaa613dd6911633fd1e233484b9f0a5e7343ed |
| eval-results/intent-paraphrase-integration-regression-2026-10-22.xml | 245 | 04d730387137347354ebd63bd1e8fcf7655fa3458156c459907910b47559224a |

Reprodução focada na raiz do worktree:

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
& .\.venv\Scripts\python.exe -m pytest -q -x tests/test_intent_paraphrase_integration.py tests/test_expression_selection_browser_trial.py
```

Regressão selecionada:

```powershell
$env:STORYTELLER_DISABLE_DOTENV = '1'
& .\.venv\Scripts\python.exe -m pytest -q -x tests/test_campaign_expression_l84.py tests/test_campaign_expression_l85.py tests/test_campaign_expression_persistence.py tests/test_campaign_expression_v2.py tests/test_campaign_source_offline_trial.py tests/test_expression_selection_browser_trial.py tests/test_expression_selection_experiment.py tests/test_expression_selection_l86.py tests/test_expression_selection_spike.py tests/test_intent_interpretation_offline.py tests/test_intent_paraphrase_admission_offline.py tests/test_intent_paraphrase_integration.py
```

## Preservação e limites

Verificador `scripts.evaluate_hybrid_campaign_luna_l86_live.gate()` confirmou
**32 hashes de fontes congeladas intactos**. Gates de custo e inferência
permanecem false/false; nenhum lote real ou nova credencial foi aberto.

API e persistência foram exercitadas por FastAPI TestClient; HTML foi inspecionado
pelos testes. Não houve nova observação visual em navegador nem reinício do
servidor que já estivesse aberto. O reload/restart referido acima é automatizado
via API/nova instância do aplicativo. Não é teste completo de navegador E.
Esta é regressão selecionada, não toda a suíte do repositório.

Recibo e operação A2 ficam em dois bancos: recibo pode ficar sem operação se a
preparação for recusada/interrompida. Ele não avança a cena. Bancos devem ser
preservados juntos; ausência de recibo causa recusa, não reconstrução especulativa.
Validação protege vínculos e catálogo no armazenamento local confiável, sem
alegar prova contra adulteração coordenada de ambos os arquivos.

Catálogo fechado não demonstra interpretação livre, improvisação nem qualidade
de modelo. CAMP-13..16 e CAMP-24 continuam abertos; nenhuma adoção de Jev,
utilidade, GOAP, nova personalidade, geometria de cena ou cânone do brainstorm.

## Transferência e parada solicitada

Texto integral do brainstorm em
`docs/handoffs/brainstorm-npc-decision-narrator-2026-10-22.md`, com a pergunta
aberta e aviso de que os detalhes da cena são exemplos, não cânone aprovado.
Atualizar checkpoint, publicar arquivos relacionados na branch de implementação,
confirmar SHA remoto e aguardar o humano voltar com resoluções e instruções.
Não iniciar nova bateria, integração ao produto ou desenvolvimento do brainstorm.
