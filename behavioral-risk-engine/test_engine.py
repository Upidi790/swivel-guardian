import copy
import json
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from demo import generate
from engine import analyze_transaction

class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = generate()
    def score(self, tx, history=None):
        return analyze_transaction(tx['user_id'], tx, self.data['transactions'] if history is None else history)
    def test_normal_and_unusual(self):
        self.assertFalse(self.score(self.data['cases'][0]['transaction'])['requires_intervention'])
        self.assertTrue(self.score(self.data['cases'][50]['transaction'])['requires_intervention'])
    def test_future_current_failed_and_other_user_do_not_change_baseline(self):
        tx = self.data['cases'][50]['transaction']
        expected = self.score(tx)['baseline']
        base = dict(tx, amount=999999, successful=True)
        extra = [dict(base, timestamp='2030-01-01T00:00:00Z'),
                 dict(base, timestamp='2026-10-01T00:00:00Z'),
                 dict(base, transaction_id='failed', timestamp='2026-10-01T00:00:00Z', successful=False),
                 dict(base, transaction_id='other', timestamp='2026-10-01T00:00:00Z', user_id='someone_else')]
        self.assertEqual(expected, self.score(tx, self.data['transactions'] + extra)['baseline'])
    def test_cold_start_and_missing_fields(self):
        tx = dict(self.data['cases'][0]['transaction'], device_id=None, ip_region=None, recipient_first_seen=None)
        result = self.score(tx, [])
        self.assertIsNone(result['features']['amount_z_score'])
        self.assertIsNone(result['features']['device_novelty'])
        self.assertEqual(4, len(result['data_quality_warnings']))
    def test_invalid_amounts(self):
        for amount in (0, -1, float('nan'), float('inf'), True, '2000'):
            with self.assertRaises(ValueError):
                self.score(dict(self.data['cases'][0]['transaction'], amount=amount))
    def test_currency_isolation(self):
        result = self.score(dict(self.data['cases'][0]['transaction'], currency='EUR'))
        self.assertEqual(0, result['baseline']['history_count'])
    def test_scenario_labels_never_change_score(self):
        tx = self.data['cases'][50]['transaction']
        self.assertEqual(self.score(tx), self.score(dict(tx, scenario_label='scam', narrative='urgent')))
    def test_frequency_uses_prior_attempts(self):
        tx = self.data['cases'][0]['transaction']
        extra = [dict(tx, transaction_id=f'attempt{i}', timestamp=f'2026-10-03T17:{i:02d}:00+00:00') for i in range(4)]
        self.assertIn('PAYMENT_FREQUENCY', [s['type'] for s in self.score(tx, self.data['transactions'] + extra)['signals']])
    def test_api(self):
        from api import make_server
        from storage import JsonStore
        server = make_server(0)
        server.store = JsonStore()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/analyze'
            request = Request(url, data=json.dumps(self.data['cases'][50]['transaction']).encode(), headers={'Content-Type':'application/json'})
            with urlopen(request, timeout=5) as response:
                self.assertTrue(json.load(response)['requires_intervention'])
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(url, data=b'[]'), timeout=5)
            self.assertEqual(400, error.exception.code)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

if __name__ == '__main__':
    unittest.main()
