# HYP-007-L84 — registro prospectivo A1 v2

Preparado em 21/10/2026, antes de qualquer chamada. Autorização: A1 aprovada com
“Prossiga”; autorização contínua de testes sintéticos <=USD 0.15 vigente no AGENTS.md.

Hipótese: com fatos críticos e fala essencial compostos pela aplicação, Luna low
consegue preencher slots breves e compatíveis, sem alterar o plano. Medir contrato,
proveniência, tamanho/latência/custo e naturalidade; não certificar semântica geral.
Contraprovas offline já mostram 9 acréscimos inválidos aceitos; esta limitação é
conhecida antes do lote e não será ocultada por um resultado técnico verde.

Alvo exato `gpt-5.6-luna`, OpenAI Responses, effort low, store false, nenhum tool.
Oito percursos/17 turnos na ordem de L83 (recusa primeiro), dados sintéticos,
RNG autorado fixo para exames. Até 768 tokens de saída e 20.000 bytes por request;
nenhuma temperatura, seed, retry, fallback ou troca de alvo. Teto USD 0.15
estimado no lote inteiro, guard antes de cada chamada. Tarifa 0.20/1.20 por milhão
entrada/saída, verificada em 21/10 na documentação oficial citada no relatório.

Schema, prompt e fontes versionados no manifesto próprio L84; 22 hashes principais
mais 10 de apoio. Preflight bloqueado para rede/chave em pytest; também executado
keyless pelo entrypoint. Latch impede segunda execução. Gates iniciam false/false.
Só ativar após conferir supervisora viva, chave recebida e hashes sem drift.

Parada: primeiro erro de transporte, estrutura, política, rota, limite, ausência
de uso ou efeito final divergente. Guard técnico não detecta toda a semântica;
revisão qualitativa após execução pode rejeitar qualquer turno tecnicamente aceito.
Examinar cada texto final, inclusive atribuição, tarefa, dano/posição, agência,
recusa sem lore inventado, conclusão sem nova tarefa e diálogo natural.

Persistir entradas sintéticas/plano, resposta bruta quando disponível, expressão
normalizada, apresentação/spans, evidências de rota/uso, custos e hashes; não
registrar credencial. Nenhum resultado modifica evidência histórica ou aprova
MVP/CAMP-24/default. Fechar os gates e relatar custo mesmo na primeira falha.

## Resultado observado — 21/10/2026

Lote c9cd77f6-8e5b-42e0-b6ad-c77fcaba2e02: 12 chamadas e 12 turnos completos
tecnicamente; 17 planejados. Uso presente nas 12: 24.587 tokens de entrada e
2.218 de saída; USD 0.0075790 estimado, cobrança não confirmada. Todos os 12
turnos mantiveram plano/estado e passaram os guards existentes. Isso não atesta
qualidade semântica. Sete turnos têm ambos os slots vazios; quatro têm ambiente;
três têm reação de Mara não vazia, todas descrições indevidamente exibidas como fala:

- CAMP-EVAL-08/1: Ela mantém a resposta sem acrescentar detalhes.
- CAMP-EVAL-02/3: Mara respira fundo, mantendo os olhos nas páginas molhadas.
- CAMP-EVAL-03/1: Mara mantém os olhos fixos no registro, em alerta.

As frases acima são saídas observadas, não exemplos prospectivos. Falha qualitativa
identificada na primeira leitura e gates fechados; o processamento já tinha
avançado. O registro 13 (CAMP-EVAL-04/1) não chamou a API. Seu erro genérico
campaign_expression_generation_failed decorre do gate fechado localmente, não
de falha observada do provedor. Supervisora voltou a idle com exit code 2.

Arquivos originais preservados em eval-results/hybrid-campaign-luna-l84-c9cd77f6-8e5b-42e0-b6ad-c77fcaba2e02.
SHA-256 records.jsonl: 3d2606a84818ab046ec592cc9ee5681338ce7267a63f5e712d1db1d46be2cffc.
Trava mantida, gates false/false; sem reexecução. A data de preço 29/09 no helper
de custos é histórica; as mesmas tarifas foram reconferidas em 21/10 no manifesto.
Conclusão: contrato/proveniência funcionaram nesta amostra; naturalidade reprovada.
L85 verificará apenas esclarecimento do campo de fala, mantendo o runtime.
