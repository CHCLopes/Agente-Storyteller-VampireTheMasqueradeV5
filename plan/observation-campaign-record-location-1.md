# Observação — localização pública do registro na campanha curta

Estado: opção A aprovada explicitamente em 03/10/2026 ("Aprovo a opção A");
implementação offline verificada. Não autoriza novo lote pago nem admite narrador.

O conteúdo aprovado em `spec/spec-architecture-hybrid-campaign-progression.md`
define o registro inicialmente sobre uma bancada baixa no Arquivo e uma
superfície seca acessível na Galeria. HYP-007-L2 revelou que o pacote B enviado
ao narrador expõe condição do registro, local da cena e Mara, mas não a posição
do objeto. O seed `SourceContextOrigin` aceita apenas local e NPCs; rejeita
summary/details/open_threads. O primeiro texto Luna foi admitido sem reiterar
a bancada; o segundo narrou retirar o registro da mesa seca. A política o
rejeitou por menos de 30 palavras antes de provar semanticamente a posição.
Portanto, não atribuir a posição inventada apenas ao modelo.

Alternativas apresentadas; a opção A foi escolhida:

1. **A — estado canônico de posição, recomendado para integridade**: campo
   versionado `record_location` restrito à campanha (`bench`, `dry_surface`),
   inicializado no seed da campanha e mudado só pelo efeito determinístico
   admitido. O pacote e replay o derivam do estado; testes de persistência,
   retomada e compatibilidade são obrigatórios. Custo técnico maior, mas não
   confunde texto do narrador com fonte de verdade.
2. **B — projeção pública derivada do catálogo/efeito**: sem novo campo no save;
   o pacote calcula um fato de posição a partir de estado/beat versionados.
   Menor intervenção, porém a derivação para inspeção, dano parcial e abandono
   deve ser especificada e provada para não afirmar bancada após resgate.
3. **C — instrução fixa no prompt**: acrescentar a bancada à abertura. É
   rápida, mas pode tornar-se falsa depois da movimentação e não dá autoridade
   verificável; não recomendada como solução de continuidade.

Independentemente da posição, o texto R-05 de L2 teve cerca de 20 palavras,
abaixo do mínimo de 30. Um futuro prompt prospectivo pode explicitar a faixa
30–150 palavras já exigida pelo validador, sem mudar o gate ou repetir L2.
Isso não resolve a autoridade da posição. Nenhuma nova chamada está autorizada
por esta observação.

## Decisão implementada — posição canônica v2

Novas sessões usam `record-at-risk.v2` / `campaign-progression.v2`, com
`record_location=bench`. R-05 e R-06 preparam `dry_surface`; o estado só muda
no commit admitido. R-07 recupera informação sem deslocar o objeto. Diálogo,
espera, perda, inspeção falha e abandono conservam `bench`. A localização do
jogador não muda por consequência da posição do documento.

Saves/cápsulas v1 continuam v1, sem campo inventado, migração ou rehash. O
leitor discrimina pela versão retida e reconstrói com o mesmo tipo; rejeita
v2 sem posição, valores desconhecidos e mistura de versões. O pacote H recebe
antes/depois e as descrições públicas de cada posição. A prosa não fornece
estado canônico. Nenhum DDL ou relaxamento do seed B genérico foi necessário.

Evidência: [relatório offline v2](../evals/narrator/reports/campaign-record-location-v2-2026-10-03.md).
Prompt prospectivo v2 separado explicita posição e 30–150 palavras, sem mudar
o prompt/gate/artefatos históricos de L2. A fidelidade de um modelo real a esses
fatos ainda precisa de nova avaliação explicitamente autorizada.
