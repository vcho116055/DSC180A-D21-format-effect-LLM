"""Controlled record-lookup experiment. Preparation never makes API calls.

python experiments/week4_study.py prepare
python experiments/week4_study.py run --directory results/week4_lookup
python experiments/week4_study.py analyze --directory results/week4_lookup
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
import platform
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'gpt-5.6-luna'
SEED = 18020261021
FORMATS = ('csv', 'json', 'xml', 'txt')
SYSTEM = 'Answer the user task. Use only the information supplied in this request. No tools are available.'
DATASETS = {
    'titanic': ('titanic.csv', 'Kaggle Titanic', 'fare'),
    'redwine': ('redwine.csv', 'Red Wine Quality', 'density'),
    'medical': ('medicalcost.csv', 'Medical Cost Personal Datasets', 'charges'),
}


def dumps(x):
    return json.dumps(x, ensure_ascii=True, separators=(',', ':'))


def sha(x):
    return hashlib.sha256(x.encode('utf-8')).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def load_data():
    data = {}
    for dataset, (filename, _, _) in DATASETS.items():
        with (ROOT/'data'/filename).open(encoding='utf-8-sig', newline='') as f:
            raw = list(csv.DictReader(f))
        if dataset == 'titanic':
            rows = [dict(record_id=r['Passengerid'], age=r['Age'], sex=r['Sex'],
                         pclass=r['Pclass'], fare=r['Fare']) for r in raw[:891]]
        elif dataset == 'redwine':
            rows = [dict(record_id=str(i+1), fixed_acidity=r['fixed acidity'],
                         volatile_acidity=r['volatile acidity'], alcohol=r['alcohol'],
                         density=r['density']) for i, r in enumerate(raw)]
        else:
            rows = [dict(record_id=str(i+1), age=r['age'], sex=r['sex'], bmi=r['bmi'],
                         smoker=r['smoker'], region=r['region'], charges=r['charges'])
                    for i, r in enumerate(raw)]
        assert len({r['record_id'] for r in rows}) == len(rows)
        assert all(all(v != '' for v in r.values()) for r in rows)
        data[dataset] = rows
    return data


def serialize(rows, fmt):
    if fmt == 'csv':
        f = io.StringIO(newline='')
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        return f.getvalue()
    if fmt == 'json':
        return dumps(rows)
    if fmt == 'xml':
        root = ET.Element('records')
        for row in rows:
            record = ET.SubElement(root, 'record')
            for k, v in row.items():
                ET.SubElement(record, k).text = v
        return ET.tostring(root, encoding='unicode')
    if fmt == 'txt':
        return '\n'.join(' | '.join(f'{k}: {v}' for k, v in row.items()) for row in rows)
    raise ValueError(fmt)


def deserialize(text, fmt):
    if fmt == 'csv':
        return list(csv.DictReader(io.StringIO(text)))
    if fmt == 'json':
        return json.loads(text)
    if fmt == 'xml':
        return [{x.tag: x.text for x in r} for r in ET.fromstring(text)]
    return [dict(pair.split(': ', 1) for pair in line.split(' | ')) for line in text.splitlines()]


def select_targets(rows, field, rng):
    counts = collections.Counter(Decimal(r[field]) for r in rows)
    targets = []
    for part in range(3):
        choices = [i for i in range(part*len(rows)//3, (part+1)*len(rows)//3)
                   if counts[Decimal(rows[i][field])] == 1]
        if not choices:
            raise ValueError('No unique target value in one table third')
        targets.append(rng.choice(choices))
    return targets


def make_lookup_cases(dataset, rows, block, stage, rng, all_values, cues=('named','neutral')):
    field = DATASETS[dataset][2] if dataset in DATASETS else 'value'
    indices = select_targets(rows, field, rng)
    queries = [dict(record_id=rows[i]['record_id'], field=field, position=i) for i in indices]
    originals = {r['record_id']: r[field] for r in (rows[i] for i in indices)}
    changed = [r.copy() for r in rows]
    used = set(all_values)
    lo, hi = min(map(float, all_values)), max(map(float, all_values))
    for i in indices:
        while True:
            replacement = f'{rng.uniform(lo,hi):.5f}'
            if Decimal(replacement) not in {Decimal(x) for x in used}:
                break
        changed[i][field] = replacement
        used.add(replacement)
    assert sum(a != b for a,b in zip(rows, changed)) == 3
    missing = '999999'
    assert missing not in {r['record_id'] for r in rows}
    questions = queries + [dict(record_id=missing, field=field, position=None)]
    rng.shuffle(questions)
    cases = []
    versions = [('original', rows)] if stage == 'synthetic' else [('altered',changed),('original',rows)]
    for version, table_rows in versions:
        for cue in cues:
            title = (f'Table source: {DATASETS[dataset][1]}.' if cue == 'named'
                     else 'Table source: a collection of records.')
            expected = {q['record_id']: next((r[field] for r in table_rows
                        if r['record_id'] == q['record_id']), 'NOT_FOUND') for q in questions}
            for fmt in FORMATS:
                table = serialize(table_rows, fmt)
                assert deserialize(table, fmt) == table_rows
                prompt = (title+'\nLook up the requested cells in exactly the supplied table. '
                          'Copy each value; do not calculate, estimate, or replace it using outside knowledge. '
                          'If a record_id is absent, use NOT_FOUND. '
                          'Return only a JSON object mapping each requested record_id to its value as a string. '
                          'Do not include an explanation.\nRequested cells: '+dumps([
                              {k:v for k,v in q.items() if k != 'position'} for q in questions])+
                          '\nTABLE:\n'+table)
                cases.append(dict(id=f'{block}_{version}_{cue}_{fmt}',stage=stage,block=block,
                                  dataset=dataset,n_rows=len(rows),version=version,cue=cue,format=fmt,
                                  queries=questions,expected=expected,original_values=originals,
                                  table_sha256=sha(dumps(table_rows)),prompt=prompt,max_output_tokens=2048))
    return cases


def build_cases():
    rng = random.Random(SEED)
    data = load_data()
    cases = []
    for dataset, rows in data.items():
        field = DATASETS[dataset][2]
        for n in (40, 200):
            for rep in range(3):
                block = f'{dataset}_{n}_b{rep}'
                selected = rng.sample(rows,n)
                cases.extend(make_lookup_cases(dataset,selected,block,'main',rng,
                                               [r[field] for r in rows]))
    for rep in range(2):
        rows = rng.sample(data['titanic'],800)
        cases.extend(make_lookup_cases('titanic',rows,f'titanic_800_b{rep}','stress',rng,
                                       [r['fare'] for r in data['titanic']],cues=('named',)))
    for n in (40,200):
        for rep in range(3):
            rows = [dict(record_id=str(i+1), category=rng.choice(['A','B','C']),
                         value=f'{rng.uniform(0,1000):.5f}') for i in range(n)]
            cases.extend(make_lookup_cases('synthetic',rows,f'synthetic_{n}_b{rep}','synthetic',rng,
                                           [r['value'] for r in rows],cues=('neutral',)))
    # Secondary arithmetic is separate from lookup and never used to infer leakage by itself.
    with (ROOT/'data/titanic.csv').open(encoding='utf-8-sig',newline='') as f:
        raw = list(csv.DictReader(f))[:891]
    for n in (40,200,800):
        for dataset in ('titanic','synthetic'):
            if dataset == 'titanic':
                rows = [dict(record_id=r['Passengerid'],survived=r['2urvived']) for r in rng.sample(raw,n)]
            else:
                rows = [dict(record_id=str(i+1),survived=str(int(rng.random()<.4))) for i in range(n)]
            expected = {'n_rows':n,'n_positive':sum(int(r['survived']) for r in rows)}
            for fmt in ('csv','json'):
                prompt = ('Count exactly the supplied rows and how many have survived=1. '
                          'Return only JSON with integer n_rows and n_positive. Do not include an explanation.\nTABLE:\n'+serialize(rows,fmt))
                cases.append(dict(id=f'arithmetic_{dataset}_{n}_{fmt}',stage='arithmetic',dataset=dataset,
                                  block=f'arithmetic_{dataset}_{n}',n_rows=n,format=fmt,
                                  prompt=prompt,expected=expected,max_output_tokens=4096))
    for dataset in DATASETS:
        for rep in (0,1):
            base = next(c for c in cases if c['id']==f'{dataset}_40_b{rep}_original_named_csv')
            known = [q for q in base['queries'] if q['position'] is not None]
            prompt = (f'Dataset: {DATASETS[dataset][1]}. No table is provided. '
                      'For Titanic, record_id means the original PassengerId; for other datasets it means '
                      'the one-based row index in the local CSV, which may differ across versions. '
                      'If you know the requested value, return it; otherwise use UNKNOWN. '
                      'Return only a JSON object mapping each record_id to a value string. Requested cells: '+
                      dumps([{k:v for k,v in q.items() if k!='position'} for q in known]))
            cases.append(dict(id=f'prior_{dataset}_b{rep}',stage='prior',dataset=dataset,
                              block=base['block'],queries=known,expected=base['original_values'],
                              prompt=prompt,max_output_tokens=2048))
        for fmt in FORMATS:
            base = next(c for c in cases if c['id']==f'{dataset}_200_b0_altered_named_{fmt}')
            case = dict(base,id=base['id']+'_repeat',stage='repeat')
            cases.append(case)
    rng.shuffle(cases)
    return cases


def budget_bound(case):
    # Byte-based input bound plus generous message overhead, at upper context-tier rates.
    return ((len((SYSTEM+case['prompt']).encode('utf-8'))+2048)*.50 +
            case['max_output_tokens']*1.80)/1e6


def prepare(directory):
    if directory.exists() and any(directory.iterdir()):
        raise RuntimeError('Refusing to replace an existing experiment plan')
    directory.mkdir(parents=True,exist_ok=True)
    cases = build_cases()
    manifest = dict(created_utc=utc(),model=MODEL,reasoning_effort='medium',seed=SEED,
                    tools=[],store=False,temperature='provider default; not set',
                    requests=len(cases),stages=dict(collections.Counter(c['stage'] for c in cases)),
                    plan_sha256=sha('\n'.join(dumps(c) for c in cases)),
                    source_sha256={name:hashlib.sha256((ROOT/'data'/v[0]).read_bytes()).hexdigest()
                                   for name,v in DATASETS.items()},
                    reservation_upper_bound_usd=sum(map(budget_bound,cases)),budget_usd=4.25,
                    input_rate_per_million=.20,output_rate_per_million=1.20,
                    python=platform.python_version(),
                    note='Exploratory plan frozen locally before responses, not public preregistration.')
    assert len({c['id'] for c in cases}) == len(cases)
    assert manifest['reservation_upper_bound_usd'] < manifest['budget_usd']
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (directory/'cases.jsonl').write_text('\n'.join(dumps(c) for c in cases)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2))


def numeric_equal(a,b):
    if isinstance(a,bool) or not isinstance(a,(str,int,float)):
        return False
    if str(a).strip()==str(b).strip():
        return True
    try:
        return Decimal(str(a).strip()).is_finite() and Decimal(str(a).strip())==Decimal(str(b).strip())
    except InvalidOperation:
        return False


def score(case, output, status):
    try:
        parsed=json.loads(output)
        if not isinstance(parsed,dict):
            raise ValueError('not object')
    except (ValueError,TypeError):
        parsed={}
    complete=status=='completed'
    items=[]
    for key,expected in case['expected'].items():
        got=parsed.get(key)
        correct=complete and numeric_equal(got,expected)
        original=case.get('original_values',{}).get(key)
        reverted=(case.get('version')=='altered' and not correct and original is not None
                  and complete and numeric_equal(got,original))
        items.append(dict(record_id=key,expected=expected,actual=got,correct=bool(correct),
                          original_value_reversion=bool(reverted),absent=expected=='NOT_FOUND',
                          literal_match=complete and isinstance(got,str) and got==str(expected)))
    return dict(parsed=parsed,valid_json_object=isinstance(parsed,dict) and bool(parsed),
                exact_keys=set(parsed)==set(case['expected']),
                string_values=bool(parsed) and all(isinstance(v,str) for v in parsed.values()),
                all_correct=all(i['correct'] for i in items),items=items)


async def run(directory, workers=4):
    from dotenv import dotenv_values
    import openai
    from openai import AsyncOpenAI
    config=dotenv_values(ROOT/'.env',encoding='utf-8-sig')
    if not config.get('OPENAI_API_KEY'):
        raise RuntimeError('OPENAI_API_KEY not configured')
    manifest=json.loads((directory/'manifest.json').read_text())
    cases=[json.loads(x) for x in (directory/'cases.jsonl').read_text().splitlines()]
    assert sha('\n'.join(dumps(c) for c in cases))==manifest['plan_sha256']
    trials_path=directory/'trials.jsonl'
    previous=[json.loads(x) for x in trials_path.read_text().splitlines()] if trials_path.exists() else []
    done={r['id'] for r in previous}
    # Started requests are never silently resent after an interruption.
    starts_path=directory/'started.jsonl'
    starts=[json.loads(x) for x in starts_path.read_text().splitlines()] if starts_path.exists() else []
    started={r['id'] for r in starts}
    abandoned=started-done
    if abandoned:
        raise RuntimeError(f'{len(abandoned)} started requests lack a response; inspect before resuming')
    remaining=[c for c in cases if c['id'] not in done]
    reserved=sum(r['reserved_max_usd'] for r in starts)
    client=AsyncOpenAI(api_key=config['OPENAI_API_KEY'],max_retries=0,timeout=120)
    sem=asyncio.Semaphore(workers)
    completed=len(previous)
    errors=0
    stop=False
    (directory/'runtime.json').write_text(json.dumps(dict(started_utc=utc(),sdk=openai.__version__,
                    python=sys.version,workers=workers),indent=2),encoding='utf-8')

    async def one(case):
        nonlocal reserved,completed,errors,stop
        async with sem:
            if stop:
                return
            bound=budget_bound(case)
            if reserved+bound>manifest['budget_usd']:
                stop=True
                return
            reserved+=bound
            with starts_path.open('a',encoding='utf-8') as f:
                f.write(dumps(dict(id=case['id'],started_utc=utc(),reserved_max_usd=bound))+'\n')
            begin=time.monotonic()
            record=dict(id=case['id'],started_utc=utc(),prompt_sha256=sha(case['prompt']))
            try:
                response=await client.responses.create(model=MODEL,instructions=SYSTEM,
                    input=[{'role':'user','content':case['prompt']}],tools=[],store=False,
                    reasoning={'effort':'medium'},max_output_tokens=case['max_output_tokens'])
                usage=response.usage.model_dump()
                record.update(response_id=response.id,returned_model=response.model,status=response.status,
                    output=response.output_text,usage=usage,elapsed_seconds=round(time.monotonic()-begin,3),
                    incomplete_details=response.incomplete_details.model_dump() if response.incomplete_details else None,
                    estimated_usd=(usage['input_tokens']*.20+usage['output_tokens']*1.20)/1e6)
                record['score']=score(case,response.output_text,response.status)
                if response.model!=MODEL:
                    record['model_mismatch']=True
                    stop=True
            except Exception as exc:
                record.update(status='api_error',error_type=type(exc).__name__,
                              http_status=getattr(exc,'status_code',None),elapsed_seconds=round(time.monotonic()-begin,3))
                errors+=1
                if errors>=3 or getattr(exc,'status_code',None) in (401,403,404):
                    stop=True
            with trials_path.open('a',encoding='utf-8') as f:
                f.write(dumps(record)+'\n')
            completed+=1
            if completed%10==0 or record['status']!='completed':
                print(dumps(dict(completed=completed,total=len(cases),latest=case['id'],status=record['status'])),flush=True)
    try:
        await asyncio.gather(*(one(c) for c in remaining))
    finally:
        await client.close()
    print(dumps(dict(completed=completed,errors=errors,stopped=stop,reserved_usd=reserved)),flush=True)


def analyze(directory):
    import numpy as np
    cases={c['id']:c for c in map(json.loads,(directory/'cases.jsonl').read_text().splitlines())}
    records=[json.loads(x) for x in (directory/'trials.jsonl').read_text().splitlines()]
    assert len({r['id'] for r in records})==len(records)
    joined=[]
    cells=[]
    for r in records:
        c=cases[r['id']]
        assert sha(c['prompt'])==r['prompt_sha256']
        s=score(c,r.get('output',''),r['status'])
        if 'score' in r:
            assert s==r['score']
        row={**{k:c.get(k) for k in ('id','stage','block','dataset','n_rows','format','cue','version')},
             'status':r['status'],'all_correct':s['all_correct'],
             'input_tokens':r.get('usage',{}).get('input_tokens'),
             'output_tokens':r.get('usage',{}).get('output_tokens')}
        joined.append(row)
        for cell in s['items']:
            cells.append({**row,**cell})
    summary=dict(planned=len(cases),requests=len(records),
                 status=dict(collections.Counter(r['status'] for r in records)),
                 returned_models=sorted({r.get('returned_model','unknown') for r in records}),
                 stages={},primary_by_format={},primary_by_dataset={},primary_by_size={},primary_by_cue={},
                 estimated_usd=sum(r.get('estimated_usd',0) for r in records))
    for stage in sorted({c['stage'] for c in cases.values()}):
        stage_rows=[r for r in joined if r['stage']==stage]
        stage_cells=[c for c in cells if c['stage']==stage and not c['absent']]
        summary['stages'][stage]=dict(requests=len(stage_rows),all_correct=sum(r['all_correct'] for r in stage_rows),
                                      cells=len(stage_cells),correct=sum(c['correct'] for c in stage_cells))
    primary=[c for c in cells if c['stage']=='main' and not c['absent']]
    for column in ('format','dataset','n_rows','cue','version'):
        groups={}
        for value in sorted({c[column] for c in primary}):
            subset=[c for c in primary if c[column]==value]
            altered=[c for c in subset if c['version']=='altered']
            groups[str(value)]=dict(correct=sum(c['correct'] for c in subset),n=len(subset),
                altered_correct=sum(c['correct'] for c in altered),altered_n=len(altered),
                reversions=sum(c['original_value_reversion'] for c in altered))
        summary['primary_by_'+('size' if column=='n_rows' else column)]=groups
    absent=[c for c in cells if c['absent']]
    summary['absent_records']=dict(correct=sum(c['correct'] for c in absent),n=len(absent))
    # Paired differences cluster on a sampled table, not individual cells or calls.
    # Bootstrap within dataset x table-size strata, with three sampled tables per stratum.
    blockinfo={c['block']:(c['dataset'],c['n_rows']) for c in primary}
    contrasts={}
    comparisons=[('json_minus_csv','format','json','csv'),('xml_minus_csv','format','xml','csv'),
                 ('txt_minus_csv','format','txt','csv'),('named_minus_neutral','cue','named','neutral'),
                 ('altered_minus_original','version','altered','original')]
    rng=np.random.default_rng(SEED)
    for name,column,a,b in comparisons:
        differences={}
        for block in blockinfo:
            aa=[c['correct'] for c in primary if c['block']==block and c[column]==a]
            bb=[c['correct'] for c in primary if c['block']==block and c[column]==b]
            if aa and bb:
                differences[block]=float(np.mean(aa)-np.mean(bb))
        strata=collections.defaultdict(list)
        for block,difference in differences.items():
            strata[blockinfo[block]].append(difference)
        draws=np.zeros(10000)
        for values in strata.values():
            draws+=rng.choice(values,size=(10000,len(values)),replace=True).sum(axis=1)
        draws/=len(differences)
        contrasts[name]=dict(difference_pp=100*float(np.mean(list(differences.values()))),
                            descriptive_bootstrap_95_percentile_pp=[100*float(v) for v in np.quantile(draws,[.025,.975])],
                            blocks=len(differences),block_differences=differences,
                            warning='Small exploratory sample; overlapping source rows; intervals can degenerate at ceiling.')
    summary['paired_contrasts']=contrasts
    (directory/'analysis.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    for filename,rows in [('scored_requests.csv',joined),('scored_cells.csv',cells)]:
        with (directory/filename).open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader();writer.writerows(rows)
    print(json.dumps(summary,indent=2))
    return summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','run','analyze'])
    parser.add_argument('--directory',type=Path,default=ROOT/'results/week4_lookup')
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    if args.action=='prepare': prepare(args.directory)
    elif args.action=='run': asyncio.run(run(args.directory,args.workers))
    else: analyze(args.directory)


if __name__=='__main__':
    main()
