"""Validate and summarize both finished runs, without any API calls."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import shutil
import statistics

from experiments.week4_study import ROOT, MODEL, sha, score, deserialize


def read_run(name):
    directory=ROOT/'results'/name
    cases={c['id']:c for c in map(json.loads,(directory/'cases.jsonl').read_text().splitlines())}
    records=[json.loads(x) for x in (directory/'trials.jsonl').read_text().splitlines()]
    assert len(records)==len(cases)
    assert len({r['id'] for r in records})==len(records)
    for r in records:
        c=cases[r['id']]
        assert r['returned_model']==MODEL
        assert r['prompt_sha256']==sha(c['prompt'])
        assert r['score']==score(c,r['output'],r['status'])
        if 'instructions' in c:
            assert r['instructions_sha256']==sha(c['instructions'])
        if c['stage']=='canonical_lookup':
            rows=deserialize(c['prompt'].split('TABLE:\n',1)[1],c['format'])
            index={x['record_id']:x for x in rows}
            assert len(rows)==40
            for key,value in c['expected'].items():
                assert value==(index[key]['fare'] if key in index else 'NOT_FOUND')
    return cases,records


def main():
    main_cases,main_records=read_run('week4_lookup')
    follow_cases,follow_records=read_run('week4_followup')
    cases={**main_cases,**follow_cases}
    records=main_records+follow_records
    summary={'requests':len(records),'model':MODEL,
             'statuses':dict(Counter(r['status'] for r in records)),
             'stages':{},'no_table_by_dataset':{},'format_input_tokens':{},'arithmetic':[],
             'observed_estimated_usd':sum(r['estimated_usd'] for r in records)}
    for stage in sorted({c['stage'] for c in cases.values()}):
        selected=[r for r in records if cases[r['id']]['stage']==stage]
        cells=[cell for r in selected for cell in r['score']['items'] if not cell['absent']]
        summary['stages'][stage]={
            'requests':len(selected),'completed':sum(r['status']=='completed' for r in selected),
            'whole_answer_correct':sum(r['score']['all_correct'] for r in selected),
            'target_values':len(cells),'target_values_correct':sum(c['correct'] for c in cells),
            'original_value_reversions':sum(c['original_value_reversion'] for c in cells)}
    for dataset in ('titanic','redwine','medical'):
        cells=[i for r in follow_records if follow_cases[r['id']]['stage']=='prior_repaired'
               and follow_cases[r['id']]['dataset']==dataset for i in r['score']['items']]
        summary['no_table_by_dataset'][dataset]=dict(n=len(cells),correct=sum(i['correct'] for i in cells),
             unknown=sum(i['actual']=='UNKNOWN' for i in cells),other=sum(not i['correct'] and i['actual']!='UNKNOWN' for i in cells))
    for fmt in ('csv','json','xml','txt'):
        rr=[r for r in main_records if main_cases[r['id']]['stage']=='main' and main_cases[r['id']]['format']==fmt]
        summary['format_input_tokens'][fmt]=round(statistics.mean(r['usage']['input_tokens'] for r in rr),1)
    for r in main_records:
        c=main_cases[r['id']]
        if c['stage']=='arithmetic':
            summary['arithmetic'].append(dict(id=c['id'],expected=c['expected'],actual=r['score']['parsed'],
                                              correct=r['score']['all_correct']))
    summary['arithmetic'].sort(key=lambda x:x['id'])
    lookup_stages=('main','stress','repeat','synthetic','canonical_lookup')
    lookup=[r for r in records if cases[r['id']]['stage'] in lookup_stages]
    summary['all_lookup']={
        'requests':len(lookup),'correct_requests':sum(r['score']['all_correct'] for r in lookup),
        'present_cells':sum(not i['absent'] for r in lookup for i in r['score']['items']),
        'correct_present_cells':sum(i['correct'] and not i['absent'] for r in lookup for i in r['score']['items']),
        'absent_correct':sum(i['correct'] and i['absent'] for r in lookup for i in r['score']['items']),
        'exact_output_schema':sum(r['score']['exact_keys'] and r['score']['string_values'] for r in lookup)}
    out=ROOT/'results/week4_overview'
    out.mkdir(exist_ok=True)
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    snapshot=out/'source_snapshot'
    snapshot.mkdir(exist_ok=True)
    for path in [ROOT/'experiments/week4_study.py',ROOT/'experiments/week4_followup.py',
                 ROOT/'experiments/test_week4_study.py',ROOT/'experiments/week4_protocol.md',
                 ROOT/'requirements-experiments.txt']:
        target=snapshot/path.name
        if target.exists():
            assert target.read_bytes()==path.read_bytes(), 'Archived source changed'
        else:
            shutil.copyfile(path,target)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
