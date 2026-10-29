"""Keyboard-first FlagWave interface, file browser and saved image collection."""
import codecs
import hashlib
import os
from pathlib import Path
import select
import shutil
import sys
import time
import textwrap

import numpy as np
from PIL import Image

from flagwave import ARCHIVE, ARCHIVE_BY_ID, COUNTRIES, ROOT, Renderer, Terminal, clean, load_image

RESET='\x1b[0m'
CYAN='\x1b[96m'
DIM='\x1b[90m'
WHITE='\x1b[97m'
SELECT='\x1b[48;5;24m\x1b[97m'
EXTENSIONS={'.png','.jpg','.jpeg','.webp','.bmp','.gif','.tif','.tiff','.ico'}


def collection_dir():
    return Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'flagwave/imports'


def save_import(path):
    image=load_image(path)
    digest=hashlib.sha256(image.tobytes()+str(image.shape).encode()).hexdigest()[:16]
    dest=collection_dir()/(clean(path.stem)[:70]+'-'+digest+'.png')
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():
        temp=dest.with_suffix('.tmp')
        Image.fromarray(image).save(temp,format='PNG')
        temp.replace(dest)
    return dest


class Keys:
    """Decode separate key events even when a terminal batches input."""
    def __init__(self, fd):
        self.fd=fd; self.pending=''; self.decoder=codecs.getincrementaldecoder('utf-8')(errors='replace')
        self.esc_started=None

    def read(self):
        if select.select([self.fd],[],[],0)[0]:
            self.pending+=self.decoder.decode(os.read(self.fd,4096))
        if not self.pending: return ''
        s=self.pending
        if s.startswith('\x1b'):
            if self.esc_started is None: self.esc_started=time.monotonic()
            if len(s)==1 and time.monotonic()-self.esc_started<.045: return ''
            if len(s)>=2 and s[1] in '[O':
                for i in range(2,len(s)):
                    if '@'<=s[i]<='~':
                        key=s[:i+1]; self.pending=s[i+1:]; self.esc_started=None
                        return {'\x1b[A':'UP','\x1b[B':'DOWN','\x1b[C':'RIGHT','\x1b[D':'LEFT',
                                '\x1bOA':'UP','\x1bOB':'DOWN','\x1bOC':'RIGHT','\x1bOD':'LEFT',
                                '\x1b[5~':'PGUP','\x1b[6~':'PGDOWN','\x1b[H':'HOME','\x1b[F':'END'}.get(key,'')
                if time.monotonic()-self.esc_started<.045: return ''
            self.pending=s[1:]; self.esc_started=None; return 'ESC'
        self.pending=s[1:]
        return {'\r':'ENTER','\n':'ENTER','\x7f':'BACKSPACE','\x08':'BACKSPACE','\x03':'QUIT','\t':'TAB'}.get(s[0],s[0])


class Screen:
    def __init__(self):
        size=shutil.get_terminal_size((100,35))
        self.w=max(1,min(220,size.columns-1)); self.h=max(1,min(75,size.lines))
        self.ox=max(0,(size.columns-1-self.w)//2); self.oy=max(0,(size.lines-self.h)//2)
        self.parts=['\x1b[H']

    def text(self,x,y,value,width=None,style=''):
        if y<0 or y>=self.h or x>=self.w: return
        width=max(0,min(self.w-x,width if width is not None else self.w-x))
        text=clean(value)[:width].ljust(width)
        self.parts.append(f'\x1b[{y+self.oy+1};{x+self.ox+1}H{style}{text}{RESET}')

    def art(self,x,y,rows):
        for offset,row in enumerate(rows.split('\r\n')):
            if y+offset>=self.h: break
            self.parts.append(f'\x1b[{y+offset+self.oy+1};{x+self.ox+1}H{row}')

    def present(self):
        sys.stdout.write(''.join(self.parts)+RESET); sys.stdout.flush()


class App:
    def __init__(self,args,code):
        self.args=args; self.code=code; self.path=args.image.expanduser() if args.image else None
        self.archive_id=getattr(args,'archive_id',None) if not self.path else None
        if self.archive_id: self.path=ROOT/ARCHIVE_BY_ID[self.archive_id]['asset']
        self.group='All'; self.groups=['All']+sorted({tag for e in ARCHIVE for tag in e['tags']})
        self.info_record=None; self.info_return='stage'; self.info_scroll=0
        self.yaw=.24; self.pitch=.12; self.wind=args.wind; self.paused=False
        self.color='none' if args.mono else args.color
        self.clock=0.; self.mode='stage'; self.query=''; self.selected=0; self.offset=0
        self.folder=Path.home()/'Pictures'
        if not self.folder.is_dir(): self.folder=Path.home()
        self.error=''; self.message=''; self.side=True; self.preview_key=None; self.preview=None
        self.fps=0.; self.entries=[]; self.show_hidden=False; self.setting=0; self.goto=None
        self.render_scale=1.; self.last_layout=None; self.renderer=None; self.reload()
        if getattr(args,'archive',False): self.open('archive')

    def reload(self):
        tex=load_image(self.path if self.path else ROOT/'flags'/f'{self.code}.png')
        self.renderer=Renderer(np.rot90(tex,3).copy() if self.args.vertical else tex,getattr(self.args,"quality","auto"))

    def open(self,mode):
        self.mode=mode; self.query=''; self.selected=0; self.offset=0; self.error=''; self.goto=None
        self.preview_key=None

    def items(self):
        q=self.query.casefold()
        if self.mode=='countries':
            return [(f'{c.upper()}  {n}',ROOT/'flags'/f'{c}.png',c,False) for c,n in COUNTRIES.items() if q in n.casefold() or q in c]
        if self.mode=='archive':
            return [(e['name'],ROOT/e['asset'],'archive:'+e['id'],False) for e in ARCHIVE
                    if (self.group=='All' or self.group in e['tags'])
                    and all(word in (e['id']+' '+e['name']+' '+e['period']+' '+' '.join(e['tags'])).casefold() for word in q.split())]
        if self.mode=='collection':
            paths=sorted(collection_dir().glob('*.png'))
            return [(p.stem.rsplit('-',1)[0],p,None,False) for p in paths if q in p.name.casefold()]
        try:
            entries=list(self.folder.iterdir())
        except OSError as e:
            self.error=clean(e); return []
        dirs=[]; files=[]
        for p in entries:
            if not self.show_hidden and p.name.startswith('.'): continue
            if q not in p.name.casefold(): continue
            try:
                if p.is_dir(): dirs.append((p.name+'/',p,None,True))
                elif p.suffix.lower() in EXTENSIONS and p.is_file(): files.append((p.name,p,None,False))
            except OSError: continue
        parent=[] if q else [('.. / parent folder',self.folder.parent,None,True)]
        return parent+sorted(dirs,key=lambda e:e[0].casefold())+sorted(files,key=lambda e:e[0].casefold())

    def accept(self):
        if not self.entries: return
        label,path,code,isdir=self.entries[self.selected]
        if isdir:
            self.folder=path; self.query=''; self.selected=0; self.offset=0; self.error=''; return
        try:
            dest=save_import(path) if self.mode=='browser' else path
            newtex=load_image(dest)
            self.renderer=Renderer(np.rot90(newtex,3).copy() if self.args.vertical else newtex,getattr(self.args,"quality","auto"))
            if code and code.startswith('archive:'):
                self.archive_id=code.split(':',1)[1]; self.path=dest
            elif code:
                self.code=code; self.path=None; self.archive_id=None
            else:
                self.path=dest; self.archive_id=None
            self.message='Imported and saved: '+label if self.mode=='browser' else 'Selected: '+label
            self.mode='stage'; self.error=''
        except (OSError,ValueError,Image.DecompressionBombError) as e: self.error=clean(e)

    def input(self,key):
        if key=='QUIT': return False
        if self.goto is not None:
            if key=='ESC': self.goto=None
            elif key=='ENTER':
                raw=self.goto.strip().strip("\"'")
                if not raw: self.goto=None; return True
                path=Path(raw).expanduser()
                if not path.is_absolute(): path=self.folder/path
                try:
                    if path.is_dir(): self.folder=path.resolve(); self.goto=None; self.query=''; self.selected=0
                    elif path.is_file():
                        dest=save_import(path); newtex=load_image(dest)
                        self.renderer=Renderer(np.rot90(newtex,3).copy() if self.args.vertical else newtex,getattr(self.args,"quality","auto"))
                        self.path=dest; self.archive_id=None; self.mode='stage'; self.goto=None; self.message='Imported and saved: '+clean(path.name)
                    else: self.error='Path does not exist.'
                except (OSError,ValueError,Image.DecompressionBombError) as e: self.error=clean(e)
            elif key=='BACKSPACE': self.goto=self.goto[:-1]
            elif key=='\x15': self.goto=''
            elif len(key)==1 and key.isprintable(): self.goto+=key
            return True
        if self.mode in ('countries','archive','browser','collection'):
            self.entries=self.items()
            self.selected=min(self.selected,max(0,len(self.entries)-1))
            if key=='ESC': self.mode='stage'; self.error=''
            elif key=='UP': self.selected=max(0,self.selected-1)
            elif key=='DOWN': self.selected=min(max(0,len(self.entries)-1),self.selected+1)
            elif key=='PGUP': self.selected=max(0,self.selected-12)
            elif key=='PGDOWN': self.selected=min(max(0,len(self.entries)-1),self.selected+12)
            elif key=='HOME': self.selected=0
            elif key=='END': self.selected=max(0,len(self.entries)-1)
            elif key=='ENTER': self.accept()
            elif key=='TAB':
                modes=['countries','archive','browser','collection']; self.open(modes[(modes.index(self.mode)+1)%len(modes)])
            elif key in ('\x06','\x12') and self.mode=='archive':
                direction=-1 if key=='\x12' else 1
                self.group=self.groups[(self.groups.index(self.group)+direction)%len(self.groups)]
                self.selected=0; self.offset=0
            elif key=='\x0f' and self.mode=='archive' and self.entries:
                self.details(self.entries[self.selected][2].split(':',1)[1])
            elif key=='LEFT' and self.mode=='browser':
                self.folder=self.folder.parent; self.query=''; self.selected=0
            elif key=='\x07' and self.mode=='browser': self.goto=''
            elif key=='\x04' and self.mode=='browser': self.show_hidden=not self.show_hidden
            elif key=='BACKSPACE': self.query=self.query[:-1]; self.selected=0
            elif len(key)==1 and key.isprintable(): self.query+=key; self.selected=0
            return True
        if self.mode=='details':
            if key in ('ESC','ENTER','d'): self.mode=self.info_return
            elif key in ('DOWN','PGDOWN'): self.info_scroll+=1 if key=='DOWN' else 10
            elif key in ('UP','PGUP'): self.info_scroll=max(0,self.info_scroll-(1 if key=='UP' else 10))
            return True
        if self.mode=='help':
            if key: self.mode='stage'
            return True
        if self.mode=='settings':
            if key in ('ESC','s'): self.mode='stage'
            elif key=='UP': self.setting=(self.setting-1)%5
            elif key=='DOWN': self.setting=(self.setting+1)%5
            elif key in ('LEFT','RIGHT','ENTER',' '):
                direction=-1 if key=='LEFT' else 1
                if self.setting==0: self.wind=round(max(0,min(2.5,self.wind+.1*direction)),1)
                if self.setting==1: self.args.fps=max(5,min(60,self.args.fps+5*direction))
                if self.setting==2:
                    colors=['truecolor','256','none']; self.color=colors[(colors.index(self.color)+direction)%3]
                if self.setting==3: self.args.vertical=not self.args.vertical; self.reload()
                if self.setting==4: self.args.blocks=not self.args.blocks
            return True
        if key=='q': return False
        if key in ('f','/'): self.open('countries')
        elif key=='a': self.open('archive')
        elif key=='d' and self.archive_id: self.details(self.archive_id)
        elif key=='i': self.open('browser')
        elif key=='b': self.open('collection')
        elif key=='s': self.open('settings')
        elif key=='?': self.open('help')
        elif key=='TAB': self.side=not self.side
        elif key==' ': self.paused=not self.paused
        elif key in ('LEFT','h'): self.yaw-=.1
        elif key in ('RIGHT','l'): self.yaw+=.1
        elif key in ('UP','k'): self.pitch=min(.9,self.pitch+.1)
        elif key in ('DOWN','j'): self.pitch=max(-.9,self.pitch-.1)
        elif key in ('+','='): self.wind=min(2.5,self.wind+.1)
        elif key=='-': self.wind=max(0,self.wind-.1)
        elif key=='v': self.args.vertical=not self.args.vertical; self.reload()
        elif key=='c': self.color={'truecolor':'256','256':'none','none':'truecolor'}[self.color]
        elif key=='r': self.yaw=.24; self.pitch=.12; self.wind=1.
        elif key in ('n','p'):
            codes=list(COUNTRIES); self.code=codes[(codes.index(self.code)+(1 if key=='n' else -1))%len(codes)]
            self.path=None; self.archive_id=None; self.reload()
        return True

    def details(self,archive_id):
        self.info_record=ARCHIVE_BY_ID[archive_id]
        self.info_return=self.mode; self.info_scroll=0; self.mode='details'

    def header(self,s,title,subtitle):
        s.text(0,0,'  F L A G W A V E                                      3D ASCII CLOTH',style=CYAN)
        s.text(0,1,'  '+title,style=WHITE)
        s.text(0,2,'  '+subtitle,style=DIM)
        s.text(0,3,'-'*s.w,style=DIM)

    def draw(self):
        s=Screen()
        # Clear each row so layout changes and resize never leave stale content.
        layout=(self.mode,s.w,s.h,s.ox,s.oy,self.side)
        if layout!=self.last_layout: s.parts.append("\x1b[2J")
        if layout!=self.last_layout or self.mode!='stage':
            for y in range(s.h): s.text(0,y,'')
        self.last_layout=layout
        if s.w<48 or s.h<16:
            s.text(0,0,'FlagWave: enlarge terminal to 49 columns x 16 rows.',style=CYAN)
            s.text(0,2,'q / Ctrl-C: quit'); s.present(); return
        if self.mode in ('countries','archive','browser','collection'):
            self.draw_picker(s)
        elif self.mode=='details':
            e=self.info_record
            self.header(s,'FLAG DETAILS','Up/down: scroll   Esc: back')
            paragraphs=[e['name'],'Period: '+e['period'],'Categories: '+', '.join(e['tags']),
                        'ID: '+e['id'],'Source: '+e['source'],'Artwork: '+e['source_file'],
                        'License: '+e['license'],'Credit: '+e['credit'],
                        'Description: '+e.get('description','')]
            lines=[]
            for paragraph in paragraphs: lines.extend(textwrap.wrap(clean(paragraph),max(15,s.w-6)) or ['']); lines.append('')
            visible=s.h-8; self.info_scroll=min(self.info_scroll,max(0,len(lines)-visible))
            for row,line in enumerate(lines[self.info_scroll:self.info_scroll+visible]): s.text(3,5+row,line,s.w-6,WHITE)
        elif self.mode=='settings':
            self.header(s,'SETTINGS','Up/down: choose   Left/right: adjust   Esc: back')
            items=[('Wind strength',f'{self.wind:.1f}'),('Target frame rate',f'{self.args.fps} FPS'),
                   ('Colour mode',self.color),('Artwork orientation','Vertical' if self.args.vertical else 'Horizontal'),
                   ('ASCII style','Solid #' if self.args.blocks else 'Shaded characters')]
            for i,(label,value) in enumerate(items): s.text(3,5+i*2,f' {label:<24} {value}',s.w-6,SELECT if i==self.setting else WHITE)
        elif self.mode=='help':
            self.header(s,'KEYBOARD GUIDE','Press any key to return')
            help_lines=['a         Historical / military / ideology archive','f or /    Search the 195 country flags','i         Browse folders and import an image','b         Open your saved imported images',
                        's         Settings: wind, FPS, colour, orientation','Arrows    Orbit and tilt the camera','+ / -     Adjust wind strength','Space     Pause / resume cloth',
                        'n / p     Next / previous country','v / c     Rotate artwork / cycle colours','Tab       Toggle stage sidebar','r         Reset wind and camera','q         Quit (Ctrl-C works on every screen)']
            for i,line in enumerate(help_lines[:s.h-6]): s.text(3,5+i,line)
        else:
            name=clean(ARCHIVE_BY_ID[self.archive_id]['name'] if self.archive_id else (self.path.stem.rsplit('-',1)[0] if self.path else COUNTRIES[self.code]))
            self.header(s,name,('PAUSED' if self.paused else 'LIVE')+f'   |   Wind {self.wind:.1f}   |   {self.fps:.0f}/{self.args.fps} FPS   |   '+self.color)
            sidebar=25 if self.side and s.w>=90 else 0
            if sidebar:
                lines=[('EXPLORE',CYAN),('f  Country flags',WHITE),('a  Historical archive',WHITE),('i  Import image',WHITE),('b  My images',WHITE),('s  Settings',WHITE),('?  Keyboard guide',WHITE),('',DIM),(f'{195+len(ARCHIVE)} offline flags',DIM),('PNG / JPG / WebP',DIM),('No GPU required',DIM),('',DIM),('Arrows  Orbit camera',DIM),('+ / -   Wind',DIM),('Space   Pause',DIM),('Tab     Hide sidebar',DIM)]
                for i,(line,style) in enumerate(lines[:s.h-8]): s.text(2,5+i,line,22,style)
            quality=getattr(self.args,'quality','auto')
            capw,caph={'low':(90,34),'auto':(140,50),'high':(200,70)}[quality]
            aw=min(s.w-sidebar,max(50,int(capw*self.render_scale)))
            ah=min(max(1,s.h-7),max(18,int(caph*self.render_scale)))
            ax=sidebar+max(0,(s.w-sidebar-aw)//2); ay=4+max(0,(s.h-7-ah)//2)
            s.art(ax,ay,self.renderer.frame(aw,ah,self.clock,self.wind,self.yaw,self.pitch,self.color,self.args.blocks))
        s.text(0,s.h-2,'  '+(self.error or self.message or 'Ready. Choose a country or import your own flag.'),style='\x1b[91m' if self.error else DIM)
        if self.mode in ('countries','archive','browser','collection'):
            footer=' Enter: select  Esc: back  Tab: switch  Type: filter'
            if self.mode=='archive': footer=' Ctrl-F/R: category  Ctrl-O: details  Enter: wave  Esc: back'
            if self.mode=='browser': footer=' Enter: open/import  Left: parent  Ctrl-G: path  Esc: back'
        else: footer=' f: flags  a: archive  i: import  b: images  s: settings  d: details  q: quit'
        s.text(0,s.h-1,footer,style=SELECT)
        s.present()

    def draw_picker(self,s):
        title={'countries':'COUNTRY FLAGS','archive':'HISTORICAL & ALTERNATE FLAGS','browser':'IMPORT IMAGE','collection':'MY IMAGES'}[self.mode]
        subtitle=clean(self.folder) if self.mode=='browser' else ('195 included flags. Type to search.' if self.mode=='countries' else 'Imported images are saved here for reuse.')
        if self.mode=='archive': subtitle=f'Category: {self.group} | {len(ARCHIVE)} designs | Ctrl-F / Ctrl-R: cycle categories'
        self.header(s,title,subtitle)
        self.entries=self.items(); self.selected=min(self.selected,max(0,len(self.entries)-1))
        if self.goto is not None: s.text(2,4,'Path > '+self.goto,style=CYAN)
        else: s.text(2,4,'Search > '+self.query+'_',style=CYAN)
        visible=max(1,s.h-9)
        if self.selected<self.offset: self.offset=self.selected
        if self.selected>=self.offset+visible: self.offset=self.selected-visible+1
        self.offset=max(0,min(self.offset,max(0,len(self.entries)-visible)))
        pane=max(25,s.w//2) if s.w>=90 else s.w-4
        for row,entry in enumerate(self.entries[self.offset:self.offset+visible]):
            idx=row+self.offset; label=entry[0]
            s.text(2,6+row,(' > ' if idx==self.selected else '   ')+label,pane-3,SELECT if idx==self.selected else WHITE)
        if not self.entries: s.text(3,7,'No images yet. Press Tab to import.' if self.mode=='collection' else 'No matches.',pane-4,DIM)
        if s.w>=90 and self.entries:
            entry=self.entries[self.selected]; _,path,_,isdir=entry
            x=pane+2; width=s.w-x-2
            s.text(x,5,'PREVIEW' if not isdir else 'FOLDER',width,CYAN)
            if isdir:
                s.text(x,8,'Enter to open this folder.',width,DIM)
                s.text(x,10,'Ctrl-G: type/paste a path',width,DIM)
                s.text(x,11,'Ctrl-D: toggle hidden files',width,DIM)
            else:
                try:
                    key=(str(path),self.args.vertical)
                    if key!=self.preview_key:
                        tex=load_image(path)
                        self.preview=Renderer(np.rot90(tex,3).copy() if self.args.vertical else tex,getattr(self.args,"quality","auto"))
                        self.preview_key=key
                    s.art(x,6,self.preview.frame(min(width,80),min(35,max(4,s.h-13)),self.clock,1,.24,.12,self.color))
                    s.text(x,s.h-6,'Enter to '+('import and save' if self.mode=='browser' else 'wave this flag'),width,CYAN)
                    if self.mode=='archive':
                        info=ARCHIVE_BY_ID[entry[2].split(':',1)[1]]
                        s.text(x,s.h-5,info['period'],width,DIM)
                        s.text(x,s.h-4,', '.join(info['tags']),width,DIM)
                except (OSError,ValueError,Image.DecompressionBombError) as e:
                    s.text(x,8,'Cannot preview this image.',width,DIM)
                    s.text(x,9,clean(e),width,DIM)
        s.text(2,s.h-3,f'{self.selected+1 if self.entries else 0} / {len(self.entries)}   |   PgUp/PgDn: scroll',style=DIM)

    def run(self):
        count=0; previous=time.monotonic()
        with Terminal() as terminal:
            keys=Keys(terminal.fd)
            while True:
                start=time.monotonic(); dt=min(start-previous,.2); previous=start
                if not self.paused: self.clock+=dt
                # Process queued events without dropping batched typing/pastes.
                for _ in range(512):
                    key=keys.read()
                    if not key: break
                    if not self.input(key): return
                self.draw(); count+=1
                if self.args.frames and count>=self.args.frames: return
                elapsed=time.monotonic()-start
                if getattr(self.args,"quality","auto")=="auto":
                    active=self.renderer if self.mode=="stage" else self.preview
                    if active is not None and elapsed>1/self.args.fps:
                        active.sample_scale=max(.45,active.sample_scale-.1)
                        if self.mode=="stage" and self.render_scale>.6:
                            self.render_scale=round(max(.6,self.render_scale-.1),1); self.last_layout=None
                self.fps=.85*self.fps+.15*(1/max(elapsed,1/self.args.fps))
                time.sleep(max(0,1/self.args.fps-elapsed))
