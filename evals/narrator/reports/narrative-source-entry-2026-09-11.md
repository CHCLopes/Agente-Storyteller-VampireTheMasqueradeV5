# Entrada interna B — 11/09/2026

Concluídos o contrato público de intenção e a guarda de consistência de contexto
para a futura entrada optativa B. Os dois novos arquivos compõem com o preparador
existente sem alterar transporte ou caminho do jogo.

## Comportamento entregue

- `SourcePlayerActionRequest` aceita exatamente `operation_id` e `player_input`:
  tipos estritos, campos extras recusados, imutabilidade e revalidação de instâncias
  adulteradas. ID B 1..240 e texto 1..500 caracteres. Padding externo recusado;
  espaços internos, quebras de linha e Unicode preservados literalmente.
- `validate_source_entry_snapshot(snapshot, *, session_id)` exige snapshot exato,
  revalida origem/cena e vincula a sessão informada pelo servidor. Retorna cópia
  independente; não autentica banco nem prova atualidade da base.
- Helpers expõem erro fechado, sem refletir input ou diagnóstico arbitrário.
  Nenhuma classificação, reserva, persistência, RNG ou chamada LLM ocorre aqui.

## Verificação observada

Rodada congelada única: **161 passed em 2,91 s**, 72 testes novos da entrada e
89 regressões diretas de contexto; zero falhas/skips. Um aviso preexistente sobre
`python_multipart`. Conftest ativo, `STORYTELLER_DISABLE_DOTENV=1`, saída 0 e
sucesso do shell conferidos junto ao JUnit. Nenhuma chamada externa.

Cobertura inclui extras privilegiados, tipos/limites, cópias adulteradas, origem
legada, sessão divergente, ausência de efeitos e composição literal com o preparador
nos limites máximos. Revisão independente do código, hashes e evidência encerrada
sem bloqueadores. Hashes dos 11 arquivos existentes monitorados preservados.
Log/JUnit e digests individuais estão registrados no JSON acompanhante.

## Desenho concluído, implementação separada

O plano do produtor pré-recibo separa controle P da cápsula K e da narrativa H.
Especifica claim antes da produção, gravação K/P em uma transação, replay antes
do CAS e falha segura sem K para esclarecimento, fora de escopo ou base obsoleta.
P pending após crash não autoriza outra interpretação/rolagem. Essas propriedades
são requisitos para o próximo incremento; não foram implementadas pela entrada.

Revisão documental incorporou quatro correções acima e uma matriz de criação,
introdução, ação, resolução, retenção, diagnóstico, reconexão e experiência.
O plano da entrada foi concluído no escopo de contrato+desenho; a implementação
do produtor tem acompanhamento próprio. Não exige chave ou nova ação do usuário.

## Limites e próximos passos

Nenhuma rota pública, frontend, default, save real ou CAP-001 alterado. O limite
ordinário do primeiro ensaio não redefine V5 ou as decisões de improvisação.
Próximo incremento: modelos puros do produtor e testes, seguido de claim/finalize
transacionais. Setup/introdução, transporte e prova narrativa continuam separados.

- [Plano da entrada concluído](../../../plan/feature-narrative-source-opt-in-entry-1.md)
- [Plano do produtor](../../../plan/feature-narrative-source-input-producer-1.md)
- [Evidência estruturada](narrative-source-entry-2026-09-11.json)
