# Preparação do diagnóstico de resposta de NPC

Em 12/09/2026, o ensaio interativo `49fffca2` terminou normalmente ao atingir
quatro chamadas. Integridade técnica aprovada: quatro HTTP 200/stop, quatro
turnos confirmados, intervalos e deadlines respeitados. A revisão narrativa
identificou a falha de experiência: Mara permanece sem responder nas quatro
iniciativas; as perguntas finais dos dois primeiros turnos pressupõem uma
resposta que não foi mostrada. A ambientação nova é improvisação válida; sua
repetição não substitui uma resposta pertinente.

Foi preparada uma variante SYSTEM experimental em arquivo próprio,
`narrative-source-dialogue-v1.md`. Ela admite informação útil, desconhecimento
ou recusa claros, pede coerência entre narrativa e pergunta final e distingue
convite falado de ação executada pelo jogador. Não substitui o prompt anterior
nem ativa uma variante na interface ou no runtime padrão.

O corpus tem três contextos autorados independentes: pergunta direta a Mara,
nova pergunta após silêncio e espera diante de um elemento concreto da cena.
As fontes sintéticas não são saídas do provedor, commits ou fatos canônicos.
Os critérios foram fixados antes da execução. O consumidor reutiliza o perfil
n/q e o transporte protegido existentes, com aliases explícitos. Núcleo,
validators, UI, prompts e evaluators históricos permanecem inalterados.

## Execução preparada

- Alvo explícito: Qwen `qwen/qwen3.8-27b`, Groq oficial, reasoning none.
- Até três tentativas: temperatura 0,65; 768 tokens por tentativa; máximo
  solicitado de 2.304 tokens de saída.
- Espera inicial e intervalo entre chamadas de pelo menos 60 segundos;
  deadline individual de 60 segundos iniciado após a espera.
- Qualquer falha operacional, de schema ou de política interrompe o restante;
  slots restantes ficam skipped. Sem retries, fallback ou chamada compensatória.
- Não há DB, UI, servidor, baseline ou comparação causal A/B neste diagnóstico.
- Credencial SecureString somente no filho de inferência; preflight e
  verificação dos artefatos não recebem a chave. O objeto do chamador é preservado.

## Verificação offline

A primeira etapa do consumidor reuniu 76 casos distintos aprovados. A rodada
teve 75 aprovações e uma falha no próprio teste da limitação de NPC em prosa:
o teste acessava `narrative_text`, enquanto a API retorna `narrative`. Somente
esse atributo foi corrigido; o caso afetado passou na segunda rodada. Não se
contam reexecuções como novos casos. Evaluator e protocolo permaneceram iguais
durante as duas rodadas.

As provas incluem os três contextos e aliases reais, preservação dos gates,
parada por falha, cancelamento, cadência, deadline, orçamento, supressão de eco
de chave sintética e rejeição de adulterações com hashes recalculados. Nenhuma
chave real, chamada ao provedor ou banco foi usado na preparação.

O lançador tem 73 casos distintos aprovados em etapas: oito iniciais,
64 restantes e seis focais finais, com reexecuções reconciliadas. Foram
verificados PS7, preflight antes da credencial, cópia de SecureString sem
alterar o objeto do chamador, isolamento, deriva das fontes, verificador e
encerramento do stub da venv e do evaluator real.

A revisão manteve `Kill(true)` como proteção conservadora da árvore própria.
O controle anterior também encerrou stub/evaluator no teste corrigido; não
há demonstração de ganho causal nesse recorte. A exploração com outra árvore
Python artificial deixou descendente ativo; taskkill excedeu o limite do
harness e não foi adotado. Observadores iniciais sem sucesso explícito na
ausência de PID e uma execução inválida por caminho longo foram preservados
e classificados. A prova final cobre o processo real que chama Groq, sem
garantia genérica para árvores extras ou encerramento abrupto do host.

O preflight integrado final `3abaa31f-d8f9-45f0-ad86-ddc1adf6d9c5` passou com exit 0,
status `preflight_only_completed`, 25 arquivos de entrada e três
requisições congeladas. Não pediu chave e não criou diretório de inferência.
SHA do preflight: `28393e5906af7a1358f409937c8530ca0af137a278898f9c933e71e2606fe26a`.

A revisão encontrou e corrigiu uma herança evitável da variável dedicada:
o ramo live fazia consultas Git de proveniência antes de retirar a chave do
ambiente. Duas contraprovas sintéticas reproduziram isso, em sucesso e drift.
A retirada agora ocorre antes dessas consultas, mantendo a chave em SecretStr
local. Helpers históricos não foram editados. Os 13 casos afetados passaram,
incluindo dois novos e 11 revalidados: total final de 78 casos distintos do
consumidor, somados aos 73 do lançador, 151 distintos no diagnóstico.

O preflight anterior 40172e00 fica como evidência intermediária, anterior a
essa correção. O preflight final foi repetido com as fontes corrigidas.
A revisão independente fechou sem pendência na preparação; seus achados,
contraprovas e limites estão no checkpoint.

Checkpoint: `eval-results/checkpoints/source-dialogue-response-preparation-20260912/manifest.json`,
127 cópias verificadas, SHA `ed8b26daba0ae1805ab62c21f8cf40aa6bf0aa55b98167b3a19e687ceeb1f962`.
As 66 cópias do ensaio anterior e seus 45 arquivos de implementação/UI
continuam idênticos, assim como o trecho histórico da retomada.
Checkout original master limpo; trabalho mantido no b008, branch
`codex/planejamento-agente-storyteller-v5`, HEAD `5e563824fcba4c53cc37b5084a8ce65f3fa30356`.
Sem commit, push ou merge.

## Limites e próximo passo

Aceitação automática não comprova qualidade narrativa. O gate existente pode
autorizar movimento a partir de palavras em fala entre aspas e não garante
detectar um NPC novo somente em prosa. Esses limites foram registrados; não
foram corrigidos por arrasto nem ocultados por critérios mais permissivos.
O protocolo foi corrigido prospectivamente para distinguir campo extra de
schema e personagem extra na prosa, antes dos testes e de qualquer inferência.

Os registros e o resumo são persistidos na finalização normal, inclusive nos
cancelamentos tratados. Término abrupto do processo/host pode impedir a criação
dos artefatos finais; sua ausência é inconclusiva e não autoriza repetir o lote.
O diagnóstico puro não demonstra a composição completa de ação, commit,
retomada de campanha ou interface. Os resultados do ensaio interativo ficam
em evidência separada.

Próximo passo: executar uma única vez o lançador protegido no PowerShell 7 do
usuário. Ele realiza automaticamente as três ações fixas e verifica os
artefatos. A única dependência humana é disponibilizar a credencial no shell
protegido; não é uma nova aprovação de escopo. Depois, auditar os artefatos e
avaliar os critérios narrativos, sem repetir tentativas para buscar êxito.
Qualidade, modelo, runtime padrão, campanha e CAP-001 permanecem sem aprovação.
