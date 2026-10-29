"""Fastfetch logo export and reversible JSONC configuration, without shell execution."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile


def config_path():
    return Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'fastfetch/config.jsonc'


def data_dir():
    return Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'flagwave/fastfetch'


def atomic_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.flagwave-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream: stream.write(data)
        if path.exists(): os.chmod(name,path.stat().st_mode & 0o777)
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


# Lex JSONC so comments, whitespace and unrelated fields survive byte-for-byte.
TOKEN=re.compile(r'\s+|//[^\r\n]*|/\*[\s\S]*?\*/|"(?:[^"\\]|\\.)*"|[^\s{}\[\]:,]+|[{}\[\]:,]')


def logo_patch(text,logo):
    tokens=[m for m in TOKEN.finditer(text) if not m[0].isspace() and not m[0].startswith(('//','/*'))]
    # Validate before editing; trailing commas are part of JSONC.
    normalized=''.join(m[0] for i,m in enumerate(tokens) if not (m[0]==',' and i+1<len(tokens) and tokens[i+1][0] in ('}',']')))
    pairs=[]
    parsed=json.loads(normalized,object_pairs_hook=lambda p: pairs.append(p) or dict(p))
    if not isinstance(parsed,dict): raise ValueError('Fastfetch config must be a JSONC object. Export a logo instead.')
    if any(len(p)!=len(dict(p)) for p in pairs): raise ValueError('Duplicate config keys: export a logo instead of editing this file.')
    depth=0
    for i,token in enumerate(tokens):
        value=token[0]
        if depth==1 and value.startswith('"') and json.loads(value)=='logo' and tokens[i+1][0]==':':
            start=i+2;end=start
            if tokens[start][0] in ('{','['):
                level=1
                while level:
                    end+=1
                    if tokens[end][0] in ('{','['): level+=1
                    elif tokens[end][0] in ('}',']'): level-=1
            return text[:tokens[start].start()]+json.dumps(logo,ensure_ascii=False)+text[tokens[end].end():]
        if value in ('{','['): depth+=1
        elif value in ('}',']'): depth-=1
    start=tokens[0].end()
    return text[:start]+'\n  "logo": '+json.dumps(logo,ensure_ascii=False)+(',' if parsed else '')+text[start:]


def export_logo(frame):
    # Renderer output contains only printable ASCII, SGR colours and line breaks.
    content=frame.replace('\r\n','\n').rstrip('\n')+'\n'
    path=data_dir()/('flag-'+hashlib.sha256(content.encode()).hexdigest()[:16]+'.ansi')
    atomic_write(path,content.encode())
    return path


def apply_logo(frame):
    target=config_path();root=data_dir();statepath=root/'state.json'
    if target.is_symlink(): raise ValueError('Config is a symlink. Export the logo and configure it in your dotfiles instead.')
    original=target.read_bytes() if target.exists() else None
    state=json.loads(statepath.read_text()) if statepath.exists() else None
    digest=hashlib.sha256(original or b'').hexdigest()
    if state and (state['config']!=str(target.absolute()) or state['applied']!=digest):
        raise ValueError('Fastfetch config changed outside FlagWave. Export only; the original backup is preserved.')
    # Validate the config before exporting or changing any existing settings.
    source=(original or b'{}\n').decode('utf-8-sig')
    path=data_dir()/('flag-'+hashlib.sha256((frame.replace('\r\n','\n').rstrip('\n')+'\n').encode()).hexdigest()[:16]+'.ansi')
    updated=logo_patch(source,{'type':'file-raw','source':shlex.quote(str(path.absolute())),'padding':{'right':3}}).encode()
    if original and original.startswith(b'\xef\xbb\xbf'): updated=b'\xef\xbb\xbf'+updated
    if not state:
        root.mkdir(parents=True,exist_ok=True)
        if original is not None: atomic_write(root/'original.config.jsonc',original)
        state={'config':str(target.absolute()),'existed':original is not None}
    export_logo(frame)
    # Persist a recovery record before the config is replaced.
    state['applied']=hashlib.sha256(updated).hexdigest()
    atomic_write(statepath,json.dumps(state).encode())
    atomic_write(target,updated)
    return target


def restore_config():
    statepath=data_dir()/'state.json'
    if not statepath.exists(): raise ValueError('No FlagWave Fastfetch setup to restore.')
    state=json.loads(statepath.read_text());target=config_path()
    if target.is_symlink() or str(target.absolute())!=state['config'] or not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=state['applied']:
        raise ValueError('Config changed outside FlagWave; restore was stopped to preserve your edits. Backup: '+str(data_dir()/'original.config.jsonc'))
    if state['existed']: atomic_write(target,(data_dir()/'original.config.jsonc').read_bytes())
    else: target.unlink()
    statepath.unlink()
    return target


def system_info():
    executable=shutil.which('fastfetch')
    if not executable: raise ValueError('Fastfetch is not installed. Install it with your distro package manager; export still works.')
    # No shell: selected flag names and file paths can never become commands.
    result=subprocess.run([executable,'--logo','none','--pipe','true'],capture_output=True,text=True,timeout=8,check=False)
    if result.returncode: raise ValueError('Fastfetch failed: '+result.stderr.strip()[:150])
    # Strip control sequences before drawing third-party module output in the TUI.
    output=re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-?]*[ -/]*[@-~]','',result.stdout)
    return [''.join(c for c in row.expandtabs(4) if c.isprintable())[:220] for row in output.splitlines()][:100]
