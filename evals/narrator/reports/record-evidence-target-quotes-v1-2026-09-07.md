# Citações exatas — preparação concluída

**Estado posterior:** lote fda8af66 executado e encerrado; [análise concluída](record-evidence-quotes-observation-fda8af66-2026-09-07.md). Não há chave ou chamada pendente nesse lote. As instruções abaixo descrevem sua preparação histórica.

Em 07/09/2026 foi concluído `record-evidence-target-quotes-v1`, sob autorização contínua do usuário. A única dependência humana restante é a entrada da chave protegida; não falta aprovação da hipótese ou do lote. [Desenho e critérios](record-evidence-target-quotes-design-d4491c21-2026-09-07.md), [corpo congelado](record-evidence-target-quotes-dossier-d4491c21-2026-09-07.json) e [metadados, hashes e verificações](record-evidence-target-quotes-v1-2026-09-07.json).

## Implementação e limites

O novo envelope declara `p/c/s/m`. O resolvedor exige citação literal única no campo de destino e calcula os índices localmente, sem modificar os registros. Recusa ausência/ambiguidade, inclusive sobreposição; não normaliza, aproxima ou escolhe a primeira ocorrência. O envelope original permanece no JSONL; índices só na auditoria do novo protocolo. Contratos e artefatos numéricos históricos permanecem intactos.

O executor aceita somente a abertura fixa bb98: uma chamada total de até 3.072 tokens, Groq/GPT-OSS direto, reasoning low, temperatura 0,65, espera inicial e deadline de 60 s. Nenhuma narrativa nova, Mara, diagnóstico, retry, fallback ou escalada de teto. SYSTEM e schema de suportes mudam juntos; USER, schemas de records/tipos internos e demais parâmetros permanecem idênticos. Composição da narrativa e gates finais são preservados. Correspondência literal não aprova fidelidade nem cobertura.

A única mudança em código compartilhado é a exclusão dos novos identificadores nas duas entradas de replay CAP-001: 12 linhas adicionadas, nenhuma removida. Runtime, adaptadores, regras, persistência e contratos do produto não foram alterados.

## Verificação concluída

**361 testes distintos passaram: 198 novos e 163 existentes; zero falhas e zero skips.** Não é a suíte integral do repositório. Os 294 da preparação anterior e rodadas repetidas/smokes não foram somados.

| Grupo | Novos | Existentes | Total |
|---|---:|---:|---:|
| Contrato de citações e compatibilidade de registros/fontes | 94 | 120 | 214 |
| Executor e fronteiras operacionais | 35 | 0 | 35 |
| Terminal protegido e proveniência | 48 | 0 | 48 |
| Recusa de replay e comportamento anterior | 21 | 43 | 64 |

O preflight reconstruiu exatamente o corpo congelado `573bfe75…` e verificou as mudanças declaradas. A integração real com chave vazia aceitou o preflight e parou na validação da credencial (exit 3), sem chamada ou novo artefato de avaliação. Parsers PowerShell 7/5 e testes operacionais PowerShell 7 passaram. Permanece apenas o aviso preexistente de python_multipart. Revisão independente sem achado material. Hashes confirmaram preservação dos resultados d4491c21/26547182 e da implementação anterior, salvo a guarda CAP declarada.

## Execução e continuidade

A janela protegida foi aberta às 14:56:45 UTC de 07/09/2026, PID 26320. Último estado observado: `running_authorized_probe` às `2026-09-07T14:57:12.4554607Z`. Não abrir outra janela para este lote. Antes de abrir outra janela, conferir o estado em `C:\Users\skate\AppData\Local\Temp\storyteller-record-quotes-live-20260907\status.json`, quando existir. Título: “Agente Storyteller - citacoes exatas - chave protegida”. Não recuperar chave antiga, .env ou credencial do Console. O launcher descarta a chave ao encerrar.

Após a única chamada, conferir summary/JSONL imutáveis, proveniência e todos os suportes; revisar separadamente fidelidade, modalidade e cobertura. Encerrar o lote após qualquer resultado e continuar o próximo passo necessário sob a autorização contínua. Uma proposta operacionalmente aceita continua sem aprovação automática de narrativa, runtime ou CAP-001.
