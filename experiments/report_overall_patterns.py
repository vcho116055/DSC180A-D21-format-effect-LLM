"""Additional descriptive views of the prespecified task/size/repetition diagnostics."""
import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments import overall_replication as r
from experiments.overall_replication_v2 import DIRECTORY
from experiments.analyze_overall_replication import md_table

COLORS={'csv':'#2878b5','json':'#d85e35','xml':'#25865b','txt':'#a67c00'}


def report(directory):
    analysis=json.loads((directory/'analysis.json').read_text())
    audit=json.loads((directory/'audit.json').read_text())
    frame=pd.read_csv(directory/'scored_requests.csv')
    consistency=pd.read_csv(directory/'repeat_consistency.csv')
    failures=json.loads((directory/'failures.json').read_text())
    manifest=json.loads((directory/'manifest.json').read_text())
    uploaded=r.read_lines(directory/'uploads.jsonl')
    upload_by_path={u['path']:u for u in uploaded}
    cases={c['id']:c for c in r.read_lines(directory/'cases.jsonl')}
    responses_with_files=set(frame.loc[frame.status!='api_error','case_id'])
    needed={a['path']:a['sha256'] for c in cases.values() if c['id'] in responses_with_files
            for a in c['assets']}
    assert all(path in upload_by_path and upload_by_path[path]['sha256']==sha
               for path,sha in needed.items()), 'File-input responses lack a corresponding hashed upload record.'
    assert all(manifest['assets_sha256'][path]==sha for path,sha in needed.items())
    primary=frame[frame.stage=='primary'].copy()
    completed_primary=primary[primary.status=='completed']
    counts=primary.groupby(['task','format']).agg(n=('id','size'),correct=('strict_correct','sum'),
        present_correct=('present_correct','sum'),present_n=('present_n','sum'),
        absent_correct=('absent_correct','sum'),absent_n=('absent_n','sum')).reset_index()
    counts['strict_pct']=counts.correct/counts.n*100
    counts['present_pct']=counts.present_correct/counts.present_n*100
    counts['absent_pct']=counts.absent_correct/counts.absent_n*100
    counts.to_csv(directory/'primary_task_format_detail.csv',index=False)
    rep=consistency[consistency.stage=='primary']
    rep_rows=[]
    incomplete_inputs=set(primary.loc[primary.status!='completed','case_id'])
    for task,group in rep.groupby('task'):
        rep_rows.append(dict(task=task,unique_inputs=len(group),
            all_three_correct=int((group.strict_successes==3).sum()),
            mixed_correctness=int(group.strict_successes.between(1,2).sum()),
            all_three_wrong=int((group.strict_successes==0).sum()),
            different_parsed_answers=int((group.distinct_parsed_answers>1).sum()),
            inputs_with_operational_or_incomplete_response=int(group.case_id.isin(incomplete_inputs).sum())))
    rep_table=pd.DataFrame(rep_rows)
    rep_table.to_csv(directory/'primary_repeat_by_task.csv',index=False)
    completed_rep=rep[~rep.case_id.isin(incomplete_inputs)]
    completed_repeat_rows=[]
    for task,group in completed_rep.groupby('task'):
        completed_repeat_rows.append(dict(task=task,unique_inputs=len(group),
            all_three_correct=int((group.strict_successes==3).sum()),
            mixed_correctness=int(group.strict_successes.between(1,2).sum()),
            all_three_wrong=int((group.strict_successes==0).sum()),
            different_parsed_answers=int((group.distinct_parsed_answers>1).sum())))
    completed_rep_table=pd.DataFrame(completed_repeat_rows)
    completed_rep_table.to_csv(directory/'primary_repeat_completed_only.csv',index=False)
    conditional=completed_primary.groupby(['task','format']).agg(
        completed_requests=('id','size'),correct=('strict_correct','sum'),
        present_correct=('present_correct','sum'),present_n=('present_n','sum'),
        absent_correct=('absent_correct','sum'),absent_n=('absent_n','sum')).reset_index()
    conditional['completed_strict_pct']=conditional.correct/conditional.completed_requests*100
    conditional.to_csv(directory/'primary_completed_response_accuracy.csv',index=False)
    near_matches=[]
    for failure in failures:
        if failure['status']!='completed' or failure['absent']:
            continue
        try:
            expected=Decimal(str(failure['expected']))
            actual=Decimal(str(failure['actual']))
            distance=abs(expected-actual)
            if expected.is_finite() and actual.is_finite() and distance<=Decimal('1e-12'):
                near_matches.append(dict(id=failure['id'],stage=failure['stage'],task=failure['task'],
                    format=failure['format'],delivery=failure['delivery'],query=failure['query_id'],
                    expected=failure['expected'],actual=failure['actual'],absolute_difference=str(distance)))
        except (InvalidOperation,ValueError):
            pass
    r.save(directory/'numerical_near_matches.json',near_matches)
    cell_frame=pd.read_csv(directory/'scored_cells.csv')
    literal=cell_frame[(~cell_frame.absent)&(cell_frame.status=='completed')].groupby(
        ['stage','task','format']).agg(present_answers=('id','size'),
        numeric_correct=('correct','sum'),literal_copies=('literal_match','sum')).reset_index()
    literal['literal_copy_pct']=literal.literal_copies/literal.present_answers*100
    literal.to_csv(directory/'literal_copy_accuracy.csv',index=False)
    query_metadata={}
    for cid,c in cases.items():
        for order,q in enumerate(c['queries']):
            pos=q['position']
            third=('absent' if pos is None else 'first' if pos<c['n_rows']//3
                   else 'middle' if pos<2*c['n_rows']//3 else 'last')
            query_metadata[(cid,q['id'])]=dict(target_third=third,
                selector_fields=1 if c['task']=='direct' else len(q['criteria']),question_order=order+1)
    for column in ('target_third','selector_fields','question_order'):
        cell_frame[column]=[query_metadata[(cid,qid)][column]
                            for cid,qid in zip(cell_frame.case_id,cell_frame.query_id)]
    present_cells=cell_frame[(cell_frame.status=='completed')&(~cell_frame.absent)]
    position_table=present_cells.groupby(['stage','task','n_rows','target_third']).agg(
        answers=('id','size'),correct=('correct','sum')).reset_index()
    position_table['error_pct']=(1-position_table.correct/position_table.answers)*100
    position_table.to_csv(directory/'target_position_diagnostics.csv',index=False)
    selector_table=present_cells.groupby(['stage','task','n_rows','selector_fields']).agg(
        answers=('id','size'),correct=('correct','sum')).reset_index()
    selector_table['error_pct']=(1-selector_table.correct/selector_table.answers)*100
    selector_table.to_csv(directory/'selector_width_diagnostics.csv',index=False)
    completed_cases=frame[frame.status=='completed'].groupby(
        ['case_id','stage','task','format','n_rows']).agg(input_tokens=('input_tokens','mean'),
        elapsed_seconds=('elapsed_seconds','mean')).reset_index()
    overhead=completed_cases.groupby(['stage','task','format','n_rows']).agg(
        unique_inputs=('case_id','size'),mean_input_tokens=('input_tokens','mean'),
        mean_elapsed_seconds=('elapsed_seconds','mean')).reset_index()
    overhead.to_csv(directory/'representation_overhead.csv',index=False)
    primary_overhead=completed_cases[completed_cases.stage=='primary'].groupby(['task','format']).agg(
        mean_input_tokens=('input_tokens','mean'),mean_elapsed_seconds=('elapsed_seconds','mean')).reset_index()
    csv_means=primary_overhead[primary_overhead.format=='csv'].set_index('task').mean_input_tokens.to_dict()
    primary_overhead['input_tokens_relative_to_csv']=[tokens/csv_means[task]
        for task,tokens in zip(primary_overhead.task,primary_overhead.mean_input_tokens)]

    fig,axes=plt.subplots(1,3,figsize=(12,4),sharey=True)
    error_top=max(float(((1-conditional.present_correct/conditional.present_n)*100).max()),
                  float(((1-conditional.absent_correct/conditional.absent_n)*100).max()),.1)*1.15
    for ax,task in zip(axes,r.TASKS):
        group=conditional[conditional.task==task].set_index('format').reindex(r.w.FORMATS)
        x=np.arange(4)
        ax.bar(x,(1-group.present_correct/group.present_n)*100,width=.38,label='Present values',color='#2878b5')
        ax.bar(x+.4,(1-group.absent_correct/group.absent_n)*100,width=.38,label='Absent query',color='#d85e35')
        ax.set_xticks(x+.2,r.w.FORMATS)
        ax.set_title(task); ax.set_ylim(0,error_top); ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Incorrect answers (%)')
    axes[-1].legend()
    fig.suptitle('Completed primary responses: present-value and missing-record errors')
    fig.tight_layout(); fig.savefig(directory/'present_vs_absent.png',dpi=180); plt.close(fig)

    fig,ax=plt.subplots(figsize=(7,4))
    bottoms=np.zeros(3)
    for successes,color in ((3,'#25865b'),(2,'#d9b44a'),(1,'#d85e35'),(0,'#7b3948')):
        values=[]
        for task in r.TASKS:
            group=completed_rep[completed_rep.task==task]
            values.append(100*(group.strict_successes==successes).mean())
        ax.bar(r.TASKS,values,bottom=bottoms,label=f'{successes}/3 correct',color=color)
        bottoms+=values
    ax.set_ylim(0,100); ax.set_ylabel('Unique primary inputs (%)')
    ax.set_title('Identical-input correctness: all three responses completed')
    ax.legend(loc='lower left'); fig.tight_layout()
    fig.savefig(directory/'repeat_consistency.png',dpi=180); plt.close(fig)

    fig,axes=plt.subplots(1,3,figsize=(12,4),sharey=True)
    for ax,task in zip(axes,r.TASKS):
        for fmt in r.w.FORMATS:
            group=frame[(frame.stage.isin(['primary','stress'])) & (frame.task==task) &
                        (frame.format==fmt) & (frame.cue=='neutral') & (frame.status=='completed')]
            values=group.groupby('n_rows').strict_correct.mean().sort_index()
            ax.plot(values.index,(1-values)*100,marker='o',label=fmt,color=COLORS[fmt])
        ax.set_title(task); ax.set_xticks([80,400,800]); ax.grid(alpha=.2)
        ax.set_xlabel('Rows in supplied table')
    axes[0].set_ylabel('Strict request error (%)')
    axes[-1].legend()
    fig.suptitle('Table size: neutral primary inputs and separate 800-row stress arm')
    fig.tight_layout(); fig.savefig(directory/'table_size_errors.png',dpi=180); plt.close(fig)

    delivery_rows=[]
    file_rows=frame[frame.stage=='file']
    selected=set(file_rows.block)
    baseline=primary[(primary.block.isin(selected)) & (primary.cue=='neutral')]
    for task in r.TASKS:
        for fmt in r.w.FORMATS:
            a=baseline[(baseline.task==task)&(baseline.format==fmt)]
            b=file_rows[(file_rows.task==task)&(file_rows.format==fmt)]
            if len(a) and len(b):
                delivery_rows.append(dict(task=task,format=fmt,inline_n=len(a),file_n=len(b),
                    inline_strict_pct=a.strict_correct.mean()*100,file_strict_pct=b.strict_correct.mean()*100,
                    file_minus_inline_pp=(b.strict_correct.mean()-a.strict_correct.mean())*100))
    delivery=pd.DataFrame(delivery_rows)
    delivery.to_csv(directory/'file_delivery_by_task_format.csv',index=False)

    total_primary=len(primary)
    total_correct=int(primary.strict_correct.sum())
    present_correct=int(primary.present_correct.sum()); present_n=int(primary.present_n.sum())
    absent_correct=int(primary.absent_correct.sum()); absent_n=int(primary.absent_n.sum())
    altered_correct=int(primary.altered_correct.sum()); altered_n=int(primary.altered_n.sum())
    reversions=int(frame.reversions.sum())
    main_fail=[f for f in failures if f['stage']=='primary']
    model_fail=[f for f in main_fail if f['status']=='completed']
    fail_absent=sum(f['absent'] for f in model_fail)
    fail_present=len(model_fail)-fail_absent
    unique_main_errors=len({(f['block'],f['query_id']) for f in main_fail})
    lines=['# Conclusions and detailed patterns\n',
        f"The completed study contains **{len(frame):,} requests**, including 24 development requests "
        'retained from the stopped calibration. It tests three query types, four serialization formats, '
        'three identical calls per non-calibration input, and separate controls for file delivery, '
        'empirical edits, and longer tables.\n',
        '## What the main experiment establishes\n',
        f"Across 36 primary sampled blocks, **{total_correct:,}/{total_primary:,} "
        f"({100*total_correct/total_primary:.3f}%)** requests were entirely correct. "
        f"Present values were correct in **{present_correct:,}/{present_n:,}** answers; "
        f"absent queries in **{absent_correct:,}/{absent_n:,}**. "
        f"Altered present values were correct in **{altered_correct:,}/{altered_n:,}** answers.\n",
        md_table(counts,['task','format','n','correct','strict_pct','present_pct','absent_pct']),
        'Each row includes all three repeated calls, original/altered tables, both name cues, and both '
        'primary sizes. Strict request success here is an end-to-end measure including operational failures. '
        'These call totals are not independent block counts.\n',
        '### Correctness conditional on a completed response\n',md_table(conditional),
        'This sensitivity view excludes operational failures and incomplete outputs from the denominator; '
        'the original prespecified end-to-end results remain unchanged. Both views are needed to avoid '
        'attributing an API failure to model reasoning.\n',
        '## Does repetition change the interpretation?\n',md_table(rep_table),
        'Mixed correctness means an identical input was right on some calls and wrong on others. '
        'All-three-wrong inputs identify observed persistent difficulty on those prompts; '
        'neither category alone establishes an underlying mechanism. Repetitions estimate reliability '
        'conditional on an input, while fresh blocks assess variation across inputs.\n',
        'For model consistency alone, exclude inputs with any operational/incomplete attempt:\n',
        md_table(completed_rep_table),
        '![Repeated calls](repeat_consistency.png)\n',
        '## Which errors matter?\n',
        f"Completed primary responses contain **{fail_present} incorrect present-value answers** and "
        f"**{fail_absent} incorrect absent-query answers**, involving **{unique_main_errors} distinct "
        'block/query combinations** across task/format/version/cue/repetition conditions. '
        'Missing-record behavior must therefore be considered separately from copying present values.\n',
        '![Present and absent errors](present_vs_absent.png)\n',
        f"Across all arms, **{reversions} altered-value answers matched the replaced original value**. "
        'A zero count would describe these tested conflicts; it would not prove absence of prior knowledge '
        'or training-data exposure.\n',
        f"A separate post-collection diagnostic found **{len(near_matches)} numerical errors within "
        '1e-12 of the expected value**. These remain incorrect under the frozen exact-decimal scorer. '
        'The diagnostic helps identify possible representation/rounding differences and does not '
        'establish their internal cause. Literal-copy rates are recorded separately in '
        'literal_copy_accuracy.csv; numerically equivalent strings can pass value scoring while '
        'differing in formatting.\n',
        '## Does a format consistently win?\n']
    contrasts=[]
    for name,c in analysis['contrasts'].items():
        if name.startswith('primary/strict_correct/'):
            contrasts.append(dict(format_comparison=c['comparison'],difference_pp=c['difference_pp'],
                interval_95=str([round(x,4) for x in c['descriptive_95_pp']]),
                adjusted_interval=str([round(x,4) for x in c['family_adjusted_98_333_pp']]),blocks=c['blocks']))
    lines.append(md_table(pd.DataFrame(contrasts)))
    significant=[a for name,a in analysis['contrasts'].items() if name.startswith('primary/strict_correct/')
        and (a['family_adjusted_98_333_pp'][0]>0 or a['family_adjusted_98_333_pp'][1]<0)]
    lines.append('The adjusted paired intervals identify an observed pooled format association in this '
        'sample. Task-level and source-level breakdowns determine its scope; it is not a universal model '
        'or format ranking.\n' if significant else
        'The prespecified pooled format comparisons do not separate from zero in the adjusted '
        'descriptive intervals. The defensible conclusion is no established consistent advantage under '
        'these conditions, rather than proven equivalence.\n')
    lines.extend(['## Actual files versus inline representations\n',md_table(delivery),
        'Actual uploads are compared only against their exact inline/neutral counterparts. The '
        'file arm has 12 selected primary table blocks, and joins use two labeled files. CSV receives '
        'spreadsheet-specific augmentation. A delivery difference therefore includes file parsing '
        'and provider preprocessing.\n',
        'The three file repetitions reuse uploaded file IDs; variability across independent '
        're-uploads is not measured. File delivery and empirical edits are separate arms, so '
        'their interaction is not tested.\n',
        '## Representation length and runtime\n',md_table(primary_overhead),
        'Input-token means first average identical calls within each input, then average inputs. '
        'CSV is the within-task reference for the displayed ratio. Latency is descriptive: '
        'concurrency changed after the rate-limit stop, and service load was not controlled. '
        'File-input token counts include provider processing and are listed separately in '
        'representation_overhead.csv.\n',
        '## Larger tables and plausible edits\n',
        '![Table size](table_size_errors.png)\n',
        'The 800-row arm is a separate stress test with only two blocks per source. The empirical-edit '
        'arm draws field values from the observed source distribution while avoiding duplicate target '
        'values inside the table. Consult REPORT.md and analysis.json for matched uniform/empirical '
        'contrasts. Neither diagnostic is pooled into the primary format estimate.\n',
        '## Additional descriptive diagnostics\n',
        md_table(position_table[position_table.stage=='primary']),
        'Target thirds refer to the selection table, not to the separately shuffled values table '
        'in joins. Position, record identity, and selector difficulty were not independently '
        'randomized. These post-collection breakdowns are associations, not an isolated position '
        'effect. Selector-width counts are in selector_width_diagnostics.csv and are likewise '
        'confounded with source and table construction. Primary scoring and contrasts are unchanged.\n',
        '## What to tell the professor\n',
        'We evaluated response consistency with three identical requests per input and variation across '
        'fresh sampled tables. We reported single-call accuracy averaged over repetitions, kept missing '
        'records separate from present values, and compared formats within matched blocks. We did not '
        'average the numerical answers or count repeated calls as new independent tables.\n',
        '## Limits and protocol history\n',
        'The initial all-correct development gate stopped at 23/24. Before any main response, a separately '
        'versioned protocol adopted a technical-completion/schema gate and retained all development '
        'records. Prompts, sampled tables, request order, and scoring were unchanged. This development '
        'decision is disclosed and is not presented as untouched preregistration.\n',
        'The primary has three purposive sources; the extra three sources extend direct lookup only. '
        'Tables overlap in source rows, selections require unique targets and valid distractors, and '
        'three calls still give imprecise per-prompt reliability estimates. The service model alias may '
        'change over time. Runtime versions are recorded and differ from the shared lock. '
        'Observed behavior does not establish training-data leakage or a model-internal explanation.\n',
        f"Audit: {audit['recorded']}/{audit['planned']} records; "
        f"{audit['file_uploads']} uploaded files; {len(audit['files_not_confirmed_deleted'])} "
        'without confirmed deletion. Raw data and reports remain local and ignored by Git.\n'])
    (directory/'CONCLUSIONS.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(dict(primary_requests=total_primary,primary_correct=total_correct,
        present_correct=present_correct,present_n=present_n,absent_correct=absent_correct,absent_n=absent_n,
        altered_correct=altered_correct,altered_n=altered_n,reversions=reversions,
        repeat_by_task=rep_rows),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',type=Path,default=DIRECTORY)
    report(parser.parse_args().directory)
