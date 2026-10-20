# HYP-007-L11 — avanço ambiental e preparação L12

Data: 18/10/2026. Target `gpt-5.6-luna`, low, prompt v4.
Batch `1b1382a6-1ed6-4ae9-840d-c01f394a0077`.

## Observado

L10 aceito e L11 autorizado por Continue. Após entrada protegida confirmada,
L11 fez seis chamadas e completou cinco turnos. CAMP-EVAL-01 ajuda/resgate
intacto concluído; CAMP-EVAL-02 confirmou aviso, dano e ajuda, mas rejeitou
resgate parcial R-06. Parada campaign_source_policy_failed. 03–08 não alcançados.
Gate paid/live L11 fechado; trava mantida, sem retry/fallback e sem transferir
11 slots restantes. Nenhum narrador admitido; TASK-013/CAMP-24/MVP abertos.

Artefatos originais preservados em
`eval-results/hybrid-campaign-luna-l11-1b1382a6-1ed6-4ae9-840d-c01f394a0077/`.
SHA256 records: `1fb30882af8b517a8f61078db84b98b6675ace979db1d92a671863f9e3003a18`.
SHA256 summary: `0c53ba1c54527ed6322d6fce4843f2708ffe4b4c1f9d4c9f30fa13655771cfe2`.
Manifesto fechado L11: `b96ae204e3d03eb3216b9c56185e56443cf520470681c1ff7ab5c30167cafa35`.

## Custo e tempo

**USD 0,0052376 estimados**, não cobrança confirmada; 18.346 tokens entrada,
1.307 saída, seis chamadas com usage, zero sem. Reproduzido por
scripts.report_luna_test_cost --settled com hash de records conferido.
Sem ajustes de cache, tarifas ou impostos. Correção/preparação adicional USD 0.
Geração: mínimo 3.289 ms/máximo 4.941 ms/média 4.016,17 ms.
Turno: mínimo 3.595 ms/máximo 5.257 ms/média 4.335,17 ms.
São seis observações sintéticas, não SLA/aceitação de UX.

## Diagnóstico e correção

Texto original: "Você retira o registro da bancada baixa no Arquivo antes que
a umidade avance mais." O scanner atribuiu avance ao jogador na oração
principal, não ao sujeito explícito umidade da subordinada temporal.
Reprodução bruta: scene_player_agency_violation, narrative, subject voce,
clause_index 0, unauthorized_concepts move.

Em _action_signature_matches, ignorar somente família advance/token avance
quando precedido por antes que a umidade e seguido de mais + pontuação/fim.
Preserva offsets/texto/verbos posteriores, sem correferência generalizada,
sem mudar autoridade, schema, prompt, catálogo, RNG ou persistência.
Não reescrever resposta ou reclassificar rejeição histórica L11.

Oito novos testes em tests/test_scene_moisture_advance_regressions.py.
Antes da correção, exato e integração segura falhavam; seis contraprovas já
passavam. Depois, 44 focados de política e 33 de preparação/histórico/exato
aprovados (sobrepostos), um aviso preexistente. Decisão/partida/abertura reais
posteriores continuam rejeitadas. Trocar umidade por sujeito pessoal não recebe
esta exceção. Integração prepara aviso/dano/ajuda e resgate parcial: seguro
confirma revisão quatro/outcome partial/posição dry_surface; inseguro mantém
revisão três/registro wet/sem desfecho e sem nova entrega. Reinício/replay
preserva envelope, uma geração/entrega do resgate, nenhum RNG novo.

Regressão ampliada: **915 aprovados**, um aviso preexistente python_multipart,
110,91s. XML eval-results/hyp-007-l12-readiness-2026-10-18.xml, zero errors/
failures. Seleção cobre históricos L5–L11/prospectivo L12, agência, atribuição,
visibilidade, contratos, campanha, persistência, custo e regressões de segurança.
Contagens focadas são sobrepostas. Não rodada suíte integral/frontend/build;
sem alteração nessas camadas. Não declarar release verde. Diff inspecionado,
diff --check sem erros; sem commit/push, checkout original preservado.

## Preparação L12, sem autorização de gasto

L12 separado: mesmo prompt v4/modelo low/oito percursos/limites, 17 chamadas,
768 tokens/20.000 bytes/60s. Teto adicional estimado proposto USD 0,15,
sem retry/fallback/admissão automática. Paid/live false, 22 hashes válidos;
preflight CLI 17 sintéticos/zero chamadas, máximo 13.614 bytes, AST sem erros.
Sem terminal/chave/trava live L12. Manifesto fechado SHA256:
`95e85fd707da58394d09bc12771a868b9f8766769740bdc12cf1b04af93c8f5c`.
Testes históricos L11 atualizam hashes só em manifesto temporário isolado e
provam recusa do runtime corrigido pelo manifesto executado preservado.

Conclusão delimitada proposta: L11 inconclusivo para campanha integral por
falso positivo de atribuição ambiental, nenhum narrador admitido. Aceitar
conclusão e autorizar L12 nos limites acima é a próxima proposta; Continue/
prossiga aprova ambos. Depois, entrada protegida. Não prometer última tentativa.
Gates lexicais não comprovam toda fidelidade semântica. Narrativa/UX ainda
precisam de julgamento humano; ressalvas L9 e pronomes com alias preservadas.
