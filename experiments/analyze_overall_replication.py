"""Offline audit, paired block comparisons, repetition diagnostics, and report."""
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments import overall_replication as r

METRICS = ('strict_correct','present_accuracy','absent_accuracy')


def bootstrap(differences, strata, draws=10000):
    """Resample blocks within dataset/size strata, retaining equal block weights."""
    values = np.asarray(differences,dtype=float)
    rng = np.random.default_rng(r.SEED+1)
    simulations = np.zeros(draws)
    for stratum in sorted(set(strata)):
        indices = [i for i,s in enumerate(strata) if s==stratum]
        v = values[indices]
        simulations += v[rng.integers(0,len(v),size=(draws,len(v)))].sum(axis=1)
    simulations /= len(values)
    return dict(difference_pp=float(values.mean()*100), blocks=len(values),
        descriptive_95_pp=(np.quantile(simulations,[.025,.975])*100).tolist(),
        family_adjusted_98_333_pp=(np.quantile(simulations,[.05/6,1-.05/6])*100).tolist(),
        zero_width=bool(np.ptp(simulations)==0),
        block_differences_pp=(values*100).tolist())


def grouped(frame, keys):
    return frame.groupby(keys,dropna=False).agg(
        requests=('id','size'),strict_correct=('strict_correct','sum'),
        strict_accuracy=('strict_correct','mean'),present_correct=('present_correct','sum'),
        present_n=('present_n','sum'),absent_correct=('absent_correct','sum'),absent_n=('absent_n','sum'),
        altered_correct=('altered_correct','sum'),altered_n=('altered_n','sum'),
        reversions=('reversions','sum')).reset_index()


def md_table(frame, columns=None):
    if columns:
        frame=frame[columns]
    header='| '+' | '.join(str(c) for c in frame.columns)+' |\n'
    header+='| '+' | '.join('---' for _ in frame.columns)+' |\n'
    return header+''.join('| '+' | '.join(f'{x:.3f}' if isinstance(x,float) else str(x)
                         for x in row)+' |\n' for row in frame.itertuples(index=False,name=None))


def analyze(directory):
    manifest,cases,requests=r.verify(directory)
    assert r.source_hashes()==manifest['data_sha256']
    records=r.read_lines(directory/'trials.jsonl')
    starts=r.read_lines(directory/'started.jsonl')
    assert len({a['id'] for a in records})==len(records)
    assert len({a['id'] for a in starts})==len(starts)
    assert {a['id'] for a in records}=={a['id'] for a in starts}
    plan={a['id']:a for a in requests}
    assert {a['id'] for a in records}<=set(plan)
    rows,cells,failures=[],[],[]
    repeat_groups=defaultdict(list)
    for record in records:
        request=plan[record['id']]
        case=cases[request['case_id']]
        assert record['request_sha256']==case['request_sha256']
        if record['status']!='api_error':
            score=r.grade(case,record['output'],record['status'])
            assert score==record['score']
            assert record['returned_model']==r.w.MODEL
            assert record.get('response_reasoning',{}).get('effort')=='medium'
        else:
            score=r.grade(case,'',record['status'])
        items=score['items']
        present=[i for i in items if not i['absent']]
        absent=[i for i in items if i['absent']]
        row={k:case[k] for k in ('stage','block','dataset','n_rows','task','version','cue','format','delivery','alteration')}
        row.update(id=record['id'],case_id=case['id'],repeat=request['repeat'],status=record['status'],
            strict_correct=score['strict_correct'],schema_correct=score['exact_keys'] and score['string_values'],
            present_correct=sum(i['correct'] for i in present),present_n=len(present),
            absent_correct=sum(i['correct'] for i in absent),absent_n=len(absent),
            altered_correct=sum(i['correct'] for i in present) if case['version']=='altered' else 0,
            altered_n=len(present) if case['version']=='altered' else 0,
            reversions=sum(i['original_value_reversion'] for i in items),
            present_accuracy=sum(i['correct'] for i in present)/len(present),
            absent_accuracy=sum(i['correct'] for i in absent)/len(absent),
            accounted_usd=record['accounted_usd'],estimated_usd=record.get('estimated_usd',0),
            elapsed_seconds=record['elapsed_seconds'],
            input_tokens=(record.get('usage') or {}).get('input_tokens',0),
            output_tokens=(record.get('usage') or {}).get('output_tokens',0))
        rows.append(row)
        repeat_groups[case['id']].append(dict(record,grade=score))
        for item in items:
            cell=dict(row,query_id=item['record_id'],expected=item['expected'],actual=item['actual'],
                      correct=item['correct'],absent=item['absent'],literal_match=item['literal_match'],
                      reversion=item['original_value_reversion'])
            cells.append(cell)
            if item['correct']:
                continue
            category=('operational_or_incomplete' if record['status']!='completed' else
                      'original_value_reversion' if item['original_value_reversion'] else
                      'invalid_or_missing' if item['actual'] is None else
                      'false_not_found' if item['actual']=='NOT_FOUND' else
                      'answer_for_absent_query' if item['absent'] else 'other_value')
            tracing=[]
            if record['status']=='completed' and item['actual'] not in (None,'NOT_FOUND'):
                table,values=r.s.decode_tables(case)
                index={v['link_id']:v[case['field']] for v in values} if values else None
                query=next(q for q in case['queries'] if q['id']==item['record_id'])
                criteria=({'record_id':query['record_id'] or '999999'} if case['task']=='direct' else query['criteria'])
                for supplied in table:
                    value=index[supplied['link_id']] if index else supplied[case['field']]
                    if r.w.numeric_equal(value,item['actual']):
                        tracing.append(dict(record_id=supplied['record_id'],
                            criteria={k:supplied[k] for k in criteria},
                            matched_criteria=sum(supplied[k]==v for k,v in criteria.items()),
                            total_criteria=len(criteria)))
                if tracing and category=='other_value':
                    category='other_supplied_value'
            failures.append(dict(cell,category=category,returned_value_matches=tracing[:10],
                                 returned_value_match_count=len(tracing)))
    frame=pd.DataFrame(rows)
    cell_frame=pd.DataFrame(cells)
    frame.to_csv(directory/'scored_requests.csv',index=False)
    cell_frame.to_csv(directory/'scored_cells.csv',index=False)
    r.save(directory/'failures.json',failures)
    repetitions=[]
    for cid,group in repeat_groups.items():
        case=cases[cid]
        if case['stage']=='calibration':
            continue
        repetitions.append(dict(case_id=cid,stage=case['stage'],block=case['block'],task=case['task'],
            format=case['format'],n=len(group),strict_successes=sum(a['grade']['strict_correct'] for a in group),
            distinct_parsed_answers=len({r.w.dumps(a['grade']['parsed']) for a in group})))
    repeat_frame=pd.DataFrame(repetitions)
    repeat_frame.to_csv(directory/'repeat_consistency.csv',index=False)

    # Contrasts use complete planned blocks, never unbalanced surviving conditions.
    recorded={a['id'] for a in records}
    expected=defaultdict(set)
    for request in requests:
        case=cases[request['case_id']]
        expected[(case['stage'],case['block'])].add(request['id'])
    complete={k for k,ids in expected.items() if ids<=recorded}
    balanced=frame[[ (row.stage,row.block) in complete for row in frame.itertuples() ]]
    contrasts={}
    primary=balanced[balanced.stage=='primary']
    def compare(group,factor,base,variant,metric,label):
        if group.empty:
            return
        paired=group.groupby(['block','dataset','n_rows',factor])[metric].mean().unstack(factor)
        if base not in paired or variant not in paired:
            return
        paired=paired.dropna(subset=[base,variant])
        if paired.empty:
            return
        diff=(paired[variant]-paired[base]).to_numpy()
        strata=[f'{key[1]}_{key[2]}' for key in paired.index]
        contrasts[label]=dict(metric=metric,comparison=f'{variant} minus {base}',
            **bootstrap(diff,strata),block_ids=[key[0] for key in paired.index])
    for metric in METRICS:
        for fmt in ('json','xml','txt'):
            compare(primary,'format','csv',fmt,metric,f'primary/{metric}/{fmt}_minus_csv')
            for task in r.TASKS:
                compare(primary[primary.task==task],'format','csv',fmt,metric,
                        f'primary/{task}/{metric}/{fmt}_minus_csv')
    for task in ('attribute','join'):
        compare(primary,'task','direct',task,'strict_correct',f'primary/task/{task}_minus_direct')
    compare(primary,'version','original','altered','strict_correct','primary/altered_minus_original')
    compare(primary,'cue','neutral','named','strict_correct','primary/named_minus_neutral')
    for stage in ('file','empirical'):
        subset=balanced[balanced.stage==stage]
        block_ids=set(subset.block)
        baseline=primary[(primary.block.isin(block_ids)) & (primary.cue=='neutral')]
        if stage=='empirical':
            baseline=baseline[baseline.version=='altered']
        combined=pd.concat([baseline.assign(comparison_arm='baseline'),subset.assign(comparison_arm=stage)])
        for metric in METRICS:
            compare(combined,'comparison_arm','baseline',stage,metric,f'{stage}/{metric}/minus_inline_uniform')
            for task in r.TASKS:
                compare(combined[combined.task==task],'comparison_arm','baseline',stage,metric,
                        f'{stage}/{task}/{metric}/minus_inline_uniform')
    summaries={}
    for label,keys in [('stage',['stage']),('task_format',['stage','task','format']),
                      ('size',['stage','n_rows','task']),('dataset',['stage','dataset','task']),
                      ('cue',['stage','cue']),('version',['stage','version']),('repeat',['stage','repeat'])]:
        table=grouped(frame,keys)
        table.to_csv(directory/f'summary_{label}.csv',index=False)
        summaries[label]=json.loads(table.to_json(orient='records'))
    recurrence=Counter((f['stage'],f['block'],f['task'],f['query_id']) for f in failures)
    source_blocks=r.read_lines(directory/'blocks.jsonl')
    overlap=[]
    for i,a in enumerate(source_blocks):
        if a['stage']!='primary':
            continue
        aset={row['record_id'] for row in a['original']}
        for b in source_blocks[i+1:]:
            if b['stage']=='primary' and (a['dataset'],a['n_rows'])==(b['dataset'],b['n_rows']):
                bset={row['record_id'] for row in b['original']}
                overlap.append(dict(dataset=a['dataset'],size=a['n_rows'],a=a['id'],b=b['id'],
                                    shared_rows=len(aset&bset),jaccard=len(aset&bset)/len(aset|bset)))
    uploads=r.read_lines(directory/'uploads.jsonl')
    cleanup=r.read_lines(directory/'cleanup.jsonl')
    removed={c['file_id'] for c in cleanup if c.get('deleted')}
    audit=dict(planned=len(requests),recorded=len(records),complete=len(records)==len(requests),
        coverage_unique=True,source_payload_and_score_checks=True,
        returned_model=r.w.MODEL,reasoning='medium',
        calibration_passed=r.gate_passed(records,requests),
        completed=sum(a['status']=='completed' for a in records),
        file_uploads=len(uploads),files_not_confirmed_deleted=sorted({u['file_id'] for u in uploads}-removed),
        complete_matched_blocks=len(complete),planned_matched_blocks=len(expected),
        runtime=r.read_lines(directory/'runtime.jsonl'),
        primary_block_overlap=overlap)
    r.save(directory/'audit.json',audit)
    result=dict(progress=r.status(directory),summaries=summaries,contrasts=contrasts,
        repeat_summary=dict(Counter(f"{x['strict_successes']}/{x['n']}" for x in repetitions)),
        repeat_parsed_disagreements=sum(x['distinct_parsed_answers']>1 for x in repetitions),
        error_categories=dict(Counter(f['category'] for f in failures)),
        distinct_error_block_task_queries=len(recurrence),
        error_recurrence=[dict(stage=k[0],block=k[1],task=k[2],query=k[3],wrong_calls=v) for k,v in recurrence.items()])
    r.save(directory/'analysis.json',result)
    make_report(directory,frame,repeat_frame,result,audit,failures)
    print(json.dumps(dict(recorded=len(records),planned=len(requests),audit='passed',
                         accounted_usd=result['progress']['accounted_usd']),indent=2))
    return result


def make_report(directory,frame,repeats,result,audit,failures):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    primary=frame[frame.stage=='primary']
    lines=['# Repeated three-task experiment: results\n',
        'Collected November 3–4, 2026 (Los Angeles session; UTC timestamps are preserved). '
        'GPT-5.6 Luna, medium reasoning, fresh requests, no tools. '
        'Historical results remain separate.\n',
        f"Recorded **{len(frame):,}/{audit['planned']:,}** planned requests. "
        f"Conservative accounted usage: **${result['progress']['accounted_usd']:.4f}**; "
        f"standard uncached token estimate: ${result['progress']['estimated_uncached_usd']:.4f}. "
        'Amounts are token-price estimates, not an exact invoice.\n',
        '## Results by study arm\n',md_table(pd.DataFrame(result['summaries']['stage'])),
        '## Primary matched comparison\n',
        'The primary contains 36 fresh sampled table blocks: six per source/size stratum, '
        'three sources, 80/400 rows. Each case was submitted three times. '
        'Calls and queried cells are not independent table samples.\n']
    if not primary.empty:
        table=grouped(primary,['task','format'])
        lines.append(md_table(table,['task','format','requests','strict_correct','strict_accuracy',
                                    'present_correct','present_n','absent_correct','absent_n','reversions']))
        for task in r.TASKS:
            group=table[table.task==task].set_index('format').reindex(r.w.FORMATS)
            plt.bar(np.arange(4)+(r.TASKS.index(task)-1)*.25,
                    (1-group.strict_accuracy)*100,width=.25,label=task)
        plt.xticks(range(4),r.w.FORMATS)
        plt.ylabel('Strict whole-request error (%)')
        plt.title('Primary study: errors by task and input format')
        plt.legend(); plt.tight_layout()
        plt.savefig(directory/'primary_format_errors.png',dpi=180); plt.close()
        lines.append('![Primary errors](primary_format_errors.png)\n')
    lines.append('## Paired format contrasts\n')
    contrast_rows=[]
    for label,c in result['contrasts'].items():
        if label.startswith('primary/strict_correct/'):
            contrast_rows.append(dict(contrast=c['comparison'],difference_pp=c['difference_pp'],
                descriptive_95=str([round(v,3) for v in c['descriptive_95_pp']]),
                adjusted_98_333=str([round(v,3) for v in c['family_adjusted_98_333_pp']]),blocks=c['blocks']))
    if contrast_rows:
        lines.append(md_table(pd.DataFrame(contrast_rows)))
        separated=[c for key,c in result['contrasts'].items() if key.startswith('primary/strict_correct/')
                   and (c['family_adjusted_98_333_pp'][0]>0 or c['family_adjusted_98_333_pp'][1]<0)]
        lines.append(('At least one pooled format contrast separates from zero in the adjusted descriptive interval. '
                      'Task-specific results must be checked before describing any advantage as general.\n') if separated else
                     'No pooled format contrast separates from zero in the adjusted descriptive intervals. '
                     'This does not establish equivalence or rule out smaller effects.\n')
    lines.extend(['Intervals resample blocks within dataset/size strata. The three prespecified pooled '
                  'format contrasts have a family adjustment; task-specific and diagnostic comparisons '
                  'are exploratory. Overlapping source rows limit population inference.\n',
                  '## Exact-input repetition\n',
                  md_table(pd.DataFrame([dict(successes=k,cases=v) for k,v in result['repeat_summary'].items()])),
                  f"{result['repeat_parsed_disagreements']} unique cases returned different parsed answers across repeats. "
                  'See repeat_consistency.csv for individual cases. Correctness is averaged across calls; '
                  'numeric answer values are never averaged.\n',
                  '## Task difficulty and table size\n',md_table(pd.DataFrame(result['summaries']['size'])),
                  '## Additional datasets\n',md_table(pd.DataFrame(result['summaries']['dataset'])),
                  '## File delivery and less conspicuous edits\n'])
    diagnostic=[]
    for key,c in result['contrasts'].items():
        if key.startswith(('file/strict_correct/','empirical/strict_correct/')):
            diagnostic.append(dict(arm=key.split('/')[0],difference_pp=c['difference_pp'],
                                   interval_95=str([round(v,3) for v in c['descriptive_95_pp']]),blocks=c['blocks']))
    if diagnostic:
        lines.append(md_table(pd.DataFrame(diagnostic)))
    lines.append('File contrasts use exact matched inline/neutral counterparts. CSV file preprocessing '
                 'differs from text extraction, so delivery results include provider-side processing. '
                 'Empirical edits use observed source values absent from the sampled table, retaining observed '
                 'precision; this reduces one conspicuous-edit limitation but does not remove selection bias.\n')
    lines.extend(['## Error inspection\n',md_table(pd.DataFrame([dict(category=k,wrong_cells=v)
        for k,v in result['error_categories'].items()])),
        f"Errors involve {result['distinct_error_block_task_queries']} distinct stage/block/task/query combinations. "
        'The failures.json file traces wrong values to supplied rows and counts partial criterion matches. '
        'These are behavioral descriptions, not proof of an internal mechanism or training-data leakage.\n'])
    for failure in failures[:8]:
        lines.append(f"- `{failure['id']}`, {failure['query_id']}: expected `{failure['expected']}`, "
                     f"returned `{failure['actual']}` ({failure['category']}).\n")
    lines.extend(['## Validation and limits\n',
        f"Artifact coverage, hashes, source identities, returned models, medium reasoning, and independent "
        f"rescoring passed. {audit['file_uploads']} files were uploaded; "
        f"{len(audit['files_not_confirmed_deleted'])} lack confirmed deletion.\n",
        'The available Python/SDK environment differs from the shared lock and is recorded in runtime.jsonl. '
        'The model alias is not an immutable model snapshot. Three repetitions characterize observed '
        'stochastic consistency, not deterministic reproducibility. Sampled tables overlap, and target '
        'uniqueness and distractor constraints select a nonrepresentative test set. Named/neutral descriptions '
        'retain informative field names. Direct-ID missing queries differ from the harder absent conjunctions. '
        'High accuracy or zero reversions cannot prove absence of prior knowledge or dataset exposure.\n',
        'This report is generated from preserved raw outputs. See analysis.json, audit.json, scored_requests.csv, '
        'scored_cells.csv, repeat_consistency.csv, and the frozen protocol/source snapshot for details.\n'])
    (directory/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',type=Path,default=r.DIRECTORY)
    analyze(parser.parse_args().directory)
