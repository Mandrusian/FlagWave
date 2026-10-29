#!/usr/bin/env python3
"""Package the web port from the shared Android shaders and flag catalogue."""
from pathlib import Path
import shutil,json,re
root=Path(__file__).resolve().parents[1];out=root/'web/dist';out.mkdir(parents=True,exist_ok=True)
for name in ['index.html','style.css','app.js','renderer.js','icon.svg','Roboto.ttf','FONT-LICENSE.txt']:
    if (root/'web'/name).exists():shutil.copy2(root/'web'/name,out/name)
catalogue=[]
for id,name in json.loads((root/'countries.json').read_text()).items():catalogue.append(dict(id=id,name=name,asset=f'flags/{id}.png',tags=['Countries'],period='',source='https://flagpedia.net/download/api',credit='Flagpedia / Wikimedia Commons',license='Public domain'))
catalogue+=json.loads((root/'archive.json').read_text())
assert len(catalogue)==len({e['id'] for e in catalogue})
for folder in ['flags','archive']:shutil.copytree(root/folder,out/'assets'/folder,dirs_exist_ok=True)
for e in catalogue:e['asset']='assets/'+e['asset']
(out/'catalogue.json').write_text(json.dumps(sorted(catalogue,key=lambda e:e['name'].casefold()),ensure_ascii=False))
source=(root/'android/app/src/main/java/tech/mandrusia/flagwave/FlagRenderer.kt').read_text()
shaders={name:re.search(r'const val '+name+r'="""(.*?)"""',source,re.S).group(1) for name in ['vertexShader','flagShader','quadShader','asciiShader']}
(out/'shaders.js').write_text('\n'.join('export const '+k+'='+json.dumps(v)+';' for k,v in shaders.items()))
shutil.copy2(root/'ARCHIVE-SOURCES.md',out/'ARCHIVE-SOURCES.md');shutil.copy2(root/'LICENSE',out/'LICENSE')
print(f'Built web app with {len(catalogue)} flag entries and shared Android shaders: {out}')
