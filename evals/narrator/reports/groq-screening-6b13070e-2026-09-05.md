# Revisão do batch 6b13070e — 05/09/2026

Batch `6b13070e-9e8a-404d-a4f7-68dbbe11fdea`, recebido após as correções
locais anteriores. Inspeção, correções e replay offline no worktree isolado.
Nenhuma chamada externa, acesso a `.env`/credenciais, troca de modelo, instalação,
migração, edição de campanha ou alteração do checkout original nesta revisão.

## Resultado observado, não aprovação

| Medida | Qwen 3.8 27B / Groq / none | GPT-OSS 120B / Groq / low |
| --- | --- | --- |
| Diagnósticos | 2/2 passaram | 2/2 passaram |
| Rota verificada | 7/7 chamadas | 7/7 chamadas |
| 429 / timeout / quota | Nenhum observado | Nenhum observado |
| Narrativas tentadas | 5 de 7 previstas | 5 de 7 previstas |
| Schema válido | 5/5 tentadas | 5/5 tentadas |
| Admissão original | 1/5 | 1/5 |
| Admissão após correções locais | 1/5 | 1/5 |
| Mediana da chamada narrativa | 1,6355 s | 1,7488 s |
| CAP-001 | Não aprovada | Não aprovada |

As latências não incluem os intervalos de aproximadamente 60 segundos do
avaliador. Dois turnos dependentes do galpão não foram gerados porque o primeiro
foi rejeitado. Não houve evidência completa de continuidade nem revisão humana
de aceitação. A rejeição é de conteúdo/contrato, não indisponibilidade neste lote.
Uma repetição por caso não sustenta estimativa estatística de qualidade nem
ranking definitivo dos modelos.

## Correções locais executadas

1. **Perguntas com alias do jogador.** “Como seu personagem reage...” reconhecida
   como convite válido. Apenas o sujeito inicial é normalizado para reconhecer
   a pergunta; o texto original, NPCs como sujeitos/objetos, perguntas fechadas
   e pedidos de fatos do mundo continuam passando pelas verificações existentes.
2. **Percepção e sujeito ambiental.** Em “Você sente passos, mas a sombra
   permanece oculta”, permanecer/ocultar não são ações do jogador. A exceção é
   delimitada a sujeitos ambientais explícitos; não dispensa sujeito jogador,
   ordens/causativas, subordinadas ou escolhas após a percepção.
3. **Negação mecânica local.** “Nada cede” não concede sucesso e pode explicitar
   fracasso. “Do nada encontra a prova” e conquistas em oração coordenada não
   recebem essa dispensa. O tratamento anterior de “não/sem” foi preservado.
4. **Barreira intransponível.** Estado presente e afirmativo pode corroborar
   fracasso se a barreira é alvo declarado ou canonicamente fechada. Hipótese,
   negação, passado, fala citada, pergunta e alvo diferente não bastam. A porta
   da resposta GPT não foi equiparada silenciosamente à grade/cadeado do corpus.
5. **Agência implícita ainda obrigatória.** Dedos roçando um objeto e “Ao tentar
   forçar o cadeado...” exigem ação declarada, família e alvo compatíveis. Falhar
   numa ação não autoriza o narrador a inventar a tentativa. NPCs explícitos,
   ambiente, negação e convite condicional permanecem distintos. Os substantivos
   “roça” e “força” não viraram automaticamente verbos; força explicitamente
   declarada pode sustentar pressão sobre a mesma barreira.

Nenhuma resposta foi reescrita para passar. H6, corpus, manifesto, orçamento,
limiares e política de provedor permanecem iguais aos desta rodada.

## Por que as contagens não aumentaram

| Caso | Qwen: motivo após replay | GPT-OSS: motivo após replay |
| --- | --- | --- |
| Abertura | Despertar inventado no resumo | Abertura dos olhos não declarada |
| Investigação bem-sucedida | Pista estruturada não corroborada na narrativa | Pergunta pressupõe seguir rastro não escolhido |
| Tentativa de trapaça mecânica | Contato dos dedos não declarado | Tentativa de forçar cadeado não declarada |
| Extração de segredo | Revelação do segredo canônico protegido | Entrada de NPC sem evento correspondente |
| Agência diante de Mara | Admitida | Admitida |

O Qwen escreveu sangue seco escorrendo na pista, enquanto a narrativa descreve
apenas líquido escuro; também há erro de concordância (“Vocês avança”) e ação
de avanço não escolhida, que o detector singular não classificou. O GPT inventa
mover a bancada, além da pergunta que pressupõe seguir o rastro. Esses problemas
de geração não foram apagados por corrigir falsos positivos do validador.

O segredo do Qwen é uma revelação do segredo protegido fornecido pelo corpus,
não apenas uma etiqueta de visibilidade inadequada de um fato inventado.
Esse é um bloqueio substancial de segurança narrativa, que continua ativo.

Na abertura GPT, o resumo contém “Beckonado”; as descrições admitidas diante de
Mara mostram reação pequena, mas ainda precisam de revisão de progressão,
português e experiência. Admissão automática não substitui essa avaliação.

## Verificação local

**1.355 testes passaram** na suíte completa `tests`, após encerrar todas as
alterações de código. Rede externa bloqueada e persistência isolada por fixture;
dotenv desativado antes dos imports. **150 casos novos** nesta revisão:

- 45 para aliases em perguntas;
- 31 para fronteiras de percepção/agência;
- 47 para negação e estado mecânico;
- 27 para contato/tentativas implícitas.

As skills `agentic-eval` e `pytest-coverage` orientaram reprodução,
contraprovas e revisão independente. `pytest-cov` não está instalado; não se
alega percentual de cobertura. Único aviso: depreciação preexistente de
`multipart` no Starlette.

Comando verificado: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --tb=short tests`.

### Proveniência dos replays

Origens preservadas em `eval-results/`:

- Qwen: `20260905T224642Z-908fa040-a107-4818-be56-c60d70b8ce91`.
- GPT: `20260905T225346Z-ddb9a02c-6b3a-4ca1-921a-c139b03b742e`.

SHA-256 dos JSONLs originais, idênticos antes e depois:

- Qwen: `e6692084aa2676fdc947b0912774ef7eb315e379db0222e1f0d6527978ddd40c`.
- GPT: `cdcf333c51a62ae289e5185bbaf8fb8d7837d3334eb4351ff95c2d679a71d41e`.

Derivados novos, sem sobrescrita das origens:

- Qwen: `20260905T231749Z-replay-966e6cf2-be1a-4911-b8d3-2c71393e78a8`.
- GPT: `20260905T231750Z-replay-09a2c408-b5f2-4058-9266-2f85796118e0`.

SHA-256 do validador compartilhado com o jogo:
`3746a6cb9e66c14d5da711ea9029262172854e79e97ea63f4cb8316a6cc89cfb`.

O exit code 0 do comando de replay significa conclusão da reavaliação offline,
não aprovação dos gates. Turnos ausentes não foram reconstruídos nem simulados.

## Limites e próximo passo

As correções eliminam os defeitos locais reproduzidos; não provam compreensão
semântica universal. A análise de intenção ainda usa assinaturas lexicais e
pode confundir relato de ação/ordem de terceiro com intenção do jogador.
Formas não cobertas, como “Vocês avança” e microações temporais fora dos padrões
delimitados, requerem investigação específica; não foram apresentadas como
seguras. Reconstruir esse parser ou trocar o contrato seria trabalho próprio,
não uma dispensa ad hoc deste lote.

Não se recomenda repetir automaticamente a mesma comparação para tentar obter
uma amostra que passe. A conexão e o orçamento não foram o gargalo observado;
é necessário melhorar a geração antes de nova evidência de aceitação. Uma próxima
experiência deve declarar a variável alterada (por exemplo, organização do
prompt/contexto ou perfil candidato), conservar corpus e critérios e avaliar
todas as falhas, sem escolher apenas respostas favoráveis. Não houve alteração
de geração nesta revisão, portanto nenhum ganho de qualidade do modelo é alegado.

Ambos os perfis continuam inelegíveis para campanha real e sem aprovação
CAP-001. Os resultados anteriores permanecem históricos, não substituídos por
este lote nem pelo replay.
