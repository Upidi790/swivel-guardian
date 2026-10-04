import copy,json,threading
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from api import make_server
from benchmark_scorer import OUT
from ml_model import ARTIFACTS

def main():
    server=make_server(0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def call(payload,route='/ml/v3/analyze'):
        request=Request(f'http://127.0.0.1:{server.server_port}'+route,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=30) as response:return json.load(response)
    results={}
    try:
        for name in ('high_score','low_score'):
            payload=json.loads((OUT/(name+'-request.json')).read_text(encoding='utf-8'))
            result=call(payload)
            assert result['persisted']
            assert call(payload)==result
            (OUT/(name+'-response.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
            results[name]={'risk_score':result['risk_score'],'requires_intervention':result['requires_intervention']}
        conflict=copy.deepcopy(payload);conflict['features']['TransactionAmt']+=1
        try:
            call(conflict);raise AssertionError('Conflicting retry accepted')
        except HTTPError as exc:assert exc.code==400
        # Activate only after both database persistence and actual HTTP scoring work.
        marker={'model_version':result['model_version'],'verified':True}
        (ARTIFACTS/'active-v3.json').write_text(json.dumps(marker,indent=2),encoding='utf-8')
        assert call(payload,'/ml/analyze')['model_version']==result['model_version']
        verification={'model_version':result['model_version'],'http_persistence':True,'stable_retries':True,'conflicting_retry_rejected':True,'default_route_verified':True,'examples':results}
        (OUT/'integration-verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
        print(json.dumps(verification,indent=2))
    finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('API verification failed:',type(exc).__name__)
        raise SystemExit(1)
