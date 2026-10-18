# Protocolo prévio — comparação com diálogo no fluxo B v1

Data: 12/09/2026. Definido antes de qualquer inferência deste experimento.
O corpus executável está em `source_dialogue_comparison_v1.json`. Este protocolo e o corpus
devem integrar o freeze por SHA256 do preflight. Não alterar critérios após o live.

## Fundamento da nova pergunta

Este experimento source-dialogue-comparison-v1 usa o SYSTEM dialogue-v1 existente,
criado após a sessão49 mostrar iniciativas sem resposta de Mara.81 e87 observaram
resposta e continuidade parcial com Qwen; GPT-OSS ainda não foi observado nessa
configuração de diálogo. A recusa falsa de87 foi corrigida localmente em etapa
separada, com426 casos. Seus resultados e os de61b83 permanecem encerrados.

Não se trata de trocar nomes de cenas ou repetir a mesma condição para forçar
um vencedor. Os casos autorados Oficina/Nina e Arquivo/Rui, ordem, limites e
rubrica de elegibilidade de61b83 são preservados. Muda o SYSTEM já investigado
por uma lacuna concreta. Não será criado outro prompt ou recalibrada a rubrica.
Nenhum resultado anterior entra neste lote; novas sessões e fontes próprias.
O parecer source-model-choice-status de12/09 antecede81/87 e não é uma decisão
arquitetural contrária a esta investigação prospectiva.

## Pergunta e recorte

Qual das duas configurações explícitas oferece melhor experiência para um piloto
restrito à entrada declarativa B, sob dialogue-v1: conversa, espera e continuidade?
Compara Qwen qwen/qwen3.8-27b, reasoning none, e GPT-OSS openai/gpt-oss-120b,
reasoning low, ambos via Groq. É comparação de configurações e trajetórias;
não estima efeito causal isolado do modelo nem demonstra campanha longa.

Os dois casos autorados preservados têm somente local, um NPC e objetivo. Não importar
save, recibo, narrativa ou resultado de lote antigo. Cada bloco cria banco/sessão
novos e passa pelo setup, produtor real, retenção e executor B. Ficha neutra
Wits3/Investigation2/Fome0; relações vazias; aliases só do NPC da própria cena.
Todos os recibos devem ser declarativos: nenhuma rolagem neste recorte. Investigação,
combate, fome, segredos autorados, campanha híbrida e interface ficam fora da evidência
live. As provas locais anteriores desses componentes não substituem avaliação live.

## Condições e ordem

Blocos fechados: Qwen/Oficina, GPT-OSS/Oficina, GPT-OSS/Arquivo, Qwen/Arquivo.
Três turnos em cada bloco, doze chamadas no máximo, uma por slot. A ordem do
primeiro candidato é invertida entre cenas. Não randomizar depois de ver resultados.
Mesmos SYSTEM narrative-source-dialogue-v1, schema estrito e parâmetros comuns:
temperature0.65, máximo768 tokens de completion por chamada, máximo9216 total,
60s iniciais e intervalo global mínimo60s entre inícios HTTP. A espera ocorre
antes de P; depois um único deadline60s compartilhado por P/K/H6, sem renovar
ao entrar no gateway. Medir início da operação, request e HTTP separadamente.
O teto de completion não garante igual quantidade de texto visível: o raciocínio
low do GPT-OSS faz parte da configuração e pode consumir orçamento. Sem ferramentas,
streaming externo, diagnósticos, retry, reparo, fallback ou troca automática de alvo.
Sem aumento de teto após truncamento. Não iniciar nova execução até fechar este lote.

Os primeiros contextos são equivalentes descontadas identidades e alvo. Nos turnos
seguintes cada candidato recebe apenas suas próprias fontes completas anteriores,
até duas; portanto os USER posteriores não são literalmente iguais entre modelos.
O briefing não é fonte narrativa e q não alimenta a memória de cena.

Qualquer falha interrompe os turnos dependentes daquele bloco. Falhas de schema,
política ou admissão permitem o próximo bloco já planejado, sem repetir o slot.
Falha local, cancelamento, eco de credencial, autenticação, limite/quota, timeout ou
indisponibilidade encerram também os blocos restantes. Slots não enviados ficam
explicitamente skipped; não classificá-los como narrativa ruim. Erro sem diagnóstico
tipado suficiente deve encerrar globalmente, não autorizar chamadas por suposição.
Categorias LLM limitadas somente à cadeia: invalid_structured_output,
malformed_response e content_rejected. Toda outra categoria LLM é global, incluindo
rota/modelo divergente, pagamento exigido e erro de configuração. Falha inesperada
do produtor declarativo também é global. Política/admissão/delivery/commit com
resultado terminal tipado preserva a falha da cadeia; exceção local não tipada é global.

## Integridade técnica — antes de comparar a narrativa

Reconstruir manifesto, hashes, ordem, configurações, requests/cápsulas/recibos,
P/K/H, commits, replays sem produção, ausência de contaminação entre bancos,
schemas, rota exata e cronologia global. Conservar request deadline e momento de
criação, além do início HTTP. Antes do commit, confrontar o corpo aprovado,
identidade/rota/modelo, observação HTTP e evidência do adapter; saída acima de768,
resposta além do prazo, eco ou observação incompatível impedem o commit e param
globalmente. Texto parseável não anula finish_reason indevido, erro ou uso
inconsistente. Desconhecido não autoriza uma chamada adicional. Auditoria usa cópia descartável de cada SQLite e
confere que os originais não mudaram. Não limitar a avaliação a exit0 ou HTTP200.
Hashes demonstram consistência local, não autenticidade independente do provedor.
Disponibilidade, truncamento e rejeição são resultados da configuração nesta
execução; não provam qualidade de texto que não chegou a existir.

## Revisão semântica independente

Revisar todos os turnos disponíveis, inclusive propostas recusadas, mantendo clara
a distinção entre proposta e texto realmente confirmado. Para pontuação de piloto,
usar apenas narrativas confirmadas com integridade técnica aprovada.
Revisor independente recebe casos, rubrica e textos sem nomes de modelo sempre que
possível; responsável principal também revisa. Sem nova chamada a provedor como juiz.
Não alegar cegamento completo: contexto herdado pode conter identidades dos modelos.
Divergências ficam registradas com trecho e razão; não apagar a avaliação original.

Gates obrigatórios por turno: respeitar ação/agência do jogador; mecânica e cânone
fornecidos; local/elenco do SYSTEM; continuidade e atribuição; incertezas preservadas;
ausência de instruções internas/reservadas na saída. Fala citada de NPC pode conter
opiniões ou perguntas ao jogador sem ser voz do narrador impondo emoção. Novo objeto,
gesto ou ocorrência ambiental plausível não é automaticamente violação. Improvisação
deve enriquecer a experiência dentro do contrato; novos NPCs permanecem fora deste
SYSTEM congelado. Causa desconhecida não deve virar certeza só por repetição.

Pontuar cada turno em três eixos de0 a2, justificando com evidência textual:

| Eixo | 0 | 1 | 2 |
|------|---|---|---|
| Utilidade para a intenção | Ignora/contradiz a ação ou não permite responder | Resposta vaga, indireta ou oportunidade fraca | Responde de modo específico e utilizável; na espera oferece oportunidade legível |
| Avanço concreto | Repetição ou cena estagnada | Gesto/atmosfera novos, pouca consequência | Informação, consequência, pressão ou oportunidade nova que muda a próxima escolha |
| Clareza e expressão | Texto confuso/incoerente | Legível com defeito lexical, redundância ou excesso | Português claro, conciso e sensorial; pergunta aberta sem pressupor decisão |

No T1, utilidade2 exige resposta concreta do NPC ao objetivo. No T2, avanço2 exige
desenvolver elemento já apresentado em algo que altere a situação ou a escolha,
sem forçar a reação do jogador. Luz piscando ou gesto isolado pode receber1, mas
não2 automaticamente. No T3, utilidade2 exige relacionar resposta à própria história
anterior; recapitulação não recebe avanço2 por si só. Não exigir um enredo inventado
pelo avaliador como única resposta correta. Tensão, recusa motivada ou obstáculo
concreto podem ser avanço útil, mesmo sem resolver o objetivo.

## Regra de recomendação de piloto

Elegível nesta rodada somente se os seis turnos do candidato tiverem gates técnicos
e semânticos aprovados; nenhum eixo0; utilidade2 em T1/T3 das duas cenas; avanço2 em
ambas as esperas. Atmosfera não compensa estagnação. Avaliação técnica incompleta por
indisponibilidade torna a comparação inconclusiva, sem inventar notas para ausências.
Se só um satisfizer todos os critérios, recomendar esse candidato para o recorte,
com as limitações observadas. Se ambos satisfizerem, preferência apenas por dominância
dos totais por cena (não inferior em nenhuma, superior em ao menos uma), com concordância
dos revisores. Empate, troca de vantagem ou divergência relevante: sem vencedor inequívoco.
Se nenhum satisfizer: nenhum candidato qualificado neste protocolo. Não repetir para
forçar vencedor. Latência/tokens entram como descrição operacional, não desempate secreto.
Recomendação não muda modelo default, ativa UI nem aprova CAP-001 ou produto; aceitação
final continua humana. Nova investigação posterior terá hipótese e protocolo próprios.

## Fontes operacionais

Documentação oficial consultada em12/09/2026: [modelos](https://console.groq.com/docs/models),
[saída estruturada](https://console.groq.com/docs/structured-outputs) e
[reasoning](https://console.groq.com/docs/reasoning). Ambas as rotas exatas e o schema
strict estão listados; reasoning none/low são opções documentadas. Isso não verifica
chave, autorização da conta, disponibilidade no instante do teste, saldo ou ZDR.
Manter uso sintético e conta gratuita já autorizada, sem alteração de plano/cobrança.
Credencial só no filho live, por ambiente autorizado ou entrada protegida; nunca .env,
chat, argumento, log, histórico ou recuperação de outra janela.
