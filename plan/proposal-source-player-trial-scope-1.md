---
goal: Delimitar a próxima experiência opcional B para aceitação do recorte pelo usuário
version: 1
date_created: 2026-09-12
last_updated: 2026-09-12
status: 'Accepted for limited trial'
---

# Proposta de uso B em uma cena

Esta proposta torna concreta a aceitação de recorte prevista em DEP-005 do
[plano de entrada](feature-narrative-source-opt-in-entry-1.md:130). A direção B
já foi autorizada; não está sendo submetida novamente à aprovação. A escolha
aqui é aceitar uma experiência limitada, diferente do jogo completo anteriormente
solicitado. Em12/09, o usuário executou o recorte descrito. Essa participação registra a aceitação do uso delimitado, sem aprovar qualidade narrativa.

## Experiência proposta

- Uma sessão nova e isolada em uma cena conhecida, com um NPC já presente e um
  objetivo imediato apresentado na introdução. Nenhum save anterior será convertido.
- O jogador pode conversar com o NPC e aguardar sua reação, escolhendo Conversar ou Aguardar na interface. A fala natural é preservada dentro do envelope existente; esperar exige confirmação própria.
- O texto permanece em área de rolagem própria, com o painel de cena/ação visível.
  Esse painel não é uma ficha completa de personagem.
- A operação distingue preparação, narrativa pendente, confirmação e recusa.
  Consulta ou reconexão não reenviam a ação. Enquanto a mesma tela permanece montada,
  texto digitado e identidades são conservados. Após reload, a conexão explícita
  recupera apenas o último texto confirmado, sem restaurar o histórico local/input.
- Uma recusa preserva seu resultado e apresenta a limitação. Não haverá reparo
  automático, rerrolagem ou troca de modelo para contornar uma resposta recusada.

O propósito é avaliar entendimento da introdução, clareza das ações disponíveis,
visibilidade do estado e interesse em continuar uma cena. Não é uma nova rodada
para qualificar narrador nem uma aceitação de progressão insuficiente como regra
do produto. Os requisitos de agência, fidelidade e reação útil permanecem vigentes.

## Estado técnico e escolhas de experiência

| Parte | Estado real |
|---|---|
| Núcleo, produtor, retenção, consulta e composição local B | Implementados e verificados em provas próprias |
| Interface técnica separada e exemplo com respostas autoradas | Implementados e verificados; dois turnos autorados, não teste de modelo |
| Qualidade narrativa dos modelos | Parcial; nenhum narrador qualificado pelo comparativo encerrado |
| Aceitação deste recorte pelo usuário | Exercida em12/09/2026 pela execução protegida e envio de fala |
| Ativação para participação do jogador | Sessão6486 encerrada antes de HTTP; correção da entrada concluída; próxima execução será nova sessão |
| Campanha completa, modelo default e CAP-001 | Fora desta proposta |

A amostra técnica autorada permanece disponível como evidência separada. A ligação
interativa real foi preparada depois do diagnóstico: launcher protegido, runner
delimitado e entrada própria. A [preparação](feature-source-player-interactive-probe-1.md)
está concluída e verificada. Houve ativação pelo jogador, mas nenhuma inferência nessa sessão; a entrada foi corrigida após seu relato.

A modalidade concreta proposta agora é Qwen via Groq, até quatro chamadas, 768
tokens/chamada, intervalo mínimo de 60 s, diálogo/espera na Galeria com Mara.
Não é seleção de narrador definitivo nem adoção do SYSTEM B de orçamento.

## Limites antes do uso

Este recorte não inicia campanha sem cena, não muda de local, não introduz novos
NPCs e não cobre segredos, memória de longo prazo ou campanha híbrida. Para esta
primeira experiência proposta, testes mecânicos e a bandeja de dados ficam fora
do percurso, mesmo havendo componentes internos de teste ordinário. O lembrete
de orientação de perícias não se torna uma tarefa implementada.

O acesso proposto é pela interface local no computador que executa o projeto,
com backend e frontend em loopback, sessão escolhida pelo servidor e origem
esperada validada. Acompanhamento do desktop pelo Codex Remote não publica essa
API na internet nem equivale a autenticação por usuário. Contas, proxy e acesso
direto por outro dispositivo exigiriam uma decisão arquitetural separada; não
são necessários para esta proposta local.

## Decisão humana concreta

**Aceitar uma próxima experiência de uso B em uma única cena, inicialmente
centrada em diálogo e espera, com esses limites explícitos.**

Essa decisão aprova apenas o recorte que será experimentado. Não aprova a
qualidade narrativa, não reduz gates, não ativa o default e não substitui o jogo
completo atual. A preparação técnica reversível segue sob a autorização contínua;
a aceitação da experiência pertence ao usuário, conforme DEP-005 e REQ-009.

A execução protegida e o relato de uso pelo usuário registram a aceitação deste
recorte. A sessão6486 encerrou com zero chamadas; isso não é avaliação narrativa.
A correção de entrada foi concluída sob a autorização contínua, sem mudar a
cobertura. A próxima sessão usa controles explícitos de conversa/espera e mantém
os mesmos limites. Não solicitar outra aceitação rotineira.

Evidência: [observação e correção](../evals/narrator/reports/source-player-dialogue-correction-2026-09-12.md).
Preservar os lotes encerrados e não iniciar amostragem equivalente para buscar
um vencedor. As decisões de campanha/default/CAP-001 continuam separadas.

Referências: [composição técnica concluída](feature-narrative-source-local-handler-1.md),
[transporte e acesso local](feature-narrative-source-transport-1.md),
[resultado do diagnóstico](../evals/narrator/reports/source-word-budget-observation-291b3960-2026-09-12.md)
e [matriz de evidências](../evals/narrator/reports/source-model-choice-status-2026-09-12.md).
