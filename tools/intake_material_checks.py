"""Offline DTO and catalog consistency checks; no workbook parser or product execution."""
import copy
from datetime import date, datetime
from urllib.parse import urlsplit
from material_schema import validate


def run(read, check, reject):
    entry_schema = read('contracts/information-entry.schema.json')
    result_schema = read('contracts/ingestion-result.schema.json')
    fixture = read('examples/information-intake.json')
    catalog = {t['name']: t for t in read('design/database-catalog.json')['tables']}
    entries = fixture['entries']
    result = fixture['result']
    def entry_contract(entry):
        validate(entry, entry_schema)
        publication = entry['publication']
        if publication['date']:
            date.fromisoformat(publication['date'])
        if len({r['reference_key'] for r in entry['source_references']}) != len(entry['source_references']):
            raise ValueError('duplicate reference key')
        for reference in entry['source_references']:
            if reference['url']:
                url = urlsplit(reference['url'])
                if url.scheme not in ('http', 'https') or not url.hostname:
                    raise ValueError('invalid source URL')
    for entry in entries:
        entry_contract(entry)
        check(True, 'Intake DTO shape/date/reference semantics: ' + entry['entry_key'])
    validate(result, result_schema)
    check(True, 'Intake output manifest shape')
    check(len({e['entry_key'] for e in entries}) == len(entries), 'Intake entry keys unique')
    imported = {e['entry_key'] for e in result['entry_results'] if e['status'] == 'imported'}
    check(imported == {e['entry_key'] for e in entries}, 'Intake output references every synthetic entry')
    check(len(imported) == fixture['expected']['readable_entries'] and any(e['status'] == 'failed' for e in result['entry_results']), 'Intake partial fixture accounting')
    check(all(e['parent_revision_id'] == result['report_revision_id'] for e in entries), 'Intake report lineage agreement')
    check(fixture['expected']['accepted_judgments_from_import'] == fixture['expected']['price_bars_from_summary'] == fixture['expected']['no_news_events'] == 0, 'Intake fixed business expectations, NOT execution results')
    checks = [('accepted field', lambda e: e.update(accepted=True)),
              ('publication midnight invented for day', lambda e: e['publication'].update(at='2026-09-29T00:00:00+08:00')),
              ('invalid civil date', lambda e: e['publication'].update(date='2026-02-30')),
              ('digest without report', lambda e: e.update(parent_revision_id=None)),
              ('duplicate reference', lambda e: e['source_references'].append(copy.deepcopy(e['source_references'][0]))),
              ('summary grading field', lambda e: e['reading_metadata'].update(company_score='80'))]
    for label, mutate in checks:
        bad = copy.deepcopy(entries[0]); mutate(bad)
        reject(lambda: entry_contract(bad), 'Intake rejects ' + label)
    bad = copy.deepcopy(result); bad['entry_results'][-1]['item_revision_id'] = entries[0]['parent_revision_id']
    reject(lambda: validate(bad, result_schema), 'Intake failed output cannot claim imported revision')
    instant = copy.deepcopy(entries[0]); instant['publication'].update(at='2026-09-29T18:30:00+08:00', precision='minute', timezone='Asia/Shanghai')
    entry_contract(instant); check(True, 'Intake minute precision supported')
    unknown = copy.deepcopy(entries[1]); unknown['publication']['date'] = '2026-09-29'
    reject(lambda: entry_contract(unknown), 'Intake unknown publication cannot invent date')
    check({'summary_text','content_kind','reading_metadata','parent_revision_id','origin_locator','published_date','published_precision','published_timezone','published_time_raw'} <= {c['name'] for c in catalog['item_revision']['columns']}, 'Intake reading/time fields in authoritative catalog')
    check(next(c for c in catalog['ingestion_run']['columns'] if c['name']=='result_manifest_id')['references']=='input_manifest.id', 'Intake output manifest FK')
    check(next(c for c in catalog['item_observation']['columns'] if c['name']=='ingestion_run_id')['references']=='ingestion_run.id', 'Intake observed batch FK')
    check(['workspace_id','item_revision_id','reference_key'] in catalog['item_source_reference']['unique_keys'], 'Intake multiple-source identity')

    read_schema = read('contracts/information-read.schema.json')
    response = fixture['expected_read_response']
    validate(response, read_schema); check(True, 'Intake common list/detail response shape')
    check(read_schema['properties']['reading_metadata'] == entry_schema['properties']['reading_metadata'] and read_schema['properties']['publication'] == entry_schema['properties']['publication'], 'Intake parser/read shared types agree')
    check(response['revision_id'] == result['entry_results'][0]['item_revision_id'], 'Intake read response is fixed imported revision')
    bad = copy.deepcopy(response); bad['reference_access'][-1]['access']['url'] = 'https://example.invalid/private'
    reject(lambda: validate(bad, read_schema), 'Intake restricted response cannot leak target URL')
    bad = copy.deepcopy(response); bad['reference_access'][0]['access']['target_revision_id'] = None
    reject(lambda: validate(bad, read_schema), 'Intake available original requires actual target revision')
