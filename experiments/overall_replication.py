"""Repeated three-task study. Only the explicit run command submits API calls."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import hashlib
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import time
from unittest.mock import patch

from experiments import week4_study as w
from experiments import week4_selection as s
from experiments import round2_newdata as n

ROOT = w.ROOT
DIRECTORY = ROOT / 'results/overall_replication_20261103'
SEED = 18020261104
CAP = 50.0
OUTPUT_CAP = 4096
TASKS = ('direct', 'attribute', 'join')
DESCRIPTORS = {**w.DATASETS, **n.DATASETS}
STAGES = ('calibration', 'primary', 'breadth', 'synthetic', 'empirical', 'stress', 'file')
MIME = dict(csv='text/csv', json='application/json', xml='application/xml', txt='text/plain')
FULL_CONTEXT_RESERVATION = (1_050_000 * .50 + OUTPUT_CAP * 1.80) / 1e6


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def append(path, value):
    with path.open('a', encoding='utf-8') as stream:
        stream.write(w.dumps(value) + '\n')
        stream.flush()


def read_lines(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def direct_block(dataset, source, size, block_id, rng):
    rows = deepcopy(rng.sample(source, size))
    field = DESCRIPTORS[dataset][2]
    indices = w.select_targets(rows, field, rng)
    queries = [dict(id=f'q{i+1}', criteria={'record_id': rows[pos]['record_id']},
                    record_id=rows[pos]['record_id'], position=pos) for i, pos in enumerate(indices)]
    queries.append(dict(id='q4', criteria={}, record_id=None, position=None))
    rng.shuffle(queries)
    altered = deepcopy(rows)
    used = {Decimal(row[field]) for row in source}
    lo, hi = float(min(used)), float(max(used))
    for pos in indices:
        while True:
            candidate = f'{rng.uniform(lo, hi):.5f}'
            if Decimal(candidate) not in used:
                break
        altered[pos][field] = candidate
        used.add(Decimal(candidate))
    keys = list(range(size))
    rng.shuffle(keys)
    for i, (original, changed) in enumerate(zip(rows, altered)):
        original['link_id'] = changed['link_id'] = f'L{keys[i]+1:05d}'
    rng.shuffle(keys)
    return dict(id=block_id, dataset=dataset, n_rows=size, attempts=1,
                field=field, original=rows, altered=altered, queries=queries, value_order=keys)


def empirical_block(block, source, rng):
    result = deepcopy(block)
    result['altered'] = deepcopy(block['original'])
    field = block['field']
    used = {Decimal(row[field]) for row in block['original']}
    for query in block['queries']:
        if query['position'] is None:
            continue
        choices = [row[field] for row in source if Decimal(row[field]) not in used]
        if not choices:
            raise ValueError(f'No empirical replacement for {block["id"]}')
        value = rng.choice(choices)
        result['altered'][query['position']][field] = value
        used.add(Decimal(value))
    return result


def validate_block(block, conjunction=True):
    original, altered = block['original'], block['altered']
    field = block['field']
    assert len(original) == len(altered) == block['n_rows']
    assert len({r['record_id'] for r in original}) == len(original)
    changed = [i for i, (a, b) in enumerate(zip(original, altered)) if a != b]
    assert set(changed) == {q['position'] for q in block['queries'] if q['position'] is not None}
    assert len(changed) == 3
    for i in changed:
        assert {k for k in original[i] if original[i][k] != altered[i][k]} == {field}
        assert sum(w.numeric_equal(original[i][field], r[field]) for r in original) == 1
        assert not any(w.numeric_equal(original[i][field], r[field]) for r in altered)
    if conjunction:
        for query in block['queries']:
            matches = s.matching(original, query['criteria'])
            assert len(matches) == (query['position'] is not None)
            if query['position'] is not None:
                for drop in query['criteria']:
                    assert len(s.matching(original, {k: v for k, v in query['criteria'].items()
                                                   if k != drop})) >= 2
            else:
                assert all(any(row[k] == v for row in original) for k, v in query['criteria'].items())


def decorate(case, delivery='inline', alteration='uniform'):
    result = dict(case, delivery=delivery, alteration=alteration)
    result['id'] += '_' + alteration + '_' + delivery
    marker = '\nRECORDS_TABLE:\n' if case['task'] == 'join' else '\nTABLE:\n'
    head, _ = case['prompt'].split(marker, 1)
    rows, values = s.decode_tables(case)
    tables = [('RECORDS_TABLE', rows), ('VALUES_TABLE', values)] if values is not None else [('TABLE', rows)]
    assets = []
    for label, logical in tables:
        text = w.serialize(logical, case['format'])
        assert w.deserialize(text, case['format']) == logical
        # Version is kept even where records tables are identical, for transparent provenance.
        relative = f"assets/{case['block']}/{alteration}/{case['version']}/{label}.{case['format']}"
        assets.append(dict(path=relative, label=label, sha256=w.sha(text), content=text))
    result['assets'] = assets if delivery == 'file' else []
    result['request_text'] = (head + '\nUse the attached table files:\n' + '\n'.join(
        f"{a['label']}: {Path(a['path']).name}" for a in assets)) if delivery == 'file' else case['prompt']
    result['request_sha256'] = w.sha(w.dumps(dict(text=result['request_text'],
        files=[dict(name=Path(a['path']).name, sha256=a['sha256']) for a in result['assets']])))
    result['max_output_tokens'] = OUTPUT_CAP
    assert s.reconstruct(result) == result['expected']
    return result


def build(data, blocks_per_stratum=6, breadth_blocks=4, controls=True):
    rng = random.Random(SEED)
    blocks, cases = [], []

    def add(block, stage, tasks=TASKS, cues=('named', 'neutral'), versions=('original', 'altered'),
            delivery='inline', alteration='uniform'):
        for case in s.cases_for(block, stage, tasks=tasks, cues=cues, versions=versions):
            cases.append(decorate(case, delivery, alteration))

    with patch.dict(w.DATASETS, DESCRIPTORS, clear=True):
        calibration = s.make_block('synthetic', [], 80, 'calibration_synthetic_80', rng)
        validate_block(calibration)
        blocks.append(dict(calibration, stage='calibration'))
        add(calibration, 'calibration', cues=('neutral',), versions=('altered',))
        add(calibration, 'calibration', cues=('neutral',), versions=('altered',), delivery='file')
        for dataset in ('titanic', 'redwine', 'medical'):
            for size in (80, 400):
                for rep in range(blocks_per_stratum):
                    block = s.make_block(dataset, data[dataset], size, f'core_{dataset}_{size}_b{rep}', rng)
                    validate_block(block)
                    blocks.append(dict(block, stage='primary'))
                    add(block, 'primary')
                    if controls and rep < 2:
                        add(block, 'file', cues=('neutral',), delivery='file')
                        subtle = empirical_block(block, data[dataset], rng)
                        validate_block(subtle)
                        blocks.append(dict(subtle, stage='empirical'))
                        add(subtle, 'empirical', cues=('neutral',), versions=('altered',), alteration='empirical')
            if controls:
                for rep in range(2):
                    block = s.make_block(dataset, data[dataset], 800, f'stress_{dataset}_800_b{rep}', rng)
                    validate_block(block)
                    blocks.append(dict(block, stage='stress'))
                    add(block, 'stress', cues=('neutral',))
        for dataset in ('ibm', 'avocado', 'creditcard'):
            for size in (80, 400):
                for rep in range(breadth_blocks):
                    block = direct_block(dataset, data[dataset], size, f'breadth_{dataset}_{size}_b{rep}', rng)
                    validate_block(block, conjunction=False)
                    blocks.append(dict(block, stage='breadth'))
                    add(block, 'breadth', tasks=('direct',))
        if controls:
            for size in (80, 400):
                for rep in range(2):
                    block = s.make_block('synthetic', [], size, f'synthetic_{size}_b{rep}', rng)
                    validate_block(block)
                    blocks.append(dict(block, stage='synthetic'))
                    add(block, 'synthetic', cues=('neutral',))
    assert len({c['id'] for c in cases}) == len(cases)
    requests = []
    for stage in STAGES:
        group = [c for c in cases if c['stage'] == stage]
        for repeat in range(1, 2 if stage == 'calibration' else 4):
            order = sorted(group, key=lambda c: c['id'])
            random.Random(f'{SEED}:{stage}:{repeat}').shuffle(order)
            requests.extend(dict(id=f"{c['id']}_r{repeat}", case_id=c['id'], stage=stage,
                                 repeat=repeat) for c in order)
    return blocks, cases, requests


def source_hashes():
    return {key: file_hash(ROOT/'data'/definition[0]) for key, definition in DESCRIPTORS.items()}


def prepare(directory):
    hashes = source_hashes()
    old = json.loads((ROOT/'results/week4_lookup/manifest.json').read_text())['source_sha256']
    old.update(json.loads((ROOT/'results/round2_newdata/manifest.json').read_text())['source_sha256'])
    assert hashes == old, 'Local dataset hashes differ from the historical versions.'
    print('All six data hashes match the historical manifests.', flush=True)
    data = {**w.load_data(), **n.load_data()}
    blocks, cases, requests = build(data)
    assert len(requests) == 8376, Counter(r['stage'] for r in requests)
    directory.mkdir(parents=True, exist_ok=False)
    for name, values in [('blocks.jsonl', blocks), ('cases.jsonl', cases), ('requests.jsonl', requests)]:
        (directory/name).write_text(''.join(w.dumps(value)+'\n' for value in values), encoding='utf-8')
    assets = {}
    for case in cases:
        for asset in case['assets']:
            path = directory/asset['path']
            if path.exists():
                assert file_hash(path) == asset['sha256']
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(asset['content'].encode('utf-8'))
            assets[asset['path']] = asset['sha256']
    snapshot = directory/'source_snapshot'
    snapshot.mkdir()
    sources = [Path(__file__), Path(w.__file__), Path(s.__file__), Path(n.__file__),
               ROOT/'experiments/overall_replication_protocol.md', ROOT/'pyproject.toml', ROOT/'uv.lock']
    if (ROOT/'experiments/analyze_overall_replication.py').exists():
        sources.append(ROOT/'experiments/analyze_overall_replication.py')
    for source in sources:
        shutil.copyfile(source, snapshot/source.name)
    manifest = dict(created_utc=w.utc(), model=w.MODEL, reasoning_effort='medium', seed=SEED,
        budget_usd=CAP, max_output_tokens=OUTPUT_CAP, tools=[], store=False, repeats=3,
        planned=len(requests), unique_cases=len(cases),
        stages=dict(Counter(r['stage'] for r in requests)), data_sha256=hashes,
        artifacts_sha256={name: file_hash(directory/name) for name in ('blocks.jsonl','cases.jsonl','requests.jsonl')},
        sources_sha256={str(path.relative_to(ROOT)): file_hash(path) for path in sources},
        assets_sha256=assets, pricing_checked='2026-11-03',
        pricing_source='https://developers.openai.com/api/docs/models/gpt-5.6-luna',
        file_inputs_source='https://developers.openai.com/api/docs/guides/file-inputs',
        operational_limit='At most 12 concurrent requests. No automatic retries.',
        interpretation='Exploratory fixed-sample replication; block dependence retained; no equivalence claim.')
    save(directory/'manifest.json', manifest)
    print(json.dumps({k: manifest[k] for k in ('planned','unique_cases','stages','budget_usd')}, indent=2))


def verify(directory, sources=True):
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['model'] == w.MODEL and manifest['reasoning_effort'] == 'medium'
    for name, sha in manifest['artifacts_sha256'].items():
        assert file_hash(directory/name) == sha, name
    if sources:
        for name, sha in manifest['sources_sha256'].items():
            assert file_hash(ROOT/name) == sha, name
    for name, sha in manifest['assets_sha256'].items():
        assert file_hash(directory/name) == sha, name
    cases = {c['id']: c for c in read_lines(directory/'cases.jsonl')}
    requests = read_lines(directory/'requests.jsonl')
    assert len({r['id'] for r in requests}) == len(requests) == manifest['planned']
    assert len(cases) == manifest['unique_cases']
    for case in cases.values():
        assert s.reconstruct(case) == case['expected']
    return manifest, cases, requests


def reservation(case):
    if case['delivery'] == 'file':
        return FULL_CONTEXT_RESERVATION
    return ((len((w.SYSTEM+case['request_text']).encode('utf-8'))+4096)*.50 + OUTPUT_CAP*1.80)/1e6


def usage_cost(usage, conservative=False):
    long_context = usage['input_tokens'] > 272_000
    rate = (.40 if long_context else .20) * (1.25 if conservative else 1)
    return (usage['input_tokens']*rate + usage['output_tokens']*(1.80 if long_context else 1.20))/1e6


def grade(case, output, status):
    result = w.score(case, output, status)
    result['strict_correct'] = bool(result['all_correct'] and result['exact_keys'] and result['string_values'])
    return result


def payload(case, file_ids=None):
    content = [{'type':'input_text', 'text':case['request_text']}]
    for asset in case['assets']:
        content.append({'type':'input_file', 'file_id':file_ids[asset['path']]})
    return dict(model=w.MODEL, instructions=w.SYSTEM,
                input=[{'role':'user','content':content}], tools=[], store=False,
                reasoning={'effort':'medium'}, max_output_tokens=OUTPUT_CAP)


def gate_passed(records, requests):
    planned = {r['id'] for r in requests if r['stage'] == 'calibration'}
    group = [r for r in records if r['stage'] == 'calibration']
    return ({r['id'] for r in group} == planned and len(group) == len(planned)
            and all(r.get('returned_model') == w.MODEL and r.get('score',{}).get('strict_correct') for r in group))


def status(directory):
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    records = read_lines(directory/'trials.jsonl')
    result = dict(updated_utc=w.utc(), planned=manifest['planned'], recorded=len(records),
        completed=sum(r['status']=='completed' for r in records),
        strict_correct=sum(r.get('score',{}).get('strict_correct',False) for r in records),
        accounted_usd=sum(r['accounted_usd'] for r in records),
        estimated_uncached_usd=sum(r.get('estimated_usd',0) for r in records),
        by_stage=dict(Counter(r['stage'] for r in records)))
    return result


async def run(directory, workers=12, client=None):
    import openai
    from dotenv import dotenv_values
    manifest, cases, requests = verify(directory)
    records = read_lines(directory/'trials.jsonl')
    starts = read_lines(directory/'started.jsonl')
    assert len({r['id'] for r in records}) == len(records)
    assert len({r['id'] for r in starts}) == len(starts)
    done = {r['id'] for r in records}
    assert done <= {r['id'] for r in requests}
    if {r['id'] for r in starts} != done:
        raise RuntimeError('A started request has an uncertain outcome. Inspect before resuming; never automatically resend.')
    if workers < 1 or workers > 12:
        raise ValueError('Workers must be 1 through 12.')
    config = dotenv_values(ROOT/'.env', encoding='utf-8-sig')
    if config.get('OPENAI_MODEL') != w.MODEL or config.get('OPENAI_REASONING_EFFORT') != 'medium':
        raise RuntimeError('Configure the frozen model and medium reasoning in .env.')
    if client is None:
        key = config.get('OPENAI_API_KEY') or os.environ.get('OPENAI_API_KEY')
        if not key:
            raise RuntimeError('API key is not configured.')
        client = openai.AsyncOpenAI(api_key=key, max_retries=0, timeout=180)
    try:
        git_head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    except Exception:
        git_head, dirty = None, None
    append(directory/'runtime.jsonl', dict(started_utc=w.utc(), python=platform.python_version(),
        implementation=platform.python_implementation(), os=platform.platform(), sdk=openai.__version__,
        distributions={d.metadata['Name']:d.version for d in distributions() if d.metadata.get('Name')},
        git_head=git_head, dirty=dirty, uv_lock_sha256=file_hash(ROOT/'uv.lock'), workers=workers,
        model=w.MODEL, reasoning_effort='medium', budget_usd=manifest['budget_usd'],
        environment_deviation='Python 3.12.14 unavailable to installed uv; using recorded available runtime, same as file pilot.'))
    spent = sum(r['accounted_usd'] for r in records)
    in_flight, errors = 0., 0
    stop_reason = None
    budget_lock = asyncio.Lock()
    file_lock = asyncio.Lock()
    uploaded = {r['path']:r['file_id'] for r in read_lines(directory/'uploads.jsonl') if r.get('file_id')}
    cleaned = {r['file_id'] for r in read_lines(directory/'cleanup.jsonl') if r.get('deleted')}
    uploaded = {path:fid for path,fid in uploaded.items() if fid not in cleaned}

    async def ensure_files(case):
        async with file_lock:
            for asset in case['assets']:
                if asset['path'] in uploaded:
                    continue
                path = directory/asset['path']
                with path.open('rb') as stream:
                    file = await client.files.create(file=(path.name,stream,MIME[case['format']]), purpose='user_data')
                uploaded[asset['path']] = file.id
                append(directory/'uploads.jsonl', dict(path=asset['path'], sha256=asset['sha256'],
                    file_id=file.id, uploaded_utc=w.utc()))

    async def one(request):
        nonlocal spent, in_flight, errors, stop_reason
        case = cases[request['case_id']]
        bound = reservation(case)
        async with budget_lock:
            if stop_reason:
                return
            if spent+in_flight+bound > manifest['budget_usd']:
                stop_reason = 'budget_reservation_limit'
                return
            in_flight += bound
            append(directory/'started.jsonl', dict(request, started_utc=w.utc(), reserved_usd=bound,
                                                  request_sha256=case['request_sha256']))
        started = time.monotonic()
        record = dict(request, started_utc=w.utc(), request_sha256=case['request_sha256'])
        cost = bound
        try:
            await ensure_files(case)
            response = await client.responses.create(**payload(case, uploaded))
            usage = response.usage.model_dump() if response.usage else None
            record.update(response_id=response.id, returned_model=response.model, status=response.status,
                output=response.output_text, usage=usage,
                response_reasoning=response.reasoning.model_dump() if response.reasoning else None,
                incomplete_details=response.incomplete_details.model_dump() if response.incomplete_details else None)
            record['score'] = grade(case,response.output_text,response.status)
            if usage:
                cost = usage_cost(usage,True)
                record['estimated_usd'] = usage_cost(usage)
            if response.model != w.MODEL or not usage:
                stop_reason = 'model_mismatch_or_missing_usage'
            if cost > bound:
                stop_reason = 'reservation_exceeded'
        except Exception as exc:
            record.update(status='api_error', error_type=type(exc).__name__,
                          http_status=getattr(exc,'status_code',None))
            errors += 1
            if errors >= 3 or getattr(exc,'status_code',None) in (401,403,404,429):
                stop_reason = 'operational_errors'
        finally:
            record.update(finished_utc=w.utc(), elapsed_seconds=round(time.monotonic()-started,3), accounted_usd=cost)
            async with budget_lock:
                in_flight -= bound
                spent += cost
                append(directory/'trials.jsonl', record)
                records.append(record)
                done.add(request['id'])
                if len(records) % 25 == 0 or record['status'] != 'completed':
                    progress = status(directory)
                    progress['stop_reason'] = stop_reason
                    save(directory/'progress.json',progress)
                    print(w.dumps(progress), flush=True)

    async def batch(group):
        queue = asyncio.Queue()
        for request in group:
            queue.put_nowait(request)
        async def worker():
            while not stop_reason:
                try:
                    request = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                await one(request)
        await asyncio.gather(*(worker() for _ in range(workers)))

    try:
        for stage in STAGES:
            if stage != 'calibration' and not gate_passed(records,requests):
                stop_reason = stop_reason or 'calibration_gate_failed'
                break
            # Finish each repeat round before starting the next.
            for repeat in range(1,2 if stage=='calibration' else 4):
                pending = [r for r in requests if r['stage']==stage and r['repeat']==repeat and r['id'] not in done]
                await batch(pending)
                if stop_reason:
                    break
            if stop_reason:
                break
    finally:
        for path,file_id in uploaded.items():
            try:
                deleted = await client.files.delete(file_id)
                append(directory/'cleanup.jsonl',dict(path=path,file_id=file_id,deleted=bool(deleted.deleted)))
            except Exception as exc:
                append(directory/'cleanup.jsonl',dict(path=path,file_id=file_id,deleted=False,error_type=type(exc).__name__))
        await client.close()
        progress = status(directory)
        progress.update(stop_reason=stop_reason or 'completed', calibration_gate=gate_passed(records,requests))
        save(directory/'progress.json',progress)
        print(json.dumps(progress,indent=2),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','run','status','analyze'))
    parser.add_argument('--directory',type=Path,default=DIRECTORY)
    parser.add_argument('--workers',type=int,default=12)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.directory)
    elif args.action == 'run':
        asyncio.run(run(args.directory,args.workers))
    elif args.action == 'status':
        print(json.dumps(status(args.directory),indent=2))
    else:
        from experiments.analyze_overall_replication import analyze
        analyze(args.directory)


if __name__ == '__main__':
    main()
