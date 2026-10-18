# Pergunta a NPC desviada para lore — observação e correção — 16/09/2026

## Observação congelada

Após o turno bem-sucedido de Mara, a mesma sessão isolada recebeu uma única ação:
`Mara, quem é a fundadora deste lugar?`. O turno foi tecnicamente confirmado,
mas não passou por H6 nem pelo catálogo. H0 classificou a pergunta como lore e a
execução registrada foi `h4.answer_lore_query`.

H4 respondeu com uma associação incorreta entre Mara e uma entidade ancestral do
clã Brujah, desviou para Perdição e Compulsão e afirmou que essa compulsão obrigava
o personagem a buscar vingança. O texto não respondia à história local, inventou
lore e atribuiu uma obrigação interna ao jogador. A persistência confirma a
fronteira contornada: o turno 2 não contém fatos nem
`world.scene.beat_resolution`.

Evidência:

- operação `mara-founder-1e44c905-2a77-470e-a1f2-9e22f71d63c0`;
- turno `ee963706-d7fc-51f8-bdf6-7ccb3d098041`;
- resultado `5c79bea14cbc16115810063b1ded9740c062f48d97e54b17e55e09432f721874`;
- Groq/Qwen, 272 tokens de entrada, 129 de saída e 401 no total;
- status histórico `completed`, sem erro, beat ou fatos.

O banco é sintético e isolado. O turno histórico não foi reescrito ou
reclassificado.

## Causa

A triagem determinística já protegia imperativos como `Mara, me fale...`, mas a
triagem LLM permanecia livre para tratar `Mara, quem é...` como consulta de lore.
Ela não recebia a lista de NPCs presentes. Assim, uma forma natural de diálogo
contornava a direção de cena, o catálogo e a admissão H6.

## Correção prospectiva

`triage_input` agora recebe aliases dos NPCs presentes. Uma mensagem iniciada pelo
nome presente seguido de vírgula, ou construída como `pergunto/digo/falo a|com`
esse NPC, é roteada deterministicamente como ação antes de chamar H0. A regra é
limitada ao elenco da cena; nomes ausentes e perguntas gerais continuam na
triagem normal. O prompt H0 também explicita que pergunta dirigida a NPC é fala
em cena.

No teste integrado, `Mara, quem é a fundadora deste lugar?` não chama H0/H4 e
produz o beat `mara.founder` com o efeito
`mara.responds.without_founder_identity`. A pergunta geral `O que é a Camarilla?`
continua lore mesmo com Mara presente.

Verificação: **165 testes passaram**, zero falhas e três avisos preexistentes
(depreciação Starlette e cache pytest sem permissão). O servidor manual em
execução foi iniciado antes da correção e precisa ser reiniciado para a
contraprova ao vivo. Nenhuma chamada adicional deve ocorrer no processo antigo.

## Limites

A correção garante a rota e a presença do beat. Ela não transforma uma amostra em
aprovação de modelo nem prova, por si só, que toda verbalização futura obedecerá ao
limite de identidade. A próxima observação deve verificar separadamente rota,
efeito declarado, narrativa, fatos, agência e ausência de revelação direta. Não
aprova modelo padrão, campanha, runtime comercial ou CAP-001.

