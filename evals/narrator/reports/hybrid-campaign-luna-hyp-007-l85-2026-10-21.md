# HYP-007-L85 — registro prospectivo: discurso direto

Preparado em 21/10/2026 antes de qualquer chamada L85. Autorização contínua de
ensaios sintéticos <= USD 0.15 por lote; usuário informou chave inserida e mandou
continuar. Nenhuma nova decisão arquitetural ou admissão decorre deste ensaio.

L84: 12 chamadas/12 turnos tecnicamente completos; três reações descrevem Mara
em terceira pessoa e são renderizadas como fala. Sete turnos têm os dois slots
vazios. Gates fechados durante revisão, antes da chamada 13; histórico preservado.

Hipótese L85: explicitar discurso direto no prompt elimina a confusão entre
fala e descrição nos slots não vazios. Se todos os slots de reação ficarem vazios,
o defeito não reaparece, mas isso não comprova capacidade de gerar diálogo.
Avaliar separadamente fidelidade, redundância, naturalidade e contribuição da LLM.
Não selecionar melhor tentativa nem apagar resultados anteriores.

Única variável funcional alterada: prompt campaign-expression-v2-dialogue-v2.md.
Runner/preflight são cópias L84 com nova identidade/paths; aplicação, schema,
renderizador, regras, histórico e parâmetros intactos. Manifesto registra os 32
hashes e prompt. Contraprovas offline (9/10 inválidas aceitas) continuam relevantes;
clareza do prompt não constitui validador semântico ou garantia de fidelidade.

Mesmos oito percursos/17 turnos, recusa primeiro; gpt-5.6-luna/OpenAI Responses,
low, store false, sem tools/temperatura/retry/fallback/seed. Até 768 tokens e
20.000 bytes por chamada, teto USD 0.15 estimado por lote. Tarifa 0.20/1.20 por
milhão de tokens, verificada em 21/10 e registrada no manifesto. Trava de execução
única. Preflight keyless e testes offline devem passar antes de ativar os gates.

Parar no primeiro erro técnico/efeito divergente/limite/uso ausente. Revisão
qualitativa acompanha os registros; fechar novos envios ao identificar falha,
permitindo que chamada já em voo termine. Essa revisão não é um guard semântico
por turno; outras chamadas podem ocorrer antes da leitura. Preservar entradas,
planos, respostas brutas/normalizadas, proveniência, uso, custo e hashes. Fechar
os gates após terminar. MVP/CAMP-24/default e admissão continuam abertos.

## Resultado observado — 21/10/2026

Preflight keyless/17 turnos e seis testes offline passaram antes do despacho.
Lote a60bde9c-5fff-46d6-95a0-f50c120a1761 completou 17 chamadas/17 turnos e oito
desfechos. Uso 35.234 tokens entrada/2.445 saída; USD 0.0099808 estimado.
Maior request 9.352 bytes; geração mediana 3.124 ms/máxima 5.036 ms nesta amostra.

Uma fala opcional em discurso direto, duas atmosferas; 14 turnos sem qualquer
texto opcional. O erro de descrição como fala não reapareceu, mas a amostra de fala
não vazia é só uma. CAMP-EVAL-03/1 afirma silêncio não estabelecido na cena;
qualidade/fidelidade geral não aprovadas. Nenhum efeito canônico divergente;
plano/spans/autoria/referências e respostas bruta/normalizada conferidos.
Gates fechados, trava mantida, supervisora idle/exit code 0. Sem reexecução.

SHA-256 records.jsonl: d55e6bfe106b5f556bc1438d835d127d0f2c070d81a6e380f6012607791281ec.
Análise completa, apresentações e proposta de próximo gate:
campaign-expression-v2-l84-l85-review-2026-10-21.md. Nenhum L86 preparado.
