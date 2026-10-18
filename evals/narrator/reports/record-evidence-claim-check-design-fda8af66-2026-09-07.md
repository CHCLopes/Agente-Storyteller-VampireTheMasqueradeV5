# Conferência das afirmações — experimento SYSTEM-only

Data: 07/09/2026. Identidade do prompt e do experimento: `record-evidence-claim-check-v1`. Protocolo de suporte preservado: `record-evidence-target-quotes-v1`. Autorização contínua do usuário; [preparação concluída](record-evidence-claim-check-v1-2026-09-07.md), com 156 testes aprovados e integração real sem chave.

## Evidência e hipótese

A [observação fda8af66](record-evidence-quotes-observation-fda8af66-2026-09-07.md) concluiu a resposta, mas citou “sussurro distante” num suporte para uma pergunta que não contém esse trecho. Quatro citações anteriores tinham correspondência única. A pergunta pressupõe observação sugerida, e o resumo omite a relação sensorial “cheiro de”. Uma correspondência em parte do resumo não cobre o restante.

Hipótese: uma conferência curta no SYSTEM, com exemplos independentes da fonte avaliada, consegue produzir referências ao campo correto e preservar relações/modos epistêmicos nesta abertura? A revisão instrui citação a partir do registro final, cobertura de afirmações completas com modalidades separadas, conservação de relações sensoriais, verificação da existência antes de perguntar agente/causa e convite dirigido ao jogador.

Os exemplos não contêm corredor, sussurro, observador, fumaça, chuva ou resposta pronta da opening. Não se fornece gabarito de records ou envelope para a cena avaliada. Não solicitar planejamento, cadeia de raciocínio ou nova narrativa na saída: permanece somente records/supports.

## Delta e limites

Mudança única no corpo: `messages[0].content`. O [dossiê completo foi congelado](record-evidence-claim-check-dossier-fda8af66-2026-09-07.json) antes do envio (SHA `5b4bd26ab85ae927c4d7ebea03d5363f20d19d8b4bc0e1ee0c0cccd6fd9a33c9`) e confrontado com o corpo anterior `573bfe7589a2efefb75435c6f38a6127c87909170798523780e8a18da1969d89`. `response_format`, USER e parâmetros devem permanecer idênticos. A identidade do novo prompt não altera a identidade do protocolo; não copiar ou mudar o contrato de citações para satisfazer o nome do experimento.

Mesma opening bb98 e fontes integrais; mesmos schemas, resolvedor literal único, composição fixa e gates finais. SYSTEM anterior preservado com um único bloco de conferência acrescentado antes da frase final histórica 768; teto API continua 3.072. A frase é limitação conhecida; não há elevação de orçamento. O novo executor explícito fica isolado dos scripts congelados. Não criar engine genérico, alterar globais de módulos antigos ou refatorar runtime nesta etapa.

Uma chamada total, Groq direta/endpoint oficial, `openai/gpt-oss-120b`, candidato sintético low, temperatura 0,65, saída até 3.072, reasoning low/include_reasoning false, structured sem streaming. Um terminal, quiet period inicial de 60 s e deadline de 60 s após revalidação. Nenhuma Mara, geração narrativa, diagnóstico, retry, fallback ou reexecução automática.

## Critérios e parada

Preservar envelope e registros originais. Citação ausente ou ambígua continua erro; não mudar caminhos, normalizar, completar texto, remover suporte nem converter artefatos antigos. Citação literal não demonstra cobertura ou implicação. Se houver resposta, auditar todos os suportes e a fidelidade de cada campo, inclusive pressuposições, modalidade, relações sensoriais e ponto de vista do convite. Lista vazia ou apoio somente a um substantivo não aprova cobertura das demais afirmações.

Revalidar corpo/dossiê, versões separadas, preflight sem credencial, espera/deadline, cancelamento, resposta completa/truncada, uma chamada e ausência de vazamentos. O replay CAP-001 deve rejeitar cada nova identidade. Chave somente no prompt protegido após todos os testes e revisão; credencial é a única intervenção humana então necessária.

Encerrar esse lote após qualquer resultado. Nenhuma amostra, mesmo admitida, aprova narrativa, runtime ou CAP-001. Comparação histórica não é A/B causal; êxito ou falha de uma abertura não demonstra generalização. Depois da análise, prosseguir autonomamente para o próximo passo sustentado pela evidência.
