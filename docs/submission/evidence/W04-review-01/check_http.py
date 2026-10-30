import json
from pathlib import Path
import httpx
tokens=json.loads(Path('/local/dev-auth/tokens.json').read_text())['users']
pid='8b497e89-40f7-421d-a76f-9573f3c2e57b'; ext='4ec4379e-16c9-4e72-a373-8734c6453f91'
paths=[f'/api/v1/projects/{pid}/sources',f'/api/v1/extractions/{ext}',f'/api/v1/extractions/{ext}/anchors?limit=100',f'/api/v1/extractions/{ext}/coverage?limit=100','/api/v1/drafts/075a2625-862f-4d9a-b932-83f94358cb3d']
results=[]
with httpx.Client(base_url='http://api:8000',timeout=20) as client:
    for path in paths:
        for label in ['user-a','user-b','anonymous']:
            headers={} if label=='anonymous' else {'Authorization':'Bearer '+tokens[label]['token']}
            r=client.get(path,headers=headers)
            results.append({'path':path,'actor':label,'status':r.status_code,'pass':r.status_code==200 if label=='user-a' else r.status_code in (401,403,404)})
Path('/reviewout/http-checks.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2));assert all(r['pass'] for r in results)
