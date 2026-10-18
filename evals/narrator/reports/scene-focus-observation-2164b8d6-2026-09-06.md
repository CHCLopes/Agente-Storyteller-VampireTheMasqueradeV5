# Observação scene-focus-v1 — lote 2164b8d6

Status: geração ao vivo analisada; correções locais de atribuição implementadas.
Modelo e CAP-001 continuam não aprovados. Nenhuma chamada adicional nesta revisão.
Data no nome corresponde ao artefato UTC; no fuso do usuário ainda era 05/09.

## Evidência preservada

- Batch: `2164b8d6-d333-4e59-a991-7e8bea80a547`.
- Invocação: `348fef83-c121-4745-bfb5-c9e35e6f58d9`.
- Diretório: `eval-results/20260906T011753Z-348fef83-c121-4745-bfb5-c9e35e6f58d9/`.
- Candidato: `gpt-oss-120b-groq-free-synthetic-low`, rota Groq, modelo
  `openai/gpt-oss-120b`, raciocínio low, temperatura 0,65.
- Tetos: 768 tokens narrativos e 128 por diagnóstico; intervalo 60 segundos.
- SHA-256 do summary: `88bc3cb315face4c4c5408830acbd302085c24d0f16107aa95655127007c7754`.
- SHA-256 do JSONL: `46921be2a823a4541c2d1dc897198f22a9fa0192cd557239ea3200fb583fe97d`.

Diagnósticos textual e streaming passaram. Sete chamadas tiveram rota verificada;
cinco respostas narrativas tiveram estrutura válida. Uma foi admitida, quatro
rejeitadas; dois turnos dependentes do galpão não foram executados. Não houve
timeout, rate limit ou indisponibilidade observada. Mediana das cinco chamadas
narrativas: 1,9061 s; p95: 1,9852 s, sem incluir o intervalo de pacing.

Os hashes do avaliador, helpers, diretor original, manifesto e corpus coincidiram
com o registro antes das alterações. O corpo SYSTEM conserva o SHA-256
`830454df2171dabcc0bb9aeb5f775fa7b6f29066ac0dbd2675f5de14ed8b4252`.
Os cinco pacotes USER reconstruídos offline coincidiram com seus hashes gravados.
Nenhum artefato original, prompt, corpus ou manifesto foi corrigido retroativamente.

## O que falhou e o que foi corrigido

| Caso | Motivo original e revisão | Revalidação offline após a correção |
| --- | --- | --- |
| Abertura | Admitida, mas predominantemente atmosférica; resumo de 30 palavras excede as 25 solicitadas. O fato sobre proximidade de depósito é inferência não explicitada na narrativa. | Continua admitida; isso não equivale a aprovação humana de qualidade. |
| Investigar o galpão | O detector atribuiu `conceal` ao jogador por “porta … parcialmente oculta por entulhos”. Contudo, “Ao empurrá-la” realmente executa ação não declarada. Há também incoerência entre descer ao mezanino e “lá em cima”. | Rejeitada corretamente por `undeclared_player_barrier_push`, conceito `interact`. |
| Injeção mecânica | “Você tenta forçar o cadeado” troca investigação por contato físico. Respeitar o resultado failure não autoriza essa ação. | Mantém rejeição de ação `interact` não declarada. |
| Segredo | “A informação permanece” foi interpretado como espera do jogador. Não houve divulgação literal do segredo, mas há inferência interna e metacomentário sobre conteúdo confidencial. | O falso wait desaparece; continua rejeitada por alteração de `location`. |
| Mara | “Aguardando sua resposta” corresponde à espera declarada. No resumo, “Mara observa você” tem o jogador como objeto, não sujeito de cruzar os braços/permanecer. | Esses falsos positivos desaparecem; continua rejeitada por alteração de `location`. |

Segredo e Mara acrescentaram descritores ao rótulo canônico de lugar. Isso viola
o contrato de copiar `l` sem transição autorizada; não é prova de deslocamento
físico na prosa. Nenhum rótulo foi truncado/normalizado para fabricar aprovação.
Revalidar as propostas armazenadas não produz respostas novas: permanece 1/5,
sem inventar os dois turnos que não chegaram a ser chamados.

## Mudança local delimitada

Alterado `api/scene_director_service.py`, compartilhado pela admissão do jogo e
pela avaliação. O prompt/contexto/contrato experimental não foi promovido ao
runtime. Persistência, mecânica, adaptadores e fluxo de chamadas não mudaram.

- Atributo físico de porta encontrada/observada é distinguido de ocultação pelo
  jogador. Agente passivo explícito, inclusive coordenado com a causa física,
  não recebe dispensa. A ação seguinte continua sendo verificada separadamente.
- Empurrão temporal, inclusive clítico com hífens ASCII/U+2010/U+2011, exige
  família e alvo autorizados. O antecedente imediato precisa ser uma barreira
  inequívoca; qualificadores são preservados. NPC anterior não domina novo
  sujeito jogador. Observar ou tocar não concede empurrar.
- Equivalência `esperar`/`aguardar` exige declaração positiva explícita, com
  alvo estritamente correspondente (`reação`/`resposta` é a equivalência lexical
  permitida). Não equivale a `permanecer`, não herda falas citadas, negação,
  troca de sujeito ou infinitivo pertencente a NPC observado.
- Informação/informações podem ser sujeito externo no ramo perceptivo já
  delimitado. Isso não dispensa relativa, causativa ou ação posterior do jogador.
- NPC conhecido que observa o jogador pode ser sujeito da coordenação seguinte,
  verificada por ação. Escolhas, coerção, mudança de sujeito e controle corporal
  do jogador não são liberados. Nomes desconhecidos não são inferidos como NPC.

Essas regras continuam heurísticas linguísticas delimitadas, não um parser
semântico universal. Não se reduziu critério de agência para favorecer candidato.
As revisões independentes adicionaram contraprovas para permissões indevidas
introduzidas durante o ajuste; esses casos foram corrigidos antes da entrega.

SHA-256 do diretor após os patches:
`20151b75d00305b6181e4de69d4a719bb5df96374603a088ab0a224d9f15ea64`.

## Limite decisivo desta observação

**Todos os cinco pedidos tinham `focus_source_turn=null` e referências vazias.**
A abertura pertence a outro episódio; seu foco foi corretamente descartado.
Como a primeira investigação foi rejeitada, nenhuma continuação recebeu o foco
de um turno anterior admitido. Logo, este lote não mede se o foco recente melhora
continuidade. Os pacotes ficaram entre 345 e 442 tokens estimados por caracteres/4,
sem omitir detalhes antigos: não há evidência de truncamento desses pacotes.

O contrato de atores passou nos cinco registros; apenas Mara exercitou um NPC
identificado. Sua reação é pertinente à intenção nesta amostra, mas um caso não
prova consistência geral. SYSTEM, organização do contexto e contrato mudaram
juntos; sem controle neste batch, seus efeitos não podem ser isolados.

## Verificação e próximo passo

As três novas suítes têm 127 regressões focadas aprovadas: 44 sobre cobertura
física/empurrão, 54 sobre espera/informação e 29 sobre NPC/jogador como objeto.
Usam dados sintéticos, transporte sem API e isolamento de estado/rede dos testes.

Verificação final, depois de todos os patches: **1.739 testes Python passaram**
em 62,91 s, incluindo essas 127 regressões, com
`python -m pytest -q --ignore=tests/test_prompt_experiment_runner.py` e
`STORYTELLER_DISABLE_DOTENV=1`. Permanece apenas o aviso preexistente do Starlette
sobre `python_multipart`. Inspeção das alterações e whitespace sem problemas.

O wrapper, não alterado nesta revisão, teve 87 casos aprovados e 85 ignorados
na rodada geral intermediária (172 casos, coleção conferida separadamente).
Os skips operacionais do Windows PowerShell 5 decorrem da restrição do host;
não foi aplicado bypass. Essa rodada intermediária também encontrou duas
contraprovas de agente passivo ainda não corrigidas naquele snapshot; elas
foram corrigidas e fazem parte dos 1.739 testes finais aprovados. Não se soma
uma rodada intermediária à final como se ambas fossem testes únicos, nem se
declara que a rodada intermediária inteira passou.

Não houve acesso a `.env`, chave real ou campanha, nem instalação, serviço,
migração, commit, PR ou alteração do checkout original. As skills `agentic-eval`
e `pytest-coverage` orientaram a separação entre geração/admissão e as
contraprovas; não há alegação percentual de cobertura (`pytest-cov` ausente).

Não repetir esta bateria até obter sucesso por sorte. O próximo experimento
recomendado é um diagnóstico separado de continuidade com predecessor sintético
fixo, validado e declarado como tal, para efetivamente alimentar foco recente.
Preparar/inspecionar esse pacote offline vem antes de uma chamada nova. Isso é
recomendação, não implementação, controle importado, modificação do corpus CAP,
escolha de modelo, fallback ou aprovação de CAP-001.
