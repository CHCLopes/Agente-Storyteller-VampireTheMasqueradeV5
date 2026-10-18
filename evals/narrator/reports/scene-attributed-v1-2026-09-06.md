# scene-attributed-v1 — preparação da observação isolada

Data: 06/09/2026. Estado: implementação e verificação offline concluídas;
nenhuma chamada ao vivo desta variante. O próximo passo depende de uma nova
credencial fornecida de forma protegida. A autorização contínua cobre a
preparação, correções locais necessárias e análise técnica; revisão humana
intermediária não é condição para concluir esse trabalho.

## Evidência e hipótese

A [comparação dos lotes afae48dd e 2ae5b1a7](scene-grounded-comparison-afae48dd-2ae5b1a7-2026-09-06.md)
demonstrou ações físicas não declaradas pelo jogador, incoerência de rótulos
de NPCs e relações acrescentadas somente nos registros derivados.
Exemplo: a narrativa da cena de Mara não estabelecia a sirene dificultando
a comunicação, mas essa relação apareceu no fato e no próximo foco.

A nova variante organiza explicitamente duas responsabilidades: atribuir
cada ação ao jogador, a um NPC ou ao ambiente; e identificar a origem de cada
registro em narrativa visível, estado anterior visível ou confidencial
fornecido. É uma hipótese de geração, ainda sem resultado empírico.

O prompt preserva improvisação de pistas, ações de NPCs e complicações.
O jogador continua decidindo suas ações; o diretor continua decidindo
ações de NPCs. Uma descoberta em um sucesso não autoriza completar o método
físico do personagem. Paráfrases são permitidas, desde que preservem ação,
responsável, relação causal e grau de certeza. Acrescentar “pode” não
fundamenta uma relação ausente da narrativa.

## Intervenção e proveniência

O baseline declarado é `scene-grounded-v1`. No código atual, somente a
mensagem SYSTEM difere entre ele e `scene-attributed-v1`: USER, foco recente,
contrato/schema de atores, corpus, manifesto, validadores e parâmetros
permanecem iguais. Os testes inspecionam pedidos completos antes do despacho
em cinco episódios iniciais e em uma continuação com foco admitido não vazio.
Essa última usa uma fixture autorada de teste; não é evidência de continuação
produzida pelo modelo, nem será importada pelo modo `-AttributedOnly`.

A intervenção SYSTEM reúne atribuição de ações e origem dos registros;
um único braço não separa a contribuição de cada instrução. Não há controle
executado ou importado. Comparações com lotes históricos não constituem A/B
causal nem medem a contribuição isolada desta redação.

Os lotes grounded históricos antecedem a correção local de dois falsos
positivos de perguntas, documentada na comparação. Essa correção já integra
ambos os caminhos comparados pelos testes atuais. O validador não mudou
durante a preparação attributed; seu SHA-256 atual permanece:

```text
30407aa4504fd2634ca6f96cdf32e3c976a029e37851a05a3b5b92228f9c0885
```

Hashes da mensagem SYSTEM carregada, sem front matter, com a mesma
normalização usada pelo avaliador:

| Variante | SHA-256 | Caracteres | Palavras por espaços |
| --- | --- | ---: | ---: |
| scene-grounded-v1 | `ff47d144200ddaac14c7db30f6328f73de5fb466730fe178fb49dc335dbac331` | 4.841 | 697 |
| scene-attributed-v1 | `da0b9087b7adcdfd2a70cf3d64c91b72eb163ce2d338f18268b10e4cd8f34aab` | 6.336 | 920 |

O novo SYSTEM é maior. Esses números não medem tokens, custo, latência ou
melhora narrativa. Os quatro prompts anteriores permanecem congelados.
Os quatro artefatos originais dos dois lotes, corpus, manifesto e módulos
de contexto/atores/cena conferem com as evidências anteriores.

## Implementação e revisão

- Novo arquivo em `evals/narrator/prompts/scene-attributed-v1.md`, registrado
  na allowlist do avaliador como variante do contexto `scene-focus-v1`.
- Metadados identificam baseline grounded, intervenção `system_prompt`,
  `causal_comparison: false`, `complete_ab_experiment: false`,
  `runtime_promoted: false` e `human_review_required: true`.
- `run_groq_prompt_experiment.ps1 -AttributedOnly` seleciona somente o novo
  braço e o candidato `gpt-oss-120b-groq-free-synthetic-low`. Recusa combinação
  com os demais modos e exige os metadados correspondentes no resultado.
- Replay legado e probe isolado de abertura continuam recusados para esses
  contratos. Predecessor rejeitado continua impedindo as duas continuações.
  Os modos anteriores mantêm sua seleção, validação e mensagens.
- A revisão estática verificou agência, hierarquia das instruções, presença
  de NPCs e separação confidencial. A redação foi ajustada para que exigências
  de exposição do ator e presença final se apliquem a fatos visíveis; atores
  confidenciais não são obrigados a aparecer no roster público. NPCs departed
  e offscene não são exigidos na presença final. Não foram criados filtros
  temáticos nem novas regras lexicais de admissão.
- Uma revisão independente final dos deltas do wrapper, de seus testes e do
  avaliador não encontrou achados acionáveis.

Os limites textuais solicitados permanecem os da variante grounded, inclusive
no máximo dois fatos no SYSTEM; o schema continua aceitando até quatro.
Não houve alteração de critérios, runtime ou decisão CAP-001.

## Verificação concluída

A suíte completa foi executada em dois grupos disjuntos. O grupo do avaliador
usou o prompt final; os arquivos do wrapper e de seus testes não foram
alterados durante nem após a execução de seu grupo:

| Grupo | Aprovados | Omitidos | Saída | Duração |
| --- | ---: | ---: | ---: | ---: |
| Todos os testes exceto `test_prompt_experiment_runner.py` | 2.030 | 0 | 0 | 116,99 s |
| `test_prompt_experiment_runner.py` | 202 | 200 | 0 | 363,97 s |
| Total | **2.232** | **200** | **0** | Execuções paralelas; durações não somadas |

Os 200 skips são testes operacionais do Windows PowerShell 5: a consulta
utilizada pela fixture não consegue carregar o módulo de política e retorna
Unavailable. O PowerShell 7 retorna RemoteSigned e seus testes operacionais
passaram. O parser foi verificado em ambos os hosts. Nenhuma política foi
contornada.

Persistem o aviso de depreciação de `python_multipart` e, no grupo do wrapper,
dois avisos de cache do pytest por permissão de escrita. Eles não representam
falhas de teste. O grupo restante usou `-p no:cacheprovider`.

As verificações cobrem isolamento real dos pedidos, hashes congelados,
metadados/proveniência, limites e pacing, ausência de retry narrativo,
seleção exclusiva de modo, interrupção e limpeza/restauração de credencial
sintética sem eco. Foram usados `STORYTELLER_DISABLE_DOTENV=1`, persistência
isolada e bloqueio de rede externo do pytest. Nenhuma dependência foi instalada
e o checkout original foi preservado.

## Próxima observação

A única dependência humana pendente é revogar a chave anteriormente exposta e
fornecer uma nova chave diretamente no prompt protegido. Não usar a chave
antiga nem colar credenciais no chat ou na linha de comando. A exposição não
foi reproduzida neste relatório.

Em um único terminal PowerShell 7, executar a linha abaixo e pressionar Enter
primeiro. Somente quando aparecer o prompt protegido, colar a nova chave:

```powershell
& "C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_prompt_experiment.ps1" -AttributedOnly -ApiKey (Read-Host "Groq API key" -AsSecureString)
```

O modo usa exclusivamente dados sintéticos e mantém saída narrativa de 768
tokens, diagnósticos de 128, temperatura 0,65, prazo de 60 segundos por
chamada após pacing e pelo menos 60 segundos entre chamadas. O máximo
continua sendo nove chamadas normais mais dois retries diagnósticos
delimitados, sem retry narrativo ou fallback. O wrapper remove/restaura
a variável temporária da credencial em `finally`.

Quando houver resultado, inspecionar summary e JSONL, conservar rejeições
e conferir proveniência antes de comparar. A revisão semântica deve observar
ações não declaradas, NPCs confundidos com objetos, presença e confidencial,
relações inventadas apenas nos registros e contexto antigo apresentado como
acontecimento novo. São os problemas e critérios já documentados, não novos
gates nem aprovação antecipada. A eventual admissão automática não decide
fidelidade da memória, qualidade narrativa, capacidade de produto ou CAP-001.

A análise técnica e correções locais comprovadas podem continuar sob a
autorização vigente, sem aguardar avaliação intermediária do usuário.
Esta preparação não disparou nem agendou novas chamadas.
