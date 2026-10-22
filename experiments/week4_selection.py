"""Round 4 preparation, execution, and analysis. Only 'run' calls the API."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter, defaultdict
from decimal import Decimal
from itertools import combinations
import hashlib
import json
from pathlib import Path
import platform
import random
import shutil
import subprocess
import time

from experiments.week4_study import (
    ROOT, MODEL, FORMATS, SYSTEM, DATASETS, dumps, sha, utc,
    load_data, serialize, deserialize, score, numeric_equal,
)

DIRECTORY = ROOT / 'results/week4_selection'
SEED = 18020261023
CALIBRATION_SEED = 18020261024
CAP = 13.0


def matching(rows, criteria):
    return [r for r in rows if all(r[k] == v for k, v in criteria.items())]


def selectors(rows, field):
    """Find unique conjunctions whose every component is necessary."""
    columns = [k for k in rows[0] if k not in ('record_id', 'link_id', field)]
    value_counts = Counter(Decimal(r[field]) for r in rows)
    result = defaultdict(list)
    for width in (2, 3):
        for cols in combinations(columns, width):
            complete = Counter(tuple(r[k] for k in cols) for r in rows)
            partial = [Counter(tuple(r[k] for k in cols if k != drop) for r in rows)
                       for drop in cols]
            for i, row in enumerate(rows):
                if value_counts[Decimal(row[field])] != 1:
                    continue
                if complete[tuple(row[k] for k in cols)] != 1:
                    continue
                if all(counts[tuple(row[k] for k in cols if k != drop)] >= 2
                       for drop, counts in zip(cols, partial)):
                    result[i].append({k: row[k] for k in cols})
    return result


def make_block(dataset, source, n, block_id, rng):
    field = DATASETS[dataset][2] if dataset in DATASETS else 'value'
    for attempt in range(1, 51):
        if dataset == 'synthetic':
            rows = [dict(record_id=str(i + 1), group_a=str(rng.randrange(15)),
                         group_b=str(rng.randrange(8)), group_c=str(rng.randrange(4)),
                         value=f'{rng.uniform(0, 1000):.5f}') for i in range(n)]
        else:
            rows = [r.copy() for r in rng.sample(source, n)]
        available = selectors(rows, field)
        thirds = [[i for i in available if part*n//3 <= i < (part+1)*n//3]
                  for part in range(3)]
        if all(thirds):
            break
    else:
        raise ValueError(f'Unable to construct {block_id}')
    indices = [rng.choice(part) for part in thirds]
    queries = []
    for j, i in enumerate(indices):
        queries.append(dict(id=f'q{j+1}', criteria=rng.choice(available[i]),
                            record_id=rows[i]['record_id'], position=i))
    cols = tuple(queries[0]['criteria'])
    for _ in range(5000):
        absent = {k: rng.choice(rows)[k] for k in cols}
        if not matching(rows, absent):
            break
    else:
        raise ValueError('Cannot construct absent conjunction')
    queries.append(dict(id='q4', criteria=absent, record_id=None, position=None))
    rng.shuffle(queries)
    keys = [f'L{i+1:05d}' for i in range(n)]
    rng.shuffle(keys)
    rows = [dict(link_id=key, **row) for key, row in zip(keys, rows)]
    altered = [r.copy() for r in rows]
    all_values = [r[field] for r in (source if dataset != 'synthetic' else rows)]
    used = {Decimal(v) for v in all_values}
    lo, hi = min(map(float, all_values)), max(map(float, all_values))
    for i in indices:
        while True:
            value = f'{rng.uniform(lo, hi):.5f}'
            if Decimal(value) not in used:
                break
        altered[i][field] = value
        used.add(Decimal(value))
    order = list(range(n))
    rng.shuffle(order)
    return dict(id=block_id, dataset=dataset, field=field, n_rows=n,
                attempts=attempt, original=rows, altered=altered,
                value_order=order, queries=queries)


def render_tables(block, version, task, fmt):
    rows, field = block[version], block['field']
    if task != 'join':
        return 'TABLE:\n' + serialize(rows, fmt)
    records = [{k: v for k, v in r.items() if k != field} for r in rows]
    values = [dict(link_id=rows[i]['link_id'], **{field: rows[i][field]})
              for i in block['value_order']]
    return 'RECORDS_TABLE:\n' + serialize(records, fmt) + '\nVALUES_TABLE:\n' + serialize(values, fmt)


def decode_tables(case):
    if case['task'] != 'join':
        return deserialize(case['prompt'].split('TABLE:\n', 1)[1], case['format']), None
    a, b = case['prompt'].split('RECORDS_TABLE:\n', 1)[1].split('\nVALUES_TABLE:\n', 1)
    return deserialize(a, case['format']), deserialize(b, case['format'])


def reconstruct(case):
    rows, values = decode_tables(case)
    index = {r['link_id']: r[case['field']] for r in values} if values is not None else None
    if values is not None:
        assert len(index) == len(rows) == len(values) == case['n_rows']
        assert set(index) == {r['link_id'] for r in rows}
    answer = {}
    for q in case['queries']:
        criteria = {'record_id': q['record_id']} if case['task'] == 'direct' else q['criteria']
        selected = matching(rows, criteria) if q['record_id'] is not None or case['task'] != 'direct' else []
        assert len(selected) == (q['position'] is not None)
        answer[q['id']] = ('NOT_FOUND' if not selected else
                          index[selected[0]['link_id']] if index is not None else selected[0][case['field']])
    return answer


def cases_for(block, stage, tasks=('attribute', 'join'), cues=('named', 'neutral'),
              versions=('original', 'altered')):
    cases = []
    field = block['field']
    original = {q['id']: block['original'][q['position']][field]
                for q in block['queries'] if q['position'] is not None}
    for task in tasks:
        for version in versions:
            expected = {q['id']: block[version][q['position']][field]
                        if q['position'] is not None else 'NOT_FOUND' for q in block['queries']}
            for cue in cues:
                title = (f"Table source: {DATASETS[block['dataset']][1]}." if cue == 'named'
                         else 'Table source: a collection of records.')
                question = [dict(query_id=q['id'], criteria=(
                    {'record_id': q['record_id'] or '999999'} if task == 'direct' else q['criteria']))
                            for q in block['queries']]
                operation = (f'Find the row matching ALL criteria, then use its link_id to copy {field} '
                             'from VALUES_TABLE.' if task == 'join' else
                             f'Find the row matching ALL criteria and copy its {field}.')
                for fmt in FORMATS:
                    prompt = (title + '\n' + operation +
                              ' Match field values exactly as written. Use only the supplied tables. '
                              'If no row matches all criteria, use NOT_FOUND. '
                              'Return only JSON mapping each query_id to a value string, with exactly the requested keys. '
                              'Do not calculate or include an explanation.\nQUERIES:\n' + dumps(question) + '\n' +
                              render_tables(block, version, task, fmt))
                    c = dict(id=f"{stage}_{block['id']}_{task}_{version}_{cue}_{fmt}",
                             stage=stage, block=block['id'], dataset=block['dataset'], task=task,
                             version=version, cue=cue, format=fmt, n_rows=block['n_rows'], field=field,
                             queries=block['queries'], expected=expected, original_values=original,
                             max_output_tokens=4096, prompt=prompt)
                    assert reconstruct(c) == expected
                    cases.append(c)
    return cases


def build(data, calibration=False):
    rng = random.Random(CALIBRATION_SEED if calibration else SEED)
    blocks, cases = [], []
    for dataset in (*DATASETS, 'synthetic'):
        sizes, reps = ((80,), 1) if calibration else ((80, 400), 2)
        for n in sizes:
            for rep in range(reps):
                block = make_block(dataset, data.get(dataset), n, f'{dataset}_{n}_b{rep}', rng)
                blocks.append({k: block[k] for k in ('id', 'dataset', 'n_rows', 'attempts')})
                if calibration:
                    cases.extend(cases_for(block, 'calibration', cues=('neutral',), versions=('altered',)))
                else:
                    stage = 'primary' if dataset != 'synthetic' else 'synthetic'
                    cases.extend(cases_for(block, stage, cues=('named', 'neutral') if stage == 'primary' else ('neutral',)))
                    if stage == 'primary':
                        cases.extend(cases_for(block, 'baseline', tasks=('direct',), cues=('neutral',), versions=('altered',)))
                        if n == 400 and rep == 0:
                            for c in cases_for(block, 'repeat', cues=('named',), versions=('altered',)):
                                cases.append(c)
    rng.shuffle(cases)
    assert len(cases) == (32 if calibration else 520)
    return cases, blocks


def bound(case):
    return ((len((SYSTEM + case['prompt']).encode()) + 2048)*.50 + case['max_output_tokens']*1.80)/1e6


def evaluate(case, output, status):
    result = score(case, output, status)
    result['schema_correct'] = result['valid_json_object'] and result['exact_keys'] and result['string_values']
    result['strict_correct'] = result['all_correct'] and result['schema_correct']
    return result


def prepare():
    if DIRECTORY.exists() and any(DIRECTORY.iterdir()):
        raise RuntimeError('Refusing to overwrite an existing experiment')
    DIRECTORY.mkdir(exist_ok=True)
    data = load_data()
    calibration, calibration_blocks = build(data, True)
    main, blocks = build(data)
    manifest = dict(created_utc=utc(), model=MODEL, reasoning_effort='medium',
                    system=SYSTEM, system_sha256=sha(SYSTEM), seed=SEED, calibration_seed=CALIBRATION_SEED,
                    main_requests=len(main), calibration_requests=len(calibration),
                    blocks=blocks, calibration_blocks=calibration_blocks,
                    source_sha256={k: hashlib.sha256((ROOT/'data'/v[0]).read_bytes()).hexdigest() for k,v in DATASETS.items()},
                    plan_sha256={k: sha('\n'.join(dumps(c) for c in cc)) for k,cc in [('main',main),('calibration',calibration)]},
                    reservation_upper_bound_usd=sum(map(bound, main+calibration)), budget_usd=CAP,
                    git_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    git_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)),
                    python=platform.python_version(), tools=[],store=False,temperature='not set',
                    protocol_sha256=sha((ROOT/'experiments/week4_selection_protocol.md').read_text(encoding='utf-8')))
    assert manifest['reservation_upper_bound_usd'] < CAP, manifest['reservation_upper_bound_usd']
    for name, cases in [('main',main),('calibration',calibration)]:
        (DIRECTORY/(name+'_cases.jsonl')).write_text('\n'.join(dumps(c) for c in cases)+'\n',encoding='utf-8')
    (DIRECTORY/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    snapshot = DIRECTORY/'source_snapshot'
    snapshot.mkdir()
    for path in [ROOT/'experiments/week4_selection.py',ROOT/'experiments/week4_selection_protocol.md',
                 ROOT/'experiments/test_week4_selection.py', ROOT/'experiments/week4_study.py',
                 ROOT/'requirements-experiments.txt']:
        shutil.copyfile(path, snapshot/path.name)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('blocks','calibration_blocks')},indent=2))


def read_cases(batch):
    manifest = json.loads((DIRECTORY/'manifest.json').read_text())
    cases = [json.loads(x) for x in (DIRECTORY/(batch+'_cases.jsonl')).read_text().splitlines()]
    assert sha('\n'.join(dumps(c) for c in cases)) == manifest['plan_sha256'][batch]
    return cases


def gate():
    path = DIRECTORY/'calibration_trials.jsonl'
    if not path.exists():
        return False
    rr = [json.loads(x) for x in path.read_text().splitlines()]
    cc = {c['id']:c for c in read_cases('calibration')}
    good = len(rr) == len(cc) and {r['id'] for r in rr} == set(cc)
    good = good and all(r['status']=='completed' and r['returned_model']==MODEL and r['score']['schema_correct'] for r in rr)
    good = good and sum(r['score']['strict_correct'] for r in rr) >= 30
    good = good and all(sum(r['score']['strict_correct'] for r in rr if cc[r['id']]['task']==task)>=15 for task in ('attribute','join'))
    return bool(good)


async def run(batch):
    from dotenv import dotenv_values
    import openai
    from openai import AsyncOpenAI
    if batch=='main' and not gate():
        raise RuntimeError('Calibration gate did not pass; no main calls dispatched')
    cases = read_cases(batch)
    path = DIRECTORY/(batch+'_trials.jsonl')
    starts = DIRECTORY/(batch+'_started.jsonl')
    if path.exists() or starts.exists():
        raise RuntimeError('Batch already started; inspect before any continuation')
    env = dotenv_values(ROOT/'.env',encoding='utf-8-sig')
    if not env.get('OPENAI_API_KEY'):
        raise RuntimeError('Missing API key')
    client = AsyncOpenAI(api_key=env['OPENAI_API_KEY'],max_retries=0,timeout=120)
    prior = read_cases('calibration') if batch=='main' else []
    reserved = sum(map(bound, prior))
    sem = asyncio.Semaphore(4)
    errors, finished, stop = 0, 0, False
    runtime = dict(started_utc=utc(),sdk=openai.__version__,python=platform.python_version(),
                   workers=4,model=MODEL,batch=batch)
    (DIRECTORY/(batch+'_runtime.json')).write_text(json.dumps(runtime,indent=2),encoding='utf-8')
    async def one(c):
        nonlocal reserved,errors,finished,stop
        async with sem:
            if stop:
                return
            reservation = bound(c)
            if reserved+reservation > CAP:
                stop=True
                return
            reserved+=reservation
            with starts.open('a',encoding='utf-8') as f:
                f.write(dumps(dict(id=c['id'],started_utc=utc(),reserved_max_usd=reservation))+'\n')
            begin=time.monotonic()
            r=dict(id=c['id'],started_utc=utc(),prompt_sha256=sha(c['prompt']),instructions_sha256=sha(SYSTEM))
            try:
                response=await client.responses.create(model=MODEL,instructions=SYSTEM,
                    input=[dict(role='user',content=c['prompt'])],reasoning={'effort':'medium'},
                    max_output_tokens=c['max_output_tokens'],tools=[],store=False)
                usage=response.usage.model_dump()
                r.update(status=response.status,returned_model=response.model,response_id=response.id,
                         output=response.output_text,usage=usage,score=evaluate(c,response.output_text,response.status),
                         incomplete_details=response.incomplete_details.model_dump() if response.incomplete_details else None,
                         estimated_usd=(usage['input_tokens']*.20+usage['output_tokens']*1.20)/1e6)
                if response.model != MODEL:
                    stop=True
            except Exception as exc:
                r.update(status='api_error',error_type=type(exc).__name__,http_status=getattr(exc,'status_code',None),
                         output='',score=evaluate(c,'','api_error'))
                errors+=1
                if errors>=3 or getattr(exc,'status_code',None) in (401,403,404):
                    stop=True
            r['elapsed_seconds']=round(time.monotonic()-begin,3)
            with path.open('a',encoding='utf-8') as f:
                f.write(dumps(r)+'\n')
            finished+=1
            if finished%20==0 or r['status']!='completed':
                print(dumps(dict(batch=batch,finished=finished,total=len(cases),status=r['status'])),flush=True)
    try:
        await asyncio.gather(*(one(c) for c in cases))
    finally:
        await client.close()
    print(dumps(dict(batch=batch,finished=finished,stopped=stop,errors=errors,gate=gate())),flush=True)


def analyze():
    import numpy as np
    summary = dict(model=MODEL, calibration_gate=gate(), batches={},primary={},secondary={},contrasts={})
    joined=[]
    for batch in ('calibration','main'):
        path=DIRECTORY/(batch+'_trials.jsonl')
        if not path.exists():
            continue
        cc={c['id']:c for c in read_cases(batch)}
        rr=[json.loads(x) for x in path.read_text().splitlines()]
        assert len({r['id'] for r in rr})==len(rr)
        for r in rr:
            c=cc[r['id']]
            assert reconstruct(c)==c['expected']
            assert sha(c['prompt'])==r['prompt_sha256'] and sha(SYSTEM)==r['instructions_sha256']
            assert evaluate(c,r['output'],r['status'])==r['score']
            if r['status']!='api_error':
                assert r['returned_model']==MODEL
            joined.append((c,r))
        summary['batches'][batch]=dict(planned=len(cc),recorded=len(rr),status=dict(Counter(r['status'] for r in rr)),
              strict_correct=sum(r['score']['strict_correct'] for r in rr),estimated_usd=sum(r.get('estimated_usd',0) for r in rr))
    def aggregate(pairs):
        present=[i for c,r in pairs for i in r['score']['items'] if not i['absent']]
        absent=[i for c,r in pairs for i in r['score']['items'] if i['absent']]
        changed=[i for c,r in pairs if c['version']=='altered' for i in r['score']['items'] if not i['absent']]
        return dict(requests=len(pairs),strict_correct=sum(r['score']['strict_correct'] for c,r in pairs),
                    present_n=len(present),present_correct=sum(i['correct'] for i in present),
                    altered_n=len(changed),altered_correct=sum(i['correct'] for i in changed),
                    absent_n=len(absent),absent_correct=sum(i['correct'] for i in absent),
                    reversions=sum(i['original_value_reversion'] for i in changed),
                    schema_correct=sum(r['score']['schema_correct'] for c,r in pairs))
    primary=[p for p in joined if p[0]['stage']=='primary']
    summary['primary_total']=aggregate(primary)
    for task in ('attribute','join'):
        summary['primary'][task]={fmt:aggregate([p for p in primary if p[0]['task']==task and p[0]['format']==fmt]) for fmt in FORMATS}
    for stage in ('calibration','synthetic','baseline','repeat'):
        summary['secondary'][stage]=aggregate([p for p in joined if p[0]['stage']==stage])
    for column in ('dataset','n_rows','cue','version'):
        summary['by_'+column]={str(v):aggregate([p for p in primary if p[0][column]==v]) for v in sorted({c[column] for c,r in primary})}
    rng=np.random.default_rng(SEED)
    for name,column,a,b in [('join_minus_attribute','task','join','attribute'),
                           ('json_minus_csv','format','json','csv'),('xml_minus_csv','format','xml','csv'),
                           ('txt_minus_csv','format','txt','csv'),('named_minus_neutral','cue','named','neutral'),
                           ('altered_minus_original','version','altered','original')]:
        strata=defaultdict(list)
        for block in sorted({c['block'] for c,r in primary}):
            pp=[p for p in primary if p[0]['block']==block]
            def accuracy(value):
                items=[i['correct'] for c,r in pp if c[column]==value for i in r['score']['items'] if not i['absent']]
                return np.mean(items)
            strata[(pp[0][0]['dataset'],pp[0][0]['n_rows'])].append(float(accuracy(a)-accuracy(b)))
        if strata:
            draws=sum((rng.choice(v,size=(10000,len(v)),replace=True).sum(axis=1) for v in strata.values()))/12
            values=[x for v in strata.values() for x in v]
            summary['contrasts'][name]=dict(difference_pp=100*float(np.mean(values)),
                descriptive_95_percentile_pp=[100*float(x) for x in np.quantile(draws,[.025,.975])],blocks=len(values))
    failures=[]
    error_categories=Counter()
    for c,r in joined:
        if not r['score']['strict_correct']:
            failures.append(dict(id=c['id'],stage=c['stage'],task=c['task'],expected=c['expected'],
                                 actual=r['score']['parsed'],status=r['status']))
        rows, values=decode_tables(c)
        supplied=[x[c['field']] for x in (values if values is not None else rows)]
        for i in r['score']['items']:
            if i['correct']:
                continue
            if r['status']!='completed': category='incomplete_or_api_error'
            elif not r['score']['valid_json_object'] or i['record_id'] not in r['score']['parsed']: category='invalid_or_missing'
            elif i['original_value_reversion']: category='replaced_original_value'
            elif i['actual']=='NOT_FOUND': category='false_not_found'
            elif i['absent']: category='answer_for_absent_query'
            elif any(numeric_equal(i['actual'],v) for v in supplied): category='other_supplied_value'
            else: category='other_value'
            error_categories[category]+=1
    summary['failures']=failures
    summary['error_categories']=dict(error_categories)
    (DIRECTORY/'analysis.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('prepare','run','analyze'))
    parser.add_argument('--batch',choices=('calibration','main'),default='calibration')
    args=parser.parse_args()
    if args.action=='prepare': prepare()
    elif args.action=='run': asyncio.run(run(args.batch))
    else: analyze()
