"""Frozen offline diagnostic for DEC-NARR-VALID-001; no proposed runtime/schema.

Run with the repository venv, --root WORKTREE --output NEW_JSON.
Uses the current full proposal validator on authored contrasts. Verdicts are
observations, not assertions that known false acceptances should be preserved.
No provider, database, credential, environment inspection, or network access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sys

os.environ['STORYTELLER_DISABLE_DOTENV'] = '1'
sys.dont_write_bytecode = True


def deny_network(*args, **kwargs):
    raise RuntimeError('offline_probe_network_forbidden')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite prior observation')
    root = args.root.resolve()
    socket.create_connection = deny_network
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    socket.socket.sendto = deny_network
    sys.path[:0] = [str(root), str(root / 'tests')]
    from test_campaign_source_capsule import capsule as initial_capsule
    from api.campaign_source_capsule import create_campaign_source_capsule
    from api.campaign_progression_service import (
        CampaignProgressState, build_campaign_narrator_packet,
        resolve_campaign_progression,
    )
    from api.campaign_source_profile import validate_campaign_source_proposal
    from api.narrative_source_preparation import DeclaredActionPreparation
    from api.campaign_source_offline_corpus import PROSE

    # Every semantic label below is authored prospectively, not inferred from
    # the validator result. Paired variants preserve exact effect IDs.
    specs = [
        ('task', 'Qual é a tarefa?', 'threatened', 'R-01'),
        ('refusal', 'Quem é a fundadora?', 'threatened', 'R-02'),
        ('warning', 'Aguardo', 'threatened', 'R-03'),
        ('preserved', 'Retiro o registro', 'threatened', 'R-05'),
        ('partial', 'Retiro o registro', 'wet', 'R-06'),
        ('abandoned', 'Desisto', 'threatened', 'R-09'),
    ]
    variants = {
        'task': [
            ('goal_synonym', False, PROSE['R-01'] + ' Mara diz: “Sua missão é investigar o conteúdo, não preservar o registro.”'),
            ('optional_inspection', True, PROSE['R-01'] + ' Mara diz: “Examinar é uma opção; o objetivo continua sendo preservar o registro.”'),
            ('npc_extra_lore', False, PROSE['R-01'] + ' Mara diz: “A fundadora me fez jurar que jamais revelaria seu nome.”'),
        ],
        'refusal': [
            ('direct_natural', True, 'Mara responde: “Essa identidade eu não revelo.” O registro continua na bancada baixa, ameaçado pela infiltração. Mara mantém a resposta dirigida à pergunta, sem tocar nas folhas.'),
            ('authored_direct', True, 'Mara responde: “Não vou divulgar essa identidade.” O registro continua na bancada baixa, ameaçado pela infiltração. Mara mantém a resposta dirigida à pergunta, sem tocar nas folhas.'),
            ('invented_oath', False, PROSE['R-02'] + ' Mara diz: “Fiz um juramento de silêncio à fundadora.”'),
        ],
        'warning': [
            ('valid_environment', True, 'Mara avisa: “A infiltração ameaça o registro.” O papel continua seco e intacto na bancada baixa. As gotas avançam pela madeira, próximas das folhas; o risco agora é evidente.'),
            ('wrong_actor', False, PROSE['R-03'] + ' Você abre a porta.'),
            ('denied_warning', False, 'A água da infiltração se aproxima do registro, ainda seco e intacto. Mara avisa apenas sobre o frio: “Não há risco para o documento.” Nenhum alerta sobre a água é dado.'),
        ],
        'preserved': [
            ('reopen_synonym', False, PROSE['R-05'] + ' Mara diz: “Agora leve o documento para a outra mesa.”'),
            ('reopen_care', False, PROSE['R-05'] + ' Mara diz: “Falta embrulhar as folhas antes de terminarmos.”'),
            ('completed_acknowledgment', True, PROSE['R-05'] + ' Mara diz: “O registro está salvo.”'),
        ],
        'partial': [
            ('dry_synonym', False, PROSE['R-06'] + ' Mara diz: “As folhas já secaram por completo.”'),
            ('wet_acknowledgment', True, PROSE['R-06'] + ' Mara diz: “As folhas continuam molhadas.”'),
            ('negated_dry', True, PROSE['R-06'] + ' Mara diz: “As folhas não secaram por completo.”'),
            ('restoration_synonym', False, PROSE['R-06'] + ' Mara diz: “Todas as linhas voltaram a ficar legíveis.”'),
        ],
        'abandoned': [
            ('invented_emotion', False, PROSE['R-09'] + ' Você sente vergonha da própria decisão.'),
            ('natural_acknowledgment', True, PROSE['R-09'] + ' Mara diz: “Entendido.”'),
        ],
    }
    observations = []
    structural = []
    packets = []
    for name, action, before, rule in specs:
        base = initial_capsule()
        state = CampaignProgressState(revision=0, record=before)
        snapshot = base.snapshot.model_copy(update={'progression': state})
        request = base.campaign_request.model_copy(update={'player_input': action, 'state': state})
        effect = resolve_campaign_progression(request)
        assert effect.rule_id == rule
        retained = create_campaign_source_capsule(
            snapshot=snapshot, operation_id=base.operation_id, created_at=base.created_at,
            player_input=action, action_preparation=DeclaredActionPreparation(),
            campaign_request=request, campaign_effect=effect,
            state={'campaign_progression': state.model_dump(mode='json')},
            relationships={}, config=base.config,
        )
        packet = build_campaign_narrator_packet(request, effect)
        packets.append({'context': name, 'packet': packet.model_dump(mode='json')})

        def check(text, effects=None, q=None):
            try:
                validate_campaign_source_proposal(
                    {'n': text, 'q': ('' if packet.state_after.outcome else 'O que você faz agora?') if q is None else q,
                     'realized_effects': packet.required_effects if effects is None else effects},
                    packet=packet, facts=retained.draft.facts, snapshot=retained.snapshot,
                )
                return True, None
            except ValueError as exc:
                return False, getattr(exc, 'code', type(exc).__name__)

        for label, expected, text in [('baseline', True, PROSE[rule]), *variants[name]]:
            accepted, error = check(text)
            observations.append({'id': f'{name}.{label}', 'rule': rule, 'authored_valid': expected,
                                 'accepted': accepted, 'error': error, 'narrative': text,
                                 'effect_ids': list(packet.required_effects)})
        accepted, error = check(PROSE[rule], effects=('forged.effect',))
        structural.append({'id': f'{name}.forged_effect', 'accepted': accepted, 'error': error})
        if packet.state_after.outcome:
            accepted, error = check(PROSE[rule], q='O que você faz agora?')
            structural.append({'id': f'{name}.terminal_question', 'accepted': accepted, 'error': error})

    # Documentary span proofs: offsets and declared actors can be identical
    # in shape for both true and false sentences. No semantic validator added.
    span_pairs = []
    for text, valid in [('As folhas continuam molhadas.', True), ('As folhas já secaram por completo.', False)]:
        start, end = 0, len(text)
        span_pairs.append({'text': text, 'actor': 'record_pages', 'effect': 'campaign.record.partial',
                           'start': start, 'end': end, 'exact_span_valid': text[start:end] == text,
                           'authored_semantic_valid': valid})

    # Read only the synthetic records in the requested historical lot interval.
    inventory = []
    for lot in range(41, 83):
        for directory in sorted((root / 'eval-results').glob(f'hybrid-campaign-luna-l{lot}-*')):
            path = directory / 'records.jsonl'
            if not path.is_file():
                continue
            rows = [json.loads(line)['record'] for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
            calls = [row for row in rows if row.get('call_made')]
            inventory.append({'lot': lot, 'path': path.relative_to(root).as_posix(),
                              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                              'calls': len(calls), 'completed': sum(row.get('status') == 'completed' for row in calls),
                              'rules': sorted({row['rule'] for row in calls if row.get('rule')})})
    gate_path = root / 'evals/narrator/reports/hybrid-campaign-luna-l83-live-gate-2026-10-20.json'
    gate = json.loads(gate_path.read_text(encoding='utf-8'))
    frozen = {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in gate['implementation_sha256']}
    result = {
        'study': 'DEC-NARR-VALID-001-A', 'date': '2026-10-21',
        'scope': 'authored contrasts; current full validator; no production modifications',
        'provider_calls': 0, 'inference_cost_usd': '0',
        'observations': observations, 'structural_controls': structural,
        'span_pairs': span_pairs, 'packets': packets, 'historical_inventory': inventory,
        'l83_closed': not gate['paid_ceiling_authorized'] and not gate['live_inference_authorized'],
        'l83_frozen_hashes_match': frozen == gate['implementation_sha256'],
        'frozen_hashes': frozen,
        'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    assert all(not row['accepted'] for row in structural)
    assert all(row['accepted'] for row in observations if row['id'].endswith('.baseline'))
    assert result['l83_closed'] and result['l83_frozen_hashes_match']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({
        'observations': len(observations),
        'mismatches': [{k: row[k] for k in ('id', 'authored_valid', 'accepted', 'error')}
                       for row in observations if row['authored_valid'] != row['accepted']],
        'structural_controls': len(structural), 'historical_lots': len(inventory),
        'historical_calls': sum(row['calls'] for row in inventory),
        'historical_completed': sum(row['completed'] for row in inventory),
        'l83_hashes_match': result['l83_frozen_hashes_match'], 'output': str(args.output),
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
