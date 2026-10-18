# Correção local de pergunta com sujeito implícito

“O que fazes?” é uma pergunta aberta válida ao jogador. O lote Estufa f97a8568 expôs um falso negativo do validador, reproduzido antes da alteração com uma proposta sintética de controle: trocar somente q fazia a admissão falhar.

A correção acrescenta uma família delimitada por fullmatch no campo normalizado integral, com os mesmos adjuntos temporais/contextuais já admitidos. O resultado participa das guardas de metanarrativa e interlocutor existentes; não acrescenta “fazes” à busca ampla de ações. Reconhece a forma simples, “O que fazes agora?” e contextos permitidos, mantendo as recusas de NPC/vocativo, metanarrativa, prefixos e perguntas múltiplas.

O diff em api/scene_director_service.py tem seis linhas acrescentadas e uma substituída em relação ao snapshot da execução: 520ad02b →143ebab3. Depois da correção, **274 testes passaram**:217 regressões de perguntas, das quais30 novas, e57 casos do perfil de fonte. Zero falhas/skips; somente o aviso preexistente de python_multipart. Agência, sigilo e mecânica permaneceram protegidos. Testes sem rede externa, dotenv ou credenciais.

O resultado ao vivo continua com política rejeitada, zero projeções e um skip; não foi reproduzido nem reclassificado. A correção é local e não comprova retroativamente a admissão integral daquela narrativa. A direção B continua sem integração ativa de produto. [Provas, RED e diff](player-question-fazes-fix-2026-09-07.json).
