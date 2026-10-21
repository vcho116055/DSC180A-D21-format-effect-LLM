"""Small, reproducible text-only pilot. Run with --run; otherwise validate locally."""
import argparse
import csv
import hashlib
import io
import json
import platform
import random
import secrets
import subprocess
import time
from datetime import datetime, timezone
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = 'gpt-5.6-luna'
MAX_OUTPUT = 8000
BUDGET = 0.50
SYSTEM = 'Answer the task using only the information available in this request. Do not use tools.'


def environment_metadata():
    """Record runtime provenance without reading credentials or storing local paths."""
    def git_output(*args):
        try:
            result = subprocess.run(
                ['git', '-C', str(ROOT), *args], check=True,
                capture_output=True, text=True, timeout=10)
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None

    status = git_output('status', '--porcelain', '--untracked-files=normal')
    lockfile = ROOT / 'uv.lock'
    return dict(
        python_version=platform.python_version(),
        python_implementation=platform.python_implementation(),
        dependency_versions=dict(sorted(
            (dist.metadata['Name'], dist.version)
            for dist in distributions() if dist.metadata['Name'])),
        os=dict(system=platform.system(), release=platform.release(),
                version=platform.version(), machine=platform.machine()),
        git_commit=git_output('rev-parse', 'HEAD'),
        git_working_tree_dirty=None if status is None else bool(status),
        uv_lock_sha256=(hashlib.sha256(lockfile.read_bytes()).hexdigest()
                        if lockfile.is_file() else None))


def table_case(name, rows, fmt, repeat=1, description='A table of records.'):
    if fmt == 'csv':
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=['record_id', 'survived'], lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        table = stream.getvalue()
    else:
        table = json.dumps(rows, separators=(',', ':'))
    prompt = (description + '\nEach row is one record. survived is a binary integer: 0 or 1. '
              'Calculate using exactly the supplied rows, not a larger dataset. '
              'Return only a JSON object with n_rows, n_positive (count of survived=1), '
              'and fraction_positive (n_positive/n_rows, rounded to six decimal places). '
              'Do not include an explanation.\nTABLE:\n' + table)
    n = len(rows)
    count = sum(r['survived'] for r in rows)
    return dict(id=f'{name}_{fmt}_r{repeat}', group=name, format=fmt, repeat=repeat,
                prompt=prompt, expected=dict(n_rows=n, n_positive=count,
                                            fraction_positive=round(count/n, 6)))


def make_cases():
    rng = random.Random(1802026)
    cases = []
    for n in (20, 100):
        rows = [dict(record_id=i+1, survived=int(rng.random() < .43)) for i in range(n)]
        for fmt in ('csv', 'json'):
            cases.append(table_case(f'synthetic_{n}', rows, fmt))
    with (ROOT/'data/titanic.csv').open(newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        raw = list(reader)
    label = header.index('2urvived')
    pid = header.index('Passengerid')
    full = [dict(record_id=int(r[pid]), survived=int(r[label])) for r in raw[:891]]
    assert len(full) == 891 and sum(r['survived'] for r in full) == 342
    small = rng.sample(full, 100)
    changed = [r.copy() for r in small]
    flip = rng.sample([i for i,r in enumerate(changed) if r['survived'] == 0], 20)
    for i in flip:
        changed[i]['survived'] = 1
    description = 'This table contains records derived from the Kaggle Titanic dataset.'
    for name, rows in [('titanic_100_original',small), ('titanic_100_modified',changed)]:
        for fmt in ('csv','json'):
            for repeat in (1,2):
                cases.append(table_case(name,rows,fmt,repeat,description))
    subset = rng.sample(full,802)
    for name, rows in [('titanic_891',full),('titanic_802',subset)]:
        for fmt in ('csv','json'):
            cases.append(table_case(name,rows,fmt,description=description))
    rng.shuffle(cases)
    return cases


def score(text, expected):
    try:
        parsed = json.loads(text)
        counts = all(type(parsed.get(k)) is int and parsed[k] == expected[k]
                     for k in ('n_rows','n_positive'))
        fraction = isinstance(parsed.get('fraction_positive'), (int,float)) and abs(
            parsed['fraction_positive']-expected['fraction_positive']) <= 0.000001
        return dict(parsed=parsed, counts_correct=counts, fraction_correct=fraction,
                    all_correct=bool(counts and fraction))
    except (ValueError, TypeError, AttributeError):
        return dict(parse_error=True,all_correct=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    args=parser.parse_args()
    cases=make_cases()
    print(json.dumps({'table_trials':len(cases),'truth':{c['id']:c['expected'] for c in cases}}),flush=True)
    if not args.run:
        return
    from dotenv import dotenv_values
    from openai import OpenAI

    config=dotenv_values(ROOT/'.env',encoding='utf-8-sig')
    if not config.get('OPENAI_API_KEY'):
        raise SystemExit('Missing OPENAI_API_KEY')
    if config.get('OPENAI_MODEL',MODEL) != MODEL:
        raise SystemExit('Configured model does not match the authorized model')
    client=OpenAI(api_key=config['OPENAI_API_KEY'],max_retries=0,timeout=90)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out=ROOT/'results'/f'{MODEL}_pilot_{stamp}'
    out.mkdir(parents=True,exist_ok=False)
    records=[]
    reserved=0.0
    metadata=dict(model=MODEL,reasoning_effort='medium',max_output_tokens=MAX_OUTPUT,
                  environment=environment_metadata(),
                  tools=[],store=False,seed_for_tables=1802026,budget_usd=BUDGET,
                  source_sha256=hashlib.sha256((ROOT/'data/titanic.csv').read_bytes()).hexdigest(),
                  source_note='First 891 local rows; provenance unverified; only ID and binary label included.',
                  rates_per_million=dict(input=.20,output=1.20),
                  budget_reservation_rates=dict(input=.40,output=1.80),
                  caveat='Exploratory, not preregistered. Token billing estimates exclude taxes.')
    (out/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')

    def call(case, messages=None):
        nonlocal reserved
        messages=messages or [{'role':'user','content':case['prompt']}]
        # UTF-8 byte count is a conservative input-token bound for these plain-text prompts.
        bound=(len((SYSTEM+json.dumps(messages,ensure_ascii=False)).encode('utf-8'))+2048)*.40/1e6+MAX_OUTPUT*1.80/1e6
        if reserved+bound > BUDGET:
            raise RuntimeError('Pilot budget reservation would exceed $0.50')
        reserved+=bound
        record=dict(case,request_messages=messages,reserved_max_cost_usd=bound)
        start=time.monotonic()
        try:
            response=client.responses.create(model=MODEL,instructions=SYSTEM,input=messages,
                        reasoning={'effort':'medium'},max_output_tokens=MAX_OUTPUT,
                        tools=[],store=False)
            usage=response.usage.model_dump()
            # Ignore cached-input discounts for a conservative standard-rate estimate.
            estimated=(usage['input_tokens']*.20+usage['output_tokens']*1.20)/1e6
            record.update(response_id=response.id,returned_model=response.model,
                          status=response.status,output=response.output_text,usage=usage,
                          estimated_cost_usd=estimated,elapsed_seconds=round(time.monotonic()-start,2),
                          incomplete_details=str(response.incomplete_details))
            if 'expected' in case:
                record['score']=score(response.output_text,case['expected'])
        except Exception as exc:
            # Never log exception bodies: authentication failures may contain key fragments.
            record.update(error_type=type(exc).__name__,http_status=getattr(exc,'status_code',None))
            cause=exc.__cause__
            chain=[]
            while cause is not None and len(chain)<5:
                chain.append(dict(type=type(cause).__name__,errno=getattr(cause,'errno',None),
                                  message=str(cause).replace(config['OPENAI_API_KEY'],'[REDACTED]')[:300]))
                cause=cause.__cause__
            record['error_causes']=chain
        records.append(record)
        with (out/'trials.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(record)+'\n')
        print(json.dumps({k:v for k,v in record.items() if k in
                         ('id','status','output','score','estimated_cost_usd','error_type','http_status','error_causes')}),flush=True)
        if 'error_type' in record:
            raise RuntimeError('API error; stopped without retry. See sanitized trial log.')
        return record

    token=secrets.token_hex(16)
    first_prompt=f'Remember this experiment code: {token}. Reply only ACK.'
    first=call(dict(id='isolation_seed',prompt=first_prompt))
    question='What experiment code did I give you earlier? If none is present in this conversation, reply UNKNOWN. Otherwise reply only the code.'
    call(dict(id='isolation_fresh',prompt=question))
    call(dict(id='isolation_history_positive_control',prompt=question),[
        {'role':'user','content':first_prompt},
        {'role':'assistant','content':first['output']},
        {'role':'user','content':question}])
    call(dict(id='titanic_no_table',prompt='For the original Kaggle Titanic competition training file train.csv (891 passengers), how many passengers survived and what fraction survived? Return only JSON with n_rows, n_positive, fraction_positive rounded to six decimal places. If unknown, use null.',
              expected=dict(n_rows=891,n_positive=342,fraction_positive=round(342/891,6))))
    for case in cases:
        call(case)
    summary=dict(trials=len(records),table_trials=len(cases),
                 table_all_correct=sum(r.get('score',{}).get('all_correct',False) for r in records[4:]),
                 fresh_request_did_not_recall=records[1]['output'].strip()=='UNKNOWN',
                 history_control_recalled=records[2]['output'].strip()==token,
                 estimated_cost_usd=sum(r.get('estimated_cost_usd',0) for r in records),
                 reserved_max_cost_usd=reserved,
                 results_path=str(out))
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    main()
