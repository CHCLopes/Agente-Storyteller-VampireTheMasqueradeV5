# Gate vivo — HYP-002-L2

**Data:** 2026-09-25

**Status:** L2 autorizada; preparação offline verificada; zero chamada HYP-002

O usuário respondeu `Aprovo HYP-002-L2`. A autorização cobre os dois alvos
exatos, oito casos novos por alvo e máximo absoluto de 16 chamadas, conforme
`narrator-prospective-admission-hypothesis-002-2026-09-25.md`.

Alvos e parâmetros congelados:

- `qwen/qwen3.8-27b`, reasoning `none`;
- `openai/gpt-oss-120b`, reasoning `low`;
- Groq oficial, temperatura 0,65, teto 768 tokens e deadline 60 segundos;
- intervalo mínimo global de 60 segundos;
- zero retry, reparo, fallback, troca de alvo ou repetição de slot.

A sonda de autenticação anterior não pertence ao lote. Nenhuma chamada HYP-002
foi realizada na criação deste gate. O corpus, protocolo, prompt, verificador,
runner e launcher foram implementados. Passaram 34 testes próprios e 66 testes
combinados de HYP-001 + HYP-002; o preflight permanece keyless, com 16 slots e
zero inspeção de credencial.

O opt-in vivo não admite candidato, não cria default e não autoriza campanha
híbrida. Depois do lote e da revisão independente, o resultado volta a checkpoint
humano.
