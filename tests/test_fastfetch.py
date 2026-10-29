import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import fastfetch_integration as fetch
import tui
from test_tui import options


class FastfetchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env=patch.dict(os.environ,{'XDG_CONFIG_HOME':self.temp.name+'/config space',
                                      'XDG_DATA_HOME':self.temp.name+"/data 'quoted'$"})
        self.env.start();self.addCleanup(self.env.stop)

    def test_preserve_jsonc_and_restore_exact_bytes(self):
        original=b'\xef\xbb\xbf{\r\n // custom layout\r\n "logo": {"type":"builtin","source":"arch"},\r\n "modules": ["title", {"type":"custom","format":"https://example.org/logo,}"},],\r\n "display": {"separator":" -> "},\r\n}\r\n'
        target=fetch.config_path();target.parent.mkdir(parents=True);target.write_bytes(original)
        target.chmod(0o640)
        frame='\x1b[38;2;255;0;0m##\x1b[0m\r\n #\x1b[0m'
        fetch.apply_logo(frame)
        changed=target.read_bytes()
        self.assertIn(b'// custom layout\r\n',changed)
        self.assertIn(b'"modules": ["title", {"type":"custom","format":"https://example.org/logo,}"},],',changed)
        self.assertEqual(target.stat().st_mode&0o777,0o640)
        self.assertIn(b'file-raw',changed)
        self.assertEqual((fetch.data_dir()/'original.config.jsonc').read_bytes(),original)
        self.assertEqual(fetch.export_logo(frame).read_text(),'\x1b[38;2;255;0;0m##\x1b[0m\n #\x1b[0m\n')
        fetch.apply_logo('a second logo')
        fetch.restore_config()
        self.assertEqual(target.read_bytes(),original)

    def test_insert_missing_logo_without_reformatting(self):
        text='{ /* keep this */ "modules": [{"type":"custom", "format":"logo"}], }\n'
        updated=fetch.logo_patch(text,{'type':'none'})
        self.assertIn('/* keep this */ "modules": [{"type":"custom", "format":"logo"}], }',updated)
        self.assertIn('"logo": {"type": "none"}',updated)
        self.assertEqual(json.loads(fetch.logo_patch('{}',{'type':'none'}))['logo']['type'],'none')
        self.assertEqual(json.loads(fetch.logo_patch('{"logo":"arch"}',{'type':'none'}))['logo']['type'],'none')

    def test_new_config_restore_and_external_edits(self):
        target=fetch.apply_logo('flag')
        fetch.restore_config();self.assertFalse(target.exists())
        fetch.apply_logo('flag')
        target.write_text(target.read_text()+'\n// later user edit\n')
        before=target.read_bytes()
        with self.assertRaisesRegex(ValueError,'changed outside'): fetch.restore_config()
        with self.assertRaisesRegex(ValueError,'changed outside'): fetch.apply_logo('other flag')
        self.assertEqual(target.read_bytes(),before)
        self.assertTrue((fetch.data_dir()/'state.json').exists())

    def test_invalid_config_and_symlink_not_modified(self):
        target=fetch.config_path();target.parent.mkdir(parents=True)
        for bad in ['{"logo":', '[1,2]', '{"logo":1,"logo":2}', '{ /* unterminated }']:
            target.write_text(bad)
            with self.assertRaises(ValueError): fetch.apply_logo('flag')
            self.assertEqual(target.read_text(),bad)
            self.assertFalse(fetch.data_dir().exists())
        other=target.with_name('dotfiles.jsonc');other.write_text('{}')
        target.unlink();target.symlink_to(other)
        with self.assertRaisesRegex(ValueError,'symlink'): fetch.apply_logo('flag')
        self.assertEqual(other.read_text(),'{}')

    def test_preview_subprocess_and_errors(self):
        with patch('shutil.which',return_value=None):
            with self.assertRaisesRegex(ValueError,'not installed'): fetch.system_info()
        result=subprocess.CompletedProcess([],0,'\x1b[31mOS: Linux\x1b[0m\n\x1b]0;title\x07CPU: Test\n','')
        with patch('shutil.which',return_value='/usr/bin/fastfetch'),patch('subprocess.run',return_value=result) as run:
            self.assertEqual(fetch.system_info(),['OS: Linux','CPU: Test'])
            self.assertEqual(run.call_args.args[0],['/usr/bin/fastfetch','--logo','none','--pipe','true'])
            self.assertNotIn('shell',run.call_args.kwargs)
        with patch('shutil.which',return_value='fastfetch'),patch('subprocess.run',return_value=subprocess.CompletedProcess([],1,'','bad config')):
            with self.assertRaisesRegex(ValueError,'bad config'): fetch.system_info()

    def test_tui_actions_imports_bounds_and_animation(self):
        app=tui.App(options(),'au');app.input('t');self.assertEqual(app.mode,'fastfetch')
        for _ in range(100): app.input('LEFT')
        self.assertEqual(app.fetch_width,20)
        app.input('DOWN')
        for _ in range(100): app.input('RIGHT')
        self.assertEqual(app.fetch_height,28)
        app.input('DOWN')
        with patch('fastfetch_integration.system_info',return_value=['OS: Test']): app.input('ENTER')
        self.assertEqual(app.mode,'fastfetch-preview');app.orbit=True;before=app.yaw;app.advance(1);self.assertNotEqual(before,app.yaw)
        app.input(' ');before=app.clock;app.advance(1);self.assertEqual(before,app.clock)
        app.input('ESC');app.input('DOWN');app.input('ENTER')
        self.assertTrue(list(fetch.data_dir().glob('*.ansi')))
        app.input('DOWN');app.input('ENTER');self.assertTrue(fetch.config_path().exists())
        app.input('DOWN');app.input('ENTER');self.assertFalse(fetch.config_path().exists())
        app.input('ESC');app.open('browser');app.folder=tui.ROOT/'flags';app.query='jp.png';app.input('ENTER')
        app.input('t');app.fetch_setting=3;app.input('ENTER');self.assertFalse(app.error)
        for size in [(49,16),(100,30),(1000,300)]:
            with patch('shutil.get_terminal_size',return_value=os.terminal_size(size)),patch('sys.stdout',new_callable=io.StringIO): app.draw()


if __name__=='__main__': unittest.main()
