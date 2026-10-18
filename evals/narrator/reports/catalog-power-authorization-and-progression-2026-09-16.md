# Autorização de poderes e progressão — TASK-012 e TASK-013

Data: 2026-09-16

## Autorização de poderes

O orquestrador deixou de manter uma tabela própria de aliases. Nomes canônicos e
aliases localizados são derivados do registro. Uma seleção em
`allowed_power_ids` não concede o poder: a ficha precisa registrar o poder ou sua
família. Quando o nível editorial é conhecido, a família precisa alcançar esse
nível. Requisitos de amálgama e poderes prévios conhecidos também são verificados.

Poder diretamente presente na ficha representa aquisição já concluída e preserva
o formato legado. Para poderes cujo nível ainda é desconhecido, a combinação de
família possuída e seleção determinística explícita continua sendo a autoridade
compatível; nenhum nível ausente é inventado.

## Progressão

Antes de calcular ou descontar XP, o serviço valida categoria, trait, faixa de
nível e transição de exatamente um nível. Categoria conhecida sem mutação
implementada também falha fechada. `ProgressionValidationError` fornece os códigos
`unknown_category`, `unknown_trait`, `unsupported_category`, `invalid_level` e
`invalid_transition`.

Compras bem-sucedidas retornam uma cópia profunda atualizada. Falhas de validação
e XP insuficiente preservam o objeto recebido. O endpoint traduz os erros tipados
para resposta estruturada, sem persistir estado parcial.

## Verificação

- Autorização/aliases/catálogos: 22 testes passaram.
- Pipeline completo e segurança: 97 passaram; uma asserção literal preexistente
  do SYSTEM falhou fora deste incremento.
- Progressão e endpoints: 11 testes passaram no recorte amplo e 10 no recorte de
  transação/endpoint.

## Próximo passo

TASK-014: classificar e implementar apenas os efeitos de clã `base_reachable`
declarados pela matriz, preservando como narrativos ou não suportados os demais.
