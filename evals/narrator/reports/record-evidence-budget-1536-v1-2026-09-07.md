# Diagnóstico record-evidence-budget-1536-v1 — preparação concluída

Data: 07/09/2026. Status: implementação e verificação offline concluídas; **a única execução autorizada foi posteriormente realizada e encerrada**. Nenhuma chamada real ocorreu durante a preparação. O lote `b129ceaa` terminou com HTTP 200/stop, schema aceito e envelope rejeitado por intervalos; sua [análise está concluída](record-evidence-budget-observation-b129ceaa-2026-09-07.md). Não há execução pendente de chave e este comando não deve ser repetido.

O usuário respondeu “Continue” à proposta de preparar e executar este diagnóstico. A autorização já existe e não requer nova confirmação. O [desenho original](record-evidence-budget-hypothesis-2c1cafde-2026-09-07.md) conserva seu status histórico de proposta; este documento registra a implementação posterior. O [registro JSON](record-evidence-budget-1536-v1-2026-09-07.json) contém parâmetros completos, hashes, grupos de testes e a integração sem credencial.

## Escopo implementado

Uma chamada para a abertura sintética fixa de bb98, usando Groq direto, `openai/gpt-oss-120b`, `reasoning_effort=low`, `include_reasoning=false`, temperatura 0,65 e saída estruturada sem streaming. SYSTEM, USER, schema, narrativa de origem e critérios de admissão são os mesmos do diagnóstico anterior. A única diferença no corpo é `max_completion_tokens: 768 → 1536`.

A execução aguarda inicialmente 60 segundos, revalida a integridade e então inicia a deadline de 60 segundos. A espera é conservadora e local; não coordena outros processos. Executar somente este diagnóstico, sem outro terminal chamando o provedor simultaneamente. Não há geração narrativa, chamada de Mara, diagnósticos de texto/streaming, retries, fallback ou loop de otimização.

Hashes SHA-256 do JSON canônico reconstruído (`ensure_ascii=False`, chaves ordenadas, separadores compactos, UTF-8):

- Corpo anterior: `e646d9e810c248dc293442ecc6582dffdc070c874c11c089c13e34f16852364f`.
- Corpo aprovado: `90a5fffba8a57247439dfa1f9cfba202aeb2dff0182ba9e2235f95673ea6429f`.
- Dossiê congelado: `a891c19c40be27c98d15f37e42a2f9f8a9706589403060d63c9cd41ced46c0fc`.

Esses hashes identificam a reconstrução canônica, não bytes capturados de tráfego.

## Arquivos e observabilidade

O novo executor `scripts/evaluate_narrator_record_budget.py` verifica o dossiê e o corpo antes da credencial e novamente antes do despacho. O wrapper `scripts/run_groq_record_budget_probe.ps1` confere escopo, proveniência, caso exato e resultado. O observador `scripts/narrator_record_budget_observer.py` restringe a tentativa ao corpo aprovado e expõe somente metadados permitidos.

Em erro, o observador lê no máximo 64 KiB dentro da mesma deadline e cancelamento. Não analisa prefixo incompleto. `failed_generation`, quando disponível, é examinado apenas em memória: presença, quantidade de caracteres, aceitação integral por `json.loads` e posição do erro. Corpo bruto, mensagem livre, raciocínio, headers e chave não são persistidos. Valores indisponíveis ficam nulos, em vez de sugerirem zero ou falso. Uso observado fica separado do agregado herdado do adaptador.

`json_valid` significa aceitação por `json.loads` do Python; não prova conformidade estrita, schema ou qualidade semântica. O normalizador HTTP 400 do runtime continua limitado a 32 KiB. Assim, o observador pode registrar um código permitido entre 32 e 64 KiB enquanto a categoria herdada continua `http_400`. O uso de `response._content` do HTTPX fica restrito ao observador experimental, para impedir buffering adicional após o limite.

O avaliador legado recebeu somente duas guardas de replay, 12 linhas adicionadas, para impedir que este diagnóstico seja usado como avaliação CAP. Runtime, prompts, contratos e validadores anteriores permanecem preservados, assim como summary/JSONL originais do lote 2c1cafde. Onze dos doze arquivos históricos conferidos mantêm o hash; a exceção é esse acréscimo explícito no avaliador legado.

## Verificação

**993 testes distintos passaram: 276 novos e 717 existentes; zero falhas finais e zero skips.** São grupos focados disjuntos, não uma nova execução da suíte inteira do repositório.

| Grupo | Aprovados | Tempo |
|---|---:|---:|
| Adaptadores e contratos anteriores | 568 | 114,42 s |
| Integração do executor | 58 | 78,88 s |
| Observador limitado | 63 | 2,06 s |
| Fronteiras de replay | 170 | 4,61 s |
| Wrapper, antes do ajuste final de case_id | 133 | 431,00 s |
| Contraprova adicional após o ajuste | 1 | 4,35 s |

O último ajuste do wrapper restringiu `case_id` exatamente a `opening`; a contraprova adicional passou depois dele. Smoke tests repetidos e execuções RED não foram somados. Houve apenas o aviso preexistente de `python_multipart`. Foram usados o venv existente, `STORYTELLER_DISABLE_DOTENV=1`, `PYTHONDONTWRITEBYTECODE=1`, persistência isolada e bloqueio de rede dos testes.

A integração real do wrapper com SecureString vazia aceitou o preflight e terminou com código 3 exatamente na validação da credencial: stderr vazio, nenhum artefato criado/removido, nenhuma chamada externa e 17 hashes preservados. Contraprovas cobrem falhas HTTP, origem não comprovada, corpo parcial/excedido, campos hostis, cancelamento, espera inicial real, integridade alterada, segunda tentativa, captura de saída e descarte do conteúdo bruto.

## Execução histórica concluída

A janela dedicada iniciou às 13:22:17 UTC e terminou às 13:24:00 UTC, depois da entrada protegida da chave pelo usuário. O comando abaixo documenta a execução já consumida; não o reutilizar como nova chamada autorizada:

```powershell
$budgetKey = Read-Host 'Groq API key - diagnostico unico 1536' -AsSecureString
try {
    & .\scripts\run_groq_record_budget_probe.ps1 -ApiKey $budgetKey
}
finally {
    $budgetKey.Dispose()
    Remove-Variable budgetKey -ErrorAction SilentlyContinue
}
```

O wrapper produziu o batch `b129ceaa-599c-4448-b095-d37c0f0411c1` em `eval-results/20260907T132254Z-a1b6496d-fa4b-4ce8-9a03-2ebc04c6af27`. O launcher confirmou `finished`, exit 1. Não iniciar outra janela nem repetir a chamada.

Summary e JSONL foram lidos integralmente; proveniência, término, intervalos e fidelidade foram analisados. A comparação com 768 tokens é histórica, sem conclusão causal A/B. Sucesso operacional não aprova qualidade narrativa, runtime ou CAP-001. A revisão técnica local segue autônoma; a aceitação final do produto continua humana.
