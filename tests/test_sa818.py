"""Exercise the SA818 CLI with simulated serial responses; no RF hardware needed."""

import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import serial


SCRIPT = Path(__file__).resolve().parents[1] / 'bin' / 'sa818'
DEFAULT_PORTS = runpy.run_path(str(SCRIPT))['SA818'].PORTS


class TestSA818(unittest.TestCase):
    def run_command(self, replies, command=None):
        instances = []

        class FakeSerial:
            def __init__(self, **kwargs):
                self.port = kwargs['port']
                self.replies = iter(replies.get(self.port, []))
                self.writes = []
                self.closed = False
                instances.append(self)

            def write(self, data):
                self.writes.append(data)

            def readline(self):
                return next(self.replies, b'')

            def close(self):
                self.closed = True

        args = ['sa818'] + (command or ['version'])
        with patch.object(serial, 'Serial', FakeSerial), \
                patch.object(sys, 'argv', args), patch('time.sleep'), \
                self.assertLogs('SA818', level='INFO') as logs:
            try:
                runpy.run_path(str(SCRIPT), run_name='__main__')
            except SystemExit as err:
                status = err.code
            else:
                status = 0
        return status, logs.output, instances

    def test_firmware_version(self):
        status, logs, ports = self.run_command({
            DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n', b'+VERSION:SA818S_V1.2_2024\r\n']})
        self.assertEqual(status, 0)
        self.assertIn('Firmware SA818S, version: V1.2_2024', logs[0])
        self.assertEqual(ports[0].writes, [b'AT+DMOCONNECT\r\n', b'AT+VERSION\r\n'])

    def test_unavailable_version(self):
        for reply in (b'Wrong command\r\n', b'', b'+VERSION:\r\n',
                      b'+VERSION:SA818S\r\n', b'+VERSION:SA818S_\r\n',
                      b'unexpected:SA818S_V1.2\r\n', b'\xff\r\n'):
            with self.subTest(reply=reply):
                status, logs, _ = self.run_command({
                    DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n', reply]})
                self.assertEqual(status, 0)
                self.assertTrue(any('firmware version unavailable' in log for log in logs))

    def test_failed_handshake(self):
        for reply in (b'', b'+DMOCONNECT:1\r\n', b'Wrong command\r\n'):
            with self.subTest(reply=reply):
                status, _, ports = self.run_command({port: [reply] for port in DEFAULT_PORTS})
                self.assertEqual(status, 1)
                self.assertEqual([port.port for port in ports], list(DEFAULT_PORTS))
                self.assertTrue(all(port.closed for port in ports))
                self.assertTrue(all(port.writes == [b'AT+DMOCONNECT\r\n'] for port in ports))

    def test_default_port_fallback(self):
        status, _, ports = self.run_command({
            DEFAULT_PORTS[-1]: [b'+DMOCONNECT:0\r\n', b'Wrong command\r\n']})
        self.assertEqual(status, 0)
        self.assertEqual([port.port for port in ports], list(DEFAULT_PORTS))
        self.assertTrue(all(port.closed for port in ports[:-1]))
        self.assertEqual(ports[-1].writes[-1], b'AT+VERSION\r\n')

    def test_explicit_port(self):
        status, _, ports = self.run_command({}, ['--port', '/dev/test', 'version'])
        self.assertEqual(status, 1)
        self.assertEqual([port.port for port in ports], ['/dev/test'])

    def test_unavailable_ports(self):
        class UnavailableSerial:
            def __init__(self, **kwargs):
                raise serial.SerialException('unavailable')

        with patch.object(serial, 'Serial', UnavailableSerial), \
                patch.object(sys, 'argv', ['sa818', 'version']), \
                self.assertLogs('SA818', level='ERROR'):
            with self.assertRaises(SystemExit) as error:
                runpy.run_path(str(SCRIPT), run_name='__main__')
        self.assertEqual(error.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
