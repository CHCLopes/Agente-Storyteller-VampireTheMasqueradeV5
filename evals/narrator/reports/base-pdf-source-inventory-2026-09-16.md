# Inventário dos PDFs-base

Data: 2026-09-16

Seis arquivos indicados pelo usuário foram identificados por nome, hash SHA-256,
número de páginas, edição quando verificável e papel de autoridade. O inventário
fica no sidecar `data/catalogs/catalog_manifest.json`; os PDFs não foram copiados
para o repositório.

## Classificação

- `Vampire the Masquerade.pdf` — livro-base V5, 431 páginas; referência mecânica
  principal para potência, clãs, poderes, tipos de predador, progressão e armas.
- `V5_QuickStart.pdf` — Quickstart V5, 43 páginas; referência direta mais estreita
  para clãs, poderes e armas.
- `Vampiro A Mascara 3ed.pdf` — 3ª edição, 314 páginas; referência legada, sem
  autoridade para confirmar mecânica V5.
- `narrative_rpg_engine_v2.4.pdf` — documento de arquitetura narrativa, 11 páginas;
  não substitui os catálogos determinísticos.
- `resumo_projeto_storyteller.pdf` — resumo histórico do projeto, 2 páginas; o
  estado aprovado atual do repositório prevalece em divergências.
- `AldiSanguineUmaAventuraVTM.pdf` — aventura, 42 páginas; material de cenário. A
  abertura não possui texto extraível, portanto regras ou conteúdo ainda exigem
  inspeção por página/OCR antes de uso específico.

## Limites

A inspeção local localizou páginas candidatas por termos no livro-base e no
Quickstart, mas não promoveu automaticamente nenhuma linha da matriz para
`references_valid: supported`. Isso exige associar cada regra usada a uma página e
verificar sua edição. O registro dos arquivos também não afirma licença,
titularidade ou permissão de redistribuição.
