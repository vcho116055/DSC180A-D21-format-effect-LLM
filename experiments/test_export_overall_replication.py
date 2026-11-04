"""Publication boundary checks; no API calls or source datasets needed."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.export_overall_replication import check_structure, review


class PublicationTests(unittest.TestCase):
    def test_aggregate_metrics_allowed(self):
        check_structure({'requests': 8376, 'reversions': 0, 'paired_contrasts': [{'difference_pp': .2}]})

    def test_raw_cells_and_remote_ids_rejected(self):
        for key in ('expected', 'actual', 'record_id', 'response_id', 'file_id', 'output', 'prompt'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                check_structure({'nested': [{key: 'private'}]})

    def test_unlisted_files_and_private_strings_rejected(self):
        with TemporaryDirectory() as temp:
            path=Path(temp)
            (path/'trials.jsonl').write_text('{}',encoding='utf-8')
            with self.assertRaises(ValueError):
                review(path)
            (path/'trials.jsonl').unlink()
            (path/'README.md').write_text('resp_'+'a'*20,encoding='utf-8')
            with self.assertRaises(ValueError):
                review(path)


if __name__=='__main__':
    unittest.main()
