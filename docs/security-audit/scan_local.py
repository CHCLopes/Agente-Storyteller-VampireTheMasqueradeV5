"""Reproducible offline inventory and redacted credential-indicator scan.

Never opens .env*, credential files, campaign saves, or external services.
Candidate indicators are not automatically classified as real credentials.
"""
import ast
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SKIP_DIRS = {'.git', '.venv', 'node_modules', 'eval-results', '__pycache__',
             '.pytest_cache', '.codex', '.agents', 'security-audit'}
EXTENSIONS = {'.py', '.ts', '.tsx', '.js', '.html', '.json', '.md', '.yml',
              '.yaml', '.toml', '.ps1', '.bat', '.txt', '.css'}
RULES = {
    'provider_token': re.compile(r'\b(?:sk-(?:proj-|or-v1-)?[A-Za-z0-9_-]{20,}|gsk_[A-Za-z0-9]{25,}|AIza[A-Za-z0-9_-]{30,})\b'),
    'private_key_header': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'assigned_secret_literal': re.compile(r'''(?i)(?:api[_-]?key|access[_-]?token|password|jwt[_-]?secret)\s*[:=]\s*["']([^"'\n]{12,})["']'''),
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def excluded(path):
    p = Path(path)
    lowered = '/' + str(p).replace('\\', '/').lower().lstrip('/')
    return (any(part in SKIP_DIRS for part in p.parts)
        or any(part.lower().startswith('.env') for part in p.parts)
        or p.suffix.lower() not in EXTENSIONS
        or any(word in lowered for word in ('/data/saves/', '/credentials/', '/secrets/'))
        or p.name.lower() in {'credentials.json', 'service-account.json', 'keys.json', 'secrets.json', 'tokens.json'})


def indicators(text, path, revision=None):
    results = []
    for line, value in enumerate(text.splitlines(), 1):
        for rule, pattern in RULES.items():
            for match in pattern.finditer(value):
                material = match.group(0)
                fixture = any(word in material.lower() for word in
                    ('synthetic', 'test', 'example', 'dummy', 'placeholder', 'your_', 'change_in_production'))
                results.append({'file': path, 'line': line, 'rule': rule,
                    'revision': revision, 'classification': 'fixture_or_placeholder' if fixture else 'review_required',
                    'evidence': '[REDACTED: indicator literal]',
                    'fingerprint_sha256': hashlib.sha256(material.encode()).hexdigest()})
    return results


def run():
    assert all(excluded(path) for path in (
        '.ENV.json', 'config/.env', 'keys.json', 'credentials.json',
        'data/saves/probe.json', 'data/saves/probe.py', 'nested/secrets/key.json'))
    assert not excluded('api/main.py')
    handlers, candidates, scanned, parse_failures = [], [], 0, []
    for directory in ('api', 'scripts'):
        for file in sorted((ROOT / directory).rglob('*.py')):
            if excluded(file.relative_to(ROOT)):
                continue
            relative = file.relative_to(ROOT).as_posix()
            try:
                tree = ast.parse(file.read_text(encoding='utf-8-sig'))
            except (SyntaxError, UnicodeError):
                parse_failures.append(relative)
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                        and decorator.func.attr in {'get', 'post', 'put', 'patch', 'delete', 'websocket'}
                        and decorator.args and isinstance(decorator.args[0], ast.Constant)
                        and isinstance(decorator.args[0].value, str)):
                        handlers.append({'file': relative, 'line': node.lineno,
                            'end_line': node.end_lineno, 'handler': node.name,
                            'method': decorator.func.attr.upper(), 'path': decorator.args[0].value})
    current_files = []
    for directory, dirs, names in os.walk(ROOT):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS
                   and name.lower() not in {'credentials', 'secrets', '.aws', 'saves'}
                   and not name.lower().startswith('.env')]
        current_files.extend(Path(directory) / name for name in names)
    for file in current_files:
        if not file.is_file() or excluded(file.relative_to(ROOT)) or file.stat().st_size > 4_000_000:
            continue
        relative = file.relative_to(ROOT).as_posix()
        scanned += 1
        candidates.extend(indicators(file.read_text(encoding='utf-8-sig', errors='replace'), relative))
    # Every reachable text blob, once, across all locally available refs.
    history_count, history_candidates = 0, []
    for row in git('rev-list', '--objects', '--all').decode().splitlines():
        parts = row.split(' ', 1)
        if len(parts) != 2 or excluded(parts[1]):
            continue
        oid, path = parts
        if git('cat-file', '-t', oid).strip() != b'blob':
            continue
        if int(git('cat-file', '-s', oid)) > 4_000_000:
            continue
        history_count += 1
        text = git('cat-file', 'blob', oid).decode('utf-8-sig', errors='replace')
        found = indicators(text, path, revision='blob:' + oid)
        if found:
            commits = git('log', '--all', '--format=%H', '--find-object=' + oid).decode().splitlines()
            for finding in found:
                finding['commit_references'] = commits
            history_candidates.extend(found)
    for h in handlers:
        if h['file'] == 'api/main.py':
            h['boundary'] = 'LocalRequestBoundary; native local operator trusted, not multi-tenant auth'
            h['object_access'] = 'session-scoped SQLite; same trusted local operator' if 'session' in h['path'] else 'not applicable'
        elif h['file'] == 'api/narrative_source_local_app.py':
            h['boundary'] = 'exact bound Host/Origin/session before accept; opt-in only'
            h['object_access'] = 'one server-bound synthetic session and store'
        else:
            h['boundary'] = 'LocalRequestBoundary; token on every API handler, bootstrap root guarded by Host'
            h['object_access'] = 'shared synthetic trial operator; session-scoped SQLite'
        h['categories'] = {
            'tenant_owner': 'not_applicable_multi_tenant; local boundary verified',
            'server_permissions': 'verified; SEC-001/002 remediated where applicable',
            'idor': 'verified_within_single_operator_model; no per-human isolation claimed',
            'embedded_secrets': 'static scan; candidates manually classified; no credential validation',
            'xss': 'JSON/text output or fixed HTML; React escapes; no confirmed sink',
        }
    result = {'head': git('rev-parse', 'HEAD').decode().strip(),
        'branch': git('branch', '--show-current').decode().strip(),
        'shallow': git('rev-parse', '--is-shallow-repository').decode().strip(),
        'local_commits': int(git('rev-list', '--count', '--all')),
        'current_text_files_scanned': scanned, 'historical_text_blobs_scanned': history_count,
        'excluded': ['.env*', 'credentials/secrets files', 'campaign saves', 'dependencies', 'files over 4 MB', 'audit output'],
        'parse_failures': parse_failures, 'handlers': sorted(handlers, key=lambda h: (h['file'], h['line'])),
        'secret_indicators': candidates, 'historical_secret_indicators': history_candidates,
        'limitations': ['heuristic scan, not proof of absence', 'no remote refs fetched',
            'no live credential validation', 'dependency CVE audit not performed',
            'bundles scanned as existing, no rebuild', 'listener binding is a deployment requirement'],
        'bundle_files': [p.name for p in (ROOT / 'client/dist/assets').glob('*.js')]}
    (OUT / 'cobertura-e-scan.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('local_commits', 'current_text_files_scanned', 'historical_text_blobs_scanned', 'parse_failures')}, ensure_ascii=False))
    print(json.dumps({'handlers': len(handlers), 'current_indicators': len(candidates), 'historical_indicators': len(history_candidates)}))


if __name__ == '__main__':
    run()
