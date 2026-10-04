"""Select across experiments using validation only; publish an optional candidate."""
import json, shutil
from ml_model import ARTIFACTS

def main():
    candidates={}
    folders=['recall-v4','recall-v5']
    if (ARTIFACTS/'balance-v6'/'comparison.json').exists():folders.append('balance-v6')
    for folder in folders:
        r=json.loads((ARTIFACTS/folder/'comparison.json').read_text())
        for name,result in r['candidates'].items():
            candidates[folder+'/'+name]=result
    selected=min(candidates,key=lambda n:candidates[n]['validation']['recall90']['false_positive_rate'])
    folder,name=selected.split('/')
    source=ARTIFACTS/folder
    out=ARTIFACTS/'recall-selected';out.mkdir(exist_ok=True)
    shutil.copyfile(source/(name+'.joblib'),out/'selected-model.joblib')
    # Examples are generated for each experiment's validation winner.
    report=json.loads((source/'comparison.json').read_text())
    assert report['winner']==name
    for label in ('high_score','low_score'):
        shutil.copyfile(source/(label+'-request.json'),out/(label+'-request.json'))
    shutil.copyfile(source/'RESULTS.md',out/'RESULTS.md')
    (out/'selection.json').write_text(json.dumps({'selected':selected,'criterion':'Minimum validation FPR at 90% validation recall','candidates':candidates},indent=2))
    print('Optional API candidate:',selected)

if __name__=='__main__':main()
