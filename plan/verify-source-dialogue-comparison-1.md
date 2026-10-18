---
goal: Avaliar Qwen e GPT-OSS com resposta de NPC e continuidade no SYSTEM dialogue-v1
date_created: 2026-09-12
status: 'Completed (offline preparation; one live comparison pending)'
---

# Comparação delimitada com diálogo efetivo

O comparativo61b83 encerrou sem candidato qualificado sob o SYSTEM progress-v1.
Depois, a experiência interativa49 mostrou quatro iniciativas sem resposta de
Mara. O SYSTEM dialogue-v1, criado para essa lacuna concreta e já observado em81
e87, produziu respostas de NPC; em87 houve continuidade textual, ainda abstrata,
e uma recusa técnica falsa corrigida separadamente com426 testes locais.

A pergunta nova é se alguma das duas configurações satisfaz os critérios de
diálogo, espera e continuidade sob esse SYSTEM existente. GPT-OSS ainda não foi
observado com dialogue-v1 neste fluxo. Não criar outra variante, afrouxar a rubrica
ou apenas renomear cenas para repetir a pergunta anterior. A comparação mantém
os mesmos casos autorados Oficina/Nina e Arquivo/Rui, a ordem invertida entre
cenas e a rubrica de elegibilidade anterior, mas não importa nenhuma resposta,
fonte, sessão, banco ou pontuação histórica.

## Escopo

Novo protocolo/corpus prospectivos source-dialogue-comparison-v1 e consumidor
experimental próprio sobre setup, produção declarativa, cápsula e execução B.
Novo launcher protegido e testes focais. Preservar todos os avaliadores antigos,
núcleo, SYSTEM dialogue-v1, schemas/gates, persistência, UI e modelos default.
Pode derivar código do comparador anterior; não executar seus métodos presos a
constantes através de monkeypatch nem extrair uma plataforma genérica.

Quatro blocos novos, três turnos cada, máximo12 HTTP e9216 tokens de completion:
Qwen/Oficina, GPT-OSS/Oficina, GPT-OSS/Arquivo, Qwen/Arquivo. Qwen none/GPT-OSS low,
temperature0.65/768, rota Groq exata; sem retry, fallback, diagnósticos ou ferramentas.
Um orçamento e relógio globais:60s iniciais e entre inícios HTTP. Espera antes de P,
depois um único deadline60s compartilhado por P/K/H6, sem renovar. Fontes posteriores
são apenas n integral dos commits do próprio bloco, até duas; q fica separado.

Reutilizar as proteções verificadas da continuidade: corpo aprovado/rota/modelo,
observação e evidência coerentes antes de commit, teto real de saída e prazo,
contenção de eco de chave. Stop global em autenticação, quota/limite, timeout,
indisponibilidade, eco, rota/modelo/configuração, cancelamento ou erro local/não
tipado. Falhas LLM chain-only: invalid_structured_output, malformed_response e
content_rejected; demais categorias são globais, incluindo pagamento exigido.
Recusas de schema/política terminam a cadeia, sem preencher skips posteriormente.
Replays em store reaberto com gateway e produtor proibidos, estado e hash lógico
inalterados. Auditoria somente em cópias de SQLite/WAL/SHM, verificando originais.

## Preparação e fechamento

1. Congelar protocolo/corpus com pergunta, critérios e regra de parada antes de inferir.
2. Implementar consumidor e verificador próprios; offline usar transporte sintético.
3. Implementar launcher SecureString com preflight/verificação em filhos sem chave.
   Chave apenas no filho live, removida antes de qualquer filho Git; não ler .env,
   ambiente de outra janela, memória de processo, histórico ou clipboard.
4. Revisão independente dos limites e das provas; preflight final sem HTTP ou chave.
5. Arquivar preparação e indicar o comando concreto do lançamento protegido.
6. Uma execução fechada, auditoria técnica e revisão narrativa separadas. Não repetir
   para forçar vencedor; se ninguém atender à rubrica, registrar nenhum qualificado.

Uma recomendação limitada não muda default, ativa campanha ou aprova CAP-001.
O recorte de uso B já foi aceito; não pedir essa aceitação novamente. A eventual
entrada da chave continua sendo intervenção humana real caso não exista mecanismo
protegido acessível ao processo. Esta preparação não depende de nova decisão de
arquitetura, bandeja de dados, interface ou campanha híbrida.

Comparação de configurações/trajetórias, sem causalidade isolada do SYSTEM.
Parecer independente conferiu pertinência e taxonomia antes da preparação.

Preparação encerrada; ver ../evals/narrator/reports/source-dialogue-comparison-preparation-2026-09-12.md.
Nenhum HTTP executado na preparação; protocolo mantém uma única comparação limitada.
