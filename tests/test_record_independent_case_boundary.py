"""The additive origin discriminator never substitutes for full source authority."""
from dataclasses import replace
import builtins
import hashlib
import json
from types import SimpleNamespace

import pytest

from scripts import narrator_record_derivation as derivation
from scripts import narrator_record_evidence as evidence
from scripts import narrator_record_quote_evidence as quotes
from scripts import narrator_record_independent_cases as independent


def _sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def _records(case):
    return derivation.RecordDerivationProposal.model_validate({
        "o": "unresolved", "l": "Lugar observado", "s": case.narrative,
        "p": [], "f": [{"k": "observation", "s": case.narrative,
                       "v": "public", "i": 0.5, "p": True, "a": []}],
        "t": [], "r": [], "q": "O que você faz agora?",
    })


@pytest.mark.parametrize("index", [0, 1])
def test_independent_case_passes_the_real_packet_and_composition_boundary(index):
    case = independent.load_independent_cases()[index]
    wire, audit = quotes.build_evidence_packet(case)
    assert audit["source"] == case.source
    assert audit["narrative_reconstructed_exactly"] is True
    assert case.narrative in wire
    proposal = derivation.compose_derivation(case, _records(case))
    assert proposal.narrative == case.narrative


@pytest.mark.parametrize("index", [0, 1])
def test_legacy_case_never_imports_or_delegates_to_independent_loader(index, monkeypatch):
    case = derivation.load_fixed_cases()[index]
    original_import = builtins.__import__
    def guarded_import(name, *args, **kwargs):
        if name == "scripts.narrator_record_independent_cases":
            raise AssertionError("A legacy case must not load the independent corpus")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded_import)
    derivation._verify_case(case)
    assert derivation.build_derivation_packet(case)[1]["source"] == case.source


@pytest.mark.parametrize("value", [None, {}, object(),
    SimpleNamespace(source={"case_binding": "record-independent-cases-v1"})])
def test_wrong_case_type_is_rejected_with_safe_contract_error(value):
    with pytest.raises(derivation.DerivationContractError,
                       match="^record_derivation_fixed_case_mismatch$"):
        derivation._verify_case(value)


@pytest.mark.parametrize("source", [None, [], "record-independent-cases-v1", 1])
def test_non_mapping_source_cannot_select_new_binding(source):
    case = replace(derivation.load_fixed_cases()[0], source=source)
    with pytest.raises(derivation.DerivationContractError):
        derivation._verify_case(case)


@pytest.mark.parametrize("index", [0, 1])
def test_pasting_new_binding_on_legacy_case_does_not_authorize_it(index):
    case = derivation.load_fixed_cases()[index]
    altered = replace(case, source=dict(case.source, case_binding=independent.VERSION))
    with pytest.raises(derivation.DerivationContractError):
        derivation._verify_case(altered)


@pytest.mark.parametrize("binding", [None, "record-derivation-v1",
    "record-independent-cases-v1 ", "RECORD-INDEPENDENT-CASES-V1"])
def test_new_case_requires_exact_discriminator(binding):
    case = independent.load_independent_cases()[0]
    source = dict(case.source)
    if binding is None:
        source.pop("case_binding")
    else:
        source["case_binding"] = binding
    with pytest.raises(derivation.DerivationContractError,
                       match="^record_derivation_fixed_case_mismatch$"):
        derivation._verify_case(replace(case, source=source))


@pytest.mark.parametrize("field,value", [
    ("case_id", "opening"), ("episode_id", "opening"), ("turn_id", "establish-scene"),
    ("narrative", "Texto adulterado."), ("player_input", "Abro a porta."),
    ("known_context", "Contexto adulterado."), ("outcome", "success"),
])
def test_correct_discriminator_does_not_authorize_altered_case(field, value):
    case = independent.load_independent_cases()[0]
    with pytest.raises(derivation.DerivationContractError):
        derivation._verify_case(replace(case, **{field: value}))


@pytest.mark.parametrize("kind", ["tag_only", "other_independent_case", "legacy", "mixed", "rehash"])
def test_source_alias_partial_binding_and_rehashed_forgery_are_rejected(kind):
    case, other = independent.load_independent_cases()
    source = dict(case.source)
    narrative = case.narrative
    if kind == "tag_only":
        source = {"case_binding": independent.VERSION}
    elif kind == "other_independent_case":
        source = dict(other.source)
    elif kind == "legacy":
        source = dict(derivation.load_fixed_cases()[0].source, case_binding=independent.VERSION)
    elif kind == "mixed":
        source.update(derivation.load_fixed_cases()[0].source)
    else:
        narrative += " Informação inventada."
        source["narrative_sha256"] = hashlib.sha256(narrative.encode()).hexdigest()
    with pytest.raises(derivation.DerivationContractError):
        derivation._verify_case(replace(case, narrative=narrative, source=source))


@pytest.mark.parametrize("entry", ["verify", "packet", "compose"])
def test_independent_source_is_reloaded_at_each_boundary(entry, tmp_path, monkeypatch):
    case = independent.load_independent_cases()[0]
    path = tmp_path / "changed.json"
    path.write_bytes(independent.CORPUS_PATH.read_bytes() + b" ")
    monkeypatch.setattr(independent, "CORPUS_PATH", path)
    call = {"verify": lambda: derivation._verify_case(case),
            "packet": lambda: derivation.build_derivation_packet(case),
            "compose": lambda: derivation.compose_derivation(case, _records(case))}[entry]
    with pytest.raises(derivation.DerivationContractError):
        call()
    # A drifted independent corpus cannot disable the original bb98 source.
    derivation._verify_case(derivation.load_fixed_cases()[0])


@pytest.mark.parametrize("kind", ["narrative", "input", "source"])
def test_legacy_tampering_keeps_its_original_error(kind):
    case = derivation.load_fixed_cases()[0]
    if kind == "narrative":
        altered = replace(case, narrative=case.narrative + " changed")
    elif kind == "input":
        altered = replace(case, player_input="Changed input")
    else:
        altered = replace(case, source=dict(case.source, line_number=9))
    with pytest.raises(derivation.DerivationContractError,
                       match="^record_derivation_fixed_case_mismatch$"):
        derivation._verify_case(altered)


# SHA-256s captured before the only change to _verify_case. Wire and complete
# audit are frozen separately, so provenance drift cannot hide behind a packet.
LEGACY_PACKETS = {
    "opening": {
        "derivation": ("25f5228aa3ee026091343e71440e527d833c70dc35cb1fc8f1ccb27de22528f1", "71997a7b69eea50acbc81bf32d75f0b2428179a32cab4d60500e4cd9e004ff52"),
        "evidence": ("42eb962a2042c00b2030d5cb63b1f7e1f17894158e5df61cdcad0d317c32a480", "6e8dbc8faab75865278af1fc5308eff1d0155d0e973ca748722af8ae60e2ed44"),
    },
    "mara": {
        "derivation": ("07325a852bb4f26198de1fbe56f945be66e1c151bf789eb0b21add2a1f9daa5d", "bc396a7acf54a8a9094a303c597c9b195d24de2d67bf699ee01dec9d2b3a7fcc"),
        "evidence": ("71dd4eb95d17a2b5feb17313cc39dec5e5e4b14677c969b2a1f09d774d3ab8eb", "44b4cf6a3710458fbfd507727c4b816bdc9ee760413dad4cced7500292003036"),
    },
}


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("kind", ["derivation", "evidence", "quotes"])
def test_bb98_packet_and_entire_audit_keep_pre_extension_hashes(index, kind):
    case = derivation.load_fixed_cases()[index]
    builder = {"derivation": derivation.build_derivation_packet,
               "evidence": evidence.build_evidence_packet,
               "quotes": quotes.build_evidence_packet}[kind]
    wire, audit = builder(case)
    expected = LEGACY_PACKETS[case.case_id]["evidence" if kind == "quotes" else kind]
    assert (hashlib.sha256(wire.encode()).hexdigest(), _sha(audit)) == expected


@pytest.mark.parametrize("model,expected", [
    (derivation.RecordDerivationProposal, "95992ae87e66bb65fb674872e4bd4065728213a25cb5af6d1859d664c066b593"),
    (evidence.RecordEvidenceProposal, "6fce65144390b13486df445af49733c7397a682245f8aa84a993cf3a3ae81cb0"),
    (quotes.RecordQuoteEvidenceProposal, "47e610110dc0f4f5773de5d7f56cf853685ac82b9de4045e2a3496bc182a13c7"),
])
def test_response_schemas_keep_pre_extension_hashes(model, expected):
    assert _sha(model.model_json_schema(by_alias=True)) == expected


@pytest.mark.parametrize("kind,expected", [
    ("low", "0ef02b6c4987318c829e7193e6cdbba67dcc58d6937e966fdcf3809c64cbd209"),
    ("medium", "5037c4c4e040c6ce800d848217951374ef19489c18bd4857aaf5ca652e13cdaf"),
])
def test_old_request_bodies_remain_exactly_frozen(kind, expected):
    from scripts import evaluate_narrator_record_claim_check as low
    from scripts import evaluate_narrator_record_medium as medium
    executor = low if kind == "low" else medium
    prepared = executor.prepare_experiment()
    assert _sha(executor._fixed_payload(executor._make_request(prepared))) == expected
