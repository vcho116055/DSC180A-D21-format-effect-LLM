"""Explicitly exploratory follow-up, kept separate from the frozen primary study."""
import asyncio
import json
import random
import time
from pathlib import Path

from experiments.week4_study import ROOT, MODEL, FORMATS, SYSTEM, dumps, sha, utc, load_data, serialize, score

DIRECTORY=ROOT/'results/week4_followup'
PRIOR_SYSTEM='Answer from your existing knowledge. No tools, browsing, or table are available. If you do not know, say UNKNOWN rather than guessing.'


def prepare():
    DIRECTORY.mkdir(parents=True,exist_ok=False)
    rng=random.Random(18020261022)
    primary=[json.loads(x) for x in (ROOT/'results/week4_lookup/cases.jsonl').read_text().splitlines()]
    cases=[]
    for c in primary:
        if c['stage']=='prior':
            cases.append(dict(c,id=c['id']+'_knowledge_allowed',stage='prior_repaired',
                              instructions=PRIOR_SYSTEM,max_output_tokens=4096))
    data=load_data()['titanic']
    first=data[:3]
    original={r['record_id']:r['fare'] for r in first}
    candidates=[r for r in data[3:] if r['fare'] not in original.values()]
    rows=[r.copy() for r in first+rng.sample(candidates,37)]
    rng.shuffle(rows)
    altered=[r.copy() for r in rows]
    replacements={'1':'20.12345','2':'31.23456','3':'42.34567'}
    for r in altered:
        if r['record_id'] in replacements:
            r['fare']=replacements[r['record_id']]
    for rep in (1,2):
        cases.append(dict(id=f'canonical_prior_r{rep}',stage='canonical_prior',dataset='titanic',
                          instructions=PRIOR_SYSTEM,max_output_tokens=4096,expected=original,
                          prompt='For the original Kaggle Titanic training file train.csv, what are the Fare values for PassengerId 1, 2, and 3? No table is supplied. Return only JSON mapping the IDs to value strings, or UNKNOWN for values you do not know.'))
    for version,table in [('original',rows),('altered',altered)]:
        for cue in ('named','neutral'):
            title='Table source: Kaggle Titanic.' if cue=='named' else 'Table source: a collection of records.'
            expected={r['record_id']:r['fare'] for r in table if r['record_id'] in original}
            expected['999999']='NOT_FOUND'
            for fmt in FORMATS:
                prompt=(title+'\nLook up fare for record_id 1, 2, 3, and 999999 in exactly the supplied table. '
                        'Copy the supplied values rather than using outside knowledge. If a record is absent, use NOT_FOUND. '
                        'Return only JSON mapping each requested record_id to a value string.\nTABLE:\n'+serialize(table,fmt))
                cases.append(dict(id=f'canonical_{version}_{cue}_{fmt}',stage='canonical_lookup',
                                  dataset='titanic',version=version,cue=cue,format=fmt,
                                  instructions=SYSTEM,prompt=prompt,max_output_tokens=2048,
                                  expected=expected,original_values=original))
    rng.shuffle(cases)
    bound=sum(((len((c['instructions']+c['prompt']).encode())+2048)*.5+c['max_output_tokens']*1.8)/1e6 for c in cases)
    assert bound<.50
    (DIRECTORY/'cases.jsonl').write_text('\n'.join(dumps(c) for c in cases)+'\n',encoding='utf-8')
    (DIRECTORY/'manifest.json').write_text(json.dumps(dict(created_utc=utc(),requests=len(cases),
        model=MODEL,reasoning_effort='medium',plan_sha256=sha('\n'.join(dumps(c) for c in cases)),
        reservation_upper_bound_usd=bound,budget_usd=.50,
        rationale='Added after interim main results showed ceiling accuracy. Original no-table probes inherited a supplied-information-only instruction; repeat them with explicit permission to use prior knowledge. Add a single recognizable first-three-passenger block and two no-table probes. Not part of primary inference.'),indent=2),encoding='utf-8')
    print('Frozen follow-up:',len(cases),'requests')


async def run():
    from dotenv import dotenv_values
    from openai import AsyncOpenAI
    cases=[json.loads(x) for x in (DIRECTORY/'cases.jsonl').read_text().splitlines()]
    manifest=json.loads((DIRECTORY/'manifest.json').read_text())
    assert sha('\n'.join(dumps(c) for c in cases))==manifest['plan_sha256']
    path=DIRECTORY/'trials.jsonl'
    if path.exists() or (DIRECTORY/'started.jsonl').exists():
        raise RuntimeError('Follow-up already started; inspect logs before any retry')
    config=dotenv_values(ROOT/'.env',encoding='utf-8-sig')
    client=AsyncOpenAI(api_key=config['OPENAI_API_KEY'],max_retries=0,timeout=120)
    sem=asyncio.Semaphore(3)
    async def one(c):
        async with sem:
            with (DIRECTORY/'started.jsonl').open('a',encoding='utf-8') as f:
                f.write(dumps({'id':c['id'],'time':utc()})+'\n')
            record={'id':c['id'],'prompt_sha256':sha(c['prompt']),'instructions_sha256':sha(c['instructions'])}
            start=time.monotonic()
            try:
                response=await client.responses.create(model=MODEL,instructions=c['instructions'],
                     input=[{'role':'user','content':c['prompt']}],tools=[],store=False,
                     reasoning={'effort':'medium'},max_output_tokens=c['max_output_tokens'])
                usage=response.usage.model_dump()
                record.update(status=response.status,returned_model=response.model,response_id=response.id,
                    output=response.output_text,usage=usage,score=score(c,response.output_text,response.status),
                    estimated_usd=(usage['input_tokens']*.2+usage['output_tokens']*1.2)/1e6,
                    elapsed_seconds=time.monotonic()-start,
                    incomplete_details=response.incomplete_details.model_dump() if response.incomplete_details else None)
            except Exception as exc:
                record.update(status='api_error',error_type=type(exc).__name__,http_status=getattr(exc,'status_code',None))
            with path.open('a',encoding='utf-8') as f:
                f.write(dumps(record)+'\n')
            print(dumps({'id':c['id'],'status':record['status'],'all_correct':record.get('score',{}).get('all_correct')}),flush=True)
    try:
        await asyncio.gather(*(one(c) for c in cases))
    finally:
        await client.close()


if __name__=='__main__':
    prepare()
