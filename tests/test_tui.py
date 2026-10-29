import argparse
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import flagwave as core
import tui


def options():
    return argparse.Namespace(image=None,wind=1.,mono=False,color='truecolor',vertical=False,blocks=False,fps=20,frames=0)


class ApplicationTests(unittest.TestCase):
    def test_catalog_and_assets(self):
        self.assertEqual(len(core.COUNTRIES),195)
        for code in core.COUNTRIES:
            image=core.load_image(core.ROOT/'flags'/f'{code}.png')
            self.assertEqual(image.shape[2],4)

    def test_surface_pinned_and_animated(self):
        u=np.array([0.,1.]); v=np.array([.3,.3])
        a=core.surface(u,v,0,1); b=core.surface(u,v,1,1)
        self.assertTrue(all(x[0]==y[0] for x,y in zip(a,b)))
        self.assertTrue(any(x[1]!=y[1] for x,y in zip(a,b)))
        r=core.Renderer(core.load_image(core.ROOT/'flags/au.png'))
        self.assertNotEqual(r.frame(70,20,0),r.frame(70,20,1))

    def test_live_search_and_selection(self):
        app=tui.App(options(),'au'); app.input('f')
        for key in 'china': app.input(key)
        self.assertEqual(len(app.items()),1)
        app.input('ENTER')
        self.assertEqual(app.code,'cn'); self.assertEqual(app.mode,'stage')

    def test_import_saved_and_reusable(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'XDG_DATA_HOME':root}):
            path=Path(root)/'custom red.png'; Image.new('RGBA',(160,100),'red').save(path)
            app=tui.App(options(),'au'); app.open('browser'); app.folder=Path(root)
            app.query='custom red'; app.input('ENTER')
            self.assertEqual(app.mode,'stage'); self.assertTrue(app.path.is_file())
            self.assertNotEqual(app.path,path)
            path.unlink()
            app.reload(); app.open('collection')
            self.assertEqual(len(app.items()),1)
            app.input('ENTER'); self.assertEqual(app.mode,'stage')

    def test_bad_import_preserves_active_flag(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'broken.png';path.write_text('not a PNG')
            app=tui.App(options(),'au'); renderer=app.renderer
            app.open('browser');app.folder=Path(root);app.query='broken'
            app.input('ENTER')
            self.assertTrue(app.error);self.assertIs(app.renderer,renderer)

    def test_path_import_and_cancel(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'XDG_DATA_HOME':root}):
            path=Path(root)/'hello.png';Image.new('RGB',(50,80),'blue').save(path)
            app=tui.App(options(),'au');app.open('browser');app.input('\x07')
            self.assertIsNotNone(app.goto);app.input('ESC');self.assertIsNone(app.goto)
            app.goto=str(path);app.input('ENTER')
            self.assertEqual(app.mode,'stage');self.assertTrue(app.path.is_file())

    def test_batched_keys(self):
        master,slave=pty.openpty()
        try:
            import tty
            tty.setcbreak(slave)
            os.write(master,b'china\x1b[A\r')
            self.assertTrue(select.select([slave],[],[],1)[0])
            keys=tui.Keys(slave)
            self.assertEqual([keys.read() for _ in range(7)],list('china')+['UP','ENTER'])
        finally: os.close(master);os.close(slave)

    def test_settings_and_small_empty_lists(self):
        app=tui.App(options(),'au'); app.open('settings')
        app.input('RIGHT');self.assertAlmostEqual(app.wind,1.1)
        app.setting=3; app.input('ENTER');self.assertTrue(app.args.vertical)
        app.open('countries');app.query='nonexistentzzz'; app.input('DOWN');app.input('ENTER')
        self.assertEqual(app.mode,'countries'); self.assertEqual(app.selected,0)

    def test_archive_sources_and_images(self):
        self.assertGreaterEqual(len(core.ARCHIVE),60)
        self.assertEqual(len(core.ARCHIVE),len(core.ARCHIVE_BY_ID))
        for entry in core.ARCHIVE:
            image=core.load_image(core.ROOT/entry['asset'])
            self.assertEqual(image.shape[2],4)
            self.assertTrue(entry['source'].startswith('https://commons.wikimedia.org/wiki/'))
            if entry['license'].startswith('CC BY'): self.assertTrue(entry['credit'])
            self.assertTrue(entry['license'])
        for flag in ['ussr','ussr-1936','nazi-germany','pnf','buf','black-flag','mutualism']:
            self.assertIn(flag,core.ARCHIVE_BY_ID)

    def test_archive_search_selection_and_details(self):
        app=tui.App(options(),'au'); app.input('a')
        app.query='soviet wwii'; app.input('ENTER')
        self.assertEqual(app.archive_id,'ussr-1936')
        self.assertEqual(app.mode,'stage')
        app.input('d'); self.assertEqual(app.mode,'details')
        self.assertEqual(app.info_record['id'],'ussr-1936')
        app.input('ESC'); app.input('v');app.input('n')
        self.assertIsNone(app.archive_id)

    def test_archive_categories_and_cli(self):
        app=tui.App(options(),'au'); app.open('archive'); app.group='Fascist'
        self.assertTrue(all('Fascist' in core.ARCHIVE_BY_ID[item[2].split(':')[1]]['tags'] for item in app.items()))
        app.input('\x06'); self.assertNotEqual(app.group,'Fascist')
        self.assertEqual(core.resolve_archive('soviet union'),'ussr')
        self.assertEqual(core.resolve_archive('germany-ww2'),'nazi-germany')
        result=subprocess.run([sys.executable,str(core.ROOT/'flagwave.py'),'--list-archive'],capture_output=True,text=True,check=True)
        self.assertEqual(len(result.stdout.splitlines()),len(core.ARCHIVE))

    def test_terminal_restoration(self):
        master,slave=pty.openpty(); old=termios.tcgetattr(slave)
        import fcntl
        fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,100,0,0))
        temp=tempfile.TemporaryDirectory()
        env=dict(os.environ,XDG_DATA_HOME=temp.name)
        proc=subprocess.Popen([sys.executable,str(core.ROOT/'flagwave.py'),'--fps','15'],stdin=slave,stdout=slave,stderr=slave,env=env)
        output=bytearray()
        def drain(seconds):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                if select.select([master],[],[],.02)[0]: output.extend(os.read(master,65536))
        try:
            drain(.5)
            os.write(master,b'fchina\r');drain(.5)
            os.write(master,b'i');drain(.15)
            os.write(master,b'\x07');drain(.15)
            os.write(master,str(core.ROOT/'flags/jp.png').encode()+b'\r');drain(.3)
            os.write(master,b'b');drain(.25)
            os.write(master,b'\x1b');drain(.2)
            os.write(master,b'q');drain(.3)
            proc.wait(timeout=5)
            self.assertEqual(proc.returncode,0)
            self.assertEqual(termios.tcgetattr(slave),old)
            self.assertIn(b'China',output)
            self.assertIn(b'MY IMAGES',output)
            self.assertEqual(len(list((Path(temp.name)/'flagwave/imports').glob('*.png'))),1)
            self.assertNotIn(b'Traceback',output)
        finally:
            if proc.poll() is None: proc.terminate();proc.wait(timeout=5)
            os.close(master);os.close(slave);temp.cleanup()


if __name__=='__main__': unittest.main()
