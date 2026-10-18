# Protocolo prospectivo: resposta de NPC em diálogo

Em 12/09/2026, a sessão interativa 49fffca2 chegou às quatro chamadas e encerrou
por budget_completed. Em todos os textos, Mara permaneceu sem responder às
perguntas insistentes. A UI e o caminho técnico funcionaram. O primeiro turno
já falha sem fonte anterior; nos seguintes, a seleção de narrativas mantém o
silêncio como continuidade. O SYSTEM progress-v1 repete a exigência de reação
do ambiente e não explicita a resposta do NPC. Isso fundamenta uma hipótese de
incentivo inadequado, ainda sem demonstração causal.

## Pergunta e limite da conclusão

O novo SYSTEM dialogue-v1 permite uma resposta pertinente já no turno da fala,
recupera um diálogo após silêncio e conserva o comportamento de espera/agência?
São três contextos autorados independentes, uma chamada por contexto, apenas
Qwen via Groq. Não há baseline executado, comparação causal A/B, novo comparativo
de modelos, importação de braço histórico nem qualificação de narrador.
As narrativas antigas permanecem evidência do problema, não dados corrigidos.

## Mudança isolada e superfície

Novo arquivo experimental narrative-source-dialogue-v1.md, sem substituir
progress-v1 ou ativar variante na interface/default. A mudança exige resposta
pertinente do NPC e coerência n/q, permitindo desconhecimento ou recusa claros
sem forçar revelação, sucesso ou controle do jogador. Reação ambiental continua
válida em espera. Convites dentro de fala não viram movimento executado.

Corpus e protocolo próprios, congelados antes das chamadas. Novo consumidor
pequeno utiliza NarrativeSourceProposal, build_source_context,
create_source_projection e validate_source_proposal, com npc_aliases explícitos.
Transporte/evidência podem reutilizar RetainedObservationAdapter, sem chamar ou
modificar evaluators e comparadores antigos. Não monkeypatchar seus prompts,
corpora ou constantes. Sem nova plataforma genérica, banco, UI ou servidor.
O diagnóstico puro não valida produção de ação, commit ou retomada de campanha;
essas provas da sessão interativa ficam separadas.

## Execução delimitada

- Ordem fixa: direct-question, after-silence, wait-control.
- Cada fonte anterior é autorada e identificada como sintética; não foi gerada
  pelo provedor ou confirmada como mundo canônico. q não é parte da fonte.
- Qwen qwen/qwen3.8-27b, Groq oficial, reasoning none, temperatura 0,65.
- Até três tentativas HTTP; 768 tokens de saída solicitados por chamada,
  máximo solicitado de 2.304. Uma inicial e cada nova chamada esperam pelo
  menos 60 segundos. O deadline de 60 segundos começa depois dessa espera.
- Contagem e intervalo conferidos imediatamente antes do envio HTTP, sem
  renovar deadline, compensar chamada falhada ou realizar retries/fallback.
- Qualquer falha operacional, schema inválido ou recusa da política encerra
  os envios restantes, registrados como skipped. Não repetir slot ou lote
  automaticamente. Avaliação narrativa ocorre após a execução delimitada.
- Preflight sem chave/rede/DB. Live somente com preflight idêntico e credencial
  SecureString fornecida ao processo-filho, jamais .env, arquivo ou argumento.
- Artefatos: preflight e binding, registros por tentativa, summary, hashes,
  parâmetros, cronologia, rota, uso, política e resultado de verificação local.
  Filtrar eco da chave antes de persistir qualquer captura. Não salvar headers.

## Critérios antes da observação

Critérios técnicos existentes: schema n/q, idioma, extensão, roster, agência,
segredos, rota explícita e orçamento. Todos permanecem inalterados. Testes
locais devem demonstrar que uma resposta de NPC é admitida e que comandos do
jogador, vazamento, campos privilegiados extras no schema e excesso continuam recusados.

A presença de NPC novo apenas na prosa de n permanece critério narrativo: o
gate atual não garante sua detecção. Aceitação técnica não comprova respeito
ao elenco em texto livre.

Critérios narrativos por caso constam do corpus. direct-question precisa de
resposta relevante ou limite claro em n. after-silence precisa superar a mesma
hesitação sem deslocar o jogador a partir de convite falado. wait-control
precisa desenvolver um elemento anterior sem decidir a ação do jogador.
Em todos, q deve corresponder a um acontecimento realmente mostrado.

Uma recusa pertinente pode ser boa narrativa; silêncio não é proibido em todo
o produto. Neste diagnóstico, a espera indefinida pela resposta, com gestos ou
ambiente cada vez mais intensos, não satisfaz responsividade. Improvisação
sensorial não é rejeitada por ser nova. Alegações de NPC continuam atribuídas.

Um resultado técnico aprovado apenas libera a leitura narrativa da amostra.
Mesmo três respostas satisfatórias não aprovam default, modelo, campanha ou
CAP-001. Registrar falhas e limites; decidir próximo trabalho a partir deles,
sem afrouxar critérios ou colecionar novas tentativas até obter êxito.
