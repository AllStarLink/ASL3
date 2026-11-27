"""Exercise the SA818 CLI with simulated serial responses; no RF hardware needed."""

import io
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import serial


SCRIPT = Path(__file__).resolve().parents[1] / 'bin' / 'sa818'
DEFAULT_PORTS = runpy.run_path(str(SCRIPT))['SA818'].PORTS


class TestSA818(unittest.TestCase):
    def run_command(self, replies, command=None, entry="sa818"):
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

        args = [entry] + (command or ['version'])
        with patch.object(serial, 'Serial', FakeSerial), \
                patch.object(sys, 'argv', args), patch('time.sleep'), \
                self.assertLogs("SR110U" if entry == "sr110u" else "SA818", level="INFO") as logs:
            try:
                runpy.run_path(str(SCRIPT.with_name(entry)), run_name='__main__')
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
        self.assertEqual(ports[-1].writes[-1], b'AT+DMOVERQ\r\n')

    def test_explicit_port(self):
        status, _, ports = self.run_command({}, ['--port', '/dev/test', 'version'])
        self.assertEqual(status, 1)
        self.assertEqual([port.port for port in ports], ['/dev/test'])

    def test_group_rejection_stops_before_tail(self):
        status, logs, ports = self.run_command({DEFAULT_PORTS[0]: [
            b'+DMOCONNECT:0\r\n', b'+DMOSETGROUP:1\r\n\x00\x00\x00\x00']},
            ['radio', '--frequency', '146.5200', '--ctcss', '103.5,None', '--tail', 'close'])
        self.assertEqual(status, 1)
        self.assertTrue(any('parameter out of range' in log for log in logs))
        self.assertEqual(len(ports[0].writes), 2)
        self.assertTrue(ports[0].closed)

    def test_programming_replies(self):
        cases = [
            (['radio', '--frequency', '146.5200'], '+DMOSETGROUP', 'programming'),
            (['volume', '--level', '5'], '+DMOSETVOLUME', 'volume'),
            (['filters', '--emphasis', 'disable', '--highpass', 'disable', '--lowpass', 'disable'], '+DMOSETFILTER', 'filter'),
        ]
        for command, prefix, label in cases:
            for reply in [b'Wrong command\r\n', b'', (prefix + ':1\r\n').encode()]:
                with self.subTest(command=command, reply=reply):
                    status, logs, ports = self.run_command({DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n', reply]}, command)
                    self.assertEqual(status, 1)
                    self.assertTrue(any(label in log and 'received' in log for log in logs))
                    self.assertTrue(ports[0].closed)
            status, _, ports = self.run_command({DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n',
                b'\x00\x00' + (prefix + ':0\r\n').encode() + b'\x00']}, command)
            self.assertEqual(status, 0)
            self.assertTrue(ports[0].closed)

    def test_tail_failure_is_not_reported_as_filter_failure(self):
        status, logs, ports = self.run_command({DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n',
            b'+DMOSETGROUP:0\r\n', b'Wrong command\r\n']},
            ['radio', '--frequency', '146.5200', '--ctcss', '103.5,None', '--tail', 'close'])
        self.assertEqual(status, 1)
        self.assertIn(b'AT+SETTAIL=0\r\n', ports[0].writes)
        self.assertTrue(any('set tail error' in log for log in logs))

    def test_sr110u_version(self):
        status, logs, ports = self.run_command({DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n',
            b'Wrong command\r\n', b'+DMOVERQ:110U-V223\r\n']})
        self.assertEqual(status, 0)
        self.assertTrue(any('Firmware SR110U, version: 110U-V223' in line for line in logs))
        self.assertEqual(ports[0].writes[-1], b'AT+DMOVERQ\r\n')

    def test_sr110u_asymmetric_channel_and_padding(self):
        status, _, ports = self.run_command({DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n',
            b'Wrong command\r\n', b'+DMOVERQ:110U-V223\r\n', b'+DMOSETGROUP:0\r\n\x00\x00']},
            ['--protocol', 'sr110u-v223', 'radio', '--frequency', '445.1250', '--offset', '5',
             '--bw', '1', '--squelch', '1', '--ctcss', '103.5,None'])
        self.assertEqual(status, 0)
        self.assertEqual(ports[0].writes[-1], b'AT+DMOSETGROUP=1,445.1250,450.1250,00,1,13,1\r\n')
        self.assertFalse(any(b'SETTAIL' in w for w in ports[0].writes))

    def test_sr110u_frequency_order_both_entry_points(self):
        # Explicit wire expectations, not values computed by the implementation.
        for entry, prefix in (('sr110u', []), ('sa818', ['--protocol', 'sr110u-v223'])):
            for offset, expected_tx in (('5', '450.1250'), ('-5', '440.1250'), ('0', '445.1250')):
                for tones, wire_tones in (('103.5,None', ('00', '13')),
                                          ('None,103.5', ('13', '00'))):
                    with self.subTest(entry=entry, offset=offset, tones=tones):
                        status, logs, ports = self.run_command(
                            self.advanced_replies(b'+DMOSETGROUP:0\r\n'),
                            prefix + ['radio', '--frequency', '445.1250', '--offset', offset,
                                      '--bw', '1', '--squelch', '1', '--ctcss', tones], entry=entry)
                        self.assertEqual(status, 0)
                        rx_tone, tx_tone = wire_tones
                        self.assertEqual(ports[0].writes[-1],
                            f'AT+DMOSETGROUP=1,445.1250,{expected_tx},{rx_tone},1,{tx_tone},1\r\n'.encode())
                        self.assertTrue(any(f'TX: {expected_tx} / RX: 445.1250' in log for log in logs))

    def test_sa818_keeps_tx_rx_wire_order(self):
        for offset, expected_tx in (('5', '450.1250'), ('-5', '440.1250'), ('0', '445.1250')):
            with self.subTest(offset=offset):
                status, _, ports = self.run_command({DEFAULT_PORTS[0]: [
                    b'+DMOCONNECT:0\r\n', b'+DMOSETGROUP:0\r\n']},
                    ['radio', '--frequency', '445.1250', '--offset', offset,
                     '--bw', '1', '--squelch', '1', '--ctcss', '103.5,None'])
                self.assertEqual(status, 0)
                self.assertEqual(ports[0].writes[-1],
                    f'AT+DMOSETGROUP=1,{expected_tx},445.1250,0013,1,0000\r\n'.encode())

    def test_sr110u_requires_exact_firmware(self):
        for version in (b'+DMOVERQ:110U-V303\r\n', b'Wrong command\r\n'):
            status, _, ports = self.run_command({DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n',
                b'Wrong command\r\n', version]},
                ['--protocol', 'sr110u-v223', 'radio', '--frequency', '445.1250'])
            self.assertEqual(status, 1)
            self.assertFalse(any(b'SETGROUP' in w for w in ports[0].writes))

    def test_sr110u_refuses_unsupported_settings_before_writing(self):
        for command in (['filters', '--emphasis', 'disable'],
                        ['radio', '--frequency', '445.1250', '--dcs', '023N'],
                        ['radio', '--frequency', '445.1250', '--ctcss', '103.5', '--tail', 'close']):
            status, _, ports = self.run_command({DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n',
                b'Wrong command\r\n', b'+DMOVERQ:110U-V223\r\n']}, ['--protocol', 'sr110u-v223', *command])
            self.assertEqual(status, 1)
            self.assertEqual(len(ports[0].writes), 3)

    def test_sr110u_group_rejection(self):
        status, logs, ports = self.run_command({DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n',
            b'Wrong command\r\n', b'+DMOVERQ:110U-V223\r\n', b'+DMOSETGROUP:1\r\n']},
            ['--protocol', 'sr110u-v223', 'radio', '--frequency', '445.1250'])
        self.assertEqual(status, 1)
        self.assertTrue(any('SR110U programming error' in line for line in logs))
        self.assertEqual(len(ports[0].writes), 4)

    def test_sr110u_volume(self):
        status, _, ports = self.run_command({DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n',
            b'Wrong command\r\n', b'+DMOVERQ:110U-V223\r\n', b'+DMOSETVOLUME:0\r\n\x00']},
            ['--protocol', 'sr110u-v223', 'volume', '--level', '5'])
        self.assertEqual(status, 0)
        self.assertEqual(ports[0].writes[-1], b'AT+DMOSETVOLUME=5\r\n')

    def advanced_command(self, vox='0', power='disable'):
        return ['--protocol', 'sr110u-v223', 'advanced', '--mic', '6',
                '--timeout', '3', '--vox', vox, '--power-saving', power]

    def advanced_replies(self, *replies):
        return {DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n', b'Wrong command\r\n',
                                  b'+DMOVERQ:110U-V223\r\n', *replies]}

    def test_sr110u_each_flag_combination(self):
        for flags in range(8):
            status, _, ports = self.run_command(self.advanced_replies(b'+DMOSETGROUP:0\r\n'),
                ['--protocol', 'sr110u-v223', 'radio', '--frequency', '445.1250', '--sr110u-flags', str(flags)])
            self.assertEqual(status, 0)
            self.assertTrue(ports[0].writes[-1].endswith(f',{flags}\r\n'.encode()))

    def test_advanced_legacy_mic_layout_scrambler_off_and_vox_last(self):
        status, _, ports = self.run_command(self.advanced_replies(
            b'+DMOSETVOX:0\r\n', b'+DMOSETMIC:0\r\n', b'+DMOAUTOPOWCONTR:0\r\n', b'+DMOSETVOX:0\r\n'),
            self.advanced_command(vox='4'))
        self.assertEqual(status, 0)
        self.assertEqual(ports[0].writes[3:], [b'AT+DMOSETVOX=0\r\n', b'AT+DMOSETMIC=6,0,3\r\n',
                                               b'AT+DMOAUTOPOWCONTR=1\r\n', b'AT+DMOSETVOX=4\r\n'])
        self.assertTrue(ports[0].closed)

    def test_advanced_off_and_power_saving_inversion(self):
        status, _, ports = self.run_command(self.advanced_replies(
            b'+DMOSETVOX:0\r\n', b'+DMOSETMIC:0\r\n', b'+DMOAUTOPOWCONTR:0\r\n'),
            self.advanced_command(power='enable'))
        self.assertEqual(status, 0)
        self.assertEqual(ports[0].writes[-1], b'AT+DMOAUTOPOWCONTR=0\r\n')
        self.assertEqual(len(ports[0].writes), 6)

    def test_advanced_failures_stop_before_enabling_vox(self):
        successes = [b'+DMOSETVOX:0\r\n', b'+DMOSETMIC:0\r\n', b'+DMOAUTOPOWCONTR:0\r\n']
        for step in range(3):
            for rejection in (b'Wrong command\r\n', b'', successes[step].replace(b':0', b':1')):
                status, _, ports = self.run_command(self.advanced_replies(*successes[:step], rejection),
                                                   self.advanced_command(vox='4'))
                self.assertEqual(status, 1)
                self.assertEqual(len(ports[0].writes), 4 + step)
                self.assertNotIn(b'AT+DMOSETVOX=4\r\n', ports[0].writes)
                self.assertTrue(ports[0].closed)

    def test_advanced_incompatible_options_do_not_open_serial(self):
        for command in (self.advanced_command(vox='1', power='enable'), self.advanced_command()[2:],
                        ['radio', '--frequency', '445.1250', '--sr110u-flags', '1']):
            status, _, ports = self.run_command({}, command)
            self.assertEqual(status, 1)
            self.assertEqual(ports, [])

    def test_advanced_wrong_firmware_sends_no_settings(self):
        replies = self.advanced_replies()
        replies[DEFAULT_PORTS[0]][2] = b'+DMOVERQ:110U-V303\r\n'
        status, _, ports = self.run_command(replies, self.advanced_command())
        self.assertEqual(status, 1)
        self.assertEqual(len(ports[0].writes), 3)

    def test_dedicated_sr110u_entry_point(self):
        status, logs, ports = self.run_command(self.advanced_replies(b'+DMOSETGROUP:0\r\n'),
            ['radio', '--frequency', '445.1250', '--offset', '5', '--ctcss', '103.5,None'], entry='sr110u')
        self.assertEqual(status, 0)
        self.assertTrue(all('SR110U:' in line for line in logs))
        self.assertEqual(ports[0].writes[-1], b'AT+DMOSETGROUP=1,445.1250,450.1250,00,4,13,1\r\n')

    def test_dedicated_sr110u_refuses_other_modules(self):
        for reply in (b'+VERSION:SA818S_V1.2\r\n', b'+VERSION:SR110U_V303\r\n', b'Wrong command\r\n'):
            status, _, ports = self.run_command({DEFAULT_PORTS[0]: [b'+DMOCONNECT:0\r\n', reply]},
                ['volume', '--level', '3'], entry='sr110u')
            self.assertEqual(status, 1)
            self.assertFalse(any(b'SETVOLUME' in w for w in ports[0].writes))
            self.assertTrue(ports[0].closed)

    def test_dedicated_sr110u_cannot_override_protocol(self):
        with patch.object(serial, 'Serial') as serial_port, \
                patch.object(sys, 'argv', ['sr110u', '--protocol', 'sa818', 'volume']), \
                patch('sys.stderr'):
            with self.assertRaises(SystemExit) as error:
                runpy.run_path(str(SCRIPT.with_name('sr110u')), run_name='__main__')
        self.assertEqual(error.exception.code, 2)
        serial_port.assert_not_called()

    def test_dedicated_sr110u_help_opens_no_port(self):
        with patch.object(serial, 'Serial') as serial_port, \
                patch.object(sys, 'argv', ['sr110u', '--help']), patch('sys.stdout', new_callable=io.StringIO) as output:
            with self.assertRaises(SystemExit) as error:
                runpy.run_path(str(SCRIPT.with_name('sr110u')), run_name='__main__')
        self.assertEqual(error.exception.code, 0)
        self.assertIn('Program SR110U firmware 110U-V223', output.getvalue())
        self.assertNotIn('filters', output.getvalue())
        self.assertNotIn('--dcs', output.getvalue())
        serial_port.assert_not_called()

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
