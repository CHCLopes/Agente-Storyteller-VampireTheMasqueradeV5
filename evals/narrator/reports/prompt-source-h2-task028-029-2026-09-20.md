# TASK-028 e TASK-029 — fontes de prompt e H2 determinístico

Data: 2026-09-20

## Resultado

- Um carregador único remove frontmatter e lê H0, H1, H4 e H6 dos Markdown versionados.
- H4 mantém duas seções editoriais distintas no mesmo documento: Q&A fundamentado e atmosfera opcional.
- Código conserva apenas composição e fallbacks técnicos curtos.
- H2 foi marcado como identificador histórico de um módulo determinístico, sem chamada LLM.
- A documentação de H2 aponta o commit transacional e proíbe novas escritas nos JSON legados.

## Verificação

- Fontes de prompt, serviços LLM e integração: 91 testes aprovados.
