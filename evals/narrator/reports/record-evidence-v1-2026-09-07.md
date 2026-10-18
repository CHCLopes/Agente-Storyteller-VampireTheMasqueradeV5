# Preparação concluída — record-evidence-v1

Data: 07/09/2026. Status: **implementação e verificação offline concluídas;
uma execução delimitada aguarda entrada protegida de credencial**.

O usuário respondeu “Prossiga” ao [desenho apresentado](record-evidence-hypothesis-c9c01a48-2026-09-07.md).
Essa autorização cobre preparar o envelope e disponibilizar até duas chamadas.
A proposta histórica conserva seu status anterior à decisão; este relatório e
a retomada registram a aprovação posterior. A revisão dos resultados pelo agente
já está autorizada, sem exigir avaliação intermediária do usuário.

## O que foi preparado

O [contrato experimental](../../../scripts/narrator_record_evidence.py) mantém
os oito campos de registros anteriores em `records` e acrescenta `supports`.
Cada suporte aponta para uma afirmação por caminho e intervalo Unicode
[início inclusivo, fim exclusivo], com um a três IDs de origem e modalidade
`established`, `suggested` ou `unresolved`. Há no máximo 12 suportes.

O USER contém apenas as duas narrativas originais bb98 e o contexto, ação e
resultado mecânico do corpus congelado. A abertura tem um enunciado narrativo;
Mara tem três. Suas unidades completas preservam separadores e reconstituem
literalmente cada narrativa. Os demais IDs apontam para itens integrais das
fontes anteriores. Derivados c9, registros antigos e controles autorados não
entram no pacote enviado ao candidato.

O [SYSTEM](../prompts/record-evidence-v1.md) pede conservação de responsáveis,
relações, certeza e pressuposições. Em resumos mistos, orienta separar as
afirmações por intervalo. Suportes não são correções nem prova de implicação:
o código verifica somente estrutura, referências, caminhos e intervalos.
`supports: []` é estruturalmente permitido e deixa a cobertura sem avaliação.
Mesmo com IDs e modalidade válidos, registros infiéis continuam possíveis.

O [executor](../../../scripts/evaluate_narrator_record_evidence.py) insere
localmente a narrativa original e aplica schema final, contrato de atores e
admissão existentes. Os suportes permanecem fora da proposta final. Não houve
alteração em H6, runtime, cena, memória ou persistência. O único delta no
avaliador legado são seis linhas que recusam esta identidade experimental
nos dois caminhos de replay CAP-001.

## Limites e medição

Mesma rota sintética: `gpt-oss-120b-groq-free-synthetic-low`, Groq direta,
`openai/gpt-oss-120b`, raciocínio baixo. Uma chamada por entrada, máximo de duas,
sem geração narrativa, diagnóstico, juiz LLM, retry, fallback ou paralelismo.

Temperatura 0,65; saída até 768 tokens por chamada, 1.536 no conjunto, incluindo
o envelope. Pacing mínimo local de 60 segundos entre despachos reais e deadline
de 60 segundos depois da espera. O snapshot é conferido antes e depois dela.
Falha de provedor, rota, schema do envelope ou referência inválida encerra a
sondagem. Rejeição do schema final ou da admissão preserva a segunda entrada
independente. Nenhum resultado autoriza repetir para elevar a taxa.

| Caso | USER: caracteres / estimativa | Envelope autorado em teste: caracteres / estimativa | Suportes autorados |
|---|---:|---:|---:|
| Abertura | 1.467 / 367 | 681 / 171 | 6 |
| Mara | 3.002 / 751 | 884 / 221 | 8 |

Estimativas usam caracteres/4. Os USERs ficam abaixo do limite estimado de
2.000, sem omissões; os dois exemplos completos demonstram representação
abaixo da estimativa de 768. Isso não mede o tokenizer do provedor nem garante
que uma resposta real futura caberá. Os exemplos são testes autorados,
não amostras do modelo nem respostas fornecidas a ele.

## Verificação

**2.998 testes passaram, zero falhas e zero skips**, em três grupos disjuntos:
2.849 na suíte Python ampla, 38 da integração Python do probe estruturado
e 111 do novo wrapper. Houve somente o aviso preexistente de python_multipart.
Os wrappers anteriores de experimento SYSTEM, probe estruturado e derivação
não foram reexecutados; os comandos exatos e exclusões constam no JSON.
A falha temporal histórica de persistência não reapareceu nesta execução
ampla, sem alteração do código ou daquele teste.

Os 243 testes novos são: 75 do contrato, 38 do executor, dez adversariais
independentes, nove da fronteira de replay e 111 do wrapper. Estão incluídos
nos grupos acima; rodadas focadas anteriores não são somadas novamente.

As contraprovas confirmam que referências, caminhos e intervalos inválidos
interrompem; índices booleanos em instâncias forjadas não viram inteiros pela
serialização; drift de fonte durante a espera impede envio; cancelamentos
preservam evidências parciais. A integração com GroqAdapter real usa
HTTPX MockTransport e confere o schema aninhado, USER literal e parâmetros.
Um registro autorado que liga papel ao endereço, com suporte estrutural
válido, permanece sem aprovação de fidelidade ou cobertura semântica.

O wrapper teve execução simulada no PowerShell 7 e parser nos PowerShell 7/5,
sem contornar política. Na integração com CLI/helper/prompt reais, uma
SecureString vazia e ambiente sem GROQ_API_KEY passaram pelo preflight e
pararam em `credential validation`, exit 3 esperado, sem chamada ou artefato.
A tentativa temporária inicial teve erro de escape antes do wrapper; apenas
esse comando foi corrigido. Duas revisões independentes não encontraram
pendências materiais no escopo. Não foi acessada credencial nem feita chamada
ao provedor nesta preparação.

O relatório histórico de derivação preserva a falha temporal de persistência
e o rerun isolado daquela ocasião. O achado de resolução prematura do controle
da matriz também permanece separado. Nenhuma dessas áreas foi alterada.

## Integridade e próximo passo

O [registro JSON](record-evidence-v1-2026-09-07.json) contém preflight,
hashes das fontes, pacotes, unidades, schemas, implementação e comandos.
SYSTEM: `6282cb3c46fee52c6ef261cd5e9103e90b516cdd38d4d4f7ceb5b077a3908b6c`.
Schema final preservado:
`bdbda5ab60a1d9c4af44bcadf3be3d09b333b566b61cad9f68cfa7e8a9065bd2`.

Em **um único terminal PowerShell 7**, executar uma vez:

```powershell
& "C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller\scripts\run_groq_record_evidence_probe.ps1" -ApiKey (Read-Host "Groq API key" -AsSecureString)
```

A única dependência humana é a entrada protegida de uma chave válida; não
há nova confirmação de escopo pendente. Não usar chave antiga ou enviada no
chat; não abrir .env nem procurar credenciais em outros processos.

Depois do término, ler summary e JSONL completos, verificar hashes e revisar
autonomamente registros e suportes pelos critérios pré-registrados. Conferir
especialmente certeza na abertura, relação papel/endereço em Mara, cobertura,
pressuposições das perguntas e origem do contexto. Um exit 0 significa sucesso
operacional somente: fidelidade e cobertura ficam `not_performed` até a revisão.
Os artefatos originais não serão reescritos para incorporar essa avaliação.

O experimento muda SYSTEM, USER e schema experimental; sua comparação histórica
não é causal. Duas entradas não demonstram generalização. CAP-001, qualidade de
produto e promoção ao runtime continuam sem aprovação.
