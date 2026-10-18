# Protocolo prospectivo: dois diálogos pelo fluxo retido B

O diagnóstico 81cb2b57 concluiu três contextos independentes com admissão
técnica. A revisão encontrou resposta mínima no primeiro, recusa reconhecível
mas recuperação parcial no segundo e espera com consequência observável.
Isso não prova uma conversa encadeada. Esta observação aborda a lacuna de
composição: n gerado → commit → fonte selecionada → segundo diálogo.

## Superfície e autoria

Consumidor novo usa create_source_producer_config, prepare_source_player_action
e execute_retained_source_turn nas APIs atuais, com SQLite e sessão sintéticos
novos. Nenhum handler, router, UI, modelo/default ou helper histórico é alterado.
Reutilizar contratos e observador protegido como bibliotecas; não chamar antigos
evaluators nem monkeypatchar seus prompts, corpora, parâmetros ou constantes.
Não criar plataforma genérica. Não reutilizar banco de ensaio anterior.

SYSTEM dialogue-v1 permanece exatamente o mesmo da observação 81cb. Cena
autorada inicial: Galeria, Mara presente e alias confiável explícito. Duas
falas do corpus são fixadas antes da execução. O primeiro contexto não contém
fonte narrativa anterior. O segundo usa somente a narrativa realmente admitida
e commitada em T1 pelo fluxo existente. q não vira fonte; o texto não é corrigido,
resumido à mão ou substituído para favorecer o segundo turno. Fonte atribuída
não confirma como verdade canônica todas as alegações de Mara.

## Limites fixos

- Qwen qwen/qwen3.8-27b, Groq oficial, reasoning none, temperatura 0,65.
- Até dois envios HTTP, um por turno; 768 tokens solicitados por envio e até
  1.536 tokens de saída solicitados no total. Sem diagnósticos adicionais.
- Espera inicial e intervalo entre HTTP de pelo menos 60 segundos. Esperar
  antes de preparar P; depois iniciar um único deadline de 60 segundos
  compartilhado por preparação e H6, sem renovar durante a operação.
- Conferir limite, corpo esperado, identidade, rota e deadline imediatamente
  antes de cada HTTP. Nenhum retry, fallback, rerrolagem ou reaplicação.
- T2 só é preparado após commit íntegro de T1. Falha operacional/schema/política
  ou inconsistência de persistência encerra o lote; registrar o restante como
  skipped. Não buscar outra resposta. Avaliar narrativa somente após o lote.
- Chave SecureString recebida apenas pelo processo de inferência. Retirar a
  variável dedicada antes de qualquer filho Git. Não abrir .env nem salvar
  cabeçalho, chave, erro bruto ou eco da chave. Preflight/auditoria sem chave.

## Vinculação e verificação

O preflight congela corpus, protocolo, SYSTEM, parâmetros, schema, configuração
e código de construção. O corpo de T2 ainda não existe; nunca apresentar um
hash prospectivo como se já contivesse a resposta do provedor. Após T1, vincular
o pedido real à cápsula, ao snapshot autoritativo, ao envelope e ao hash do n
efetivamente commitado, conferindo essa composição antes de enviar T2.

Guardar pedidos e respostas protegidos, evidência de provedor, identidades,
cronologia, hashes e os contadores P/K/H/attempts/turnos/eventos. Conferir o
segundo USER contra o n normalizado do primeiro envelope e excluir q da fonte.
Depois das chamadas, reabrir persistência e consultar/reexecutar a operação
terminal com gateway proibido; o resultado confirmado deve ser preservado sem
nova produção, HTTP, RNG ou mutação. Esses acessos são locais, não novos turnos.
Fechar SQLite antes da auditoria; preservar os arquivos efetivos, incluindo
WAL/SHM se existirem. Não presumir SQLite immutable com WAL não vazio.

O verificador separado deve recompor integridade do resumo, JSONL e projeções
da persistência, vínculo entre os turnos, budgets/tempos/rota e replay. Asserções
de bytes não substituem a revisão narrativa. O encerramento abrupto pode impedir
os artefatos finais; sua ausência não prova zero chamadas nem libera repetição.

## Critérios e limites da conclusão

Os critérios narrativos constam por turno no corpus. Resposta curta ou recusa
podem ser pertinentes; registrar falta de especificidade e pouca consequência,
sem mudar critérios após ver a saída. Se T1 permanecer sem resposta, isso é uma
falha narrativa observada, não motivo para corrigir sua fonte antes de T2.
Improvisação atribuída é permitida; preservar agência, mecânica e separação das
fontes. O gate lexical de movimento dentro de fala e a detecção incompleta de
NPC novo na prosa continuam limites conhecidos, sem alteração por arrasto.

Esta é uma observação de composição com SYSTEM idêntico, não novo braço para
ganhar taxa, comparação causal A/B, escolha definitiva de modelo ou aprovação
de UI/campanha/runtime/CAP-001. Não reclassificar os resultados anteriores.
