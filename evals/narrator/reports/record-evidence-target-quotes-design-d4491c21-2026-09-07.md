# Experimento de citação exata do trecho derivado

Data: 07/09/2026. Identidade: `record-evidence-target-quotes-v1`. Estado: autorizado pela instrução contínua do usuário; [preparação técnica concluída](record-evidence-target-quotes-v1-2026-09-07.md), com 361 testes aprovados. Trata-se de protocolo exclusivo da avaliação sintética. Nenhuma decisão de arquitetura do produto, contrato de runtime ou promoção de modelo é alterada.

## Evidência e hipótese

A [observação d4491c21](record-evidence-target-budget-observation-d4491c21-2026-09-07.md) terminou normalmente com JSON estruturado, mas dois suportes extrapolaram seus campos e outro cortou o modalizador. A saída usou 1.409 tokens, abaixo do teto anterior 1.536; não se aumenta novamente o orçamento.

Hipótese delimitada: substituir a contagem de caracteres pela declaração literal do trecho-alvo permite obter referências resolvíveis nesta abertura? A LLM devolve `p/c/s/m`: caminho do registro, citação do trecho nesse campo, IDs das fontes e modalidade. O código local procura a citação na string decodificada e calcula início/fim somente quando existe uma única ocorrência exata, contando também ocorrências sobrepostas.

Uma citação ausente ou ambígua é recusada. Não há trim, normalização Unicode, mudança de caixa, correspondência aproximada, escolha arbitrária da primeira ocorrência, remoção de suportes ou reescrita dos registros. O envelope declarado permanece no JSONL. Apenas a auditoria do protocolo novo contém os índices derivados; não se convertem ou consertam artefatos antigos.

Esta representação transfere uma operação determinística ao código. Isso não demonstra que o trecho citado é uma afirmação completa, que a fonte implica seu conteúdo ou que o conjunto cobre os registros. Um trecho literal que corte “sugerindo” ainda pode ser numericamente resolvível; o revisor deve recusá-lo como evidência suficiente. A pergunta sobre observação continua como contraprova semântica independente: metadado `suggested` nunca corrige uma pressuposição infiel.

## Alteração exata e fronteira

O [dossiê congelado](record-evidence-target-quotes-dossier-d4491c21-2026-09-07.json) contém o corpo completo reconstruído localmente. SHA `b5e60a9d0313209a413c90c9f68b081b16cb943d9d6a55a899e91d2691daadfc`. Corpo anterior `5e376cb4cdee903b0f1a5bbcd3a14fa181d966656102f4c4985d87b4eb9ea186`; novo `573bfe7589a2efefb75435c6f38a6127c87909170798523780e8a18da1969d89`.

Somente `messages[0].content` e `response_format` mudam no corpo: instruções de SUPPORTS e schema do envelope passam a declarar o protocolo de citação. O SYSTEM até RECORDS e a frase final histórica 768 permanecem idênticos. Esta frase é uma limitação conhecida, preservada para não acrescentar outro ajuste; o limite enviado à API segue 3.072. Não apresentar o experimento como SYSTEM-only. Não é comparação causal A/B.

O USER é byte a byte o mesmo (`42eb962a2042c00b2030d5cb63b1f7e1f17894158e5df61cdcad0d317c32a480`), com fonte n0 integral e narrativa bb98 de 197 caracteres. O schema de records e seus tipos internos permanecem iguais. A validação de caminho, fontes e intervalos usa o contrato anterior intacto depois da resolução literal única. Composição da narrativa fixa, schema final, atores, agência, mecânica, visibilidade e admissão permanecem sem alterações.

## Limites anteriores ao envio

Uma chamada total, somente opening bb98; nenhum caso Mara ou geração narrativa. Groq direta, endpoint oficial, candidato `gpt-oss-120b-groq-free-synthetic-low`, modelo `openai/gpt-oss-120b`, reasoning low e include_reasoning false, temperatura 0,65, structured sem streaming. Teto API e total 3.072. Um terminal, espera conservadora inicial de 60 s, revalidação de integridade antes/depois da espera, deadline de 60 s criado após a espera. Nenhum retry, fallback, diagnóstico ou escalada automática de orçamento.

O observador conserva somente metadados permitidos, com limite de 64 KiB para inspeção de erro; não retém reasoning ou erro bruto. O corpo do dossiê é sintético, não contém headers/credenciais e não é captura de tráfego. A chave será fornecida no prompt protegido apenas após testes, revisão, preflight e integração com chave vazia; a instrução contínua dispensa nova aprovação do experimento.

## Verificação e regra de parada

Antes de envio: contraprovas de citação ausente/repetida/sobreposta, Unicode e diferenças exatas de caixa/espaço/acento; caminhos e fontes inválidos; envelope forjado; preservação de registros/fontes; ausência de reparo de amostra numérica antiga; correspondência estrutural não promovida a cobertura/fidelidade. Verificar também corpo/dossiê, quiet period/deadline, uma única chamada, erros/truncamento/cancelamento, ausência de credencial no preflight e de saída sensível no wrapper. Os artefatos novos devem ser recusados por todas as entradas de replay CAP-001.

Encerrar o lote após seu único resultado, seja qual for. Se houver envelope, auditar todos os trechos e revisar registros e cobertura separadamente. Se não houver, limitar conclusões à evidência operacional disponível. Uma proposta admitida continua sem aprovação semântica automática, de runtime ou CAP-001. Após análise, escolher e preparar autonomamente o próximo passo necessário; parar somente por chave/credencial/intervenção humana real.
