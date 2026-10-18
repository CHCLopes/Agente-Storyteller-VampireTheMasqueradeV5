---
name: vtm-relational-engine
description: Documento do módulo determinístico de relacionamentos; não é um agente cognitivo.
---

# H2 descontinuado como skill cognitiva

O identificador histórico H2 permanece apenas para rastreabilidade. O runtime não
invoca modelo, prompt, skill ou adaptador para relações. `api/relationship_service.py`
é o módulo determinístico responsável por validar e calcular transições.

## Estado e transições

- O estado relacional tipado é carregado da campanha persistida.
- A intenção e o resultado mecânico já resolvido alimentam regras Python.
- A disposição e a confiança só mudam pelas transições implementadas e testadas.
- A projeção destinada ao narrador respeita visibilidade e orçamento de contexto.

## Persistência

Novos turnos persistem relações no mesmo commit transacional de fatos, eventos,
estado e narrativa. Arquivos legados podem ser lidos somente pelo migrador de
compatibilidade existente; não são a fonte de verdade e não recebem novas escritas.

## Autoridade

O narrador pode representar reações coerentes com o estado recebido, mas não pode
calcular, alterar ou persistir disposição e confiança por conta própria.
