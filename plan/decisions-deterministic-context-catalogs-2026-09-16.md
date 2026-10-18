# Decisões aprovadas — catálogos determinísticos

As cinco recomendações foram aprovadas conjuntamente pelo usuário em 16/09/2026.

Elas passam a orientar as tarefas dependentes. A aprovação da estrutura de
proveniência não identifica retroativamente a fonte dos arquivos legados.

## DEC-001 — subconjunto V5 do candidato a MVP

**Recomendação:** assumir compromisso oficial apenas com as entradas alcançáveis
pela ficha base e pelos fluxos atualmente expostos, mantendo todas as demais como
`catalogued` ou `partial`. A primeira matriz deve descrever o estado atual; uma
entrada só vira `supported` após mecânica, narrativa, testes positivos, testes
negativos e limitações estarem preenchidos.

Alternativas: declarar todas as 66 entradas como compromisso imediato, com grande
expansão de implementação; ou reduzir o MVP a uma única configuração fixa, com
menor valor de cobertura. A recomendação preserva variedade existente sem fingir
suporte integral.

## DEC-002 — fonte de verdade dos contratos H0/H1/H4/H6

**Recomendação:** Markdown versionado como fonte editorial única para os quatro
contratos, carregado pelo runtime; código mantém apenas composição, validação e
fallback técnico não editável. H1/H6 já se aproximam desse desenho e H0/H4 seriam
migrados sem manter prompts concorrentes.

Alternativas: prompts inline como única fonte, com menor transparência editorial;
ou geração automática a partir de outro schema, que adiciona uma representação
antes de haver necessidade comprovada.

## DEC-003 — destino de H2

**Recomendação:** descontinuar H2 como “skill” cognitiva e documentar o motor
relacional determinístico vigente como módulo de domínio. Manter o arquivo antigo
apenas com aviso de descontinuação e ponte documental até referências serem
removidas.

Alternativa: reescrever H2 como contrato Markdown do módulo determinístico. Isso
preserva simetria nominal, mas sugere incorretamente que existe uma chamada ou
agente H2 no runtime.

## DEC-004 — fronteira da resposta H4

**Recomendação:** H4 direto recebe somente lookup tipado e fundamentado; pode
reformular esses fatos para leitura, mas não acrescenta enriquecimento atmosférico
como fato. Quando a cobertura for ausente, responde `not_covered` de forma útil e
limitada. Atmosfera pertence à narração H6 em cena.

Alternativa: permitir enriquecimento H4 opcional separado e explicitamente marcado.
Isso aumenta o risco de uma consulta factual misturar cânone com invenção e exige
um contrato adicional de apresentação.

## DEC-005 — proveniência editorial mínima

**Recomendação:** manifesto sidecar com `schema_version`, `content_version`,
`reviewed_at`, `source_title`, `edition`, `page_or_section`, `license_basis`,
`editorial_notes` e SHA-256 por arquivo. Fonte e fundamento de uso devem ser
aprovados por uma pessoa; ausência de fonte mantém a entrada parcial e impede
afirmação de conformidade.

Alternativas: metadados dentro de cada catálogo, que quebrariam loaders atuais;
ou apenas hash/data, insuficientes para rastrear conteúdo e fundamento de uso.

## Estado

`DEC-001` a `DEC-005`: **Approved**. Permanece uma dependência factual separada:
identificar e aprovar título, edição, página/seção e fundamento de uso de cada
arquivo legado. Até isso ocorrer, o manifesto deve conservar `unverified`.
