"""Human-authorized temporary in-memory lease, not an approval authority.

No HTTP listener, credential file, permanent environment change, retry or
automatic approval. Each queued lot still requires its own approved manifest.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
FORTALEZA = timezone(timedelta(hours=-3))


def local_credential_problem(value: str) -> str | None:
    # Reuse the adapter check, which is itself in frozen evaluation manifests.
    os.environ['STORYTELLER_DISABLE_DOTENV'] = '1'
    from scripts.evaluate_openai_luna_low_live import credential_problem
    return credential_problem(value)


def read_credential(expires: datetime, deadline: float, *, read_char=None, write=None) -> str:
    """Windows masked editor; never read clipboard or echo raw input.

    Escape/Ctrl+U clear; Backspace edits; Ctrl+C cancels. A bare Ctrl+V is
    rejected rather than becoming a control character in an HTTP header.
    """
    output = write or (lambda text: (sys.stdout.write(text), sys.stdout.flush()))
    if read_char is None:
        if os.name != 'nt':
            raise OSError('masked_windows_console_required')
        import msvcrt
        def read_char():
            while not msvcrt.kbhit():
                remaining(expires, deadline)
                time.sleep(0.05)
            return msvcrt.getwch()
    chars: list[str] = []
    tainted = False
    previous_width = 0
    output('Cole com Ctrl+Shift+V; Backspace corrige; Esc/Ctrl+U limpa; Ctrl+C cancela.\n')
    try:
        while True:
            remaining(expires, deadline)
            line = 'Chave: ' + '*' * min(len(chars), 32) + f' [{len(chars)} caracteres]'
            output('\r' + line + ' ' * max(0, previous_width - len(line)))
            previous_width = len(line)
            char = read_char()
            remaining(expires, deadline)
            if char == '\x03':
                raise KeyboardInterrupt
            if char in ('\x1b', '\x15'):
                chars.clear(); tainted = False
                continue
            if char in ('\b', '\x7f'):
                if chars:chars.pop()
                continue
            if char in ('\x00', '\xe0'):
                tainted = True
                read_char()  # Ignore a Windows extended key, never its scan code.
                continue
            if char in ('\r', '\n'):
                value = ''.join(chars)
                problem = 'invalid_characters' if tainted else local_credential_problem(value)
                if problem is None:
                    output('\nFormato local validado; autenticacao na API ainda nao verificada.\n')
                    return value
                messages = {
                    'missing': 'Entrada vazia. Cole a chave uma vez.',
                    'repeated': 'Possivel colagem repetida. Entrada descartada; cole uma unica vez.',
                    'invalid_characters': 'Entrada invalida. Sem espacos ou controles; use Ctrl+Shift+V.',
                }
                output('\n' + messages[problem] + '\n')
                value = ''; chars.clear(); tainted = False; previous_width = 0
                continue
            if len(chars) >= 4096 or len(char) != 1 or ord(char) < 32:
                tainted = True
                continue
            chars.append(char)
    finally:
        chars.clear()


def now() -> datetime:
    return datetime.now(timezone.utc)


def next_midnight(at: datetime) -> datetime:
    return (at.astimezone(FORTALEZA) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def remaining(expires: datetime, deadline: float) -> float:
    value = min((expires - now()).total_seconds(), deadline - time.monotonic())
    if value <= 0:
        raise ValueError('lease_expired')
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_request(request: dict, root: Path, expires: datetime,
                     deadline: float) -> tuple[int, Path]:
    remaining(expires, deadline)
    if not isinstance(request, dict) or set(request) != {'lot', 'manifest_sha256'}:
        raise ValueError('request_invalid')
    lot, digest = request['lot'], request['manifest_sha256']
    if type(lot) is not int or not 25 <= lot <= 999:
        raise ValueError('lot_invalid')
    if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
        raise ValueError('digest_invalid')
    manifests = list((root / 'evals/narrator/reports').glob(
        f'hybrid-campaign-luna-l{lot}-live-gate-????-??-??.json'))
    if len(manifests) != 1 or sha(manifests[0]) != digest:
        raise ValueError('manifest_mismatch')
    gate = json.loads(manifests[0].read_text(encoding='utf-8'))
    expected = {
        'hypothesis_id': 'HYP-007', 'lot_id': f'HYP-007-L{lot}',
        'target_model': 'gpt-5.6-luna', 'reasoning_effort': 'low',
        'max_calls': 17, 'max_output_tokens_per_call': 768,
        'max_request_bytes': 20000, 'max_estimated_usd': '0.15',
        'paid_ceiling_authorized': True, 'live_inference_authorized': True,
        'retry': False, 'fallback': False, 'admission_automatic': False,
        'synthetic_only': True,
    }
    for key, value in expected.items():
        if type(gate.get(key)) is not type(value) or gate[key] != value:
            raise ValueError('gate_invalid')
    frozen = gate.get('implementation_sha256')
    if not isinstance(frozen, dict) or len(frozen) != 22:
        raise ValueError('hashes_invalid')
    runner = root / f'scripts/evaluate_hybrid_campaign_luna_l{lot}_live.py'
    if runner.relative_to(root).as_posix() not in frozen:
        raise ValueError('runner_not_frozen')
    for relative, digest in frozen.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or sha(path) != digest:
            raise ValueError('implementation_drifted')
    if (root / f'eval-results/hybrid-campaign-luna-l{lot}-once').exists():
        raise ValueError('lot_already_dispatched')
    return lot, runner


def wait_child(process: subprocess.Popen, expires: datetime, deadline: float) -> int:
    """Expiry/interrupt terminate a running evaluator, not just the next lot."""
    try:
        return process.wait(timeout=remaining(expires, deadline))
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def dispatch(request: dict, key: str, expires: datetime, deadline: float,
             *, root: Path = ROOT) -> int:
    if local_credential_problem(key):
        raise ValueError('credential_input_invalid')
    lot, runner = validate_request(request, root, expires, deadline)
    environment = os.environ.copy()
    for name in tuple(environment):
        if name.startswith('STORYTELLER_OPENAI_HYP007_L') and name.endswith('_KEY'):
            del environment[name]
    environment['STORYTELLER_DISABLE_DOTENV'] = '1'
    command = [sys.executable, '-m', f'scripts.{runner.stem}']
    # No credential in the supervisor environment or the preflight subprocess.
    process = subprocess.Popen(command + ['--preflight'], cwd=root, env=environment)
    if wait_child(process, expires, deadline) != 0:
        raise ValueError('preflight_failed')
    # Verify approval/frozen inputs/lease again immediately before inference.
    validate_request(request, root, expires, deadline)
    remaining(expires, deadline)
    environment[f'STORYTELLER_OPENAI_HYP007_L{lot}_KEY'] = key
    try:
        process = subprocess.Popen(command + ['--live', '--batch-id', str(uuid4())],
                                   cwd=root, env=environment)
    finally:
        environment.clear()
    try:
        return wait_child(process, expires, deadline)
    except (ValueError, KeyboardInterrupt, subprocess.TimeoutExpired):
        print('CUSTO FINAL LUNA: indisponivel; execucao interrompida. Conferir artefatos.', flush=True)
        raise


def write_status(directory: Path, expires: datetime, phase: str, **fields) -> None:
    value = {'protocol': 'luna-credential-lease-v1', 'process_id': os.getpid(),
             'expires_at_utc': expires.isoformat(), 'phase': phase, **fields}
    temporary = directory / 'status.tmp'
    temporary.write_text(json.dumps(value, sort_keys=True) + '\n', encoding='utf-8')
    temporary.replace(directory / 'status.json')


def supervise(expires: datetime, deadline: float, *, root: Path = ROOT) -> int:
    remaining(expires, deadline)
    directory = root / 'eval-results/credential-leases' / str(uuid4())
    directory.mkdir(parents=True, exist_ok=False)
    write_status(directory, expires, 'awaiting_secure_credential')
    key = ''
    try:
        if not sys.stdin.isatty():
            raise ValueError('interactive_console_required')
        print('Sessao temporaria. Entrada oculta; nao envie a chave pelo chat.', flush=True)
        key = read_credential(expires, deadline)
        if local_credential_problem(key):
            raise ValueError('credential_input_invalid')
        remaining(expires, deadline)
        write_status(directory, expires, 'idle', credential_local_validation='passed')
        print('Pronta. Somente lotes aprovados; expira a meia-noite de Fortaleza.', flush=True)
        seen_lots: set[int] = set()
        while remaining(expires, deadline) > 0:
            for path in sorted(directory.glob('request-*.json')):
                remaining(expires, deadline)
                claimed = path.with_suffix('.claimed')
                path.rename(claimed)
                try:
                    if claimed.stat().st_size > 1024:
                        raise ValueError('request_too_large')
                    request = json.loads(claimed.read_text(encoding='utf-8'))
                    lot, _ = validate_request(request, root, expires, deadline)
                    if lot in seen_lots:
                        raise ValueError('lot_already_requested')
                    seen_lots.add(lot)
                    write_status(directory, expires, 'running', lot=lot)
                    code = dispatch(request, key, expires, deadline, root=root)
                    write_status(directory, expires, 'idle', last_lot=lot, last_exit_code=code)
                except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
                    # Never record exception text, request body or environment.
                    write_status(directory, expires, 'request_rejected_or_stopped')
            time.sleep(min(1, remaining(expires, deadline)))
    except (OSError, ValueError, KeyboardInterrupt, EOFError, subprocess.TimeoutExpired):
        return 0
    finally:
        key = ''
        write_status(directory, expires, 'closed')
        print('Sessao encerrada. Credencial nao sera reutilizada.', flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--expires-at', required=True)
    args = parser.parse_args()
    expires = datetime.fromisoformat(args.expires_at)
    current = now()
    # Explicit deadline prevents a delayed/restarted window renewing the lease.
    if expires.tzinfo is None or expires > next_midnight(current):
        raise ValueError('expiry_invalid')
    deadline = time.monotonic() + (expires - current).total_seconds()
    remaining(expires, deadline)
    return supervise(expires, deadline)


if __name__ == '__main__':
    raise SystemExit(main())
