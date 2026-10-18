> Estado atual: lote 84ea2c0c executado e analisado; janela terminada. [Resultado](record-evidence-reasoning-medium-observation-84ea2c0c-2026-09-07.md). O conteúdo abaixo descreve a preparação histórica; não reutilizar a janela ou o wrapper.

# Raciocínio medium — preparação concluída

A observação `record-evidence-reasoning-medium-v1` está preparada sob autorização contínua. O [perfil experimental](../groq_medium_observation_profile_2026-09-07.json) conserva os perfis históricos, e o [dossiê congelado](record-evidence-reasoning-medium-dossier-9192b8fa-2026-09-07.json) muda somente `reasoning_effort` de low para medium. SYSTEM claim-check, USER, protocolo de citações, schema e parâmetros restantes estão preservados.

Uma opening fixa bb98, Groq direta/GPT-OSS120B, temperatura 0,65, teto da API 3.072, espera inicial e deadline de 60 s. Uma chamada, sem retry, fallback, diagnóstico, Mara ou nova narrativa. O corpo tem SHA `5037c4c4…`; a fonte histórica continua identificada como low, e o candidato da nova chamada é explicitamente medium.

**219 testes distintos passaram: 176 novos e 43 existentes**, sem falhas ou skips. São 35 do observador, 52 do executor, 68 do wrapper e 64 de replay/compatibilidade. Rodadas históricas e smokes não foram somados. Não é suíte integral do repositório; apenas o warning preexistente de python_multipart. Os [metadados e verificações](record-evidence-reasoning-medium-v1-2026-09-07.json) registram hashes e resultados completos.

O transporte simulado confirmou o payload medium e a identidade do adaptador. O construtor Groq original continua recusando medium; o experimental inicializa o transporte diretamente sob sua própria política fixa. Preflight puro, revisão independente, parsers PowerShell e integração real com SecureString vazia passaram. A integração parou na validação da credencial sem chamada e sem artefatos de avaliação. Os arquivos históricos e seis artefatos dos três lotes anteriores foram preservados por hash. A única alteração compartilhada acrescenta 12 linhas para impedir replay da nova identidade como CAP-001.

Os [critérios semânticos prévios](record-evidence-semantic-criteria-9192b8fa-2026-09-07.md) distinguem fidelidade de correspondência literal. Depois de qualquer resultado, encerrar o lote. Falha encerra esta linha de variações na opening; não aumentar automaticamente esforço, tokens ou instruções. Sucesso neste caso exige verificação independente antes de generalização. Narrativa, runtime e CAP-001 permanecem sem aprovação.

Janela medium iniciada às 2026-09-07T15:48:23.9501113Z, PID 21268; último estado `running_authorized_probe`. Não abrir outra janela. Conferir primeiro `C:\Users\skate\AppData\Local\Temp\storyteller-record-medium-live-20260907\status.json` e o prompt de retomada. Não duplicar janela/lote. A única dependência humana é a entrada segura da chave; a autorização técnica já existe. A chave é descartada ao término.
