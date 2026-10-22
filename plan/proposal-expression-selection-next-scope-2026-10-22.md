# Próximo escopo após A2 — proposta para decisão humana

Status: opção B aprovada pelo humano em 22/10/2026 (resposta “b”).
Aprovação limitada ao desenho e experimento offline descritos abaixo; sem integração,
modelo real, nova autoridade causal ou aceite de MVP. Opção A não aprovada.

## Evidência que motiva a decisão

A2 resolve de maneira autorada consequências, fala e retenção no catálogo atual.
L86 não demonstrou ganho editorial consistente do seletor LLM. O ensaio em navegador
confirma funcionamento e recuperação desse recorte, sem inferência. “Por que?” é
recusado sem consumir turno; “Mara, leve o registro” recebe orientação, mas Mara
não executa o pedido. Não há suporte geral a métodos inesperados ou diálogo livre.
CAMP-24 inclui improvisação interessante. Logo, não está satisfeito pelo A2.

## Escolhas de produto

A. Priorizar integração experimental do recorte fechado à interface do jogo.
Isso valida somente começo, progressão, consequências e retomada. Improvisação
permanece explicitamente fora desta entrega e CAMP-24 segue aberto. Integração
exige plano próprio; não modificar o original ou saves existentes por este aceite.

B. Manter A2 como referência e priorizar interpretação de ações antes de integrar
(recomendação). Autorizar o desenho e um experimento exclusivamente offline da
fronteira descrita abaixo. O objetivo é verificar se aceitar paráfrases com segurança
pode reduzir a rigidez sem transferir a autoridade causal ao modelo. Não promete
resolver improvisação geral. Métodos realmente novos continuam uma decisão de
escopo posterior, apoiada pelos casos que o experimento revelar.

## Escopo concreto proposto para B

1. Novo experimento separado de A2, sem alterar os 32 arquivos congelados, produto,
   configurações, banco L86 ou saves reais. Corpus sintético de 24 casos revisáveis:
   oito paráfrases de intenções conhecidas, quatro ambiguidades, quatro negações ou
   ações atribuídas a NPC, quatro métodos inéditos e quatro tentativas de injetar cânone.
2. Contrato candidato: `kind = known_intent | clarification | unsupported`, intenção
   existente quando aplicável e trechos literais da entrada que sustentam a proposta.
   Não admitir texto narrativo, fato novo, decisão mecânica, segredo, relação ou
   consequência. Uma proposta válida no formato ainda pode ser semanticamente falsa.
3. Baseline do classificador atual versus respostas sintéticas válidas/inválidas e
   avaliação caso a caso. Sem modelo real, gateway, instalação ou custo de API nessa fase.
   O contrato deve permitir adaptadores locais/gratuitos futuramente; isso não demonstra
   sua capacidade nem autoriza selecionar um modelo ou provedor por conveniência.
4. Saídas ambíguas, negação perdida, ator trocado ou método não coberto não podem
   acionar consequência. Conservar a entrada; pedir esclarecimento ou declarar limite,
   sem consumir turno ou sortear. Nenhuma nova intenção/regra é criada automaticamente.
5. Caso seja posteriormente acoplado, proposta e efeito precisam de vínculos de sessão,
   operação, versão e estado; idempotência e recibo mecânico preservados. O experimento
   offline testa o contrato e não efetua esse acoplamento nem admite um interpretador.
6. Relatório explícito de falsos aceites, falsos bloqueios e casos não resolvidos;
   primeira falha de autoridade reprova a variante. Sem ajuste silencioso dos rótulos.
   Próximo gate após a fase: aprovar/rejeitar contrato e eventual avaliação com modelo,
   ou reformular o mínimo de improvisação necessário. Não afirmar CAMP-24 concluído.

## Limites preservados

Esta proposta não reativa `proposal-dual-model-narrator-resolver.md` nem a alternativa
causal ALT-003 rejeitada. Não permite modelo escolher consequências, criar cânone,
controlar NPC ou substituir o resolvedor determinístico. Se os casos demonstrarem
necessidade desses poderes, registrar o impedimento e voltar ao humano.

O insight para a ferramenta original é manter autoridade, admissão e persistência
fora do texto gerado. Copiar apenas o prompt ou o renderer não corrige sua ordem
atual de mutação/persistência e streaming. Uma adaptação real continua separada.

## Critério da decisão humana

Escolher A ou B define prioridade e a superfície da próxima entrega; não constitui
aceite final do produto, admissão de narrador ou rebaixamento da visão de RPG aberto.
A recomendação B preserva essa visão e evita investir na integração antes de tratar
seu principal limite observável.
