# Proposta de despacho local B — preparação de TASK-001

11/09/2026. Proposta documental anexada ao plano; nenhuma rota ou integração implementada por este documento.
Não decide modelo, não ativa experiência e não declara integração/testes prontos.

O próximo incremento pode preparar seleção e provas inativas do ensaio de um
operador no desktop, já previsto no plano de transporte (linhas 60, 169–175).
A escolha de API acessível diretamente de outra máquina permanece fora deste recorte.

## Ponto de entrada e efeitos existentes

- O ponto mínimo de despacho é antes de `api/main.py:649`, o primeiro `accept`
  de `websocket_endpoint` (`:647–648`). A seleção precisa anteceder também a fila
  e a tarefa leitora desse handler; não basta trocar apenas o narrador mais adiante.
- O legado chama `load_session_state` em `main.py:696`, cria estado ausente e o
  salva em `:698–710`, carrega/salva relações em `:712–715`, abre contexto de sessão
  em `:717–722`, decodifica a ação em `:743` e reserva tentativa em `:814–821`.
- `api/state_service.py:222–240` mostra que a leitura legada inclui migração de
  JSON em `:232`; por isso ela não serve para descobrir se uma sessão é B.
- Limite adicional: `api/main.py:144–149` recupera tentativas no lifespan, antes
  de qualquer WebSocket. Uma guarda no handler não prova ausência de atividade
  legada no bootstrap. O futuro ensaio precisa preservar o banco sintético isolado
  e conferir esse caminho; nenhum ajuste desse bootstrap é proposto aqui.

## Dados confiáveis e dados recebidos

O chamador servidor deve fornecer a seleção explícita do ensaio, o identificador
exato da sessão B previamente criada, o store/banco sintético daquele ensaio e a
origem local esperada da interface. São vínculos do lançamento/configuração do
servidor, não flags ou cabeçalhos escolhidos pelo cliente. O manifesto/origem B
deve ser lido por leitor B e revalidado contra esse vínculo antes de atender o
ensaio; uma sessão ausente ou incompatível não provoca criação/migração automática.

Ficha, relações, aliases e `SourceProducerConfig` também pertencem ao servidor
(plano, linhas 30–35). O modelo/configuração concreta só será fixado no momento
apropriado; esta proposta não copia o Qwen do launcher antigo como decisão nova.
`session_id` na URL, `Host`, `Origin` e os campos da ação são dados não confiáveis.
Compará-los ao vínculo do servidor limita o destino atendido, sem autenticar pessoa.

## Tabela proposta, antes de aceitar a conexão

| Condição | Despacho | Efeito permitido neste ponto |
|---|---|---|
| Destino classificado como legado pela configuração/montagem do servidor, fora da entrada do ensaio B | Legado preservado | Entrar no handler v1 existente somente após resolver a seleção. Uma flag B recebida do cliente não habilita B. |
| Entrada reservada para B, mas ensaio não habilitado pelo servidor ou vínculo de lançamento incompleto | Rejeitar | Nenhum `accept`, leitor, criação, reserva ou fallback v1. |
| Ensaio B habilitado, mas sessão recebida difere da sessão exata escolhida pelo servidor | Rejeitar | Não consultar bancos/saves por aquele ID; não criar sessão substituta. |
| Ensaio B com `Host` ou `Origin` ausente/incompatível com a URL local definida no lançamento | Rejeitar | Recorte da interface no navegador local; não aceitar aliases/origens adicionais por inferência. Nenhum fallback v1. |
| Seleção, sessão e origem local compatíveis, mas manifesto/origem B do banco sintético está ausente/inválido | Rejeitar | Somente consulta B de verificação; nenhuma leitura migratória, seed ou reserva v1. |
| Todas as verificações B satisfeitas | B local | Entregar sessão/store/configuração do servidor ao futuro handler B, que poderá aceitar a conexão e usar os leitores e projeções B. Nunca passar pelo corpo legado. |

A tabela não fixa uma nova URL pública. A montagem/configuração do servidor
determina primeiro se o destino é legado ou B; o ID recebido não escolhe esse ramo.
Uma conexão destinada a B que falha em qualquer verificação não pode cair na linha
de legado. A ausência de handler B
implementado mantém a experiência inativa, inclusive quando o desenho é consistente.

Depois da conexão, a ação continua restrita a `SourcePlayerActionRequest` e ao
fluxo `prepare_source_player_action` → K pronto → `execute_retained_source_turn`,
conforme plano, linhas 33–38. Reconexão/consulta reapresenta briefing, texto confirmado
e estado, sem produzir fala automaticamente; pending/terminal não autoriza takeover,
rerrolagem, retry ou troca de alvo. São contratos existentes, não novos requisitos.

## Fronteira que o launcher atual demonstra

`scripts/run_storyteller_manual_test.ps1:13–22` separa diretório/banco e constrói
sessão/URL local. `:90–100` confere listener loopback e PID do processo próprio ou
filho Python. `:113–123` fornece ambiente permitido, desliga dotenv e escolhe banco;
`:177` inicia uvicorn ligado a `127.0.0.1:8000`. Esses elementos são referências de
isolamento do ensaio, não ativação B: o script declara B inativo em `:165`.

Nem o PID do listener, nem loopback, UUID, hash, Host/Origin ou vínculo de sessão
identificam/autenticam o jogador. Processos locais confiáveis continuam dentro da
fronteira; processos locais hostis podem construir requisições/cabeçalhos. Não há
conta, proprietário, revogação ou proteção contra comprometimento do desktop.
Controle remoto do desktop não exige publicar a API. Identidade/proxy/contas ou
acesso direto remoto exigiriam a decisão arquitetural separada do plano (:170).

## Evidência e alcance da próxima verificação

Provas ainda a preparar: nenhuma conexão B chega a `accept`, leitura/reserva v1 ou
criação automática quando recusada; ramo legado permanece separado; vínculo B não
é substituído por URL/flag/headers; consulta/reconexão não produz turno. A integração
com handler requer TASK-004 e ainda não existe. Ativação permanece dependente da
experiência e aceitação do recorte (plano, linhas 45–47 e 169), distinta deste desenho.

Referências conferidas no worktree
`C:\Users\skate\.codex\worktrees\b008\AgenteStoryteller`: os três arquivos de
código indicados acima e `plan/feature-narrative-source-transport-1.md`.
