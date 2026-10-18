# Decisão prospectiva após HYP-005 L1

Data: 2026-09-27  
Estado: proposta, sem autorização de inferência  
Chamadas realizadas por este documento: 0

## Evidência que motiva a decisão

HYP-005 L1 não produziu candidato elegível. Nemotron e Liquid consumiram o teto de
768 tokens na maior parte das respostas antes de concluir o JSON. O único texto
concluído pelo Liquid falhou um critério semântico fatal. A rota gratuita exata do
DeepSeek retornou indisponível durante o lote, embora o catálogo público volte a
listar o slug como gratuito no momento desta preparação.

Isso não demonstra que mais tokens melhorariam a qualidade semântica; demonstra
somente que o teto de L1 impediu a observação de quase todos os casos.

## Opções humanas

### A — encerrar a busca atual sem narrador admitido

Não há novas chamadas nem mudanças de código de runtime. O checklist do MVP
permanece bloqueado na admissão do narrador até uma alternativa futura.

Vantagem: nenhum novo consumo de cota ou tempo de avaliação.  
Consequência: não permite avançar honestamente para a campanha jogável dependente
do narrador.

### B — HYP-005-L2, isolamento do teto de saída — recomendada

Repetir prospectivamente o mesmo protocolo, prompt, corpus, schema, temperatura,
alvos exatos, ordem e gates, alterando somente:

- `max_output_tokens`: 768 para 2048;
- novo identificador de hipótese, lote, preflight e hashes;
- preflight de catálogo imediatamente antes do lote;
- máximo absoluto de 24 chamadas gratuitas.

Permanecem zero retry, zero reparo, zero fallback, custo reportado exatamente
zero, dados sintéticos, admissão 8/8 por candidato e revisão humana independente.
Se o slug gratuito do DeepSeek não estiver disponível no preflight, seus oito
slots são recusados antes da rede; não se substitui pelo slug pago.

Vantagem: testa causalmente a explicação operacional sem misturar mudança de
prompt ou raciocínio.  
Risco: pode consumir até 49.152 tokens de saída gratuitos e ainda produzir
truncamento ou falha semântica.

### C — HYP-005-L2 com raciocínio desabilitado

Adicionar `reasoning.enabled: false`, mantendo 768 tokens ou alterando também o
teto. A documentação atual do OpenRouter descreve o controle de raciocínio e os
modelos Nemotron e Liquid como modelos de raciocínio; `require_parameters: true`
continua obrigatório.

Vantagem: pode reservar mais do orçamento para o JSON final.  
Risco: altera a política de raciocínio e, se combinado com novo teto, impede
atribuir o efeito a uma única variável. Deve ser uma hipótese distinta, posterior
à opção B, ou substituir B por decisão explícita.

### D — Luna/API paga

Fora de escopo pela decisão vigente de não usar provedores pagos. Não preparar nem
executar.

## Recomendação

Após aceitar a classificação de L1, aprovar a opção B. Ela é a menor hipótese
capaz de distinguir incompatibilidade do teto de uma falha real dos modelos sem
modificar prompt, schema ou comportamento de raciocínio. A implementação e todos
os testes offline podem ser concluídos antes de nova entrada de chave.

## Fontes técnicas atuais

- OpenRouter Structured Outputs:
  https://openrouter.ai/docs/guides/features/structured-outputs
- Nemotron 3 Super gratuito:
  https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b%3Afree/api
- Liquid LFM 2.5 2.6B gratuito:
  https://openrouter.ai/liquid/lfm-2.5-2.6b%3Afree
- DeepSeek V4 Flash 0731 gratuito:
  https://openrouter.ai/deepseek/deepseek-v4-flash-0731%3Afree

