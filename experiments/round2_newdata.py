"""Round 2 record-lookup design repeated on three new datasets. Preparation never makes API calls.

Reuses table construction, serialization, scoring, and analysis from week4_study.py unchanged; only the
datasets, the secondary components, and the spending cap differ (see round2_newdata_protocol.md).

python -m experiments.round2_newdata prepare
python -m experiments.round2_newdata run [--budget USD]
python -m experiments.round2_newdata analyze
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import csv
import hashlib
import json
import platform
import random
import sys
import time
from pathlib import Path
from unittest import mock

from experiments import week4_study as w

ROOT = w.ROOT
DIRECTORY = ROOT/'results/round2_newdata'
SEED = 18020261025
BUDGET_USD = 1.00
# Round 2 actually spent $0.396 against a $4.011 worst-case reservation; used only to report an expected cost
ROUND2_ACTUAL_TO_BOUND = 0.396/4.011
DATASETS = {
    'ibm': ('IBM.csv', 'IBM HR Analytics Employee Attrition', 'monthly_income'),
    'avocado': ('avocado.csv', 'Avocado Prices', 'total_volume'),
    'creditcard': ('creditcard.csv', 'Credit Card Fraud Detection', 'amount'),
}
STRESS_DATASET = 'ibm'  # Round 2 used Titanic; the 800-row stress test needs a source with at least 800 rows


def load_data():
    data = {}
    for dataset, (filename, _, _) in DATASETS.items():
        with (ROOT/'data'/filename).open(encoding='utf-8-sig', newline='') as f:
            raw = csv.DictReader(f)
            if dataset == 'ibm':
                rows = [dict(record_id=r['EmployeeNumber'], age=r['Age'], gender=r['Gender'],
                             department=r['Department'], job_role=r['JobRole'],
                             monthly_income=r['MonthlyIncome']) for r in raw]
            elif dataset == 'avocado':
                rows = [dict(record_id=str(i+1), date=r['Date'], region=r['region'], type=r['type'],
                             average_price=r['AveragePrice'], total_volume=r['Total Volume'])
                        for i, r in enumerate(raw)]
            else:
                rows = [dict(record_id=str(i+1), time=r['Time'], v1=r['V1'], v2=r['V2'], amount=r['Amount'])
                        for i, r in enumerate(raw)]
        assert len({r['record_id'] for r in rows}) == len(rows)
        assert all(all(v != '' for v in r.values()) for r in rows)
        data[dataset] = rows
    return data


def build_cases():
    rng = random.Random(SEED)
    data = load_data()
    cases = []
    # make_lookup_cases reads dataset titles and queried fields from week4_study.DATASETS
    with mock.patch.dict(w.DATASETS, DATASETS, clear=True):
        for dataset, rows in data.items():
            field = DATASETS[dataset][2]
            all_values = [r[field] for r in rows]
            for n in (40, 200):
                for rep in range(3):
                    cases.extend(w.make_lookup_cases(dataset, rng.sample(rows, n), f'{dataset}_{n}_b{rep}',
                                                     'main', rng, all_values))
        field = DATASETS[STRESS_DATASET][2]
        for rep in range(2):
            cases.extend(w.make_lookup_cases(STRESS_DATASET, rng.sample(data[STRESS_DATASET], 800),
                                             f'{STRESS_DATASET}_800_b{rep}', 'stress', rng,
                                             [r[field] for r in data[STRESS_DATASET]], cues=('named',)))
        for n in (40, 200):
            for rep in range(3):
                rows = [dict(record_id=str(i+1), category=rng.choice(['A','B','C']),
                             value=f'{rng.uniform(0,1000):.5f}') for i in range(n)]
                cases.extend(w.make_lookup_cases('synthetic', rows, f'synthetic_{n}_b{rep}', 'synthetic', rng,
                                                 [r['value'] for r in rows], cues=('neutral',)))
    for dataset in DATASETS:
        for fmt in w.FORMATS:
            base = next(c for c in cases if c['id'] == f'{dataset}_200_b0_altered_named_{fmt}')
            cases.append(dict(base, id=base['id']+'_repeat', stage='repeat'))
    rng.shuffle(cases)
    return cases


def dispatch_order(cases):
    """Order requests so a run stopped by the spending cap still holds whole primary blocks in every stratum.

    Primary blocks go first: block 0 of every dataset and size, then block 1, then block 2, with the 16 conditions
    of each block shuffled. Secondary requests follow: repeats, synthetic, then the expensive 800-row stress tables.
    """
    rng = random.Random(SEED+1)
    main = collections.defaultdict(list)
    for c in cases:
        if c['stage'] == 'main':
            main[c['block']].append(c)
    ordered = []
    for block in sorted(main, key=lambda b: (b.rsplit('_b', 1)[1], b)):
        group = sorted(main[block], key=lambda c: c['id'])
        rng.shuffle(group)
        ordered += group
    for stage in ('repeat', 'synthetic', 'stress'):
        group = sorted((c for c in cases if c['stage'] == stage), key=lambda c: c['id'])
        rng.shuffle(group)
        ordered += group
    assert len(ordered) == len(cases)
    return ordered


def prepare(directory):
    if directory.exists() and any(directory.iterdir()):
        raise RuntimeError('Refusing to replace an existing experiment plan')
    directory.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
    bound = sum(map(w.budget_bound, cases))
    manifest = dict(created_utc=w.utc(), design='Round 2 record lookup (week4_study.py) on new datasets',
                    model=w.MODEL, reasoning_effort='medium', seed=SEED,
                    tools=[], store=False, temperature='provider default; not set',
                    requests=len(cases), stages=dict(collections.Counter(c['stage'] for c in cases)),
                    plan_sha256=w.sha('\n'.join(w.dumps(c) for c in cases)),
                    source_sha256={name: hashlib.sha256((ROOT/'data'/v[0]).read_bytes()).hexdigest()
                                   for name, v in DATASETS.items()},
                    budget_usd=BUDGET_USD,
                    budget_rule='Spending cap on actual estimated cost: a request is dispatched only if spent '
                                'plus in-flight worst-case reservations plus its own worst case fit the cap.',
                    worst_case_all_requests_usd=bound,
                    expected_usd_at_round2_ratio=bound*ROUND2_ACTUAL_TO_BOUND,
                    dispatch_order='Primary blocks b0 of every stratum, then b1, then b2; then repeat, '
                                   f'synthetic, stress. Seeded with {SEED+1}.',
                    input_rate_per_million=.20, output_rate_per_million=1.20,
                    python=platform.python_version(),
                    note='Exploratory plan frozen locally before responses, not public preregistration.')
    assert len({c['id'] for c in cases}) == len(cases)
    (directory/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (directory/'cases.jsonl').write_text('\n'.join(w.dumps(c) for c in cases)+'\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))


def read_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


def complete_main_blocks(cases, recorded):
    blocks = collections.defaultdict(list)
    for c in cases:
        if c['stage'] == 'main':
            blocks[c['block']].append(c['id'] in recorded)
    return sorted(b for b, sent in blocks.items() if all(sent))


async def run(directory, workers=4, budget=None, client=None):
    """week4_study.run with a cap on actual spending instead of on summed worst-case reservations.

    Same logging, resume, and stop rules: starts are logged before dispatch, completed IDs are skipped, a started
    request without a response blocks resuming, and there are no automatic retries.
    """
    manifest = json.loads((directory/'manifest.json').read_text())
    budget = manifest['budget_usd'] if budget is None else budget
    cases = read_jsonl(directory/'cases.jsonl')
    assert w.sha('\n'.join(w.dumps(c) for c in cases)) == manifest['plan_sha256']
    trials_path, starts_path = directory/'trials.jsonl', directory/'started.jsonl'
    previous = read_jsonl(trials_path)
    done = {r['id'] for r in previous}
    abandoned = {r['id'] for r in read_jsonl(starts_path)}-done
    if abandoned:
        raise RuntimeError(f'{len(abandoned)} started requests lack a response; inspect before resuming')
    spent = sum(r['counted_usd'] for r in previous)
    remaining = [c for c in dispatch_order(cases) if c['id'] not in done]
    sdk = 'injected test client'
    if client is None:
        from dotenv import dotenv_values
        import openai
        from openai import AsyncOpenAI
        config = dotenv_values(ROOT/'.env', encoding='utf-8-sig')
        if not config.get('OPENAI_API_KEY'):
            raise RuntimeError('OPENAI_API_KEY not configured')
        client = AsyncOpenAI(api_key=config['OPENAI_API_KEY'], max_retries=0, timeout=120)
        sdk = openai.__version__
    sem = asyncio.Semaphore(workers)
    in_flight = 0.0
    errors = 0
    sent = 0
    stop_reason = None
    with (directory/'runtime.jsonl').open('a', encoding='utf-8') as f:
        f.write(w.dumps(dict(started_utc=w.utc(), sdk=sdk, python=sys.version, workers=workers,
                             budget_usd=budget, spent_before_usd=spent, remaining=len(remaining)))+'\n')

    async def one(case):
        nonlocal spent, in_flight, errors, sent, stop_reason
        async with sem:
            if stop_reason:
                return
            bound = w.budget_bound(case)
            if spent+in_flight+bound > budget:
                stop_reason = 'spending cap'
                return
            in_flight += bound
            with starts_path.open('a', encoding='utf-8') as f:
                f.write(w.dumps(dict(id=case['id'], started_utc=w.utc(), reserved_max_usd=bound))+'\n')
            begin = time.monotonic()
            record = dict(id=case['id'], started_utc=w.utc(), prompt_sha256=w.sha(case['prompt']))
            try:
                response = await client.responses.create(model=w.MODEL, instructions=w.SYSTEM,
                    input=[{'role': 'user', 'content': case['prompt']}], tools=[], store=False,
                    reasoning={'effort': 'medium'}, max_output_tokens=case['max_output_tokens'])
                usage = response.usage.model_dump()
                cost = (usage['input_tokens']*.20+usage['output_tokens']*1.20)/1e6
                record.update(response_id=response.id, returned_model=response.model, status=response.status,
                    output=response.output_text, usage=usage, elapsed_seconds=round(time.monotonic()-begin, 3),
                    incomplete_details=response.incomplete_details.model_dump() if response.incomplete_details else None,
                    estimated_usd=cost, counted_usd=cost)
                record['score'] = w.score(case, response.output_text, response.status)
                if response.model != w.MODEL:
                    record['model_mismatch'] = True
                    stop_reason = 'model mismatch'
            except Exception as exc:
                # A failed request may still have been billed, so its whole worst case stays counted
                record.update(status='api_error', error_type=type(exc).__name__,
                              http_status=getattr(exc, 'status_code', None),
                              elapsed_seconds=round(time.monotonic()-begin, 3), counted_usd=bound)
                errors += 1
                if errors >= 3 or getattr(exc, 'status_code', None) in (401, 403, 404):
                    stop_reason = 'API errors'
            in_flight -= bound
            spent += record['counted_usd']
            sent += 1
            with trials_path.open('a', encoding='utf-8') as f:
                f.write(w.dumps(record)+'\n')
            if record['status'] != 'completed' or sent % 10 == 0:
                print(w.dumps(dict(latest=case['id'], status=record['status'], spent_usd=round(spent, 4))), flush=True)
    try:
        await asyncio.gather(*(one(c) for c in remaining))
    finally:
        await client.close()

    recorded = {r['id'] for r in read_jsonl(trials_path)}
    unsent = [c['id'] for c in dispatch_order(cases) if c['id'] not in recorded]
    status = dict(updated_utc=w.utc(), budget_usd=budget, spent_usd=spent, stop_reason=stop_reason,
                  recorded=len(recorded), planned=len(cases), unsent=len(unsent),
                  complete_main_blocks=complete_main_blocks(cases, recorded),
                  unsent_by_stage=dict(collections.Counter(c['stage'] for c in cases if c['id'] in set(unsent))))
    (directory/'budget_status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    print(json.dumps(status, indent=2))
    if unsent and stop_reason == 'spending cap':
        print(f'\nSpending cap reached: ${spent:.4f} of ${budget:.2f} counted, {len(unsent)} requests not sent.\n'
              f'- Partial results: python -m experiments.round2_newdata analyze  (complete primary blocks only)\n'
              f'- To continue: python -m experiments.round2_newdata run --budget <higher cap>  (sends only the rest)')
    return status


def analyze(directory):
    """Analyze all responses, or, if some planned requests were never sent, only the complete primary blocks."""
    cases = read_jsonl(directory/'cases.jsonl')
    records = read_jsonl(directory/'trials.jsonl')
    recorded = {r['id'] for r in records}
    if len(recorded) == len(cases):
        return w.analyze(directory)
    blocks = set(complete_main_blocks(cases, recorded))
    keep = {c['id'] for c in cases if c['id'] in recorded and (c['stage'] != 'main' or c['block'] in blocks)}
    partial = directory/'partial'
    partial.mkdir(exist_ok=True)
    (partial/'cases.jsonl').write_text(''.join(w.dumps(c)+'\n' for c in cases if c['id'] in keep), encoding='utf-8')
    (partial/'trials.jsonl').write_text(''.join(w.dumps(r)+'\n' for r in records if r['id'] in keep), encoding='utf-8')
    print(f'Partial run: {len(recorded)}/{len(cases)} requests recorded; analyzing {len(blocks)}/18 complete '
          f'primary blocks plus recorded secondary requests in {partial}', file=sys.stderr)
    return w.analyze(partial)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'run', 'analyze'])
    parser.add_argument('--directory', type=Path, default=DIRECTORY)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--budget', type=float, help='override the manifest spending cap, in USD')
    args = parser.parse_args()
    if args.action == 'prepare': prepare(args.directory)
    elif args.action == 'run': asyncio.run(run(args.directory, args.workers, args.budget))
    else: analyze(args.directory)


if __name__ == '__main__':
    main()
