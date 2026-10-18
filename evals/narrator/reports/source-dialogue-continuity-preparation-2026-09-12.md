# Preparação de dois diálogos encadeados pelo fluxo B

A observação 81cb2b57 foi encerrada com integridade técnica aprovada e resultado
narrativo parcial: resposta mínima, recusa reconhecível mas pouco concreta e
espera com consequência observável. Seus três contextos eram independentes.
Esta preparação cobre a lacuna seguinte: narrativa gerada, commit confirmado,
seleção da fonte persistida e uso dessa fonte no segundo diálogo.

O SYSTEM dialogue-v1, Qwen qwen/qwen3.8-27b via Groq, parâmetros e gates
existentes foram preservados. Não há nova escolha de modelo ou variante para
buscar uma resposta favorável. O consumidor novo compõe as APIs B existentes,
sem alterar núcleo, interface, configurações padrão ou avaliações históricas.

## Recorte prospectivo

Uma sessão SQLite sintética nova, com Galeria e Mara, receberá duas falas fixas:

1. `Digo a Mara: "Mara, o que é este lugar?"`
2. `Digo a Mara: "Mara, explique melhor sua resposta."`

T2 só pode ser preparado depois do commit íntegro de T1. Sua fonte é o n
efetivamente salvo, sem edição, resumo manual ou transformação de q em fonte.
O preflight congela ações, configuração e código de construção; não declara
como pronto um corpo HTTP que ainda depende da geração e da cápsula.

Até dois envios HTTP, 768 tokens solicitados por envio e até 1.536 no total,
temperatura 0,65 e reasoning none. Há espera inicial e espaçamento mínimo de
60 segundos antes de P; preparação e H6 compartilham um único deadline de
60 segundos depois da espera. Falha operacional, schema, política ou
persistência interrompe os turnos restantes. Sem retry, fallback ou rerrolagem.

Após a execução, a operação terminal é consultada/reexecutada com persistência
reaberta e gateway proibido, para comprovar recuperação do resultado sem nova
produção. Os artefatos registram a relação entre P/K/H, fonte, pedido e resposta.
A auditoria separada confere consistência dos arquivos e da persistência sem
reescrever os brutos originais.

## Verificação da preparação

Foram aprovados 33 casos distintos do consumidor em etapas e 60 casos do lançador, sem chamadas reais. Não se somaram reexecuções como casos novos. O consumidor usa as APIs reais de preparação, retenção e aplicação sobre SQLite sintético; o transporte HTTP dos testes é simulado.

O primeiro recorte do consumidor teve 27 aprovações e cinco falhas. Treze casos afetados passaram após correções localizadas: preservação do timestamp de envio ao descartar eco de credencial, recomposição correta do estado timed_out e rejeição de observações HTTP/finish incompatíveis com sucesso. Uma contraprova adicional demonstrou snapshots com dados de erro apesar de declararem indisponibilidade; a correção exige igualdade com o snapshot vazio completo. Os quatro casos finais selecionados passaram, incluindo a composição válida de dois commits. Os 33 identificadores foram reconciliados pelo último resultado; versões, deltas e resultados vermelhos permanecem arquivados.

O lançador passou em duas seleções disjuntas de nove e 51 casos com as mesmas versões de código e testes. Foram verificados isolamento da credencial, orçamento, integridade do preflight e encerramento do processo próprio. O consumidor verificou o uso do n commitado em T2, separação de q, parada antes de T2 em falhas, deadline compartilhado, replay sem gateway/produção/RNG, adulterações e inspeção da persistência antes da gravação do resumo nos casos de eco sintético.

A revisão independente leu os deltas e as provas, sem repetir as suítes. As receitas de reprodução do consumidor foram registradas após as execuções; os logs, XML e hashes antes/depois constituem as provas das execuções observadas. O aviso preexistente de depreciação Starlette/python_multipart foi preservado, sem mudança de dependências. Não houve nova inferência, leitura de .env ou uso de credencial real nesta preparação.

Preflight final `9b21955c-3d46-4c76-a453-8d703a7f5891`: exit 0, status
`preflight_only_completed`, 33 arquivos de entrada conferidos e duas
ações fixas. Nenhuma chave solicitada, inferência ou banco de execução criado.
SHA do preflight: `8eef86e1c47f96974fd5e28a49ba78e7196fbfa61966774f148fc610d5bdcfc6`.

Checkpoint `eval-results/checkpoints/source-dialogue-continuity-preparation-20260912/manifest.json`: 97 cópias verificadas,
SHA `ebe2721a72838aaaaf2be744aadb39a0af9914dfa4f99878183a88e3ffd1ce50`. As 41 cópias da observação 81cb2b57
e seus originais permaneceram idênticos. Trabalho no b008, branch
`codex/planejamento-agente-storyteller-v5`; checkout original master preservado.
Sem commit, push ou merge.

## Limites e continuidade

Testes locais e preflight não avaliam a qualidade do próximo texto do modelo.
Os critérios narrativos foram fixados por turno antes das chamadas e incluem
resposta pertinente, explicação consistente com a resposta ou recusa anterior,
consequência conversacional e preservação da iniciativa do jogador. Uma recusa
pode ser adequada; baixa especificidade deve continuar visível na avaliação.

Os limites conhecidos do gate lexical de movimento em fala e da detecção de
NPC extra em prosa permanecem inalterados. Não há garantia genérica de
encerramento de árvores arbitrárias de processos ou queda abrupta do host.
Interrupção abrupta pode impedir a gravação final mesmo após consumo de
chamadas; ausência de artefatos não demonstra ausência de inferência nem
autoriza repetir o lote. Hashes demonstram consistência local, não autenticidade
externa do provedor. Custos e limites atuais da conta não foram presumidos.

O próximo passo é uma única execução no PowerShell 7 com a credencial protegida.
O consumidor realizará as duas ações automaticamente, sem navegador ou entrada
manual de falas. Depois, conferir os artefatos e avaliar os textos completos.
A dependência humana é a chave na sessão protegida; a autorização técnica para
o escopo permanece vigente. Nenhuma promoção de modelo, runtime, campanha,
interface ou CAP-001 está implícita nesta preparação.
