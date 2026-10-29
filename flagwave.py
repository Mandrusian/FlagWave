#!/usr/bin/env python3
"""FlagWave: perspective cloth in your terminal. No GPU or window system needed."""
import argparse
import json
import math
import os
from pathlib import Path
import select
import shutil
import signal
import sys
import termios
import time
import tty

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
COUNTRIES = json.loads((ROOT / 'countries.json').read_text())
ARCHIVE = json.loads((ROOT / 'archive.json').read_text())
ARCHIVE_BY_ID = {entry['id']:entry for entry in ARCHIVE}
RAMP = np.array(list('.,:;irsXA253hMHGS#9B&@'))


def load_image(path):
    with Image.open(path) as source:
        source = ImageOps.exif_transpose(source)
        source.thumbnail((640, 640))
        rgba = source.convert('RGBA')
        bg = Image.new('RGBA', rgba.size, (0, 0, 0, 0))
        bg.alpha_composite(rgba)
        return np.asarray(bg).copy()


def surface(u, v, t, wind):
    """Hoist fixed at u=0; traveling waves move cloth in Y and Z."""
    phase = 10*u - t*3.3 + 2.2*v
    z = wind*u*(.29*np.sin(phase) + .10*np.sin(17*u-t*5.1-5*v))
    y = .5-v + wind*u*(.08*np.sin(8*u-t*2.5+3*v) - .055*u)
    x = u - wind*.025*u*np.cos(phase)
    return x, y, z


class Renderer:
    def __init__(self, texture, quality="auto"):
        self.texture = texture
        self.quality=quality
        self.sample_scale=1.0
        self.grid_key = None

    def frame(self, width, height, t, wind=1., yaw=.24, pitch=.12, color='truecolor', blocks=False):
        # Supersample the cloth, project into character cells, and depth-test.
        key = (width, height, self.quality, round(self.sample_scale,1))
        if self.grid_key != key:
            factor={"low":1.35,"auto":2.3,"high":5.0}[self.quality]*self.sample_scale
            nu = max(45, min(600, int(width*factor)))
            nv = max(30, min(400, int(height*factor*1.3)))
            self.u, self.v = np.meshgrid(np.linspace(0,1,nu), np.linspace(0,1,nv))
            self.grid_key = key
        u, v = self.u, self.v
        tex = self.texture
        aspect = tex.shape[1] / tex.shape[0]
        x, y, z = surface(u, v, t, wind)
        x = (x-.5)*aspect
        # Surface normals give moving highlights and darker folds.
        dyv, dyu = np.gradient(y)
        dzv, dzu = np.gradient(z)
        dxv, dxu = np.gradient(x)
        nx = dyu*dzv-dzu*dyv
        ny = dzu*dxv-dxu*dzv
        nz = dxu*dyv-dyu*dxv
        norm = np.sqrt(nx*nx+ny*ny+nz*nz) + 1e-12
        light = .42+.58*np.abs((nx*.25+ny*.35+nz*.90)/norm)
        cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        xx, zz = x*cy+z*sy, -x*sy+z*cy
        yy, zz = y*cp-zz*sp, y*sp+zz*cp
        perspective = 3.8/(3.8-zz)
        scale = min(width*.70/max(aspect, .6), height*1.1)
        sx = np.rint(width*.52 + xx*perspective*scale).astype(int)
        syy = np.rint(height*.47 - yy*perspective*scale*.50).astype(int)
        tx = np.clip((u*(tex.shape[1]-1)).astype(int),0,tex.shape[1]-1)
        ty = np.clip((v*(tex.shape[0]-1)).astype(int),0,tex.shape[0]-1)
        rgba = tex[ty,tx]
        valid = (sx>=0)&(sx<width)&(syy>=0)&(syy<height)&(rgba[:,:,3]>100)
        idx = (syy[valid]*width+sx[valid]).ravel()
        depths = zz[valid].ravel()
        # Last point at each pixel is nearest the camera.
        order = np.lexsort((depths,idx))
        sorted_idx = idx[order]
        last = np.r_[sorted_idx[1:] != sorted_idx[:-1], True] if len(idx) else np.array([],bool)
        chosen = order[last]
        target = idx[chosen]
        rgb = np.clip(rgba[:,:,:3][valid][chosen]*light[valid][chosen,None],0,255).astype(np.uint8)
        chars = np.full(width*height, ' ', dtype='<U1')
        # Keep black regions visible; shade comes from both ink and cloth normals.
        lum = (rgb @ np.array([.2126,.7152,.0722]))/255
        value = np.clip(.30+.40*light[valid][chosen]+.30*lum,0,1)
        chars[target] = '#' if blocks else RAMP[(value*(len(RAMP)-1)).astype(int)]
        colors = np.zeros((width*height,3),np.uint8)
        colors[target] = rgb
        rows=[]
        for row in range(height):
            pieces=[]; previous=None
            for col in range(width):
                i=row*width+col; ch=chars[i]
                if ch==' ':
                    pieces.append(' '); continue
                r,g,b=map(int,colors[i])
                if color=='truecolor': code=f'\x1b[38;2;{r};{g};{b}m'
                elif color=='256': code=f'\x1b[38;5;{16+36*round(r/51)+6*round(g/51)+round(b/51)}m'
                else: code=''
                if code!=previous: pieces.append(code); previous=code
                pieces.append(ch)
            rows.append(''.join(pieces)+'\x1b[0m')
        return '\r\n'.join(rows)


def clean(text):
    return ''.join(c if c.isprintable() else '?' for c in str(text))


class Terminal:
    def __enter__(self):
        self.fd=sys.stdin.fileno(); self.old=termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        sys.stdout.write('\x1b[?1049h\x1b[?25l\x1b[2J'); sys.stdout.flush()
        return self

    def __exit__(self, *args):
        termios.tcsetattr(self.fd,termios.TCSADRAIN,self.old)
        sys.stdout.write('\x1b[0m\x1b[?25h\x1b[?1049l'); sys.stdout.flush()

    def key(self):
        if select.select([self.fd],[],[],0)[0]:
            return os.read(self.fd,128).decode(errors='ignore')
        return ''

    def prompt(self, label):
        termios.tcsetattr(self.fd,termios.TCSADRAIN,self.old)
        sys.stdout.write('\x1b[2J\x1b[H\x1b[?25h'+label); sys.stdout.flush()
        try: return input().strip()
        finally:
            tty.setcbreak(self.fd)
            sys.stdout.write('\x1b[?25l\x1b[2J'); sys.stdout.flush()


def resolve(value):
    value=value.casefold().strip()
    aliases={'uk':'gb','usa':'us','china':'cn','vatican':'va','palestine':'ps','south korea':'kr','north korea':'kp','russia':'ru','turkey':'tr'}
    value=aliases.get(value,value)
    if value in COUNTRIES: return value
    exact=[c for c,n in COUNTRIES.items() if n.casefold()==value]
    matches=exact or [c for c,n in COUNTRIES.items() if value in n.casefold()]
    if len(matches)==1: return matches[0]
    raise ValueError('Enter a country code or a unique country name. Try --list.')


def resolve_archive(value):
    value=value.casefold().strip()
    aliases={'ccp':'cpc','cpa':'cpaus','cp-australia':'cpaus','rek':'red-eureka','red eureka':'red-eureka','communist-eureka':'red-eureka','soviet union':'ussr','soviet-union':'ussr','su':'ussr','ussr-ww2':'ussr-1936',
             'germany-ww2':'nazi-germany','nazi':'nazi-germany','east germany':'east-germany',
             'gdr':'east-germany','rising-sun':'japan-army'}
    value=aliases.get(value,value)
    if value in ARCHIVE_BY_ID: return value
    matches=[entry['id'] for entry in ARCHIVE if value==entry['name'].casefold()]
    matches=matches or [entry['id'] for entry in ARCHIVE if value in entry['name'].casefold()]
    if len(matches)==1: return matches[0]
    raise ValueError('No unique flag match. Try --list, --list-archive, or the TUI archive (a).')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('country',nargs='?',default='red-eureka',help='country code/name or archive ID (default red-eureka)')
    p.add_argument('--image',type=Path,help='PNG/JPG/WebP/GIF/BMP; first frame for animated images')
    p.add_argument('--list',action='store_true',help='list the 195 included flags')
    p.add_argument('--list-archive',action='store_true',help='list historical, military and political flag IDs')
    p.add_argument('--archive',action='store_true',help='open the historical and alternate flag picker')
    p.add_argument('--random',action='store_true',help='start with a random flag')
    p.add_argument('--fps',type=int,default=20)
    p.add_argument('--quality',choices=['auto','low','high'],default='auto',help='auto adapts sampling to your CPU')
    p.add_argument('--low-power',action='store_true',help='12 FPS with low-cost sampling')
    p.add_argument('--orbit',action='store_true',help='slowly spin the camera around the waving flag')
    p.add_argument('--orbit-speed',type=float,default=6.,help='orbit degrees per second, -60..60 excluding zero (default 6)')
    p.add_argument('--wind',type=float,default=1.)
    p.add_argument('--color',choices=['truecolor','256','none'],default='truecolor')
    p.add_argument('--mono',action='store_true',help='uncoloured ASCII')
    p.add_argument('--blocks',action='store_true',help='use solid ASCII # instead of shading characters')
    p.add_argument('--vertical',action='store_true',help='rotate the image to make a hanging banner')
    p.add_argument('--frames',type=int,default=0,help='stop after this many frames (0 = unlimited)')
    args=p.parse_args()
    if args.low_power: args.quality="low"; args.fps=12
    if args.list_archive:
        for entry in ARCHIVE:
            print(f"{entry['id']:<24} {entry['name']} | {entry['period']} | {', '.join(entry['tags'])}")
        return
    if args.list:
        for c,n in COUNTRIES.items(): print(f'{c.upper()}  {n}')
        return
    if not 1<=args.fps<=60: p.error('--fps must be 1..60')
    if not math.isfinite(args.wind) or not 0<=args.wind<=2.5: p.error('--wind must be 0..2.5')
    if not math.isfinite(args.orbit_speed) or not 0<abs(args.orbit_speed)<=60: p.error('--orbit-speed must be nonzero within -60..60')
    if args.frames<0: p.error('--frames must be non-negative')
    if not sys.stdin.isatty() or not sys.stdout.isatty(): p.error('run in an interactive terminal; --list works in pipes')
    import random
    try: code=random.choice(list(COUNTRIES)) if args.random else resolve(args.country)
    except ValueError:
        try:
            args.archive_id=resolve_archive(args.country)
            code='au'
        except ValueError as e: p.error(str(e))
    from tui import App
    def stop(*_): raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    try:
        app=App(args,code)
    except (OSError,ValueError,Image.DecompressionBombError) as e: p.error(str(e))
    try: app.run()
    except (KeyboardInterrupt,EOFError): pass


if __name__=='__main__': main()
