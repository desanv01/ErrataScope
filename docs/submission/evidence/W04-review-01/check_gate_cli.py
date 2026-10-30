import contextlib,io,json
from pathlib import Path
from erratascope_service.ingestion.cli import verify_evidence
result=[]
for status,gate in [('partial','fail'),('pass','pass')]:
    p=Path('/reviewout/negative-manifest.json');p.write_text(json.dumps({'status':status,'gates':{'B2':{'status':gate}},'files':[]}))
    output=io.StringIO()
    with contextlib.redirect_stdout(output):code=verify_evidence(str(p))
    result.append({'manifest_status':status,'gate_status':gate,'files':0,'actual_exit':code,'actual_result':json.loads(output.getvalue())['status'],'defect_reproduced':code==0})
Path('/reviewout/evidence-cli-counterexamples.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
