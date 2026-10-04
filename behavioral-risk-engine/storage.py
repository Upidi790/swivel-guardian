"""Local JSON demo or real PostgreSQL/Tiger Data persistence."""
import json
import os
from pathlib import Path
from engine import VERSION, analyze_transaction, validate
from config import load_config, connection_options

ROOT = Path(__file__).parent

class JsonStore:
    def __init__(self):
        self.data = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
    def analyze(self, tx):
        if tx.get('user_id') not in {u['user_id'] for u in self.data['users']}:
            raise ValueError('Unknown user')
        return analyze_transaction(tx['user_id'], tx, self.data['transactions'])

class TigerStore:
    def connect(self):
        import psycopg
        # Uses libpq environment variables; credentials never need to be in source.
        return psycopg.connect(**connection_options(), connect_timeout=10)
    def initialize(self, data):
        from psycopg.types.json import Jsonb
        with self.connect() as conn:
            conn.execute((ROOT / 'schema.sql').read_text(encoding='utf-8'))
            for user in data['users']:
                conn.execute('INSERT INTO users VALUES (%s,%s) ON CONFLICT DO NOTHING', (user['user_id'], Jsonb(user)))
                for device in user['known_devices']:
                    conn.execute('INSERT INTO devices VALUES (%s,%s) ON CONFLICT DO NOTHING', (user['user_id'], device))
            profiles = {u['user_id']: u for u in data['users']}
            for tx in data['transactions']:
                validate(tx)
                conn.execute('INSERT INTO recipients VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                             (tx['user_id'], tx['recipient_id'], tx['recipient_first_seen'], tx['recipient_type'],
                              tx['recipient_id'] in profiles[tx['user_id']]['trusted_recipients']))
                conn.execute('INSERT INTO transactions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                             (tx['timestamp'], tx['transaction_id'], tx['user_id'], tx['amount'], tx['currency'],
                              tx['recipient_id'], tx['transaction_type'], tx['successful'], Jsonb(tx)))
    def analyze(self, tx):
        from psycopg.types.json import Jsonb
        validate(tx)
        with self.connect() as conn:
            # Serialize evaluations per user and make retries stable.
            user = conn.execute('SELECT user_id FROM users WHERE user_id=%s FOR UPDATE', (tx['user_id'],)).fetchone()
            if user is None:
                raise ValueError('Unknown user')
            old = conn.execute('SELECT request,result FROM risk_events WHERE user_id=%s AND transaction_id=%s AND model_version=%s',
                               (tx['user_id'], tx['transaction_id'], VERSION)).fetchone()
            if old:
                if old[0] != tx:
                    raise ValueError('Transaction id already used with a different payload')
                return old[1]
            rows = conn.execute('SELECT payload FROM transactions WHERE user_id=%s AND timestamp < %s ORDER BY timestamp',
                                (tx['user_id'], tx['timestamp'])).fetchall()
            result = analyze_transaction(tx['user_id'], tx, [row[0] for row in rows])
            conn.execute('INSERT INTO risk_events(user_id,transaction_id,model_version,request,result) VALUES (%s,%s,%s,%s,%s)',
                         (tx['user_id'], tx['transaction_id'], VERSION, Jsonb(tx), Jsonb(result)))
            return result

if __name__ == '__main__':
    load_config()
    TigerStore().initialize(json.loads((ROOT / 'data.json').read_text(encoding='utf-8')))
    print('Synthetic dataset loaded into Tiger Data.')
