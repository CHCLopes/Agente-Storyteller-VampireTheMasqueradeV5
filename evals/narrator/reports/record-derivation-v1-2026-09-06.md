# Derivação de registros v1 — preparação verificada

Data documental: 06/09/2026. Autorização: o usuário aprovou explicitamente o
desenho de [derivação isolada](record-derivation-hypothesis-bb98ae1e-2026-09-06.md)
com “Autorizado. Prossiga”. A preparação local está concluída; a execução real
depende somente de chave inserida no prompt protegido. Nenhuma chamada real
foi feita durante esta preparação.

## Pergunta e limites

Avaliar se o mesmo candidato consegue derivar registros fiéis quando a narrativa
já está fixa. Isso não é outra variante SYSTEM-only, uma comparação causal A/B
nem a implementação de um Narrador com duas etapas no produto.

- Duas entradas sintéticas existentes do lote bb98: abertura (linha 3) e Mara
  (linha 9). Somente `proposal.narrative` é reaproveitada como narrativa fixa.
- Uma chamada por entrada, máximo de duas. Sem diagnósticos, nova narrativa,
  retry, fallback, chamadas paralelas ou substituição de modelo/provedor.
- Candidato `gpt-oss-120b-groq-free-synthetic-low`, Groq direta, modelo
  `openai/gpt-oss-120b`, reasoning `low`.
- Temperatura 0,65, até 768 tokens de saída por chamada (1.536 no conjunto),
  intervalo mínimo de 60 segundos entre despachos e deadline de 60 segundos
  definido após a espera. Custo ausente permanece indisponível.
- USER com limite de 2.000 tokens estimados por caracteres/4. Os pacotes
  completos usam **214 e 317**, sem omissões. Nenhum derivado anterior gerado
  pelo modelo integra o USER.
- As duas entradas têm zero segredos protegidos; esta sondagem não mede sigilo.

## Implementação e preservação

[Contrato e carregamento](../../../scripts/narrator_record_derivation.py)
verificam hashes, linhas e identidade dos artefatos de origem. O
[SYSTEM de derivação](../prompts/record-derivation-v1.md) pede somente
`o/l/s/p/f/t/r/q`, preservando origem, ator, objeto, acontecimento e certeza.
O schema usa os tipos existentes de fatos e atores. Nenhum campo de narrativa
é aceito na resposta.

O [executor isolado](../../../scripts/evaluate_narrator_record_derivation.py)
compõe a proposta final com `n` literal e os registros retornados, sem completar
ou corrigir conteúdo. Usa o mesmo schema final e os validadores existentes.
A API, H6, corpus, manifesto e resultados bb98 permaneceram intactos.

A única alteração no avaliador legado foi uma recusa explícita de artefatos
`record_derivation_probe` nos dois caminhos de replay (seis linhas).
Os novos registros têm tipos próprios `record_derivation_call/skip`.
Um adaptador temporário em memória permite agregar uso/custo com os helpers
existentes; ele nunca é persistido como turno de avaliação completa.

Erros operacionais de provedor, rota ou schema da resposta impedem a segunda
chamada. Rejeição pela política de admissão ou pelo schema final fica registrada
e permite a segunda entrada independente. Não há reenvio em nenhum caso.
O JSONL é gravado após cada resultado. Cancelamento preserva o número real de
chamadas e distingue entrada pulada de chamada interrompida.

O [comando protegido](../../../scripts/run_groq_record_derivation_probe.ps1)
executa preflight sem a chave, valida os parâmetros, só então converte a
SecureString e passa a chave ao filho pelo ambiente. Compara a proveniência
do resumo com o preflight e restaura o ambiente no `finally`.
Não ecoa saída bruta do filho, respostas geradas ou mensagens de exceção.

## Correções comprovadas durante a revisão

1. Uma checagem de integridade demorada após o pacer podia reduzir o intervalo
   real: contraprova despachou em 20 e 60 segundos (40 de diferença).
   A referência temporal agora é atualizada na fronteira do despacho.
2. Uma rota divergente junto de outra verificada não pode produzir
   `identity_consistent:true`; agora produz false.
3. Uma resposta válida no schema de derivados, mas sem fato ou alteração de
   pendência, pode falhar no schema final. Agora registra
   `final_schema_errors`, sem ser classificada como falha interna nem impedir
   o caso seguinte.

Os três casos foram demonstrados falhando antes da correção e passaram depois.
A revisão independente também cobriu deriva de escopo e cancelamento na segunda
espera/chamada, com artefatos reais em diretório temporário e transporte simulado.

## Verificação offline

**179 testes novos passaram**: 45 de contrato, 37 de execução, 10 contraprovas
independentes do executor, 9 de replay e 78 do wrapper. Estão incluídos nos
grupos abaixo; não foram somados novamente.

| Grupo disjunto | Aprovados | Falhas | Tempo |
| --- | ---: | ---: | ---: |
| Regressão Python ampla, excluindo os três arquivos de wrappers indicados no JSON | 2.716 | 1 | 155,75 s |
| Integração Python do probe estruturado anterior, sem wrapper | 38 | 0 | 2,24 s |
| Novo wrapper, subprocessos sintéticos | 78 | 0 | 155,82 s |
| Total observado | 2.832 | 1 | — |

Nenhum skip nesses grupos. O segundo grupo desmarcou 78 testes operacionais
antigos, que não foram executados. O grupo do novo wrapper executou operação
em PowerShell 7 e parsing em PowerShell 7 e Windows PowerShell 5, sem bypass
da política. Um aviso preexistente de `python_multipart` apareceu em cada grupo.
Não alegar aprovação operacional do wrapper no PowerShell 5.

A falha ampla ocorreu no teste existente
`test_restart_recovery_cancels_pending_attempts_once_and_preserves_replay`:
a recuperação retornou zero em vez de um. A única reexecução focada passou
(0,25 s) e não foi somada ao total. O resultado amplo original permanece falho.
A rotina usa `started_at < cutoff`; contraprova em banco temporário confirmou
zero quando os horários são iguais e uma recuperação com cutoff um microssegundo
posterior. O cutoff da falha original não foi salvo, portanto igualdade naquela
execução é inferência, não fato comprovado.

Esse achado fica registrado para acompanhamento separado: nenhum código ou teste
de persistência foi alterado. Não bloqueia a sondagem isolada, que não chama
a recuperação de tentativas no startup. Não houve relaxamento dos testes.


A integração real do wrapper com o CLI também foi conferida com SecureString
vazia e variável de chave removida antes do subprocesso: o preflight passou e
a execução parou na validação da credencial (exit 3 esperado), com stderr vazio,
nenhuma chamada live e nenhum caminho novo ou removido em `eval-results`.

Preflight final: exit 0, executado sem chave e sem API. A proveniência completa,
hashes e comandos de verificação constam no [registro JSON](record-derivation-v1-2026-09-06.json).
Os hashes de schema do JSON usam serialização `sort_keys=True` com separadores
padrão; o schema enviado após normalização Groq tem hash próprio.

| Evidência | SHA-256 |
| --- | --- |
| JSONL bb98 preservado | `f682846c98cd7ea0d1982ccceddea4033932bd6f1c564576a0f7e4cd9ec00288` |
| Narrativa de abertura | `a03124561fb5b22a6cfca73a60766b29b68af06fefc1b9efa921b018fb95cf18` |
| Narrativa de Mara | `6c00eeb827eb1b0ddf7544af9a527b9ff12d4c4cf83c2605363da72074f8cb26` |
| SYSTEM derivação | `b69898a1ad9c6adb0ac54254b42dc6c32afde9fb20af7e2df17d6d810f18e411` |
| Schema final preservado | `bdbda5ab60a1d9c4af44bcadf3be3d09b333b566b61cad9f68cfa7e8a9065bd2` |

## Próximo passo autorizado

Em **um único terminal PowerShell 7**, executar:

```powershell
& "C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_record_derivation_probe.ps1" -ApiKey (Read-Host "Groq API key" -AsSecureString)
```

Inserir a chave somente quando o prompt protegido aparecer. Não colocá-la no
chat, arquivo, argumento literal ou histórico. A revogação da chave anteriormente
exposta não foi verificada; não reutilizar essa credencial.

Após o término, ler integralmente o novo JSONL e summary, verificar proveniência,
limites, schema/rota e admissão, e revisar a fidelidade dos registros de cada
entrada contra sua narrativa fixa e o contexto original. Essa revisão pelo
agente já está autorizada e não depende de uma avaliação intermediária do usuário.

Exit 0 significa duas respostas com rota/schema/admissão aceitos nesta sondagem.
Fidelidade semântica ainda deve ser revisada; `human_review_required:true` reserva
a aceitação humana de produto, sem bloquear a análise técnica pelo agente.
Nenhum exit aprova CAP-001, runtime, qualidade geral ou causalidade.
Exit 1 registra rejeição; 2 indica erro de disponibilidade normalizado; 3 indica
falha local ou de verificação dos artefatos; 130 indica cancelamento verificável.
Não repetir a sondagem para obter uma taxa melhor. Outra hipótese material exige
decisão própria após a análise completa.
