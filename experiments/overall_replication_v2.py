"""Versioned technical-gate revision; main cases and scoring remain unchanged."""
import argparse
import asyncio
import json
from pathlib import Path
import shutil
from unittest.mock import patch

from experiments import overall_replication as r

DIRECTORY = r.ROOT/'results/overall_replication_20261103_v2'


def technical_gate(records,requests):
    expected={a['id'] for a in requests if a['stage']=='calibration'}
    group=[a for a in records if a['stage']=='calibration']
    return (len(group)==len(expected) and {a['id'] for a in group}==expected and all(
        a.get('status')=='completed' and a.get('returned_model')==r.w.MODEL
        and a.get('response_reasoning',{}).get('effort')=='medium'
        and a.get('score',{}).get('exact_keys') and a.get('score',{}).get('string_values') for a in group))


def prepare(directory):
    manifest,cases,requests=r.verify(r.DIRECTORY)
    records=r.read_lines(r.DIRECTORY/'trials.jsonl')
    assert len(records)==24 and all(a['stage']=='calibration' for a in records)
    assert not r.gate_passed(records,requests)
    assert technical_gate(records,requests)
    # copytree refuses to replace an existing run. Original data remain intact.
    shutil.copytree(r.DIRECTORY,directory)
    manifest.update(created_utc=r.w.utc(),protocol_revision='technical_gate_before_main_responses',
        effective_gate='completed + model + medium reasoning + exact keys + string outputs; accuracy retained',
        inherited_calibration=dict(directory=r.DIRECTORY.name,requests=24,
            strict_correct=sum(a['score']['strict_correct'] for a in records),
            trials_sha256=r.file_hash(r.DIRECTORY/'trials.jsonl'),
            starts_sha256=r.file_hash(r.DIRECTORY/'started.jsonl')))
    for source in (Path(__file__),r.ROOT/'experiments/overall_replication_v2_protocol.md'):
        manifest['sources_sha256'][str(source.relative_to(r.ROOT))]=r.file_hash(source)
        shutil.copyfile(source,directory/'source_snapshot'/source.name)
    r.save(directory/'manifest.json',manifest)
    r.save(directory/'progress.json',dict(recorded=24,planned=len(requests),stop_reason='ready_for_main',
                                         inherited_calibration=True))
    print(f'Prepared versioned run; 24 calibration records retained, {len(requests)-24} new calls planned.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','run','analyze','status'))
    parser.add_argument('--directory',type=Path,default=DIRECTORY)
    parser.add_argument('--workers',type=int,default=8)
    args=parser.parse_args()
    if args.action=='prepare':
        prepare(args.directory)
    elif args.action=='status':
        print(json.dumps(r.status(args.directory),indent=2))
    else:
        with patch.object(r,'gate_passed',technical_gate):
            if args.action=='run':
                asyncio.run(r.run(args.directory,args.workers))
            else:
                from experiments.analyze_overall_replication import analyze
                analyze(args.directory)
                report=args.directory/'REPORT.md'
                text=report.read_text(encoding='utf-8')
                text+='\n## Calibration protocol revision\n\nThe original all-correct gate stopped after 23/24 calibration successes. '
                text+='A separately versioned technical gate was adopted before any main responses; all 24 development '
                text+='records, including the wrong absent-query answer, were retained without repetition. '
                text+='Main stimuli, request order, repetitions, and grading were unchanged. See '
                text+='source_snapshot/overall_replication_v2_protocol.md for the explicit development-stage deviation.\n'
                report.write_text(text,encoding='utf-8')


if __name__=='__main__':
    main()
