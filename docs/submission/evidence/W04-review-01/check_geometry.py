import json, re
from pathlib import Path
import pdfplumber
x=json.loads(Path('/reviewout/cited-context-private.json').read_text())
checks=[]
with pdfplumber.open('/w04/st-es0620.pdf') as pdf:
    assert len(pdf.pages)==38
    for a in x['anchors']:
        b=a['bbox'];p=pdf.pages[a['page']]
        good=0<=b['left']<b['right']<=1 and 0<=b['top']<b['bottom']<=1
        # Direct PDF text check for body anchors; table/context are deliberately composed.
        if ':s2.' in a['key']:
            text=p.extract_text() or ''
            norm=lambda v:re.sub(r'\s+',' ',v).strip()
            good=good and norm(a['text']) in norm(text)
        checks.append({'anchor':a['key'],'pass':good})
Path('/reviewout/geometry-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print('PDF page count 38; direct body-text and normalized geometry:',sum(c['pass'] for c in checks),'/',len(checks));assert all(c['pass'] for c in checks)
