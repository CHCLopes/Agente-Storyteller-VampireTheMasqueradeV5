# Contraprova ao vivo — `mara.founder`

## Escopo

Após reiniciar o servidor com a correção de roteamento, foi preparada uma cena
isolada em `Galeria` com `Mara` presente. A ação
`Mara, quem é a fundadora deste lugar?` foi enviada uma única vez na cena
confirmada. Não houve rolagem, retry narrativo ou fallback.

Uma tentativa operacional anterior não conta para o gate: a preparação apontou
para o repositório de estado incorreto, a conexão permaneceu em `Elysium` com
`Príncipe` e `Xerife`, e a pergunta seguiu pela rota de lore. O erro foi detectado
antes da contraprova válida e não foi usado como evidência semântica.

## Resultado técnico

- sessão `local.6b1e2940-08c5-4aa8-bc62-dff0bf173916`;
- operação `mara-founder-929e1015-50b8-4e50-976c-8402d0d9c1fb`;
- turno `057f5315-aaf2-59e9-aa0a-fd162ed19ada`, número 2;
- execução `H6.direct_scene`, sem H0/H4;
- catálogo `mara.founder`;
- efeito `mara.responds.without_founder_identity`;
- Groq/Qwen, 1.639 tokens de entrada, 284 de saída e 1.923 no total;
- status `completed`, uma única persistência, sem erro;
- hash de resultado e payload
  `e47058814d828082a7eec70eabcfff75a46e6d1271ac1cd10f25a7adf6b680cf`.

## Resultado narrativo

Mara não revelou nome, rosto ou identidade da fundadora. Ela a chamou apenas de
“A Primeira”, respondeu de modo reservado e protetor, e transformou a recusa em
uma pista acionável ao convidar o jogador a ver os remanescentes do arquivo. O
turno não atribuiu fala, movimento, intenção ou decisão ao personagem do jogador.
O convite preserva a agência e oferece avanço sem tornar o catálogo um roteiro.

O modelo criou livremente gesto, diálogo, metáfora, atmosfera e a forma da pista.
O catálogo permaneceu mínimo: efeito vinculante, objetivos e espectros de reação
em chaves, sem fala pronta. Os fatos admitidos conservaram local e elenco e
registraram apenas mudanças observáveis coerentes com a resposta.

## Conclusão delimitada

TASK-025 passou. A correção de roteamento e o catálogo mínimo de Mara funcionaram
juntos no caminho padrão para este tópico. Esta observação encerra o incremento
Mara, mas não aprova modelo padrão, campanha, runtime ou CAP-001.
