# scene-faithful-v1 — preparação da observação isolada

Data: 06/09/2026. Estado: preparação e verificação offline concluídas; nenhuma
chamada de inferência desta variante. A próxima etapa está pronta e depende
somente de entrada protegida da credencial no terminal local. A análise e as
correções locais subsequentes continuam autorizadas sem avaliação intermediária.

## Evidência e hipótese

A [observação attributed dc9d13ba](scene-attributed-observation-dc9d13ba-2026-09-06.md)
mostrou que registros podem alterar o estado ou o grau de certeza do que a
narrativa estabeleceu. Na cena de Mara, a narrativa mostrava o papel, enquanto
o fato o mantinha oculto. No galpão apareceram relações adicionais apenas nos
registros. Admissão automática não cobriu toda essa divergência semântica.

A nova variante acrescenta ao SYSTEM attributed uma operação de compressão:
estabelecer o acontecimento em `n` e preservar responsável, ação ou estado,
objeto ou lugar, momento, negação e certeza ao resumi-lo. Dois microexemplos
positivos mostram exposição sem entrega e uma percepção de origem incerta,
sem atribuir causa pela coexistência de sinais.

Os pares são fragmentos instrutivos de `n` e `s`/`f[].s`, identificados como
exemplos fora da crônica, sem substituir o JSON completo. Celina, medalhão,
mostrador e vibração não aparecem no corpus atual. A redação mantém todas as
instruções attributed anteriores e permite paráfrase, improvisação e ações de
NPCs. Estado anterior visível e confidencial fornecido conservam fontes distintas.

É uma hipótese de geração. Procedimento e exemplos compõem uma intervenção
conjunta no SYSTEM; este braço não separa suas contribuições. Os possíveis
efeitos adversos a observar são reutilização de objetos ou fórmulas dos
exemplos, predominância de NPCs exibindo objetos, cópia de resposta incompleta
e aumento do prompt sem melhora. Isso não cria novos gates lexicais.

## Isolamento e proveniência

Baseline declarado: `scene-attributed-v1`. No código atual, o pacote USER,
foco recente, schema/contrato de atores, validadores, corpus, manifesto e
parâmetros são iguais entre as duas seleções. Os testes capturam pedidos
efetivos antes do despacho em cinco episódios iniciais e em uma continuação
com foco admitido não vazio. Essa continuação usa fixture autorada, não um
antecessor importado de execução histórica.

O validador corrigido após o lote attributed está aplicado igualmente às
duas variantes atuais e permaneceu congelado durante esta preparação:

```text
c874b176de47c33d9e0335fa4a923d439d98e98a7710311aede0a5c3e7c85d18
```

O lote histórico attributed foi executado antes dessas correções de agência.
Sua revalidação isolada admitiu 3/7 propostas, mas o predecessor do galpão agora
é rejeitado: as duas continuações históricas não seriam alcançadas pela cadeia
atual. Não tratar 3/7 como uma cadeia válida nem como baseline causal.

O modo `-FaithfulOnly` não executa ou importa baseline. Não há A/B completo ou
conclusão causal sobre melhora. O relatório de proveniência
[em JSON](scene-faithful-v1-2026-09-06.json) conserva fingerprints da preparação,
seis artefatos originais dos três lotes e os arquivos congelados.

Hashes do SYSTEM carregado pelo avaliador, sem front matter:

| Variante | SHA-256 | Caracteres | Palavras por espaços |
| --- | --- | ---: | ---: |
| scene-attributed-v1 | `da0b9087b7adcdfd2a70cf3d64c91b72eb163ce2d338f18268b10e4cd8f34aab` | 6.336 | 920 |
| scene-faithful-v1 | `76a9ffdb37296be672e94e1a8c741d90cb5c44164c8dcf888107d308865218d2` | 7.878 | 1.160 |

O aumento de 1.542 caracteres e 240 palavras não mede tokens, custo, latência
ou qualidade. Os cinco prompts de avaliação anteriores e H6 de runtime
permanecem intactos. O schema conserva SHA-256
`bdbda5ab60a1d9c4af44bcadf3be3d09b333b566b61cad9f68cfa7e8a9065bd2`.

## Implementação e revisão

- Novo arquivo `evals/narrator/prompts/scene-faithful-v1.md`, registrado na
  allowlist do avaliador e no conjunto de variantes do contexto scene-focus.
- Metadados declaram baseline attributed, intervenção `system_prompt`,
  `causal_comparison: false`, `complete_ab_experiment: false`,
  `runtime_promoted: false` e `human_review_required: true`.
- `-FaithfulOnly` seleciona exclusivamente `gpt-oss-120b-groq-free-synthetic-low`,
  recusa os quatro modos anteriores em conjunto e verifica proveniência
  faithful/attributed. A verificação attributed/grounded continua preservada.
- Falha de predecessor continua bloqueando as duas continuações. Replay legado
  e probe isolado de abertura são recusados. Nenhuma resposta é reescrita,
  regenerada ou reaproveitada para produzir aprovação.
- Revisões independentes do prompt e da integração não encontraram achados
  acionáveis. A revisão estática não demonstra melhora de geração.
- `AGENTS.md` e a retomada registram que concluir uma etapa deve levar ao
  próximo passo autorizado, até dependência humana real ou limite vigente.

Não houve alteração de runtime, schema, critérios, dependências, produto ou
decisão CAP-001. O limite solicitado de dois fatos continua distinto do máximo
de quatro aceito pelo schema. A diferença já existia no baseline.

## Verificação

A suíte completa foi executada em dois grupos disjuntos, com arquivos de
implementação congelados durante as execuções:

| Grupo | Aprovados | Omitidos | Saída | Duração |
| --- | ---: | ---: | ---: | ---: |
| Todos os testes exceto `test_prompt_experiment_runner.py` | 2.147 | 0 | 0 | 111,53 s |
| `test_prompt_experiment_runner.py` | 297 | 295 | 0 | 491,75 s |
| Total | **2.444** | **295** | **0** | Grupos paralelos |

Os 60 testes focados passaram antes da suíte completa e já estão incluídos no
total, sem contagem dupla. Os skips correspondem aos testes operacionais do
Windows PowerShell 5: a consulta de política retorna Unavailable porque o
módulo não carrega. Os testes operacionais em PowerShell 7 e o parser em ambos
os hosts passaram; nenhuma política foi contornada.

Foi usado o venv existente, `STORYTELLER_DISABLE_DOTENV=1`,
`PYTHONDONTWRITEBYTECODE=1` e `-p no:cacheprovider`, com persistência isolada e
bloqueio de rede externo do pytest. Cada grupo apresentou um aviso; a depreciação de
`python_multipart` permanece preexistente. Não houve chamada real de inferência.
A inspeção dos deltas e a conferência de hashes preservaram a evidência antiga
e o checkout original.

## Próximo passo pronto

Executar uma única observação em um terminal **PowerShell 7**. Primeiro
executar a linha e pressionar Enter; só depois colar a chave no prompt
protegido. Usar uma chave válida não exposta, sem reutilizar a antiga chave da
conversa. A revogação anterior não foi verificada pelo agente.

```powershell
& "C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_prompt_experiment.ps1" -FaithfulOnly -ApiKey (Read-Host "Groq API key" -AsSecureString)
```

Somente fixtures sintéticas; até nove chamadas normais e dois retries
diagnósticos delimitados; saída narrativa de 768 tokens, diagnósticos de 128,
temperatura 0,65, deadline de 60 segundos por chamada após pacing e intervalo
mínimo de 60 segundos. Sem retry narrativo ou fallback. A variável temporária
da chave é removida/restaurada em `finally`.

Ao chegar o resultado, conferir summary e JSONL, proveniência, schema, agência,
atores/presença, sigilo, fidelidade narrativa→memória e possível reutilização
dos exemplos. Distinguir instrução descumprida, defeito de validador e qualidade
narrativa. Corrigir defeitos locais demonstráveis com contraprovas e seguir
para a próxima intervenção autorizada, sem aguardar avaliação intermediária.
Não repetir o lote em loop, relaxar critérios ou importar predecessor rejeitado.
A eventual admissão não aprova capacidade de produto ou CAP-001.

A preparação não disparou nem agendou chamadas; a credencial é a dependência
humana necessária para a observação ao vivo.
