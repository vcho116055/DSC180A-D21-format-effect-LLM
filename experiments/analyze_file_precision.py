"""Post-collection precision sensitivity. Never changes frozen scoring or calls the API."""
from decimal import Decimal, DecimalException
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments import overall_replication as r
from experiments.overall_replication_v2 import DIRECTORY
from experiments.analyze_overall_replication import bootstrap, md_table


def close_numeric(actual,expected):
    if r.w.numeric_equal(actual,expected):
        return True
    try:
        a,b=Decimal(str(actual)),Decimal(str(expected))
        return a.is_finite() and b.is_finite() and abs(a-b)<=Decimal('1e-12')
    except (DecimalException,ValueError):
        return False


def analyze(directory):
    cases={c['id']:c for c in r.read_lines(directory/'cases.jsonl')}
    records=r.read_lines(directory/'trials.jsonl')
    file_blocks={c['block'] for c in cases.values() if c['stage']=='file'}
    rows=[]
    for record in records:
        c=cases[record['case_id']]
        if not (c['stage']=='file' or (c['stage']=='primary' and c['block'] in file_blocks and c['cue']=='neutral')):
            continue
        original=record.get('score',{})
        complete=record['status']=='completed'
        schema=complete and original.get('exact_keys') and original.get('string_values')
        relaxed=bool(schema and all(close_numeric(i['actual'],i['expected']) for i in original['items']))
        exact=bool(original.get('strict_correct',False))
        assert not exact or relaxed
        rows.append(dict(id=record['id'],block=c['block'],dataset=c['dataset'],n_rows=c['n_rows'],
            task=c['task'],format=c['format'],delivery=c['delivery'],completed=complete,
            exact_correct=exact,tolerant_correct=relaxed,precision_only_failure=relaxed and not exact))
    frame=pd.DataFrame(rows)
    frame.to_csv(directory/'file_precision_sensitivity_requests.csv',index=False)
    table=frame.groupby(['delivery','task','format']).agg(attempts=('id','size'),
        completed=('completed','sum'),exact_correct=('exact_correct','sum'),
        tolerant_correct=('tolerant_correct','sum'),precision_only_failures=('precision_only_failure','sum')).reset_index()
    table.to_csv(directory/'file_precision_sensitivity_summary.csv',index=False)
    contrasts={}
    for metric in ('exact_correct','tolerant_correct'):
        paired=frame.groupby(['block','dataset','n_rows','delivery'])[metric].mean().unstack('delivery')
        differences=(paired['file']-paired['inline']).to_numpy()
        contrasts[metric]=bootstrap(differences,[f'{key[1]}_{key[2]}' for key in paired.index])
    totals=frame.groupby('delivery').agg(attempts=('id','size'),completed=('completed','sum'),
        exact_correct=('exact_correct','sum'),tolerant_correct=('tolerant_correct','sum'),
        precision_only_failures=('precision_only_failure','sum')).reset_index()
    result=dict(status='post-collection sensitivity, not a replacement primary score',
        tolerance='absolute finite Decimal difference <= 1e-12 for numeric values; strings/keys/status unchanged',
        totals=json.loads(totals.to_json(orient='records')),contrasts=contrasts,
        by_task_format=json.loads(table.to_json(orient='records')))
    r.save(directory/'file_precision_sensitivity.json',result)
    fig,axes=plt.subplots(1,3,figsize=(12,4),sharey=True)
    for ax,task in zip(axes,r.TASKS):
        x=np.arange(4)
        a=table[(table.task==task)&(table.delivery=='inline')].set_index('format').reindex(r.w.FORMATS)
        b=table[(table.task==task)&(table.delivery=='file')].set_index('format').reindex(r.w.FORMATS)
        ax.bar(x-.24,100*(1-a.exact_correct/a.attempts),width=.24,label='Inline: frozen score',color='#2878b5')
        ax.bar(x,100*(1-b.exact_correct/b.attempts),width=.24,label='File: frozen score',color='#d85e35')
        ax.bar(x+.24,100*(1-b.tolerant_correct/b.attempts),width=.24,label='File: precision sensitivity',color='#25865b')
        ax.set_xticks(x,r.w.FORMATS); ax.set_title(task); ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Strict whole-request failure (%)')
    axes[-1].legend(fontsize=8)
    fig.suptitle('Matched inline/file comparisons: precision explains part of the CSV gap')
    fig.tight_layout(); fig.savefig(directory/'file_delivery_precision.png',dpi=180); plt.close(fig)
    section='\n## CSV precision sensitivity (post-collection)\n\n'
    section+='The exact-decimal primary scores remain unchanged. A separate sensitivity allows absolute '
    section+='numeric differences up to 1e-12 while retaining completion, key, string-type, and NOT_FOUND requirements. '
    section+='This was added after inspecting the errors and is descriptive, not a new prespecified endpoint.\n\n'
    section+=md_table(totals)+'\n'+md_table(table)+'\n'
    repaired=int(totals.loc[totals.delivery=='file','precision_only_failures'].iloc[0])
    near=json.loads((directory/'numerical_near_matches.json').read_text(encoding='utf-8'))
    section+=f'There were {len(near)} near-exact numeric cell errors, all in native CSV uploads. '
    section+=f'{repaired} file requests failed solely because of those precision differences. '
    section+='Allowing the small differences in this sensitivity reduces but does not remove '
    section+='the matched file-delivery gap. Other CSV failures primarily returned NOT_FOUND for present records. '
    section+='The observations identify changes in numeric fidelity and retrieval behavior; they do not identify '
    section+='whether the provider parser, augmented representation, or model inference caused them. '
    section+='The failure rate includes the two retained server errors, which are reported separately from model mistakes.\n\n'
    for metric,c in contrasts.items():
        section+=f"- {metric}, file minus inline: {c['difference_pp']:.3f} percentage points; "
        section+=f"descriptive block-bootstrap 95% interval [{c['descriptive_95_pp'][0]:.3f}, {c['descriptive_95_pp'][1]:.3f}].\n"
    section+='\n![File delivery and precision sensitivity](file_delivery_precision.png)\n'
    for filename in ('REPORT.md','CONCLUSIONS.md'):
        path=directory/filename
        existing=path.read_text(encoding='utf-8').split('\n## CSV precision sensitivity (post-collection)')[0]
        path.write_text(existing+section,encoding='utf-8')
    print(json.dumps(result['totals'],indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',type=Path,default=DIRECTORY)
    analyze(parser.parse_args().directory)
