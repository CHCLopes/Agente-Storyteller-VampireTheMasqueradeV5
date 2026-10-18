# Rota A — pesquisa e proposta HYP-003

**Data:** 2026-09-26

**Status:** Gemini Flash gratuito escolhido; preparação offline verificada;
credencial de projeto Free Tier pendente. Zero inferência nesta preparação.

## Escopo e recomendação

A resposta `Aprovo NARRATOR-ROUTE-A` autoriza pesquisar outro candidato sem
alterar arquitetura ou gates. HYP-001 e HYP-002 permanecem encerradas, aceitas
e sem elegível. Esta proposta não promove experimento a produto.

Em 26/09/2026, o usuário excluiu provedores pagos e determinou novos testes no
Gemini Flash gratuito. O alvo escolhido é **`gemini-3.8-flash`, API direta
Google Gemini no Free Tier**. A documentação oficial registra o ID como estável,
saída estruturada e thinking `low`; isso não é evidência de qualidade narrativa.
O adaptador nativo já existente foi mantido isolado do runtime de campanha.

## Lista curta consultada

Preços de texto Standard por milhão de tokens de entrada/saída, sem cache,
ferramentas ou desconto de batch. Disponibilidade na conta não foi testada.

| Candidato exato / provedor direto | US$/MTok entrada / saída | Adequação e limitação observada |
|---|---:|---|
| `claude-sonnet-5` / Anthropic | 2 / 10 | Excluído desta rodada: provedor pago. |
| `gpt-6-sol` / OpenAI | 2 / 10 | Excluído desta rodada: provedor pago. |
| `gemini-3.8-flash` / Google | gratuito no Free Tier | Escolhido; modelo estável, saída estruturada e adaptador nativo existente. Somente fixtures sintéticas porque o nível gratuito pode usar conteúdo para melhorar produtos. |

Fontes oficiais verificadas em 26/09/2026:

- [Sonnet 5: ID e preços](https://platform.claude.com/docs/en/models/sonnet-5/overview).
- [IDs Claude: snapshots fixos; infraestrutura ainda pode variar](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions).
- [Sonnet 5: desativar thinking e omitir sampling não suportado](https://platform.claude.com/docs/en/models/sonnet-5/whats-new-sonnet-5).
- [JSON estruturado Claude](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
- [GPT-6 Sol: recursos e preços](https://developers.openai.com/api/docs/models/gpt-6-sol).
- [Gemini 3.8 Flash: modelo](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) e [preços](https://ai.google.dev/gemini-api/docs/pricing).

Observação local: `api/llm/adapters/gemini.py` já impõe endpoint oficial, modelo
estável, ausência de redirect, rota observável e schema nativo. O runner HYP-003
usa esse adaptador diretamente e não passa pelo runtime padrão. Nenhum default
será modificado.

## Pergunta e desenho prospectivo

HYP-003: este novo alvo consegue realizar o mesmo contrato de mundo fechado
em oito situações inéditas, com 8/8 válidas e sem inventar fatos ou agência?

Permanecem o `closed_world_render_plan`, campos obrigatórios, paleta sensorial
finita, desconhecidos, proibições, schema `n`/`q`, 30–150 palavras de narrativa,
pergunta aberta, pontuação terminal e revisão semântica vinculada aos brutos.
Autoridade canônica, RNG e commit nunca serão delegados ao modelo.

Não é um experimento causal que muda somente o modelo: provedor, protocolo,
sampling e corpus também mudam. A temperatura histórica 0,65 não será enviada,
pois Sonnet 5 rejeita sampling não padrão. Não se pode atribuir eventual melhora
isoladamente ao modelo nem reclassificar os lotes antigos.

### Cenários prospectivos propostos

São especificações para fixtures, ainda não um corpus congelado. Na preparação,
cada uma receberá todas as unidades e proibições explícitas, sem lacunas a serem
preenchidas pelo modelo. Checar novidade frente aos corpora anteriores antes do
freeze; mudar somente nomes locais em caso de colisão, nunca gates ou resultado.

| Slot | Classe preservada | Cena e fronteira factual |
|---|---|---|
| 1 | Espera sem transição | Depósito de mapas: jogador aguarda junto à bancada; cilindro lacrado permanece imóvel, iluminação branca constante. Não abrir lacre, mover jogador ou inventar som/presença. |
| 2 | Espera com transição | Mesmo depósito após a espera: servidor autoriza apenas a lâmpada branca apagar; cilindro continua lacrado. Sem chegada de NPC, passagem presumida de tempo ou ação do jogador. Recebe somente a prosa validada do slot 1 como contexto. |
| 3 | Objeto conhecido | Jogador examina um selo hexagonal de resina âmbar já sobre o balcão; marca de três traços visível. Não pegar, aproximar-se, atribuir origem ou função ao selo. |
| 4 | Objeto desconhecido | Jogador observa um estojo opaco fechado, sem inscrição. Conteúdo e mecanismo de fecho desconhecidos; não inferir arma, carta, resistência ou intenção de abertura. |
| 5 | Resultado favorável | Teste já resolvido autoriza destravar uma grade, que permanece fechada. Prosa não rola dados nem abre a grade, concede passagem ou inventa recompensa. |
| 6 | Resultado desfavorável | Tentativa já resolvida não desloca um contrapeso; cabo permanece íntegro. Não quebrar cabo, causar ferimento, repetir esforço ou converter fracasso em sucesso. |
| 7 | Segredo e pista | Iara informa apenas que a etiqueta aponta para a estante seis; a identidade sintética protegida é enviada no bloco confidencial para testar não divulgação. Não revelar dono da etiqueta ou conteúdo da estante. |
| 8 | Ação ambígua | Jogador diz que vai lidar com um disco de cerâmica e uma tira de linho sobre a mesa. Nenhum método foi escolhido: narrar apenas disponibilidade e perguntar como; não executar manipulação. |

Slots 1–2 formam um par de continuidade; nenhum efeito do slot 1 é promovido ao
cânone. Se o slot 1 for inválido ou não puder ser validado antes do seguinte,
slot 2 é skipped, sem substituição por prosa fabricada. Os outros slots são
independentes. Skip torna o candidato inelegível; não preencher depois.

## Envelope escolhido HYP-003-GEMINI-FREE-L1

- Alvo único: `gemini-3.8-flash`; URL oficial fixa
  `https://generativelanguage.googleapis.com/v1beta`.
- Projeto da chave confirmado pelo usuário como Free Tier e sem billing antes
  do prompt de credencial; se não for possível confirmar, nenhuma chamada.
- Transporte nativo opt-in, sem redirect, proxy, tools, grounding, arquivos,
  cache, batch, prioridade ou troca de provedor.
- Thinking `low`; sampling, seed e demais knobs omitidos.
- JSON schema nativo estrito `n`/`q`; `maxOutputTokens: 768`; timeout de 60
  segundos; inícios separados por pelo menos 60 segundos.
- Oito POSTs de geração sequenciais, um por slot. Timeout/desconexão consome o
  slot e não é reenviado, mesmo após reinício.
- Retry, reparo, fallback, rotação de chave/modelo e extensão automática: proibidos.
- Receipts locais preservam IDs, versão efetiva reportada, hashes sem segredo,
  usage e vínculo ao lote. Cabeçalhos de autenticação nunca são registrados.

## Orçamento e segurança

Orçamento autorizado: **US$ 0,00**. A página oficial registra entrada e saída
gratuitas no Free Tier. O mesmo modelo também possui modalidade paga; por isso o
launcher exige confirmação humana de que o projeto da chave continua no Free
Tier e sem billing habilitado. Não há tentativa automática de mudar tier, comprar
créditos ou continuar por uma chave associada a projeto pago.

Somente fixtures sintéticas, sem campanhas, dados pessoais ou lore privado. A
[página oficial de preços](https://ai.google.dev/gemini-api/docs/pricing) informa
que conteúdo do Free Tier pode ser usado para melhorar produtos. A autorização
vale somente para este corpus sintético e não admite segurança produtiva.

Credencial futura: inserção mascarada pelo usuário em terminal dedicado,
variável somente do processo, limpeza em `finally`; nunca chat, `.env`, arquivo,
argumento, histórico visível ou relatório. Não reutilizar chave Groq. Nenhuma
credencial foi consultada nem autenticação testada na preparação.

## Verificação, parada e decisão

Antes de rede: corpus/schema/protocolo/prompt/templates/ordem congelados com hashes;
testes offline de payload, sanitização, limite de chamadas/custo, timeout sem
reenvio, proveniência e adulteração de artefatos; preparação sem chave e sem rede.
Implementar no recorte de avaliação, sem acoplar o novo provedor ao caminho v1.

Falhas de autenticação, transporte, proveniência, orçamento ou integridade param
os slots restantes. Falha semântica registrada não autoriza repetição: demais
casos independentes podem prosseguir dentro do lote. Exigir 8/8, nenhum skip,
schema válido e todos os gates históricos. Resposta estruturada não prova
fidelidade factual. Revisão deve avaliar cada proposição e relacioná-la a unidade
permitida; aceitação narrativa final permanece humana.

Após revisão, parar para aceitação do resultado, inclusive se nenhum elegível.
Mesmo 8/8 não aprova CAP-001, default produtivo ou campanha híbrida.

**Decisão registrada:** em 26/09/2026, o usuário determinou que provedores pagos
estão fora de questão e pediu novos testes no Gemini Flash gratuito. Isso escolhe
alvo, provedor, Free Tier e orçamento zero para este lote. A preparação offline
foi concluída; a rede depende apenas da confirmação do projeto Free Tier e da
entrada protegida da credencial.

Configuração recomendada para inserir a credencial e acompanhar o lote:

- Modelo: gpt-5.6-sol.
- Esforço: low.
- Motivo: ação mecânica de confirmar o Free Tier e inserir uma chave mascarada; a auditoria semântica posterior usará Sol high.
- Ação humana necessária: confirmar no AI Studio que o projeto está no Free Tier sem billing, digitar `FREE` no launcher e inserir a chave no prompt mascarado.
- O que continuará autonomamente depois da ação: observar o lote, verificar os artefatos, revisar os oito resultados e preparar o checkpoint formal de aceitação.
