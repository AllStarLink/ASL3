"""
Tests for remote IP perception checking functions in bin/asl-node-auth-check.

Coverage:
  - check_remote_ip_perception()
  - get_remote_ip_http()
  - udp_ping()
"""

import importlib.machinery
import importlib.util
import os
import socket
import unittest
from unittest.mock import patch, MagicMock
import requests

# ---------------------------------------------------------------------------
# Load bin/asl-node-auth-check as a module (no .py extension)
# ---------------------------------------------------------------------------
_SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "bin", "asl-node-auth-check"
)


def _load_script():
    loader = importlib.machinery.SourceFileLoader("asl_node_auth_check", _SCRIPT_PATH)
    spec = importlib.util.spec_from_loader("asl_node_auth_check", loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mod = _load_script()
check_remote_ip_perception = _mod.check_remote_ip_perception
get_remote_ip_http = _mod.get_remote_ip_http
udp_ping = _mod.udp_ping


class TestGetRemoteIpHttp(unittest.TestCase):
    """Tests for get_remote_ip_http() function."""

    def test_get_remote_ip_http_success(self):
        """Valid HTTP response returns IP address."""
        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = "44.15.4.13\n"
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = get_remote_ip_http("https://example.com/ip")
            self.assertEqual(result, "44.15.4.13")

    def test_get_remote_ip_http_strips_whitespace(self):
        """Whitespace in response is stripped."""
        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = "  44.15.4.13  \n"
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = get_remote_ip_http("https://example.com/ip")
            self.assertEqual(result, "44.15.4.13")

    def test_get_remote_ip_http_timeout(self):
        """Request timeout returns None."""
        with patch.object(_mod.requests, 'get', side_effect=requests.Timeout("Connection timeout")):
            result = get_remote_ip_http("https://example.com/ip")
            self.assertIsNone(result)

    def test_get_remote_ip_http_connection_error(self):
        """Connection error returns None."""
        with patch.object(_mod.requests, 'get', side_effect=requests.ConnectionError("Connection refused")):
            result = get_remote_ip_http("https://example.com/ip")
            self.assertIsNone(result)

    def test_get_remote_ip_http_http_error(self):
        """HTTP error (4xx/5xx) returns None."""
        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
            mock_get.return_value = mock_response
            
            result = get_remote_ip_http("https://example.com/ip")
            self.assertIsNone(result)


class TestUdpPing(unittest.TestCase):
    """Tests for udp_ping() function."""

    def test_udp_ping_success(self):
        """Valid UDP ping returns IP."""
        with patch.object(_mod.socket, 'getaddrinfo') as mock_getaddrinfo, \
             patch.object(_mod.socket, 'socket') as mock_socket_class:
            # Mock address info
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_DGRAM, 0, '', ('192.0.2.1', 4569))
            ]
            
            # Mock socket
            mock_sock = MagicMock()
            mock_sock.recvfrom.return_value = (b"44.15.4.13", ('192.0.2.1', 4569))
            mock_socket_class.return_value = mock_sock
            
            result = udp_ping("udp://example.com:4569")
            self.assertEqual(result, "44.15.4.13")

    def test_udp_ping_invalid_scheme(self):
        """Non-UDP scheme raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            udp_ping("http://example.com:4569")
        self.assertIn("udp://", str(ctx.exception))

    def test_udp_ping_missing_host(self):
        """Missing host in URL raises ValueError."""
        with self.assertRaises(ValueError):
            udp_ping("udp://:4569")

    def test_udp_ping_missing_port(self):
        """Missing port in URL raises ValueError."""
        with self.assertRaises(ValueError):
            udp_ping("udp://example.com")

    def test_udp_ping_timeout(self):
        """UDP timeout returns None."""
        with patch.object(_mod.socket, 'getaddrinfo') as mock_getaddrinfo, \
             patch.object(_mod.socket, 'socket') as mock_socket_class:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_DGRAM, 0, '', ('192.0.2.1', 4569))
            ]
            
            mock_sock = MagicMock()
            mock_sock.recvfrom.side_effect = socket.timeout()
            mock_socket_class.return_value = mock_sock
            
            result = udp_ping("udp://example.com:4569", timeout=1.0)
            self.assertIsNone(result)

    def test_udp_ping_dns_lookup_fails(self):
        """DNS lookup failure returns None."""
        with patch.object(_mod.socket, 'getaddrinfo', side_effect=socket.gaierror("Name resolution failed")):
            result = udp_ping("udp://nonexistent.invalid:4569")
            self.assertIsNone(result)

    def test_udp_ping_custom_message(self):
        """Custom message is sent."""
        custom_msg = "hello"
        with patch.object(_mod.socket, 'getaddrinfo') as mock_getaddrinfo, \
             patch.object(_mod.socket, 'socket') as mock_socket_class:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_DGRAM, 0, '', ('192.0.2.1', 4569))
            ]
            
            mock_sock = MagicMock()
            mock_sock.recvfrom.return_value = (b"44.15.4.13", ('192.0.2.1', 4569))
            mock_socket_class.return_value = mock_sock
            
            udp_ping("udp://example.com:4569", message=custom_msg)
            
            # Verify message was sent
            mock_sock.sendto.assert_called_once()
            sent_data = mock_sock.sendto.call_args[0][0]
            self.assertIn(custom_msg.encode(), sent_data)

    def test_udp_ping_closes_socket(self):
        """Socket is closed after communication."""
        with patch.object(_mod.socket, 'getaddrinfo') as mock_getaddrinfo, \
             patch.object(_mod.socket, 'socket') as mock_socket_class:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_DGRAM, 0, '', ('192.0.2.1', 4569))
            ]
            
            mock_sock = MagicMock()
            mock_sock.recvfrom.return_value = (b"44.15.4.13", ('192.0.2.1', 4569))
            mock_socket_class.return_value = mock_sock
            
            udp_ping("udp://example.com:4569")
            
            # Verify socket was closed
            mock_sock.close.assert_called_once()

    def test_udp_ping_extracts_ip_from_colon_format(self):
        """IP:Port format is split to extract just the IP."""
        with patch.object(_mod.socket, 'getaddrinfo') as mock_getaddrinfo, \
             patch.object(_mod.socket, 'socket') as mock_socket_class:
            mock_getaddrinfo.return_value = [
                (socket.AF_INET, socket.SOCK_DGRAM, 0, '', ('192.0.2.1', 4569))
            ]
            
            mock_sock = MagicMock()
            # Response contains IP:port
            mock_sock.recvfrom.return_value = (b"44.15.4.13:4569", ('192.0.2.1', 4569))
            mock_socket_class.return_value = mock_sock
            
            result = udp_ping("udp://example.com:4569")
            # Should extract just the IP
            self.assertEqual(result, "44.15.4.13")


class TestCheckRemoteIpPerception(unittest.TestCase):
    """Tests for check_remote_ip_perception() function."""

    def test_check_remote_ip_perception_http_consensus(self):
        """HTTP probes with consensus print OK message."""
        with patch.object(_mod, 'get_remote_ip_http') as mock_http, \
             patch.object(_mod, 'udp_ping') as mock_udp, \
             patch.object(_mod, 'print_ok') as mock_ok, \
             patch.object(_mod, 'print_info'), \
             patch.object(_mod, 'print_error') as mock_err:
            
            # All HTTP probes return same IP
            mock_http.side_effect = ["44.15.4.13", "44.15.4.13", "44.15.4.13"]
            # All UDP probes return same IP
            mock_udp.side_effect = ["44.15.4.13", "44.15.4.13", "44.15.4.13"]
            
            check_remote_ip_perception()
            
            # Should have OK messages for both HTTP and IAX consensus
            ok_calls = [call[0][0] for call in mock_ok.call_args_list]
            self.assertTrue(any("HTTP" in msg for msg in ok_calls))
            self.assertTrue(any("IAX" in msg for msg in ok_calls))

    def test_check_remote_ip_perception_http_no_consensus(self):
        """HTTP probes without consensus print error message."""
        with patch.object(_mod, 'get_remote_ip_http') as mock_http, \
             patch.object(_mod, 'udp_ping') as mock_udp, \
             patch.object(_mod, 'print_error') as mock_err, \
             patch.object(_mod, 'print_ok'), \
             patch.object(_mod, 'print_info'):
            
            # Different IPs from HTTP probes
            mock_http.side_effect = ["44.15.4.13", "44.15.4.14", "44.15.4.15"]
            # All UDP probes return same IP
            mock_udp.side_effect = ["44.15.4.13", "44.15.4.13", "44.15.4.13"]
            
            check_remote_ip_perception()
            
            # Should have error about HTTP no consensus
            error_calls = [call[0][0] for call in mock_err.call_args_list]
            self.assertTrue(any("HTTP" in msg and "DO NOT" in msg for msg in error_calls))

    def test_check_remote_ip_perception_iax_no_consensus(self):
        """IAX probes without consensus print error message."""
        with patch.object(_mod, 'get_remote_ip_http') as mock_http, \
             patch.object(_mod, 'udp_ping') as mock_udp, \
             patch.object(_mod, 'print_error') as mock_err, \
             patch.object(_mod, 'print_ok'), \
             patch.object(_mod, 'print_info'):
            
            # All HTTP probes return same IP
            mock_http.side_effect = ["44.15.4.13", "44.15.4.13", "44.15.4.13"]
            # Different IPs from IAX probes
            mock_udp.side_effect = ["44.15.4.13", "44.15.4.14", "44.15.4.15"]
            
            check_remote_ip_perception()
            
            # Should have error about IAX no consensus
            error_calls = [call[0][0] for call in mock_err.call_args_list]
            self.assertTrue(any("IAX" in msg and "DO NOT" in msg for msg in error_calls))

    def test_check_remote_ip_perception_failed_probes_ignored(self):
        """Failed probes (None results) are ignored."""
        with patch.object(_mod, 'get_remote_ip_http') as mock_http, \
             patch.object(_mod, 'udp_ping') as mock_udp, \
             patch.object(_mod, 'print_ok') as mock_ok, \
             patch.object(_mod, 'print_warning'), \
             patch.object(_mod, 'print_info'):
            
            # Some probes fail, some succeed
            mock_http.side_effect = ["44.15.4.13", None, "44.15.4.13"]
            mock_udp.side_effect = [None, "44.15.4.13", "44.15.4.13"]
            
            check_remote_ip_perception()
            
            # Should still detect consensus from successful probes
            ok_calls = [call[0][0] for call in mock_ok.call_args_list]
            self.assertTrue(any("consensus" in msg for msg in ok_calls))


if __name__ == "__main__":
    unittest.main()
