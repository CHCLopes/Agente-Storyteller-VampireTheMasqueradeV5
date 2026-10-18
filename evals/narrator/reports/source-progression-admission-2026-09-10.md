# Contraprova offline de admissão de progressão

Em 10/09/2026, o coordenador atual admitiu uma continuação autorada com interrupção
do som e pulsações na luz, sem mudança no core ou nos validadores. Os quatro testes
passaram: um positivo e três negativos. A revisão independente não encontrou bloqueador.
Isso demonstra que a admissão permite ao menos essa progressão concreta; não prova
que o modelo a produzirá, nem que toda boa narrativa será admitida.

## Evidência e origem

O primeiro texto é cópia literal da resposta sintética inicial do lote progressing
19b93f22, identificado como fixture FakeLLM. A continuação foi escrita pelo agente
revisor; não é resposta do Groq. Os alvos dos testes são fake/synthetic. Nenhuma
chamada externa, credencial, save real ou promoção de narrativa a fato canônico.

Continuação autorada:

> O zumbido do ar-condicionado se interrompe. Por um instante, a luz central enfraquece, e a partícula de poeira desaparece no escuro. Quando o feixe retorna, pulsa duas vezes; seu brilho descontínuo recorta as molduras e faz o reflexo no mármore surgir e sumir. O ar-condicionado continua silencioso. Após uma pausa, as duas pulsações se repetem, enquanto o restante da galeria conserva a iluminação fria. A causa dessas pulsações permanece incerta.

> O que você faz diante dessas pulsações?

## Resultado verificável

- Positivo: dois commits; fonte inicial integral no segundo USER; duas fontes
  recuperadas após reinício; replay sem gateway ou novo chunk. Cena, estado e relações
  preservados. Revisões e eventos de declaração avançaram normalmente; nenhuma memória
  ou novidade ficcional da prosa virou fato canônico.
- Ação forçada e emoção forçada: recusadas por `scene_player_agency_violation`.
- Conteúdo mecânico interno: recusado por `scene_internal_content`.
- Cada recusa impediu o segundo commit/fonte/chunk e o replay terminal não reenviou.

Rodada focada: **4 passed, 0 failures, 0 skips**, 1,74 s no pytest (1,619 s no JUnit).
Bloqueio de rede do conftest ativo. Somente warning preexistente de python_multipart.
Os 55 fingerprints de preservação permaneceram intactos. Código e evidência com hashes
no JSON correspondente; prova final: `C:\Users\skate\AppData\Local\Temp\storyteller-source-progression-admission-20260910\final.json`, SHA-256 `5e055bdd686aaca1f9bd35b3138ea0ba8e83a0df3811a4f32e57e65a4510fee4`.

## Limites e continuidade

O negativo mecânico cobre conteúdo técnico interno explícito. Não comprova detector
geral de dano ou recurso inventado quando o resultado é unresolved. Esse limite
preexistente não foi alterado e nenhuma ocorrência desse tipo foi observada no lote.

Qualidade geral, capacidade do modelo, runtime e CAP-001 continuam sem aprovação.
Próximo passo autorizado: diagnóstico puro com duas fontes sintéticas autoradas,
ambiente estável e acontecimento iniciado, preservando SYSTEM, schema, alvo e parâmetros.
As condições são independentes; uma resposta não alimenta a outra. Plano:
`plan/feature-source-progression-diagnostic-1.md`.
