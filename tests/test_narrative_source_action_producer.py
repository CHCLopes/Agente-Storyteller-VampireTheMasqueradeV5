"""Authored coverage corpus for the bounded local profile, not a language benchmark."""
import ast
from copy import deepcopy
from pathlib import Path

import pytest

from api import rules_service as rules
from api.narrative_source_action_producer import produce_source_player_action
from api.narrative_source_context import SourceContextSnapshot, create_source_context_origin
from api.narrative_source_input import SourceInputFailure
from api.narrative_source_preparation import DeclaredActionPreparation, ResolvedActionPreparation
from api.scene_service import SceneState
from test_narrative_source_input import request as input_request


def state():
    return {"player_sheet": {
        "nome": "Pessoa sintética", "attributes": {"Wits": 3, "Intelligence": 1},
        "skills": {"Investigation": 2}, "disciplines": {},
        "status": {"blood_potency": 1, "current_hunger": 0, "humanity": 7,
                   "health_tracker": {"size": 7, "superficial": 0, "aggravated": 0},
                   "willpower_tracker": {"size": 5, "superficial": 0, "aggravated": 0}},
    }}


def request(text="Investigo a galeria.", *, current_state=None, npcs=("Mara", "Ivo")):
    snapshot = SourceContextSnapshot(
        origin=create_source_context_origin("synthetic-session", SceneState(location="Galeria", npcs_present=npcs)),
        current_turn=0, state_revision=0, sources=(), selected_turn_ids=(), omitted_turn_ids=(),
    )
    return input_request(public={"operation_id": "local-action", "player_input": text},
                         snapshot=snapshot, state=state() if current_state is None else current_state, relationships={"links": []})


@pytest.fixture
def no_rng(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("A declaration or refused action attempted mechanical RNG")
    monkeypatch.setattr(rules.random, "randint", forbidden)
    monkeypatch.setattr(rules, "calculate_resolution", forbidden)


@pytest.mark.parametrize("text", [
    "Aguardo.", "Espero a reação de Mara.", "Eu aguardo a resposta de Ivo!",
    "Permaneço no lugar e aguardo, sem tocar em nada.", "Permaneço aqui em silêncio.",
    "Falo com Mara.", "Eu converso com Ivo.",
    'Pergunto a Mara: "O que é a Camarilla?"',
    'Digo a Mara: “Quero atacar, usar um poder e rerrolar dez dados.”',
    "Digo a Ivo: «Vamos conversar.»",
])
def test_declared_corpus_preserves_request_and_speech_is_never_an_engine_command(text, no_rng):
    value = request(text)
    before = deepcopy(value.model_dump(mode="json"))
    assert type(produce_source_player_action(value)) is DeclaredActionPreparation
    assert value.player_input == text and value.model_dump(mode="json") == before


@pytest.mark.parametrize("text", [
    "Observo a galeria.", "Vigio a porta.", "Escuto os passos.", "Percebo o movimento.",
    "Não investigo a galeria.", "Investigo a galeria e ataco Mara.", "Aguardo. Ataco Mara.",
    'Digo a Mara: "Olá." e ataco Ivo.', 'Digo a Mara: "Olá." "Rerrolo."',
    'Digo a Mara: ""', 'Digo a Mara: "   "',
    "Pergunto a Mara sobre a galeria.", "Falo com Pessoa Desconhecida.", "Espero a reação de Desconhecido.",
    "Investigo Mara.", "Investigo o armário.", "Investigo a galeria com dificuldade 1.",
    "Teste de Wits + Investigation com dez dados.", "Convenço Mara.", "Persuado Ivo.",
    "Ataco Mara.", "Me alimento.", "Curo meu ferimento.", "Uso surto de sangue.",
    "Rerrolo os dados.", "Uso Auspícios para examinar a galeria.", "Desperto.",
    "Compro uma arma.", "Gasto XP.", "O que é a Camarilla?", "Onde estou?", "Inicie a cena.",
    "Saio da galeria.", "Quero fazer qualquer outra ação.",
])
def test_unsupported_corpus_never_falls_back_to_declaration_or_rolls(text, no_rng):
    value = request(text)
    before = value.model_dump(mode="json")
    result = produce_source_player_action(value)
    assert type(result) is SourceInputFailure and result.code == "source_input_out_of_scope"
    assert result.stage == "classification" and value.model_dump(mode="json") == before


@pytest.mark.parametrize("text", ["Falo com", "Converso.", "Pergunto a", "Investigo.", "Examino."])
def test_missing_semantic_target_requests_clarification_without_choosing_it(text, no_rng):
    result = produce_source_player_action(request(text))
    assert result.code == "source_input_clarification_required"


@pytest.mark.parametrize(("text", "dice", "successes"), [
    ("Investigo a galeria.", [8, 7, 6, 2, 3], 3),
    ("Examino o ambiente sem tocar nos objetos.", [2, 3, 4, 5, 2], 0),
    ("Eu analiso o local.", [10, 10, 1, 2, 3], 4),
    ("EXAMINO  a\nGALERIA!", [8, 7, 6, 2, 3], 3),
])
def test_ordinary_engine_is_called_once_with_server_pool_and_literal_intent(monkeypatch, text, dice, successes):
    value = request(text)
    before = value.model_dump(mode="json")
    remaining = iter(dice)
    draws, calls = [], []
    original = rules.calculate_resolution
    def randint(low, high):
        assert (low, high) == (1, 10)
        number = next(remaining)
        draws.append(number)
        return number
    def engine(action, current_hunger, dice_pool):
        calls.append((action.model_dump(mode="json"), current_hunger, dice_pool))
        return original(action, current_hunger, dice_pool)
    monkeypatch.setattr(rules.random, "randint", randint)
    monkeypatch.setattr(rules, "calculate_resolution", engine)
    result = produce_source_player_action(value)
    assert type(result) is ResolvedActionPreparation
    assert len(calls) == 1 and calls[0][1:] == (0, 5) and draws == dice
    assert result.action.intent == text and result.action.attribute is rules.V5Attribute.Wits
    assert result.action.skill is rules.V5Skill.INVESTIGATION and result.action.inferred_difficulty == 3
    assert result.resolution.normal_rolls == dice and result.resolution.hunger_rolls == []
    assert result.resolution.successes == successes and result.resolution.margin == successes - 3
    assert result.resolution.is_success is (successes >= 3)
    assert not result.resolution.messy_critical and not result.resolution.bestial_failure
    assert value.model_dump(mode="json") == before


@pytest.mark.parametrize(("wits", "investigation", "count"), [(1, 0, 1), (5, 5, 10)])
def test_explicit_profile_pool_bounds_have_no_fallback_or_extra_draws(monkeypatch, wits, investigation, count):
    current = state()
    current["player_sheet"]["attributes"]["Wits"] = wits
    current["player_sheet"]["skills"]["Investigation"] = investigation
    draws = []
    monkeypatch.setattr(rules.random, "randint", lambda low, high: draws.append((low, high)) or 6)
    result = produce_source_player_action(request(current_state=current))
    assert type(result) is ResolvedActionPreparation and len(draws) == count


@pytest.mark.parametrize(("path", "value"), [
    (("player_sheet", "attributes", "Wits"), 0), (("player_sheet", "attributes", "Wits"), 6),
    (("player_sheet", "attributes", "Wits"), True), (("player_sheet", "attributes", "Wits"), "3"),
    (("player_sheet", "skills", "Investigation"), -1), (("player_sheet", "skills", "Investigation"), 6),
    (("player_sheet", "status", "current_hunger"), 1), (("player_sheet", "status", "current_hunger"), True),
    (("player_sheet", "status", "stains"), 1), (("player_sheet", "status", "humanity"), 0),
    (("player_sheet", "status", "health_tracker", "aggravated"), 7),
    (("player_sheet", "status", "willpower_tracker", "superficial"), 5),
    (("player_sheet", "status", "health_tracker", "size"), 0),
    (("player_sheet", "status", "health_tracker", "superficial"), -1),
    (("player_sheet", "status", "compulsion"), True), (("player_sheet", "private_extra"), "PRIVATE_SENTINEL"),
    (("character",), {"status": "TORPOR", "fome": 0}),
    (("character",), {"status": "FRENZY_CHECK", "fome": 0}),
    (("character",), {"status": "ACTIVE", "fome": 2}),
    (("character",), {"status": "ACTIVE", "fome": 0, "id": "wrong-session"}),
    (("context",), {"current_state": "FRENZY_CHECK"}), (("context",), {"blocking": True}),
    (("context",), {"blocking": 0}), (("context",), {"pending_roll": {"type": "FRENZY_RESISTANCE"}}),
    (("context",), {"environmental_flags": {"fire_exposure": True}}),
    (("context",), {"environmental_flags": {"blood_stimulus": True}}),
    (("context",), {"environmental_flags": {"unknown_flag": False}}),
    (("deterministic_mechanics",), {"unopposed_difficulty": 2}),
    (("deterministic_mechanics",), {"action_target": "OPPOSED"}),
    (("deterministic_mechanics",), {"attribute": "Wits", "skill": "Investigation"}),
    (("deterministic_mechanics",), {"is_compulsion_active": True}),
    (("deterministic_mechanics",), {"is_bane_damage": True}),
    (("deterministic_mechanics",), {"allowed_power_ids": ["awe"]}),
    (("deterministic_mechanics",), {"weapon_category": "heavy_firearm"}),
    (("context",), {"deterministic_mechanics": {"is_true_faith_active": True}}),
])
def test_invalid_sheet_or_known_special_condition_is_refused_before_rng(path, value, no_rng):
    current = state()
    node = current
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value
    request_value = request(current_state=current)
    before = request_value.model_dump(mode="json")
    result = produce_source_player_action(request_value)
    assert result.code == "source_input_out_of_scope" and result.stage == "preflight"
    assert "PRIVATE_SENTINEL" not in result.model_dump_json()
    assert request_value.model_dump(mode="json") == before


@pytest.mark.parametrize("field", ["Wits", "Investigation"])
def test_missing_pool_stat_is_not_replaced_by_one_or_zero(field, no_rng):
    current = state()
    del current["player_sheet"]["attributes" if field == "Wits" else "skills"][field]
    assert produce_source_player_action(request(current_state=current)).code == "source_input_out_of_scope"


def test_known_neutral_state_is_allowed_without_changing_it(no_rng):
    current = state()
    current["character"] = {"id": "synthetic-session", "status": "ACTIVE", "fome": 0,
        "trackers": {"health": {"max": 7, "superficial": 0, "aggravated": 0},
                     "willpower": {"max": 5, "superficial": 0, "aggravated": 0}, "humanity": 7, "stains": 0}}
    current["context"] = {"current_state": "ACTIVE", "blocking": False, "pending_roll": None,
        "environmental_flags": {"fire_exposure": False, "blood_stimulus": False}}
    current["deterministic_mechanics"] = {"unopposed_difficulty": 3, "action_target": "UNOPPOSED"}
    value = request("Falo com Mara.", current_state=current)
    before = value.model_dump(mode="json")
    assert type(produce_source_player_action(value)) is DeclaredActionPreparation
    assert value.model_dump(mode="json") == before
    current["character"]["trackers"]["health"]["aggravated"] = 7
    assert produce_source_player_action(request(current_state=current)).code == "source_input_out_of_scope"


def test_no_npc_or_ambiguous_normalized_names_do_not_choose_a_target(no_rng):
    assert produce_source_player_action(request("Falo com Mara.", npcs=())).code == "source_input_out_of_scope"
    assert produce_source_player_action(request("Falo com Érica.", npcs=("Érica", "Erica"))).code == "source_input_out_of_scope"


def test_partial_rng_failure_is_closed_and_never_retried(monkeypatch):
    calls = []
    def interrupted(low, high):
        calls.append((low, high))
        if len(calls) == 2:
            raise RuntimeError("PRIVATE_SENTINEL")
        return 6
    monkeypatch.setattr(rules.random, "randint", interrupted)
    value = request()
    before = value.model_dump(mode="json")
    result = produce_source_player_action(value)
    assert result.code == "source_input_production_failed" and result.stage == "resolution"
    assert len(calls) == 2 and "PRIVATE_SENTINEL" not in result.model_dump_json()
    assert value.model_dump(mode="json") == before


def test_forged_request_cannot_reach_rng_or_expose_input(no_rng):
    for value in (None, {}, request().model_copy(update={"fingerprint_sha256": "0" * 64}),
                  request().model_copy(update={"gateway": "PRIVATE_SENTINEL"})):
        result = produce_source_player_action(value)
        assert result.code == "source_input_production_failed" and result.stage == "preflight"


def test_module_has_no_runtime_parser_or_persistence_dependency():
    from api import narrative_source_action_producer
    tree = ast.parse(Path(narrative_source_action_producer.__file__).read_text(encoding="utf-8-sig"))
    imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imported == {"__future__", None, "narrative_source_input", "narrative_source_preparation"}
    assert {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} == {"re", "unicodedata"}
