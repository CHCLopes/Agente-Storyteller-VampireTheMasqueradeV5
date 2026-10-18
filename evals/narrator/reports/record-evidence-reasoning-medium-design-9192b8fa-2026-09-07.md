# Observação de raciocínio medium — desenho delimitado

A hipótese é que o esforço medium preserve melhor a fidelidade das afirmações e a separação de modalidades. O lote claim-check passou operacionalmente, mas falhou nesses pontos. A resposta será avaliada pelos [critérios registrados antes do envio](record-evidence-semantic-criteria-9192b8fa-2026-09-07.md).

O [dossiê congelado](record-evidence-reasoning-medium-dossier-9192b8fa-2026-09-07.json) preserva o corpo claim-check e muda apenas `/reasoning_effort`: low para medium. SYSTEM, USER, envelope de citações, schema nativo estrito, validadores e fontes permanecem idênticos. A frase histórica de 768 tokens no SYSTEM permanece, enquanto o teto da API continua 3.072; esse potencial fator não é alterado neste teste.

O [perfil isolado](../groq_medium_observation_profile_2026-09-07.json) identifica explicitamente `gpt-oss-120b-groq-free-synthetic-medium`, a rota direta Groq e o adaptador experimental. O manifesto low e seu construtor mantêm as restrições originais. O novo adaptador inicializa o transporte diretamente com medium e é restrito ao corpo congelado; não muda atributos de uma instância low nem relaxa o guard antigo.

Uma opening sintética fixa; no máximo uma chamada, temperatura 0,65, teto 3.072, espera inicial 60 s e deadline 60 s após a espera. Zero retry, fallback, diagnóstico, narrativa nova ou Mara. Sem captura de raciocínio bruto. A chave entra somente no prompt protegido e é descartada ao terminar.

A API documenta low/medium/high para GPT-OSS. A disponibilidade do parâmetro não prova sua eficácia narrativa. [Referência oficial](https://console.groq.com/docs/api-reference). O uso de schema estrito neste modelo é documentado em [Structured Outputs](https://console.groq.com/docs/structured-outputs).

Cada resultado encerra este lote. Falha semântica encerra esta linha de variações na opening; não há escalada automática para high, teto maior ou novas instruções. Sucesso só permite caracterizar este caso e preparar verificações independentes. Nenhuma comparação histórica será apresentada como A/B causal. Runtime e CAP-001 permanecem sem aprovação.
