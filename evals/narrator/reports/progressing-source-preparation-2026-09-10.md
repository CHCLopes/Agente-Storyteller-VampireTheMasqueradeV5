# Preparação da variante de progressão — 10/09/2026

Preparação concluída; **nenhuma chamada real desta variante foi feita**.
O lote anterior demonstrou transporte integral e dois turnos admitidos, mas sua
segunda narrativa quase repetiu a primeira. [Leitura e evidência preservada](retained-source-observation-e9689855-2026-09-10.md).

## Mudança e critérios

`narrative-source-progress-v1` mantém todos os parágrafos anteriores e acrescenta
um: desenvolver um elemento da cena em acontecimento observável, deixando a
reação do jogador livre. Preserva causas desconhecidas e incertezas sem suporte.
O novo texto também evita explicar as restrições de interação na própria prosa.

O critério principal é haver, no segundo turno, um acontecimento identificável
ligado a elemento anterior, com algo novo a perceber ou escolher. Repetição e
comentário sobre a passagem do tempo não bastam. Agência, local/elenco, mecânica
e incertezas continuam critérios de preservação. Essa revisão é autorada e
separada dos gates técnicos; nenhum gate foi acrescentado ou relaxado.

## Provas offline

- **77 testes distintos passaram em duas rodadas focadas**: 40 do avaliador
  (97,35 s na saída pytest) e 37 do lançador (148,98 s); zero falhas, erros ou skips.
  Não houve repetição final de suítes verdes. Aviso preexistente de python_multipart.
- Cinco controles novos verificam diferenças fechadas no código, preservação do
  prompt e igualdade do pedido fora do SYSTEM, inclusive no segundo USER com
  as mesmas fontes e identidades. Os 72 controles herdados foram exercitados nos
  novos arquivos, com rede bloqueada e SQLite temporário.
- Revisão independente encerrada sem bloqueador. Avaliador: oito substituições
  de prompt/identidade/isolamento. Lançador: três substituições de nomes.
  Algoritmos, contratos, gates, parâmetros e construção USER permanecem iguais.
- Preflight real `-PreflightOnly` terminou com saída 0, lote `52d34b4a-924b-47e8-921f-8f94d1fd5626`,
  sem chave e sem diretório de execução. O lote live será outro UUID.
- Arquivos da aplicação, executáveis anteriores e artefatos da Galeria preservados.

## Próxima observação

Mesmo cenário Galeria, mesmas ações observar/aguardar, modelo
`qwen/qwen3.8-27b` em Groq direto, mesmo schema e alvo do manifesto.
Até duas chamadas dependentes, 768 tokens cada, total 1536, temperatura 0.65,
reasoning none; espera inicial e intervalo mínimo de 60 s, prazo de 60 s por
chamada. Primeira falha interrompe. Sem diagnóstico, retry, reparo ou fallback.

```powershell
pwsh -NoProfile -File "C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_progressing_source_probe.ps1"
```

A chave é inserida somente no prompt protegido do lançador; não recuperar chave
de .env, variáveis existentes ou processo do jogo. O wrapper usa variável privada
e ambiente isolado; suas rotinas de limpeza não garantem finally após encerramento
forçado pelo sistema operacional.

O SYSTEM é o fator configurado alterado. IDs e tempos variam entre lotes, e o
segundo USER depende da primeira resposta gerada. Não importar o lote anterior
como controle nem alegar A/B causal. Qualidade continua desconhecida até observar.
Sem ativação no produto, mudança de save/default ou aprovação CAP-001.

[Plano e critérios anteriores ao envio](../../../plan/feature-progressing-source-observation-1.md).
[Hashes, preflight e evidência estruturada](progressing-source-preparation-2026-09-10.json).

## Janela de observação preparada

Lote `19b93f22-a4da-408d-992f-2c1dd42213b0`, processo próprio `7500`.
Snapshot em `2026-09-11T00:10:38.4356924Z`: `awaiting_secure_credential`.
A chave depende da entrada direta do usuário no prompt protegido. Antes de abrir
outra janela, conferir `C:\Users\skate\AppData\Local\Temp\storyteller-progressing-source-window-19b93f22-a4da-408d-992f-2c1dd42213b0\lifecycle.json`; não duplicar o lote.
Esse registro descreve o lançamento, não um resultado ao vivo.
