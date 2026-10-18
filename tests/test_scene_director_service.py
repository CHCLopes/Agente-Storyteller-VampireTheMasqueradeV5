from datetime import datetime, timezone

import pytest

from api.scene_director_service import (
    SceneContinuationProposal,
    SceneProposalError,
    project_scene,
    validate_scene_continuation,
)
from api.scene_service import SceneState
from api.turn_models import CanonicalFact, Visibility


NOW = datetime(2026, 8, 26, tzinfo=timezone.utc)


def _resolution(success: bool) -> CanonicalFact:
    return CanonicalFact(
        fact_id="resolution",
        fact_type="mechanics.resolution",
        predicate="resolved_player_action",
        value={"is_success": success},
        occurred_at=NOW,
    )


def _proposal(**updates) -> SceneContinuationProposal:
    payload = {
        "narrative": (
            "As lâmpadas do galpão piscam quando a porta cede, revelando marcas "
            "recentes no piso e um rádio ainda ligado sobre a bancada; do mezanino, "
            "passos lentos respondem ao ruído e fazem a situação avançar."
        ),
        "outcome": "success",
        "location": "Galpão abandonado",
        "scene_summary": (
            "A entrada foi vencida, marcas recentes cruzam o piso e alguém se move no mezanino."
        ),
        "npcs_present": [],
        "new_facts": [
            {
                "kind": "clue",
                "summary": "Marcas recentes atravessam o piso em direção ao mezanino.",
                "visibility": "player",
                "importance": 0.8,
                "pending": False,
            },
            {
                "kind": "hook",
                "summary": "Passos lentos soam no mezanino.",
                "visibility": "player",
                "importance": 0.7,
                "pending": True,
            },
        ],
        "open_threads": ["Descobrir quem está no mezanino"],
        "player_prompt": "Os passos param acima de você; o que faz?",
    }
    payload.update(updates)
    return SceneContinuationProposal.model_validate(payload)


def test_admitted_improvisation_projects_a_reusable_scene() -> None:
    proposal = validate_scene_continuation(
        _proposal(), facts=(_resolution(True),), current_scene=None
    )

    scene = project_scene(proposal, previous=None, turn_number=4)

    assert scene.location == "Galpão abandonado"
    assert scene.last_turn == 4
    assert "Marcas recentes" in scene.details[0]
    assert scene.open_threads == ("Descobrir quem está no mezanino",)


def test_llm_wire_format_is_compact_but_round_trips_to_domain_names() -> None:
    proposal = _proposal()

    wire = proposal.model_dump_json(by_alias=True)
    restored = SceneContinuationProposal.model_validate_json(wire)

    assert '"n":' in wire
    assert '"f":' in wire
    assert '"r":' in wire
    assert '"narrative":' not in wire
    assert '"new_facts":' not in wire
    assert restored == proposal
    assert restored.model_dump()["narrative"] == proposal.narrative


def test_open_thread_is_removed_only_by_an_explicit_known_resolution() -> None:
    previous = SceneState(
        location="Galpão abandonado",
        open_threads=(
            "Descobrir quem está no mezanino",
            "Identificar o dono do rádio",
        ),
    )
    proposal = _proposal(
        outcome="unresolved",
        location=previous.location,
        open_threads=("A sirene distante exige uma reação",),
        resolved_threads=("Descobrir quem está no mezanino",),
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(),
        current_scene=previous,
        player_input="Investigo quem está no mezanino.",
    )
    scene = project_scene(accepted, previous=previous, turn_number=5)

    assert scene.open_threads == (
        "Identificar o dono do rádio",
        "A sirene distante exige uma reação",
    )


def test_unknown_thread_cannot_be_declared_resolved() -> None:
    previous = SceneState(
        location="Galpão abandonado",
        open_threads=("Encontrar a chave do cofre azul",),
    )

    with pytest.raises(
        SceneProposalError, match="scene_unknown_thread_resolution"
    ):
        validate_scene_continuation(
            _proposal(
                outcome="unresolved",
                location=previous.location,
                resolved_threads=("Descobrir quem está no mezanino",),
            ),
            facts=(),
            current_scene=previous,
        )


def test_known_thread_needs_evidence_in_the_completed_beat() -> None:
    previous = SceneState(
        location="Galpão abandonado",
        open_threads=("Encontrar a chave do cofre azul",),
    )

    with pytest.raises(
        SceneProposalError, match="scene_thread_resolution_without_evidence"
    ):
        validate_scene_continuation(
            _proposal(
                outcome="unresolved",
                location=previous.location,
                resolved_threads=("Encontrar a chave do cofre azul",),
            ),
            facts=(),
            current_scene=previous,
        )


def test_scene_projection_never_silently_discards_open_threads() -> None:
    previous = SceneState(
        location="Galpão abandonado",
        open_threads=tuple(f"Pendência {index}" for index in range(1, 6)),
    )
    proposal = _proposal(
        outcome="unresolved",
        location=previous.location,
        open_threads=("Nova pendência",),
    )

    scene = project_scene(proposal, previous=previous, turn_number=6)

    assert scene.open_threads == (*previous.open_threads, "Nova pendência")


def test_scene_without_a_roll_can_be_established_instead_of_stalling() -> None:
    proposal = _proposal(outcome="unresolved")

    accepted = validate_scene_continuation(
        proposal, facts=(), current_scene=None
    )

    assert accepted.location == "Galpão abandonado"
    assert "o que faz" in accepted.player_prompt.casefold()


def test_mechanical_outcome_remains_authoritative() -> None:
    with pytest.raises(SceneProposalError, match="scene_outcome_mismatch"):
        validate_scene_continuation(
            _proposal(outcome="failure"),
            facts=(_resolution(True),),
            current_scene=None,
        )


def test_failure_can_add_pressure_but_not_a_conclusive_clue() -> None:
    failed = _proposal(
        outcome="failure",
        narrative=(
            "A busca falha em localizar o registro esperado, e nada conclusivo surge "
            "entre as caixas; antes que o silêncio retorne, faróis varrem as janelas "
            "e a pressão de uma chegada transforma a demora em risco imediato."
        ),
        new_facts=[
            {
                "kind": "clue",
                "summary": "O livro-caixa identifica definitivamente o culpado.",
                "visibility": "player",
                "importance": 0.9,
                "pending": False,
            }
        ],
    )

    with pytest.raises(
        SceneProposalError, match="scene_failure_granted_conclusive_clue"
    ):
        validate_scene_continuation(
            failed, facts=(_resolution(False),), current_scene=None
        )


def test_failure_narrative_cannot_claim_that_the_goal_was_reached() -> None:
    failed = _proposal(
        outcome="failure",
        narrative=(
            "A busca falha diante das caixas lacradas, mas descobre o registro "
            "definitivo escondido sob a bancada; a pressão cresce quando faróis "
            "varrem as janelas e um motor para diante do galpão abandonado."
        ),
        new_facts=[
            {
                "kind": "complication",
                "summary": "Um veículo para diante do galpão.",
                "visibility": "player",
                "importance": 0.8,
                "pending": True,
            }
        ],
    )

    with pytest.raises(SceneProposalError, match="scene_failure_granted_goal"):
        validate_scene_continuation(
            failed, facts=(_resolution(False),), current_scene=None
        )


def test_location_change_requires_an_explicit_transition_fact() -> None:
    previous = SceneState(location="Elysium")

    with pytest.raises(
        SceneProposalError, match="scene_location_changed_without_transition"
    ):
        validate_scene_continuation(
            _proposal(new_facts=_proposal().new_facts[:1]),
            facts=(_resolution(True),),
            current_scene=previous,
        )


def test_npc_roster_change_requires_an_explicit_scene_event() -> None:
    previous = SceneState(location="Galpão abandonado")

    with pytest.raises(
        SceneProposalError, match="scene_npc_roster_changed_without_event"
    ):
        validate_scene_continuation(
            _proposal(npcs_present=("Mara",)),
            facts=(_resolution(True),),
            current_scene=previous,
        )


def test_narrator_cannot_decide_for_the_player_character() -> None:
    proposal = _proposal(
        narrative=(
            "A porta se abre para o galpão e você decide aceitar o chamado vindo do "
            "mezanino, enquanto as lâmpadas oscilam sobre marcas recentes no chão e "
            "um rádio ligado repete uma frequência sem identificação."
        )
    )

    with pytest.raises(SceneProposalError, match="scene_player_agency_violation"):
        validate_scene_continuation(
            proposal, facts=(_resolution(True),), current_scene=None
        )


def test_storyteller_fact_cannot_be_copied_into_player_text() -> None:
    secret = "O Príncipe ordenou secretamente a emboscada no galpão."
    proposal = _proposal(
        narrative=(
            "A investigação consegue avançar entre as caixas e o rádio ligado chia "
            f"antes de uma voz desaparecer; {secret} A tensão aumenta quando passos "
            "medidos cruzam o mezanino acima."
        ),
        new_facts=[
            {
                "kind": "hook",
                "summary": secret,
                "visibility": Visibility.STORYTELLER,
                "importance": 0.9,
                "pending": True,
            }
        ],
    )

    with pytest.raises(SceneProposalError, match="scene_secret_disclosed"):
        validate_scene_continuation(
            proposal, facts=(_resolution(True),), current_scene=None
        )


@pytest.mark.parametrize(
    ("field", "visible_value"),
    (
        ("location", "O Xerife armou uma emboscada no cais."),
        ("scene_summary", "O Xerife armou uma emboscada no cais."),
        ("npcs_present", ("O Xerife armou uma emboscada no cais.",)),
        ("open_threads", ("O Xerife armou uma emboscada no cais.",)),
        ("player_prompt", "O Xerife armou uma emboscada no cais; o que faz?"),
    ),
)
def test_storyteller_fact_cannot_leak_through_other_player_visible_fields(
    field: str,
    visible_value,
) -> None:
    secret = "O Xerife armou uma emboscada no cais."
    proposal = _proposal(
        **{
            field: visible_value,
            "new_facts": [
                {
                    "kind": "hook",
                    "summary": secret,
                    "visibility": Visibility.STORYTELLER,
                    "importance": 0.9,
                    "pending": True,
                }
            ],
        }
    )

    with pytest.raises(SceneProposalError, match="scene_secret_disclosed"):
        validate_scene_continuation(
            proposal, facts=(_resolution(True),), current_scene=None
        )


def test_storyteller_fact_paraphrase_is_rejected_conservatively() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Uma armadilha ordenada pela autoridade da guarda cerca os armazéns "
            "do porto. Sombras ocupam as saídas enquanto um motor distante se cala, "
            "deixando claro que alguém aguarda qualquer movimento entre os prédios."
        ),
        scene_summary=(
            "Uma armadilha organizada pela guarda cerca os armazéns do porto."
        ),
        new_facts=[
            {
                "kind": "hook",
                "summary": "O Xerife armou uma emboscada no cais.",
                "visibility": Visibility.STORYTELLER,
                "importance": 0.9,
                "pending": True,
            }
        ],
        open_threads=("Escapar do cerco",),
        player_prompt="Como pretende sair sem chamar atenção?",
    )

    with pytest.raises(SceneProposalError, match="scene_secret_disclosed"):
        validate_scene_continuation(proposal, facts=(), current_scene=None)


def test_storyteller_fact_cannot_overlap_a_player_visible_fact() -> None:
    proposal = _proposal(
        outcome="unresolved",
        new_facts=[
            {
                "kind": "hook",
                "summary": "O Xerife armou uma emboscada no cais.",
                "visibility": Visibility.STORYTELLER,
                "importance": 0.9,
                "pending": True,
            },
            {
                "kind": "observation",
                "summary": "A emboscada do Xerife ocupa o cais.",
                "visibility": Visibility.PLAYER,
                "importance": 0.8,
                "pending": True,
            },
        ],
    )

    with pytest.raises(SceneProposalError, match="scene_secret_disclosed"):
        validate_scene_continuation(proposal, facts=(), current_scene=None)


def test_unannounced_player_actions_are_rejected() -> None:
    proposal = _proposal(
        outcome="unresolved",
        location="Galpão abandonado",
        narrative=(
            "Você entra no corredor, fecha a porta atrás de si e guarda uma chave "
            "no bolso. O rádio chia sobre a bancada enquanto passos apressados se "
            "aproximam pelo salão escuro e uma lâmpada oscila sobre as caixas."
        ),
        scene_summary="O corredor contém uma chave e uma ameaça próxima.",
        new_facts=[
            {
                "kind": "observation",
                "summary": "Há papéis espalhados sobre a bancada.",
                "visibility": Visibility.PLAYER,
            }
        ],
        open_threads=("Passos se aproximam",),
        player_prompt="Como reage à aproximação?",
    )

    with pytest.raises(SceneProposalError, match="scene_player_agency_violation"):
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=SceneState(location="Galpão abandonado"),
            player_input="Investigo as marcas no chão.",
        )


def test_static_location_between_objects_is_not_player_movement() -> None:
    proposal = _proposal(
        outcome="unresolved",
        location="Beco sob néon",
        narrative=(
            "A chuva fina escorre pelos postes e deixa o asfalto brilhando sob a "
            "luz vermelha. Você está num beco estreito, entre caixotes úmidos e "
            "uma parede coberta de pichações antigas. Um letreiro falha acima da "
            "rua, enquanto passos distantes quebram o silêncio sem decidir seu rumo."
        ),
        scene_summary="O Neófito está em um beco estreito sob um letreiro instável.",
        new_facts=[
            {
                "kind": "observation",
                "summary": "Caixotes úmidos ocupam um lado do beco.",
                "visibility": Visibility.PLAYER,
            }
        ],
        open_threads=("Identificar a origem dos passos",),
        player_prompt="O que você faz primeiro?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(),
        current_scene=None,
        player_input="Onde estou?",
        player_aliases=("Neófito",),
    )

    assert accepted is proposal


def test_crossing_a_door_is_rejected_when_player_only_investigated() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você cruza a porta metálica e chega ao centro do galpão. O rádio "
            "chia mais alto na bancada, enquanto passos ecoam no mezanino e a "
            "poeira dança na luz fraca. Entre as caixas, uma sombra muda de lugar "
            "e faz uma corrente bater contra a parede de concreto."
        ),
        player_prompt="O que você faz diante da sombra?",
    )

    with pytest.raises(SceneProposalError, match="scene_player_agency_violation"):
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=SceneState(location="Galpão abandonado"),
            player_input="Investigo o galpão abandonado.",
        )


def test_bare_character_label_cannot_invent_waking_or_amnesia() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "A chuva fina escorre pelos postes, deixando o asfalto brilhante sob "
            "a luz vermelha. Você está num beco estreito, entre caixotes úmidos e "
            "uma parede coberta de pichações antigas. Um letreiro falha acima da "
            "rua, enquanto passos distantes quebram o silêncio da madrugada."
        ),
        location="Beco sob néon",
        scene_summary=(
            "Personagem desperta num beco chuvoso, sem memória do local, com um "
            "bar próximo como referência."
        ),
        new_facts=[
            {
                "kind": "observation",
                "summary": "A chuva apagou os rastros visíveis no chão do beco.",
                "visibility": Visibility.PLAYER,
            }
        ],
        open_threads=("Descobrir como chegou ao beco",),
        player_prompt="O que você faz diante do letreiro?",
    )

    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=None,
            player_input="Onde estou?",
        )

    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["field"] == "scene_summary"


def test_declared_player_actions_may_be_echoed() -> None:
    proposal = _proposal(
        outcome="unresolved",
        location="Galpão abandonado",
        narrative=(
            "Você entra no corredor, fecha a porta atrás de si e guarda uma chave "
            "no bolso. O rádio chia sobre a bancada enquanto passos apressados se "
            "aproximam pelo salão escuro e uma lâmpada oscila sobre as caixas."
        ),
        scene_summary="O corredor contém uma chave e uma ameaça próxima.",
        new_facts=[
            {
                "kind": "observation",
                "summary": "Há papéis espalhados sobre a bancada.",
                "visibility": Visibility.PLAYER,
            }
        ],
        open_threads=("Passos se aproximam",),
        player_prompt="Como reage à aproximação?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Entro no corredor, fecho a porta e guardo a chave.",
    )

    assert accepted is proposal


def test_location_change_requires_player_movement_intent() -> None:
    proposal = _proposal(
        outcome="unresolved",
        location="Telhado",
        narrative=(
            "Uma rajada empurra as portas do salão e revela a escada para o telhado. "
            "As antenas vibram sob a tempestade enquanto uma silhueta observa a rua, "
            "criando uma nova pressão imediata acima do edifício escuro."
        ),
        scene_summary="Uma escada exposta conduz ao telhado sob observação.",
        new_facts=[
            {
                "kind": "transition",
                "summary": "A cena avançou até o telhado.",
                "visibility": Visibility.PLAYER,
            }
        ],
        open_threads=("Identificar a silhueta",),
        player_prompt="O que observa antes de agir?",
    )

    with pytest.raises(
        SceneProposalError, match="scene_player_movement_not_authorized"
    ):
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=SceneState(location="Elysium"),
            player_input="Observo o salão.",
        )


def test_failure_observation_must_remain_pending() -> None:
    proposal = _proposal(
        outcome="failure",
        narrative=(
            "A busca falha entre os armários e permanece incompleta. Antes que o "
            "silêncio retorne, faróis varrem as janelas e a pressão de uma chegada "
            "transforma a demora em risco imediato dentro do galpão escuro."
        ),
        scene_summary="A busca incompleta aumenta a pressão no galpão.",
        new_facts=[
            {
                "kind": "observation",
                "summary": "Marcas interrompidas surgem perto do armário.",
                "visibility": Visibility.PLAYER,
                "pending": False,
            }
        ],
        open_threads=("Entender as marcas interrompidas",),
        player_prompt="O que faz antes que os visitantes entrem?",
    )

    with pytest.raises(
        SceneProposalError,
        match="scene_failure_granted_conclusive_observation",
    ):
        validate_scene_continuation(
            proposal,
            facts=(_resolution(False),),
            current_scene=None,
            player_input="Investigo os armários.",
        )


def test_failure_marker_defense_rejects_goal_hidden_in_another_fact_kind() -> None:
    proposal = _proposal(
        outcome="failure",
        narrative=(
            "A busca falha entre os armários e permanece incompleta. Antes que o "
            "silêncio retorne, faróis varrem as janelas e a pressão de uma chegada "
            "transforma a demora em risco imediato dentro do galpão escuro."
        ),
        scene_summary="A busca incompleta aumenta a pressão no galpão.",
        new_facts=[
            {
                "kind": "complication",
                "summary": "A prova definitiva identifica o responsável.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Lidar com os visitantes",),
        player_prompt="O que faz antes que os visitantes entrem?",
    )

    with pytest.raises(SceneProposalError, match="scene_failure_granted_goal"):
        validate_scene_continuation(
            proposal,
            facts=(_resolution(False),),
            current_scene=None,
            player_input="Investigo os armários.",
        )


def test_historical_storyteller_secret_cannot_be_copied_to_visible_output() -> None:
    secret = "O Xerife armou uma emboscada no cais."
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "A névoa cobre o cais enquanto o rádio chia entre os contêineres. "
            f"{secret} Passos ecoam na passarela, uma corrente bate contra o metal "
            "e a tensão cresce antes que qualquer rosto apareça sob a luz vermelha."
        ),
    )

    with pytest.raises(SceneProposalError, match="scene_secret_disclosed"):
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=None,
            protected_secrets=(secret,),
        )


def test_player_name_cannot_hide_an_undeclared_action() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Neófito abre a porta lateral e entra no corredor sem hesitar. As "
            "lâmpadas oscilam sobre o piso molhado, um rádio chia perto da bancada "
            "e passos apressados respondem ao movimento vindo do salão escuro."
        ),
    )

    with pytest.raises(SceneProposalError, match="scene_player_agency_violation"):
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=None,
            player_input="Observo o salão.",
            player_aliases=("Neófito",),
        )


def test_ambiguous_pronoun_cannot_hide_an_undeclared_player_action() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Ele abre a porta lateral e entra no corredor sem hesitar. As lâmpadas "
            "oscilam sobre o piso molhado, um rádio chia perto da bancada e passos "
            "apressados respondem ao movimento vindo do salão escuro."
        ),
    )

    with pytest.raises(SceneProposalError, match="scene_player_agency_violation"):
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=None,
            player_input="Observo o salão.",
            player_aliases=("Neófito",),
        )


def test_npc_named_after_pronoun_cannot_mask_player_action() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Neófito examina o salão sob as lâmpadas vacilantes. Ele abre a porta "
            "diante do Guarda e entra no corredor, enquanto o rádio chia sobre a "
            "bancada e passos apressados respondem do outro lado do galpão."
        ),
    )

    with pytest.raises(SceneProposalError, match="scene_player_agency_violation"):
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=None,
            player_input="Observo o salão.",
            player_aliases=("Neófito",),
            npc_aliases=("Guarda",),
        )


def test_pronoun_may_follow_an_explicitly_named_npc() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "O Guarda examina o salão sob as lâmpadas vacilantes. Ele abre a porta "
            "lateral e entra no corredor, enquanto o rádio chia sobre a bancada e "
            "passos apressados respondem do outro lado do galpão abandonado."
        ),
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(),
        current_scene=None,
        player_input="Observo o salão.",
        player_aliases=("Neófito",),
        npc_aliases=("Guarda",),
    )

    assert accepted is proposal


def test_failure_cannot_grant_goal_as_a_possessive_complication() -> None:
    proposal = _proposal(
        outcome="failure",
        narrative=(
            "A busca falha entre os armários e permanece incompleta enquanto passos "
            "se aproximam do galpão. Ainda assim, a chave procurada repousa agora na "
            "palma da mão de Neófito, antes que faróis atravessem as janelas sujas."
        ),
        new_facts=[
            {
                "kind": "complication",
                "summary": "A chave procurada repousa na palma da mão de Neófito.",
                "visibility": Visibility.PLAYER,
                "pending": False,
            }
        ],
    )

    with pytest.raises(SceneProposalError, match="scene_failure_granted_goal"):
        validate_scene_continuation(
            proposal,
            facts=(_resolution(False),),
            current_scene=None,
            player_input="Procuro a chave nos armários.",
            player_aliases=("Neófito",),
        )


def test_thread_stays_open_when_the_beat_says_it_remains_unknown() -> None:
    thread = "Descobrir quem se move atrás da porta metálica"
    previous = SceneState(
        location="Galpão abandonado",
        open_threads=(thread,),
    )
    proposal = _proposal(
        outcome="unresolved",
        location=previous.location,
        narrative=(
            "Ruídos persistem atrás da porta metálica, mas a identidade continua "
            "desconhecida. A maçaneta vibra sob uma pressão breve, o rádio perde o "
            "sinal e passos recuam antes que qualquer figura atravesse o corredor."
        ),
        scene_summary=(
            "A presença atrás da porta metálica permanece desconhecida e ativa."
        ),
        resolved_threads=(thread,),
    )

    with pytest.raises(
        SceneProposalError, match="scene_thread_resolution_without_evidence"
    ):
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=previous,
        )


def test_environmental_motion_after_player_perception_preserves_agency() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você sente o frio subir pelas botas enquanto o rádio chia sobre a "
            "bancada. Uma corrente bate contra o metal no fundo do galpão, passos "
            "pesados ecoam no mezanino e a névoa avança por baixo da porta lateral."
        ),
        scene_summary="O frio e a névoa anunciam uma presença no galpão.",
        new_facts=[
            {
                "kind": "complication",
                "summary": "A névoa fria avança por baixo da porta lateral.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar os passos no mezanino",),
        player_prompt="O que você faz diante desses sinais?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Permaneço atento aos sons do galpão.",
    )

    assert accepted is proposal


def test_tool_word_does_not_count_as_combat_action() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você examina as ferramentas cobertas de ferrugem sobre a bancada. O "
            "rádio chia entre caixas molhadas, passos lentos cruzam o mezanino e "
            "uma lâmpada vacila quando a porta lateral começa a vibrar no escuro."
        ),
        scene_summary="Ferramentas antigas dividem a bancada com um rádio ligado.",
        new_facts=[
            {
                "kind": "observation",
                "summary": "As ferramentas da bancada estão cobertas de ferrugem.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Descobrir quem está no mezanino",),
        player_prompt="O que você faz antes que a porta se abra?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Examino as ferramentas da bancada.",
    )

    assert accepted is proposal


@pytest.mark.parametrize(
    ("updates", "expected_field"),
    (
        (
            {
                "narrative": (
                    "You watch Mara cross the empty bar while a siren grows louder "
                    "outside. The windows tremble, a glass rolls over the counter, "
                    "and approaching footsteps turn the silence into immediate danger."
                )
            },
            "narrative",
        ),
        (
            {
                "new_facts": [
                    {
                        "kind": "complication",
                        "summary": "The approaching siren announces immediate danger.",
                        "visibility": Visibility.PLAYER,
                        "pending": True,
                    }
                ]
            },
            "new_facts[0].summary",
        ),
        (
            {"player_prompt": "What will you do before the siren reaches the bar?"},
            "player_prompt",
        ),
    ),
)
def test_player_facing_scene_fields_must_be_in_portuguese(
    updates: dict, expected_field: str
) -> None:
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(**updates),
            facts=(_resolution(True),),
            current_scene=None,
        )

    assert caught.value.code == "scene_output_not_portuguese"
    assert caught.value.evidence["field"] == expected_field


@pytest.mark.parametrize(
    ("updates", "expected_field"),
    (
        ({"location": "The warehouse in the harbor"}, "location"),
        (
            {"scene_summary": "The guard waits inside the abandoned warehouse."},
            "scene_summary",
        ),
        (
            {"npcs_present": ("The guard from the harbor",)},
            "npcs_present[0]",
        ),
        (
            {"open_threads": ("Find who waits inside the warehouse",)},
            "open_threads[0]",
        ),
        (
            {
                "resolved_threads": ("Discover who opened the warehouse door",),
            },
            "resolved_threads[0]",
        ),
        (
            {
                "new_facts": [
                    {
                        "kind": "hook",
                        "summary": "The sheriff waits inside the warehouse.",
                        "visibility": Visibility.STORYTELLER,
                        "pending": True,
                    }
                ]
            },
            "new_facts[0].summary",
        ),
    ),
)
def test_all_generated_h6_text_fields_apply_the_portuguese_gate(
    updates: dict, expected_field: str
) -> None:
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(**updates),
            facts=(_resolution(True),),
            current_scene=SceneState(
                location="Galpão abandonado",
                open_threads=("Discover who opened the warehouse door",),
            ),
        )

    assert caught.value.code == "scene_output_not_portuguese"
    assert caught.value.evidence["field"] == expected_field


def test_proper_names_do_not_fail_the_portuguese_gate() -> None:
    proposal = _proposal(
        npcs_present=("Mara", "Will Stone"),
        new_facts=[
            {
                "kind": "npc_action",
                "summary": "Mara observa a porta lateral do galpão.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(_resolution(True),),
        current_scene=None,
        npc_aliases=("Mara", "Will Stone"),
    )

    assert accepted is proposal


def test_agency_rejection_identifies_field_clause_and_concepts() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você entra no corredor e abre a porta sem esperar. As lâmpadas "
            "oscilam sobre o piso molhado, um rádio chia perto da bancada e passos "
            "apressados respondem do outro lado do galpão abandonado."
        ),
    )

    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=SceneState(location="Galpão abandonado"),
            player_input="Observo o corredor.",
        )

    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["field"] == "narrative"
    assert caught.value.evidence["subject"] == "voce"
    assert caught.value.evidence["unauthorized_concepts"] == [
        "interact",
        "move",
        "wait",
    ]
    assert caught.value.evidence["clause_index"] == 0
    assert "clause" not in caught.value.evidence


@pytest.mark.parametrize(
    "player_prompt",
    (
        "O que o pendrive pode revelar sobre o galpão?",
        "Qual é a fonte dos passos no mezanino?",
        "Mara decidirá falar antes de a sirene chegar ao bar?",
    ),
)
def test_player_prompt_must_invite_the_players_next_action(
    player_prompt: str,
) -> None:
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(player_prompt=player_prompt),
            facts=(_resolution(True),),
            current_scene=None,
        )

    assert caught.value.code == "scene_player_prompt_not_actionable"
    assert caught.value.evidence["field"] == "player_prompt"
    assert "player_prompt" not in caught.value.evidence


def test_english_npc_decision_prompt_is_rejected_without_echoing_it() -> None:
    player_prompt = "Will Mara decide to speak before the siren reaches the bar?"

    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(player_prompt=player_prompt),
            facts=(_resolution(True),),
            current_scene=None,
        )

    assert caught.value.code == "scene_output_not_portuguese"
    assert caught.value.evidence["field"] == "player_prompt"
    assert player_prompt not in str(caught.value.evidence)


def test_player_prompt_must_be_an_open_question_with_at_most_fifteen_words() -> None:
    prompts = (
        "Você abre a porta lateral?",
        (
            "Diante dos passos, da sirene e da janela quebrada, qual será agora "
            "a próxima ação cuidadosa do seu personagem?"
        ),
    )

    for player_prompt in prompts:
        with pytest.raises(SceneProposalError) as caught:
            validate_scene_continuation(
                _proposal(player_prompt=player_prompt),
                facts=(_resolution(True),),
                current_scene=None,
            )

        assert caught.value.code in {
            "scene_player_prompt_not_open",
            "scene_player_prompt_too_long",
        }


@pytest.mark.parametrize(
    "player_prompt",
    (
        "Como você lida com a ameaça?",
        "Qual caminho você escolhe?",
        "Qual será seu próximo movimento?",
        "Que caminho escolhe para alcançar a saída?",
    ),
)
def test_varied_open_player_action_questions_are_admitted(
    player_prompt: str,
) -> None:
    accepted = validate_scene_continuation(
        _proposal(player_prompt=player_prompt),
        facts=(_resolution(True),),
        current_scene=None,
    )

    assert accepted.player_prompt == player_prompt


def test_narrator_cannot_invent_waking_or_missing_player_knowledge() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você acorda deitado no asfalto frio, sem saber como chegou ao beco. "
            "Uma sirene cresce além dos telhados, as vitrines devolvem reflexos "
            "vazios e passos cautelosos ecoam atrás de uma caçamba enferrujada."
        ),
        location="Beco",
        scene_summary="Uma sirene e passos desconhecidos pressionam a cena no beco.",
        new_facts=[
            {
                "kind": "complication",
                "summary": "Passos cautelosos ecoam atrás de uma caçamba.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar a origem dos passos",),
        player_prompt="O que você faz ao ouvir os passos?",
    )

    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=SceneState(location="Beco"),
            player_input="Onde estou?",
        )

    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["field"] == "narrative"
    assert caught.value.evidence["rule"] in {
        "assigned_internal_state",
        "undeclared_player_action",
    }


@pytest.mark.parametrize(
    "player_prompt",
    (
        "O que fará Mara antes que a sirene chegue?",
        "Como reage Mara à aproximação dos passos?",
        "Qual caminho Mara escolhe?",
    ),
)
def test_player_prompt_cannot_address_an_npc_instead_of_the_player(
    player_prompt: str,
) -> None:
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(player_prompt=player_prompt),
            facts=(_resolution(True),),
            current_scene=None,
        )

    assert caught.value.code == "scene_player_prompt_not_actionable"
    assert caught.value.evidence["field"] == "player_prompt"
    assert caught.value.evidence["reason"] == "addresses_non_player_actor"
    assert player_prompt not in str(caught.value.evidence)


def test_one_interaction_verb_does_not_authorize_different_interactions() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você fecha a porta e aciona o alarme sem aviso. Uma sirene corta o "
            "galpão, luzes vermelhas cobrem as caixas e passos apressados respondem "
            "do mezanino enquanto a saída lateral começa a tremer."
        ),
        scene_summary="O alarme desperta movimento no galpão escuro.",
        new_facts=[
            {
                "kind": "complication",
                "summary": "O alarme atrai passos apressados no mezanino.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar quem respondeu ao alarme",),
        player_prompt="O que você faz diante da sirene?",
    )

    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=SceneState(location="Galpão abandonado"),
            player_input="Abro a porta.",
        )

    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["rule"] == "undeclared_player_action"
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


def test_same_declared_action_is_authorized_across_valid_inflections() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você abre a porta devagar. O rádio chia sobre a bancada, uma corrente "
            "bate contra o metal ao fundo e passos lentos cruzam o mezanino enquanto "
            "a luz da rua recorta caixas empilhadas no galpão."
        ),
        scene_summary="A porta aberta expõe um galpão ocupado por sinais recentes.",
        new_facts=[
            {
                "kind": "observation",
                "summary": "A porta aberta revela caixas empilhadas no galpão.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar os passos no mezanino",),
        player_prompt="O que você faz depois de abrir a porta?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Eu abro a porta devagar.",
    )

    assert accepted is proposal


def test_perception_does_not_exempt_a_required_player_action() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você percebe que precisa abrir a porta para escapar. A sirene cresce "
            "do lado de fora, luzes vermelhas atravessam as janelas e passos "
            "apressados descem do mezanino enquanto a maçaneta vibra no escuro."
        ),
        scene_summary="A porta fechada separa a personagem da saída.",
        new_facts=[
            {
                "kind": "complication",
                "summary": "Passos apressados descem do mezanino.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Escapar antes da chegada dos passos",),
        player_prompt="O que você faz diante da porta fechada?",
    )

    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=SceneState(location="Galpão abandonado"),
            player_input="Observo a porta.",
        )

    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]


def test_word_falha_does_not_count_as_player_speech() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você observa uma falha estreita no concreto junto da porta. O rádio "
            "chia sobre a bancada, poeira cai do teto e passos lentos atravessam o "
            "mezanino enquanto uma corrente balança sem vento no galpão."
        ),
        scene_summary="Uma falha no concreto acompanha sinais de atividade recente.",
        new_facts=[
            {
                "kind": "observation",
                "summary": "Há uma falha estreita no concreto junto da porta.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar os passos no mezanino",),
        player_prompt="O que você faz após observar a falha?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Observo a parede junto da porta.",
    )

    assert accepted is proposal


@pytest.mark.parametrize(
    ("updates", "expected_field"),
    (
        ({"open_threads": ("Footsteps nearby",)}, "open_threads[0]"),
        (
            {
                "new_facts": [
                    {
                        "kind": "complication",
                        "summary": "Danger nearby in warehouse",
                        "visibility": Visibility.PLAYER,
                        "pending": True,
                    }
                ]
            },
            "new_facts[0].summary",
        ),
    ),
)
def test_short_clearly_english_fragments_are_rejected(
    updates: dict, expected_field: str
) -> None:
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(**updates),
            facts=(_resolution(True),),
            current_scene=None,
        )

    assert caught.value.code == "scene_output_not_portuguese"
    assert caught.value.evidence["field"] == expected_field


def test_investigation_intent_authorizes_equivalent_investigation_paraphrase() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você examina o galpão sob a luz instável. O rádio chia sobre a "
            "bancada, poeira cai do teto e passos lentos atravessam o mezanino "
            "enquanto uma corrente balança sem vento entre as caixas empilhadas."
        ),
        scene_summary="A investigação encontra sinais recentes no galpão.",
        new_facts=[
            {
                "kind": "observation",
                "summary": "Sinais recentes aparecem entre as caixas empilhadas.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar os passos no mezanino",),
        player_prompt="O que você faz após examinar o galpão?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Investigo o galpão.",
    )

    assert accepted is proposal


@pytest.mark.parametrize(
    "player_prompt",
    (
        "O que fará Mara enquanto você espera?",
        "Como reage Mara enquanto você observa?",
        "Qual caminho Mara escolhe enquanto você espera?",
    ),
)
def test_player_subordinate_does_not_change_the_prompts_main_npc_subject(
    player_prompt: str,
) -> None:
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(player_prompt=player_prompt),
            facts=(_resolution(True),),
            current_scene=None,
        )

    assert caught.value.code == "scene_player_prompt_not_actionable"
    assert caught.value.evidence["reason"] == "addresses_non_player_actor"
    assert player_prompt not in str(caught.value.evidence)


def test_negated_failure_action_is_not_mistaken_for_granted_goal() -> None:
    proposal = _proposal(
        outcome="failure",
        narrative=(
            "Você falha em localizar o registro e nada conclusivo surge entre as "
            "caixas. Faróis atravessam as janelas, um motor para diante do galpão "
            "e passos apressados aumentam a pressão junto da entrada lateral."
        ),
        scene_summary="A busca falha enquanto visitantes se aproximam do galpão.",
        new_facts=[
            {
                "kind": "complication",
                "summary": "Um veículo para diante do galpão.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Lidar com a chegada dos visitantes",),
        player_prompt="O que você faz antes que os visitantes entrem?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(_resolution(False),),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Procuro o registro entre as caixas.",
    )

    assert accepted is proposal


@pytest.mark.parametrize(
    ("updates", "expected_field"),
    (
        ({"open_threads": ("New clue found",)}, "open_threads[0]"),
        ({"open_threads": ("Radio crackles nearby",)}, "open_threads[0]"),
        ({"scene_summary": "A shadow appears"}, "scene_summary"),
        ({"open_threads": ("Mara enters warehouse",)}, "open_threads[0]"),
    ),
)
def test_general_short_english_narrative_fragments_are_rejected(
    updates: dict, expected_field: str
) -> None:
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(**updates),
            facts=(_resolution(True),),
            current_scene=None,
        )

    assert caught.value.code == "scene_output_not_portuguese"
    assert caught.value.evidence["field"] == expected_field


@pytest.mark.parametrize(
    "short_portuguese",
    (
        "Nova pista encontrada",
        "Rádio chia perto",
        "Uma sombra aparece",
        "Mara entra no galpão",
        "Porta lateral",
        "Motor ligado",
        "Chuva forte",
        "Sangue seco",
    ),
)
def test_short_portuguese_fragments_remain_valid(short_portuguese: str) -> None:
    proposal = _proposal(open_threads=(short_portuguese,))

    accepted = validate_scene_continuation(
        proposal,
        facts=(_resolution(True),),
        current_scene=None,
    )

    assert accepted is proposal


def test_declared_action_does_not_authorize_a_different_explicit_target() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você abre o cofre sob a luz instável. O rádio chia sobre a bancada, "
            "poeira cai do teto e passos lentos atravessam o mezanino enquanto uma "
            "corrente balança sem vento entre as caixas empilhadas do galpão."
        ),
        scene_summary="O cofre aberto fica exposto no galpão escuro.",
        new_facts=[
            {
                "kind": "observation",
                "summary": "O cofre aberto fica exposto sob a bancada.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar os passos no mezanino",),
        player_prompt="O que você faz diante do cofre?",
    )

    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=SceneState(location="Galpão abandonado"),
            player_input="Abro a porta lateral.",
        )

    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]
    assert "target" not in caught.value.evidence


@pytest.mark.parametrize(
    ("player_input", "proposed_target"),
    (
        ("Abro a porta lateral.", "janela lateral"),
        ("Abro o armário antigo.", "cofre antigo"),
        ("Abro a velha porta.", "velha janela"),
        ("Abro a porta lateral.", "porta principal"),
        ("Abro a porta lateral.", "cofre atrás da porta lateral"),
    ),
)
def test_shared_modifier_does_not_authorize_a_different_action_target(
    player_input: str,
    proposed_target: str,
) -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            f"Você abre {proposed_target} sob a luz instável. O rádio chia sobre "
            "a bancada, poeira cai do teto e passos lentos atravessam o mezanino "
            "enquanto uma corrente balança entre as caixas do galpão."
        ),
        scene_summary="A abertura expõe um objeto no galpão escuro.",
        new_facts=[
            {
                "kind": "observation",
                "summary": "Um objeto aberto fica exposto no galpão.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar os passos no mezanino",),
        player_prompt="O que você faz diante dos passos?",
    )

    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=SceneState(location="Galpão abandonado"),
            player_input=player_input,
        )

    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["unauthorized_concepts"] == ["interact"]
    assert "target" not in caught.value.evidence


def test_implicit_action_target_may_echo_an_explicit_declared_target() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você a abre. O rádio chia sobre a bancada, poeira cai do teto e "
            "passos lentos atravessam o mezanino enquanto uma corrente balança sem "
            "vento entre as caixas empilhadas do galpão abandonado."
        ),
        scene_summary="A abertura expõe sinais de atividade no galpão.",
        new_facts=[
            {
                "kind": "observation",
                "summary": "Sinais recentes aparecem além da porta lateral.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar os passos no mezanino",),
        player_prompt="O que você faz depois de abrir a porta?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Abro a porta lateral.",
    )

    assert accepted is proposal


def test_observing_does_not_authorize_searching_the_same_target() -> None:
    proposal = _proposal(
        outcome="unresolved",
        narrative=(
            "Você revista Mara sob a luz instável. O rádio chia sobre a bancada, "
            "poeira cai do teto e passos lentos atravessam o mezanino enquanto uma "
            "corrente balança sem vento entre as caixas empilhadas."
        ),
        scene_summary="Mara permanece junto da bancada no galpão.",
        new_facts=[
            {
                "kind": "npc_action",
                "summary": "Mara permanece imóvel junto da bancada.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        npcs_present=("Mara",),
        open_threads=("Entender a presença de Mara",),
        player_prompt="O que você faz diante de Mara?",
    )

    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            proposal,
            facts=(),
            current_scene=SceneState(
                location="Galpão abandonado",
                npcs_present=("Mara",),
            ),
            player_input="Observo Mara.",
            player_aliases=("Neófito",),
            npc_aliases=("Mara",),
        )

    assert caught.value.code == "scene_player_agency_violation"
    assert caught.value.evidence["unauthorized_concepts"] == ["inspect"]


@pytest.mark.parametrize(
    "player_prompt",
    (
        "O que fará Mara se você esperar?",
        "Como reage Mara caso você observe?",
        "O que fará Mara assim que você entrar?",
        "O que Mara fará assim que você entrar?",
        "O que a guarda fará quando você esperar?",
        "Como reage a guarda quando você observa?",
        "O que a chefe da guarda fará assim que você entrar?",
    ),
)
def test_conditional_player_clause_does_not_replace_the_main_npc_subject(
    player_prompt: str,
) -> None:
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(player_prompt=player_prompt),
            facts=(_resolution(True),),
            current_scene=None,
        )

    assert caught.value.code == "scene_player_prompt_not_actionable"
    assert caught.value.evidence["reason"] == "addresses_non_player_actor"


def test_failure_pending_threads_are_not_treated_as_granted_goals() -> None:
    proposal = _proposal(
        outcome="failure",
        narrative=(
            "A busca falha entre as caixas e nada conclusivo surge. Faróis "
            "atravessam as janelas, um motor para diante do galpão e passos "
            "apressados aumentam a pressão junto da entrada lateral."
        ),
        scene_summary="A busca falha enquanto visitantes chegam ao galpão.",
        new_facts=[
            {
                "kind": "complication",
                "summary": "Um veículo para diante do galpão.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar quem chegou",),
        player_prompt="O que você faz para descobrir quem chegou?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(_resolution(False),),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Investigo as caixas.",
    )

    assert accepted is proposal


def test_passive_negation_does_not_grant_a_failed_goal() -> None:
    proposal = _proposal(
        outcome="failure",
        narrative=(
            "Nada foi encontrado entre as caixas, e a busca permanece incompleta. "
            "Faróis atravessam as janelas, um motor para diante do galpão e passos "
            "apressados aumentam a pressão junto da entrada lateral."
        ),
        scene_summary="A busca permanece incompleta enquanto visitantes se aproximam.",
        new_facts=[
            {
                "kind": "complication",
                "summary": "Um veículo para diante do galpão.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar quem chegou",),
        player_prompt="O que você faz diante da chegada dos visitantes?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(_resolution(False),),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Procuro algo entre as caixas.",
    )

    assert accepted is proposal


def test_impersonal_negation_does_not_grant_a_failed_goal() -> None:
    proposal = _proposal(
        outcome="failure",
        narrative=(
            "Não se encontrou o registro entre as caixas, e a busca permanece "
            "incompleta. Faróis atravessam as janelas, um motor para diante do "
            "galpão e passos apressados aumentam a pressão junto da entrada."
        ),
        scene_summary="A busca permanece incompleta enquanto visitantes se aproximam.",
        new_facts=[
            {
                "kind": "complication",
                "summary": "Um veículo para diante do galpão.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar quem chegou",),
        player_prompt="O que você faz diante da chegada dos visitantes?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(_resolution(False),),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Procuro o registro entre as caixas.",
    )

    assert accepted is proposal


def test_nested_impersonal_negation_does_not_grant_a_failed_goal() -> None:
    proposal = _proposal(
        outcome="failure",
        narrative=(
            "Não se conseguiu encontrar o registro entre as caixas, e a busca "
            "permanece incompleta. Faróis atravessam as janelas, um motor para "
            "diante do galpão e passos apressados aumentam a pressão na entrada."
        ),
        scene_summary="A busca permanece incompleta enquanto visitantes se aproximam.",
        new_facts=[
            {
                "kind": "complication",
                "summary": "Um veículo para diante do galpão.",
                "visibility": Visibility.PLAYER,
                "pending": True,
            }
        ],
        open_threads=("Identificar quem chegou",),
        player_prompt="O que você faz diante da chegada dos visitantes?",
    )

    accepted = validate_scene_continuation(
        proposal,
        facts=(_resolution(False),),
        current_scene=SceneState(location="Galpão abandonado"),
        player_input="Procuro o registro entre as caixas.",
    )

    assert accepted is proposal


@pytest.mark.parametrize(
    "english_fragment",
    (
        "Silent corridor",
        "Unknown signal",
        "Night falls",
        "Mara watches",
    ),
)
def test_unproven_non_name_short_fragments_fail_closed(
    english_fragment: str,
) -> None:
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(open_threads=(english_fragment,)),
            facts=(_resolution(True),),
            current_scene=None,
        )

    assert caught.value.code == "scene_output_not_portuguese"
    assert caught.value.evidence["field"] == "open_threads[0]"


@pytest.mark.parametrize(
    ("field", "name"),
    (
        ("location", "Bar Last Call"),
        ("npcs_present", "Mara"),
        ("npcs_present", "Will Stone"),
        ("npcs_present", "Jean-Luc Picard"),
    ),
)
def test_name_like_values_are_allowed_only_in_name_fields(
    field: str,
    name: str,
) -> None:
    updates = {field: (name,) if field == "npcs_present" else name}
    proposal = _proposal(**updates)

    accepted = validate_scene_continuation(
        proposal,
        facts=(_resolution(True),),
        current_scene=None,
    )

    assert accepted is proposal


@pytest.mark.parametrize(
    "foreign_location",
    ("Abandoned Warehouse", "Silent Corridor", "The Dark Alley"),
)
def test_title_case_does_not_hide_a_foreign_generated_location(
    foreign_location: str,
) -> None:
    with pytest.raises(SceneProposalError) as caught:
        validate_scene_continuation(
            _proposal(location=foreign_location),
            facts=(_resolution(True),),
            current_scene=None,
        )

    assert caught.value.code == "scene_output_not_portuguese"
    assert caught.value.evidence["field"] == "location"


def test_existing_named_location_is_preserved_without_translation() -> None:
    proposal = _proposal(location="The Dark Alley")

    accepted = validate_scene_continuation(
        proposal,
        facts=(_resolution(True),),
        current_scene=SceneState(location="The Dark Alley"),
    )

    assert accepted is proposal
