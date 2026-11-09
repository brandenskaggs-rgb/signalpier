import json
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Server, Workbench, command, detect_peaks, parse_events, parse_power, settings


class ReceiverTests(unittest.TestCase):
    def test_stitches_hops_and_preserves_invalid_bins(self):
        rows = '2026-11-07,12:00:00,100,130,10,8,-60,nan,-40\n2026-11-07,12:00:00,130,150,10,8,-50,-70\n'
        sweeps = parse_power(rows)
        self.assertEqual(len(sweeps), 1)
        self.assertEqual(sweeps[0]['points'], [[100.0,-60.0],[110.0,None],[120.0,-40.0],[130.0,-50.0],[140.0,-70.0]])
        json.dumps(sweeps, allow_nan=False)

    def test_peak_candidates_exclude_noise_and_missing_data(self):
        points = [[0,-70],[1,-71],[2,-30],[3,-69],[4,-70],[5,None],[6,-20],[7,-70]]
        self.assertEqual([p['frequency_hz'] for p in detect_peaks(points)], [2])

    def test_rejects_invalid_ranges_and_command_injection(self):
        for config in ({'start_mhz':500,'end_mhz':400}, {'end_mhz':900},
                       {'start_mhz':'nan'}, {'device':'0; echo bad'}, {'duration':100},
                       {'mode':'unknown'}, {'end_mhz':530,'bin_khz':5}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                settings(config)

    def test_decoder_command_is_explicit_and_bounded(self):
        args=command(settings({'kind':'decode','frequency_mhz':915,'duration':5}))
        self.assertEqual(args[:3], ['rtl_433','-c','0'])
        self.assertIn('915000000',args)
        self.assertEqual(args[args.index('-T')+1], '5')

    def test_packet_parser_discards_noise_and_caps_events(self):
        text='diagnostic\n[1,2]\n'+ '\n'.join(json.dumps({'id':i}) for i in range(250))
        events=parse_events(text)
        self.assertEqual(len(events),200)
        self.assertEqual(events[0]['id'],50)

    def wait_for_job(self,workbench):
        limit=time.monotonic()+4
        while workbench.snapshot()['status']=='running' and time.monotonic()<limit:
            time.sleep(.02)
        self.assertNotEqual(workbench.snapshot()['status'],'running')

    def test_demo_and_receiver_exclusion(self):
        bench=Workbench()
        bench.start({'duration':2})
        with self.assertRaises(RuntimeError): bench.start({'duration':2})
        self.wait_for_job(bench)
        self.assertEqual(bench.snapshot()['status'],'complete')
        self.assertTrue(bench.snapshot()['peaks'])
        self.assertEqual(bench.snapshot()['mode'],'demo')

    def test_stop_releases_receiver(self):
        bench=Workbench();bench.start({'duration':60});bench.stop();self.wait_for_job(bench)
        self.assertEqual(bench.snapshot()['status'],'stopped')
        bench.start({'kind':'decode','duration':2});self.wait_for_job(bench)
        self.assertTrue(bench.snapshot()['events'][0]['simulated'])

    def test_missing_hardware_tool_does_not_fall_back_to_demo(self):
        bench=Workbench()
        with patch('app.shutil.which',return_value=None):
            bench.start({'mode':'hardware','duration':2});self.wait_for_job(bench)
        self.assertEqual(bench.snapshot()['status'],'error')
        self.assertEqual(bench.snapshot()['sweeps'],[])

    def test_subprocess_output_failure_timeout_and_cancel(self):
        bench=Workbench()
        with patch('app.shutil.which',return_value=sys.executable):
            self.assertEqual(bench.capture(['python','-c','print("packet")'],2).strip(),'packet')
            with self.assertRaises(ValueError): bench.capture(['python','-c','raise SystemExit(3)'],2)
            with self.assertRaises(TimeoutError): bench.capture(['python','-c','import time; time.sleep(10)'],.1)
            timer=threading.Timer(.15,bench.stop);timer.start()
            started=time.monotonic()
            bench.capture(['python','-c','import time; time.sleep(10)'],20)
            timer.join()
            self.assertLess(time.monotonic()-started,4)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=Server(('127.0.0.1',0))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.workbench.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def test_static_and_status(self):
        with urlopen(self.base+'/') as response:
            self.assertIn(b'SIGNALPIER',response.read())
            self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
        with urlopen(self.base+'/api/status') as response:
            self.assertIn('token',json.load(response))

    def test_receiver_routes_require_token_for_probe_and_return_discovery(self):
        with patch('receivers.inspect_receiver',return_value={'status':'not_connected','message':'Connect a receiver','devices':[]}):
            with urlopen(self.base+'/api/receivers?refresh=1') as response:
                self.assertEqual(json.load(response)['status'],'not_connected')
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(self.base+'/api/receivers/test',data=b'{"device":"0"}'))
        self.assertEqual(caught.exception.code,403);caught.exception.close()
        with patch('app.inspect_receiver',return_value={'status':'ready','message':'Ready','devices':[]}):
            request=Request(self.base+'/api/receivers/test',data=b'{"device":"0"}',headers={'X-Workbench-Token':self.server.token})
            with urlopen(request) as response: self.assertEqual(json.load(response)['status'],'ready')

    def test_rejects_missing_token_bad_origin_and_rebinding(self):
        for headers in ({}, {'X-Workbench-Token':self.server.token,'Origin':'https://example.com'},
                        {'X-Workbench-Token':self.server.token,'Host':'attacker.example'}):
            with self.subTest(headers=list(headers)), self.assertRaises(HTTPError) as caught:
                urlopen(Request(self.base+'/api/start',data=b'{}',headers=headers))
            self.assertEqual(caught.exception.code,403)
            caught.exception.close()

    def test_invalid_json_and_static_traversal(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(self.base+'/api/start',data=b'[]',headers={'X-Workbench-Token':self.server.token}))
        self.assertEqual(caught.exception.code,400)
        caught.exception.close()
        with self.assertRaises(HTTPError) as caught: urlopen(self.base+'/../app.py')
        self.assertEqual(caught.exception.code,404)
        caught.exception.close()


if __name__=='__main__': unittest.main()
