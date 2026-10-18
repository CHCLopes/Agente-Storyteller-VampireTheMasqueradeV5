---
goal: Preparar observação SYSTEM-only de progressão narrativa na entrada B retida
version: 1
date_created: 2026-09-10
last_updated: 2026-09-10
owner: Agente Storyteller
status: 'Completed'
tags: [evaluation, narrative-source, prompt, synthetic]
---

# Preparação de progressão narrativa

O lote e9689855 foi encerrado com duas chamadas, duas admissões e dois replays.
A primeira fonte chegou inteira ao segundo USER, mas a segunda resposta repetiu
o ambiente sem novo acontecimento. Essa observação motiva a hipótese abaixo;
não altera o resultado operacional, o gate ou a fonte histórica.

## 1. Hipótese e critérios anteriores ao envio

Uma instrução SYSTEM adicional para desenvolver um elemento do ambiente em uma
mudança observável pode produzir continuidade com avanço, preservando agência,
elenco/local, incertezas e ausência de efeitos mecânicos inventados.

- Critério narrativo principal: o segundo turno mostra um acontecimento novo
  observável, ligado a um elemento anterior, que oferece algo novo a perceber
  ou escolher; mera repetição ou comentário sobre o tempo não satisfaz.
- Critérios de preservação: nenhuma ação/emoção/fala imposta ao jogador; nenhuma
  troca de local/elenco; nenhuma resolução mecânica inventada; nenhuma incerteza
  resolvida sem novo suporte; q aberta e legível. Avaliação autorada separada.
- Critérios técnicos: os mesmos gates do perfil, dois commits/replays e fonte
  anterior integral. Rejeição técnica interrompe a cadeia; sucesso técnico não
  implica satisfação do critério narrativo.
- O SYSTEM é o fator configurado alterado. Em lotes separados também variam
  IDs/tempos; o segundo USER depende da primeira resposta de cada lote. Não é
  A/B causal nem comparação com entrada dinâmica idêntica.

## 2. Escopo e limites

- Novo prompt narrative-source-progress-v1 preserva integralmente o SYSTEM
  anterior e acrescenta um único parágrafo. Não alterar prompt/perfil anteriores.
- Preservar Galeria, mesmas ações observar/aguardar, estado/relacionamentos
  vazios, coordenador/contratos/gates/schema, alvo/modelo Groq/Qwen do manifesto,
  construção USER e parâmetros. Sem novo produtor, RNG, API/UI/default/save.
- Novo avaliador e wrapper copiados de forma controlada da preparação verificada,
  com diferenças limitadas ao prompt e à identidade/isolamento do experimento.
  A comparação de código deve demonstrar ausência de mudança comportamental
  nos controles. Nenhum refactor do executor histórico ou monkeypatch de runtime.
- Lote/diretório/variável privada novos; sem importar resposta antiga como controle.
- Até 2 chamadas dependentes, 768 tokens cada, total 1536, temperatura 0.65,
  reasoning none, espera inicial 60 s, intervalo mínimo 60 s, deadline 60 s.
- Primeira falha encerra; sem diagnóstico, retry, reparo, fallback ou baseline.
- Não criar gate semântico novo, relaxar política, aprovar CAP-001 ou runtime.
- Toda preparação e verificação offline antecede a entrada protegida da chave.

## 3. Implementação e verificação

| Tarefa | Entrega | Concluída |
|---|---|---|
| TASK-001 | Novo prompt e plano; preservar hashes históricos e registrar leitura do lote e9689855. | Sim |
| TASK-002 | Novo scripts/evaluate_progressing_source.py e tests/test_progressing_source_probe.py; prova de isolamento do SYSTEM e comportamento herdado. | Sim |
| TASK-003 | Novo scripts/run_groq_progressing_source_probe.ps1 e tests/test_progressing_source_probe_wrapper.py; preflight protegido e isolamento de chave/lote. | Sim |
| TASK-004 | Revisão, testes focados, preflight real sem chave, relatório de preparação e atualização da retomada. | Sim |

Verificações: diferenças fechadas entre os executáveis; primeiro template sem
SYSTEM idêntico; segundo USER idêntico quando as mesmas fontes/IDs são fornecidas;
composição do prompt preservada; cadeia/replay, limites, recusa e verificador
continuam funcionando com HTTPX MockTransport e SQLite temporário; wrapper
mantém seus controles de segredo/interrupção. Artefatos históricos só leitura.

## 4. Arquivos

Novos: evals/narrator/prompts/narrative-source-progress-v1.md;
scripts/evaluate_progressing_source.py; scripts/run_groq_progressing_source_probe.ps1;
tests/test_progressing_source_probe.py; tests/test_progressing_source_probe_wrapper.py;
evals/narrator/reports/retained-source-observation-e9689855-2026-09-10.md/json;
evals/narrator/reports/progressing-source-preparation-2026-09-10.md/json.
Estado: este plano e topo de PROMPT_RETOMADA_2026-09-06.md.

## 5. Limites da conclusão

Uma observação nova pode falhar ou continuar repetitiva. Não elevar taxa repetindo
o mesmo lote. O perfil segue restrito à cena conhecida e fonte atribuída; evolução
canônica de campanha, abertura, NPCs e produtor anterior ao RNG são etapas distintas.

Fechamento: preparação concluída com 77 testes distintos em duas rodadas focadas e
preflight real offline com saída 0. Observação live da variante ainda não executada.
