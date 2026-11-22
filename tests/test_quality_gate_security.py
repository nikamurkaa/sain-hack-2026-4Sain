"""Offline source integrity/security regression; no remote scanning or secrets emitted."""
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parents[1]


def test_requirements_are_pinned_and_npm_lock_has_integrity():
    req=[line.strip() for line in (ROOT/'requirements.txt').read_text().splitlines()
         if line.strip() and not line.lstrip().startswith('#')]
    assert req and all(re.fullmatch(r'[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+',v) for v in req)
    lock=json.loads((ROOT/'frontend/package-lock.json').read_text())
    nodes={k:v for k,v in lock.get('packages',{}).items() if k.startswith('node_modules/') and not v.get('link')}
    assert nodes and all(v.get('integrity','').startswith('sha512-') for v in nodes.values())


def test_source_contains_no_private_keys_or_long_provider_tokens():
    patterns=[
        re.compile(r'-----BEGIN (?:OPENSSH |EC |RSA )?PRIVATE KEY-----'),
        re.compile(r'\b(?:ghp_|gho_|github_pat_)[A-Za-z0-9_]{25,}\b'),
        re.compile(r'\bsk-[A-Za-z0-9_-]{28,}\b'),
    ]
    failures=[]
    for folder in ('backend','frontend/src','scripts','windows','tests'):
        for item in (ROOT/folder).rglob('*'):
            if item.suffix not in ('.py','.ts','.tsx','.js','.ps1','.cmd','.md','.yml'): continue
            if any(s in item.parts for s in ['dist','node_modules','__pycache__']):continue
            text=item.read_text(encoding='utf-8',errors='replace')
            if any(p.search(text) for p in patterns):failures.append(str(item.relative_to(ROOT)))
    assert not failures, 'Possible private credential in: '+', '.join(failures)
