"""Post-run coverage audit and descriptive diagnostics; never sends API requests."""
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from experiments.week4_selection import DIRECTORY, ROOT, MODEL, DATASETS, read_cases, decode_tables, numeric_equal


def main():
    manifest=json.loads((DIRECTORY/'manifest.json').read_text())
    for name,definition in DATASETS.items():
        assert hashlib.sha256((ROOT/'data'/definition[0]).read_bytes()).hexdigest()==manifest['source_sha256'][name]
    for archived in (DIRECTORY/'source_snapshot').iterdir():
        current=ROOT/'requirements-experiments.txt' if archived.name=='requirements-experiments.txt' else ROOT/'experiments'/archived.name
        assert archived.read_bytes()==current.read_bytes(),archived.name
    cases={}
    records={}
    for batch in ('calibration','main'):
        cc={c['id']:c for c in read_cases(batch)}
        rr=[json.loads(x) for x in (DIRECTORY/(batch+'_trials.jsonl')).read_text().splitlines()]
        starts=[json.loads(x) for x in (DIRECTORY/(batch+'_started.jsonl')).read_text().splitlines()]
        assert len(rr)==len(cc)==len(starts)
        assert len({r['id'] for r in rr})==len(rr)
        assert {r['id'] for r in rr}=={r['id'] for r in starts}==set(cc)
        assert all(r['status']=='completed' and r['returned_model']==MODEL for r in rr)
        cases.update(cc)
        records.update({r['id']:r for r in rr})
    groups=defaultdict(dict)
    target_errors=Counter()
    almost_equal=[]
    failures=[]
    task_size={}
    for cid,c in cases.items():
        if c['stage']!='primary':
            continue
        r=records[cid]
        rows,values=decode_tables(c)
        if values is not None:
            value_index={v['link_id']:v[c['field']] for v in values}
            rows=[dict(row,**{c['field']:value_index[row['link_id']]}) for row in rows]
        groups[(c['block'],c['task'],c['cue'],c['format'])][c['version']]=r['score']['strict_correct']
        for item in r['score']['items']:
            if item['correct']:
                continue
            target_errors[(c['block'],item['record_id'])]+=1
            criteria=next(q['criteria'] for q in c['queries'] if q['id']==item['record_id'])
            candidates=[dict(record_id=row['record_id'],criteria_values={k:row[k] for k in criteria},
                             criteria_matches={k:row[k]==v for k,v in criteria.items()})
                        for row in rows if numeric_equal(row[c['field']],item['actual'])]
            failures.append(dict(id=cid,block=c['block'],query=item['record_id'],criteria=criteria,
                                 expected=item['expected'],actual=item['actual'],returned_value_rows=candidates))
            try:
                distance=abs(Decimal(str(item['expected']))-Decimal(str(item['actual'])))
                if distance.is_finite() and distance<=Decimal('1e-12'):
                    almost_equal.append(dict(id=cid,query=item['record_id'],absolute_difference=str(distance)))
            except InvalidOperation:
                pass
    for task in ('attribute','join'):
        task_size[task]={}
        for size in (80,400):
            rr=[records[cid] for cid,c in cases.items() if c['stage']=='primary' and c['task']==task and c['n_rows']==size]
            items=[i for r in rr for i in r['score']['items'] if not i['absent']]
            task_size[task][str(size)]=dict(requests=len(rr),strict_correct=sum(r['score']['strict_correct'] for r in rr),
                present_n=len(items),present_correct=sum(i['correct'] for i in items))
    repeat_pairs=[]
    for cid,c in cases.items():
        if c['stage']=='repeat':
            primary_id=cid.replace('repeat_','primary_',1)
            a,b=records[primary_id],records[cid]
            assert cases[primary_id]['prompt']==c['prompt']
            repeat_pairs.append(dict(id=cid,same_parsed_answer=a['score']['parsed']==b['score']['parsed'],
                                     primary_correct=a['score']['strict_correct'],repeat_correct=b['score']['strict_correct']))
    result=dict(completed_experimental_requests=len(records),coverage_verified=True,
                paired_original_altered_comparisons=len(groups),
                pairs_both_strictly_correct=sum(all(v.values()) for v in groups.values()),
                unique_primary_erroneous_block_queries=len(target_errors),
                primary_target_error_repetitions=[dict(block=k[0],query=k[1],errors=v) for k,v in target_errors.items()],
                primary_cell_errors=failures,task_by_size=task_size,
                posthoc_numeric_near_matches_1e_minus12=almost_equal,
                posthoc_note='Near-match and returned-value row tracing were added after collection; neither changes predefined scores or proves an internal mechanism.',
                repeat_pairs=repeat_pairs,
                estimated_usd=sum(r.get('estimated_usd',0) for r in records.values()))
    (DIRECTORY/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
