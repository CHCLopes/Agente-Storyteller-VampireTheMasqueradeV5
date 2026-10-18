# Protocolo offline de resolução de cena v1

O corpus `scene_resolution_offline_v1.json` é sintético, autorado e congelado.
Não contém geração de provedor nem dados de campanha. Cada caso fornece um beat,
uma proposta H6 e o estado anterior. O avaliador usa os validadores e a projeção
de produção, sem rede, relógio, banco ou aleatoriedade.

Os cinco gates são obrigatórios: causalidade entre beat e proposta; preservação
da agência do jogador; atribuição e proteção de segredos; progressão observável;
e não contradição do resultado, local, pendências e fatos vinculantes. Casos
marcados `admitted` precisam passar todos e produzir estado compatível. Casos
marcados `rejected` precisam falhar com o código exato autorado.

Um resultado aprovado qualifica somente o contrato offline. Não escolhe modelo,
não ativa o resolvedor, não aprova campanha, runtime ou CAP-001.
