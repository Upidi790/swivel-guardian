"""Loopback-only hackathon API. No payment execution or external messaging."""
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from storage import JsonStore, TigerStore
from config import load_config, database_configured

class Handler(BaseHTTPRequestHandler):
    def respond(self, status, payload):
        body = json.dumps(payload, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path == '/health':
            self.respond(200, {'status': 'running', 'storage': 'tiger' if isinstance(self.server.store, TigerStore) else 'json',
                               'database_connectivity': 'not_checked'})
        else:
            self.respond(404, {'error': 'Not found'})
    def do_POST(self):
        if self.path not in ('/analyze', '/ml/analyze', '/ml/v2/analyze', '/ml/v3/analyze', '/ml/candidate/analyze', '/behavior/analyze'):
            return self.respond(404, {'error': 'Not found'})
        try:
            size = int(self.headers.get('Content-Length', 0))
            if size <= 0 or size > 65536:
                return self.respond(413, {'error': 'Body must be 1–65536 bytes'})
            tx = json.loads(self.rfile.read(size))
            if not isinstance(tx, dict):
                raise ValueError('Expected a transaction object')
            if self.path == '/behavior/analyze':
                if self.server.behavior_service is None:
                    from sparkov_service import SparkovService
                    self.server.behavior_service=SparkovService(persist=database_configured())
                result=self.server.behavior_service.analyze(tx)
            elif self.path == '/ml/v2/analyze':
                if self.server.legacy_ml_service is None:
                    from ml_service import MLService
                    self.server.legacy_ml_service = MLService(persist=database_configured())
                result = self.server.legacy_ml_service.analyze(tx)
            elif self.path == '/ml/v3/analyze':
                if self.server.benchmark_ml_service is None:
                    from ml_service import MLService
                    from benchmark_scorer import BenchmarkScorer
                    self.server.benchmark_ml_service = MLService(persist=database_configured(),scorer=BenchmarkScorer())
                result = self.server.benchmark_ml_service.analyze(tx)
            elif self.path == '/ml/candidate/analyze':
                if self.server.candidate_ml_service is None:
                    from ml_service import MLService
                    from recall_scorer import RecallScorer
                    self.server.candidate_ml_service=MLService(persist=database_configured(),scorer=RecallScorer())
                result=self.server.candidate_ml_service.analyze(tx)
            elif self.path == '/ml/analyze':
                if self.server.ml_service is None:
                    from ml_service import MLService
                    scorer = None
                    if (Path(__file__).parent/'ml_artifacts'/'active-v3.json').exists():
                        from benchmark_scorer import BenchmarkScorer
                        scorer = BenchmarkScorer()
                    self.server.ml_service = MLService(persist=database_configured(),scorer=scorer)
                result = self.server.ml_service.analyze(tx)
            else:
                result = self.server.store.analyze(tx)
            self.respond(200, result)
        except (ValueError, KeyError, TypeError, AttributeError):
            self.respond(400, {'error': 'Invalid transaction, incompatible feature schema, unknown user, or conflicting transaction id'})
        except Exception:
            self.respond(503, {'error': 'Risk service unavailable; caller must use an explicit fallback policy'})

def make_server(port=8000):
    load_config()
    server = HTTPServer(('127.0.0.1', port), Handler)
    server.store = TigerStore() if database_configured() else JsonStore()
    server.ml_service = None
    server.legacy_ml_service = None
    server.benchmark_ml_service = None
    server.candidate_ml_service = None
    server.behavior_service = None
    return server

if __name__ == '__main__':
    print('Demo risk API: http://127.0.0.1:8000 (POST /analyze)')
    make_server().serve_forever()
