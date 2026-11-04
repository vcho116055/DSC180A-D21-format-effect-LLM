"""Separate synthetic file-input feasibility pilot. Only `run` uses the API."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import platform
import random

from experiments import week4_study as w

DEFAULT_DIRECTORY = w.ROOT / 'results/file_input_pilot_20261103'
BUDGET = 1.0
OUTPUT_CAP = 4096
# Official model documentation checked 2026-11-03. Reserve the full context,
# even for tiny files, because provider-side file augmentation is not observable.
CONTEXT_CAP = 1_050_000
# Long-context input x2, output x1.5; allow input cache-write x1.25 too.
RESERVATION = (CONTEXT_CAP * .50 + OUTPUT_CAP * 1.80) / 1e6
MIME = {'csv': 'text/csv', 'json': 'application/json',
        'xml': 'application/xml', 'txt': 'text/plain'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def append(path, value):
    with path.open('a', encoding='utf-8') as stream:
        stream.write(w.dumps(value) + '\n')


def build():
    # Every present query requires both attributes; absent values each occur in
    # other rows. Synthetic only: no dataset rights or real-data prerequisites.
    rows = [dict(record_id=str(i+1), group_a=f'A{i % 5}',
                 group_b=f'B{i // 5}', value=f'{31.25 + i * 7.125:.3f}')
            for i in range(20)]
    rows[-1]['group_b'] = 'B2'  # makes A4/B3 an absent conjunction
    queries = [dict(query_id=f'q{j+1}', criteria={k: rows[i][k]
               for k in ('group_a', 'group_b')})
               for j, i in enumerate((0, 8, 17))]
    queries.append(dict(query_id='q4', criteria=dict(group_a='A4', group_b='B3')))
    expected = {}
    for query in queries:
        matches = [row for row in rows if all(row[k] == v for k, v in query['criteria'].items())]
        assert len(matches) == (query['query_id'] != 'q4')
        expected[query['query_id']] = matches[0]['value'] if matches else 'NOT_FOUND'
    task = ('Find the row matching ALL criteria in the supplied table and copy its value. '
            'Match field values exactly as written. If no row matches all criteria, use NOT_FOUND. '
            'Return only JSON mapping each query_id to a value string, with exactly the requested keys. '
            'Do not calculate or include an explanation.\nQUERIES:\n' + w.dumps(queries))
    cases = []
    for repeat in range(1, 4):
        batch = []
        for fmt in w.FORMATS:
            payload = w.serialize(rows, fmt)
            assert w.deserialize(payload, fmt) == rows
            for delivery in ('inline', 'file'):
                batch.append(dict(id=f'r{repeat}_{fmt}_{delivery}', repeat=repeat,
                                  format=fmt, delivery=delivery, filename=f'table.{fmt}',
                                  task=task, payload=payload, expected=expected))
        random.Random(18020261103 + repeat).shuffle(batch)
        cases.extend(batch)
    return cases


def prepare(directory):
    cases = build()
    directory.mkdir(parents=True, exist_ok=False)
    for case in cases[:8]:
        (directory / case['filename']).write_bytes(case['payload'].encode('utf-8'))
    plan = directory / 'cases.jsonl'
    plan.write_text(''.join(w.dumps(c) + '\n' for c in cases), encoding='utf-8')
    write_json(directory / 'manifest.json', dict(
        created_utc=w.utc(), model=w.MODEL, budget_usd=BUDGET, rows=20,
        first_gate_requests=8, maximum_requests=24, repeats=3,
        reasoning='medium', max_output_tokens=OUTPUT_CAP, tools=[], store=False,
        reservation_per_call_usd=RESERVATION,
        input_rate_per_million=.20, output_rate_per_million=1.20,
        pricing_checked='2026-11-03',
        pricing_source='https://developers.openai.com/api/docs/models/gpt-5.6-luna',
        file_input_source='https://developers.openai.com/api/docs/guides/file-inputs',
        plan_sha256=digest(plan), runner_sha256=digest(__file__),
        helper_sha256=digest(w.__file__),
        file_hashes={f'table.{fmt}': digest(directory / f'table.{fmt}') for fmt in w.FORMATS},
        note='Synthetic feasibility only; no format ranking or main-study inference.'))
    print(f'Prepared 8 feasibility requests, maximum 24 after the gate; cap ${BUDGET:.2f}.')


def charge(usage):
    # No discount credit; conservatively allow cache writes on all input tokens.
    long_context = usage['input_tokens'] > 272_000
    return (usage['input_tokens'] * (.50 if long_context else .25)
            + usage['output_tokens'] * (1.80 if long_context else 1.20)) / 1e6


def gate(records):
    first = [r for r in records if r['repeat'] == 1]
    return (len(first) == 8 and len({r['id'] for r in first}) == 8
            and all(r.get('strict_correct', False) for r in first))


def summarize(directory, records, accounted, reason):
    groups = defaultdict(list)
    for record in records:
        groups[f"{record['format']}/{record['delivery']}"].append(record)
    summary = dict(recorded=len(records), maximum=24, gate_passed=gate(records),
                   accounted_usd=accounted, budget_usd=BUDGET, stop_reason=reason,
                   by_condition={k: dict(n=len(v), strict_correct=sum(
                       r.get('strict_correct', False) for r in v)) for k, v in groups.items()})
    write_json(directory / 'summary.json', summary)
    return summary


def run(directory, env_file):
    from dotenv import dotenv_values
    import openai

    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['model'] == w.MODEL and manifest['budget_usd'] == BUDGET
    assert manifest['plan_sha256'] == digest(directory / 'cases.jsonl')
    assert manifest['runner_sha256'] == digest(__file__)
    assert manifest['helper_sha256'] == digest(w.__file__)
    for filename, expected in manifest['file_hashes'].items():
        assert digest(directory / filename) == expected
    cases = [json.loads(line) for line in (directory / 'cases.jsonl').read_text(encoding='utf-8').splitlines()]
    if any((directory / name).exists() for name in ('started.jsonl', 'trials.jsonl', 'uploads.jsonl')):
        raise RuntimeError('Run already started. Inspect its records; automatic reruns are forbidden.')
    config = dotenv_values(env_file, encoding='utf-8-sig') if env_file.is_file() else {}
    key = os.environ.get('OPENAI_API_KEY') or config.get('OPENAI_API_KEY')
    if not key:
        raise RuntimeError('OPENAI_API_KEY not configured. Set it locally; never paste it into chat.')
    configured_model = config.get('OPENAI_MODEL') or os.environ.get('OPENAI_MODEL')
    if configured_model and configured_model != w.MODEL:
        raise RuntimeError('Configured model differs from the frozen pilot model.')
    client = openai.OpenAI(api_key=key, max_retries=0, timeout=120)
    write_json(directory / 'runtime.json', dict(started_utc=w.utc(), python=platform.python_version(),
               openai=openai.__version__, model=w.MODEL, budget_usd=BUDGET,
               workers=1, retries=0, environment_note='Actual runtime; not a claim of locked-environment parity.'))
    records, files, accounted, reason = [], {}, 0.0, 'completed'
    try:
        for case in cases:
            if case['repeat'] > 1 and not gate(records):
                reason = 'initial_feasibility_gate_failed'
                break
            if accounted + RESERVATION > BUDGET:
                reason = 'budget_reservation_limit'
                break
            record = {k: case[k] for k in ('id', 'repeat', 'format', 'delivery')}
            record.update(started_utc=w.utc(), reservation_usd=RESERVATION,
                          task_sha256=w.sha(case['task']), payload_sha256=w.sha(case['payload']))
            append(directory / 'started.jsonl', record)
            fatal = False
            call_charge = RESERVATION
            try:
                content = [{'type': 'input_text', 'text': case['task']}]
                if case['delivery'] == 'inline':
                    content[0]['text'] += '\nTABLE:\n' + case['payload']
                else:
                    fmt = case['format']
                    if fmt not in files:
                        # Actual local bytes are uploaded, never a local path string.
                        path = directory / case['filename']
                        with path.open('rb') as stream:
                            uploaded = client.files.create(
                                file=(case['filename'], stream, MIME[fmt]), purpose='user_data')
                        files[fmt] = uploaded.id
                        append(directory / 'uploads.jsonl', dict(format=fmt, file_id=uploaded.id,
                               filename=case['filename'], mime=MIME[fmt], sha256=digest(path)))
                    content.append({'type': 'input_file', 'file_id': files[fmt]})
                response = client.responses.create(
                    model=w.MODEL, instructions=w.SYSTEM,
                    input=[{'role': 'user', 'content': content}], reasoning={'effort': 'medium'},
                    max_output_tokens=OUTPUT_CAP, tools=[], store=False)
                usage = response.usage.model_dump() if response.usage else None
                record.update(response_id=response.id, model=response.model, status=response.status,
                              output=response.output_text, usage=usage,
                              incomplete_details=response.incomplete_details.model_dump()
                              if response.incomplete_details else None)
                call_charge = charge(usage) if usage else RESERVATION
                grade = w.score(case, response.output_text, response.status)
                record.update(score=grade, strict_correct=bool(
                    grade['all_correct'] and grade['exact_keys'] and grade['string_values']
                    and response.model == w.MODEL))
                fatal = response.model != w.MODEL or not usage or accounted + call_charge > BUDGET
            except Exception as error:
                # Unknown billing remains reserved; preserve failures without retry.
                call_charge = RESERVATION
                record.update(status='api_error', error_type=type(error).__name__,
                              http_status=getattr(error, 'status_code', None), strict_correct=False)
                fatal = (getattr(error, 'status_code', None) in (401, 403, 429)
                         or isinstance(error, openai.APIConnectionError))
            accounted += call_charge
            record['accounted_usd'] = call_charge
            record['finished_utc'] = w.utc()
            append(directory / 'trials.jsonl', record)
            records.append(record)
            summarize(directory, records, accounted, 'in_progress')
            print(f"{case['id']}: {record['status']}, correct={record['strict_correct']}, accounted=${accounted:.6f}", flush=True)
            if fatal:
                reason = 'model_usage_or_operational_stop'
                break
    finally:
        # Remove only files created by this pilot, retaining their IDs/hashes in logs.
        for fmt, file_id in files.items():
            try:
                deleted = client.files.delete(file_id)
                append(directory / 'cleanup.jsonl', dict(format=fmt, file_id=file_id,
                       deleted=bool(deleted.deleted)))
            except Exception as error:
                append(directory / 'cleanup.jsonl', dict(format=fmt, file_id=file_id,
                       deleted=False, error_type=type(error).__name__))
        client.close()
        summarize(directory, records, accounted, reason)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run'))
    parser.add_argument('--directory', type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument('--env-file', type=Path, default=w.ROOT / '.env')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.directory)
    else:
        run(args.directory, args.env_file)
