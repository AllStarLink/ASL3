"""
Tests for utility and helper functions in bin/asl-node-auth-check.

Coverage:
  - reverse_dns()
  - is_register_allstarlink_up()
  - get_iax_bindport()
  - compare_node_lists()
"""

import importlib.machinery
import importlib.util
import os
import socket
import tempfile
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
reverse_dns = _mod.reverse_dns
is_register_allstarlink_up = _mod.is_register_allstarlink_up
get_iax_bindport = _mod.get_iax_bindport
compare_node_lists = _mod.compare_node_lists


class TestReverseDns(unittest.TestCase):
    """Tests for reverse_dns() function."""

    def test_reverse_dns_ipv4_valid(self):
        """Valid IPv4 address returns hostname."""
        with patch('socket.gethostbyaddr') as mock_gethostbyaddr:
            mock_gethostbyaddr.return_value = ('example.com', [], ['10.0.0.1'])
            result = reverse_dns("10.0.0.1")
            self.assertEqual(result, 'example.com')

    def test_reverse_dns_ipv6_valid(self):
        """Valid IPv6 address returns hostname."""
        with patch('socket.gethostbyaddr') as mock_gethostbyaddr:
            mock_gethostbyaddr.return_value = ('example.com', [], ['::1'])
            result = reverse_dns("::1")
            self.assertEqual(result, 'example.com')

    def test_reverse_dns_invalid_ip(self):
        """Invalid IP address returns None."""
        result = reverse_dns("not-an-ip")
        self.assertIsNone(result)

    def test_reverse_dns_lookup_fails(self):
        """DNS lookup failure returns None."""
        with patch('socket.gethostbyaddr', side_effect=socket.herror("DNS lookup failed")):
            result = reverse_dns("10.0.0.1")
            self.assertIsNone(result)

    def test_reverse_dns_localhost(self):
        """Localhost IP (127.0.0.1) returns hostname."""
        with patch('socket.gethostbyaddr') as mock_gethostbyaddr:
            mock_gethostbyaddr.return_value = ('localhost', [], ['127.0.0.1'])
            result = reverse_dns("127.0.0.1")
            self.assertEqual(result, 'localhost')


class TestIsRegisterAllstarlinkUp(unittest.TestCase):
    """Tests for is_register_allstarlink_up() function."""

    def test_is_register_allstarlink_up_success(self):
        """HTTP 200 response returns True."""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = is_register_allstarlink_up()
            self.assertTrue(result)

    def test_is_register_allstarlink_up_404(self):
        """HTTP 404 response returns False."""
        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            result = is_register_allstarlink_up()
            self.assertFalse(result)

    def test_is_register_allstarlink_up_500(self):
        """HTTP 500 response returns False."""
        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            
            result = is_register_allstarlink_up()
            self.assertFalse(result)

    def test_is_register_allstarlink_up_timeout(self):
        """Request timeout returns False."""
        with patch.object(_mod.requests, 'get', side_effect=requests.Timeout("Connection timeout")):
            result = is_register_allstarlink_up()
            self.assertFalse(result)

    def test_is_register_allstarlink_up_connection_error(self):
        """Connection error returns False."""
        with patch.object(_mod.requests, 'get', side_effect=requests.ConnectionError("Connection refused")):
            result = is_register_allstarlink_up()
            self.assertFalse(result)

    def test_is_register_allstarlink_up_custom_timeout(self):
        """Custom timeout value is passed to requests."""
        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            is_register_allstarlink_up(timeout=10)
            # Check that timeout was passed
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args[1]
            self.assertEqual(call_kwargs['timeout'], 10)


class TestGetIaxBindport(unittest.TestCase):
    """Tests for get_iax_bindport() function."""

    def test_get_iax_bindport_found(self):
        """Valid bindport line is extracted and returned as int."""
        conf_content = """
[general]
bindport = 4569
port = 5060
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                result = get_iax_bindport(f.name)
                self.assertEqual(result, 4569)
                self.assertIsInstance(result, int)
            finally:
                os.unlink(f.name)

    def test_get_iax_bindport_with_spaces(self):
        """Bindport line with spaces around = is parsed."""
        conf_content = "bindport   =   4569\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                result = get_iax_bindport(f.name)
                self.assertEqual(result, 4569)
            finally:
                os.unlink(f.name)

    def test_get_iax_bindport_not_found(self):
        """Missing bindport line prints error and returns None."""
        conf_content = """
[general]
port = 5060
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch.object(_mod, 'print_error'):
                    result = get_iax_bindport(f.name)
                    self.assertIsNone(result)
            finally:
                os.unlink(f.name)

    def test_get_iax_bindport_nonexistent_file(self):
        """Nonexistent file returns None."""
        result = get_iax_bindport("/nonexistent/path/iax.conf")
        self.assertIsNone(result)

    def test_get_iax_bindport_multiple_lines(self):
        """Only first bindport line is used."""
        conf_content = """
bindport = 4569
bindport = 4570
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                result = get_iax_bindport(f.name)
                self.assertEqual(result, 4569)
            finally:
                os.unlink(f.name)

    def test_get_iax_bindport_non_numeric(self):
        """Non-numeric bindport value is not parsed."""
        conf_content = "bindport = invalid\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                result = get_iax_bindport(f.name)
                # Should return None if parsing fails
                self.assertIsNone(result)
            finally:
                os.unlink(f.name)


class TestCompareNodeLists(unittest.TestCase):
    """Tests for compare_node_lists() function."""

    def test_compare_node_lists_identical(self):
        """Identical lists return True and empty difference lists."""
        configured = ["12345", "54321", "99999"]
        registrations = ["12345", "54321", "99999"]
        
        identical, missing_config, missing_regs = compare_node_lists(configured, registrations)
        self.assertTrue(identical)
        self.assertEqual(missing_config, [])
        self.assertEqual(missing_regs, [])

    def test_compare_node_lists_extra_in_config(self):
        """Nodes in config but not in registration are identified."""
        configured = ["12345", "54321", "99999"]
        registrations = ["12345", "54321"]
        
        identical, missing_config, missing_regs = compare_node_lists(configured, registrations)
        self.assertFalse(identical)
        self.assertEqual(missing_config, [])
        self.assertIn("99999", missing_regs)

    def test_compare_node_lists_extra_in_registration(self):
        """Nodes in registration but not in config are identified."""
        configured = ["12345", "54321"]
        registrations = ["12345", "54321", "99999"]
        
        identical, missing_config, missing_regs = compare_node_lists(configured, registrations)
        self.assertFalse(identical)
        self.assertIn("99999", missing_config)
        self.assertEqual(missing_regs, [])

    def test_compare_node_lists_both_missing(self):
        """Both types of differences are identified together."""
        configured = ["12345", "54321", "88888"]
        registrations = ["12345", "99999"]
        
        identical, missing_config, missing_regs = compare_node_lists(configured, registrations)
        self.assertFalse(identical)
        self.assertIn("99999", missing_config)
        self.assertIn("54321", missing_regs)
        self.assertIn("88888", missing_regs)

    def test_compare_node_lists_empty_config(self):
        """Empty config list vs non-empty registration."""
        configured = []
        registrations = ["12345"]
        
        identical, missing_config, missing_regs = compare_node_lists(configured, registrations)
        self.assertFalse(identical)
        self.assertIn("12345", missing_config)

    def test_compare_node_lists_empty_registration(self):
        """Non-empty config vs empty registration list."""
        configured = ["12345"]
        registrations = []
        
        identical, missing_config, missing_regs = compare_node_lists(configured, registrations)
        self.assertFalse(identical)
        self.assertIn("12345", missing_regs)

    def test_compare_node_lists_both_empty(self):
        """Both empty lists are identical."""
        configured = []
        registrations = []
        
        identical, missing_config, missing_regs = compare_node_lists(configured, registrations)
        self.assertTrue(identical)
        self.assertEqual(missing_config, [])
        self.assertEqual(missing_regs, [])

    def test_compare_node_lists_duplicates_in_config(self):
        """Duplicates in configured list are handled."""
        configured = ["12345", "12345", "54321"]
        registrations = ["12345", "54321"]
        
        identical, missing_config, missing_regs = compare_node_lists(configured, registrations)
        # Sets handle duplicates, so should be identical
        self.assertTrue(identical)

    def test_compare_node_lists_order_independent(self):
        """Order of nodes doesn't matter for comparison."""
        configured = ["99999", "12345", "54321"]
        registrations = ["54321", "12345", "99999"]
        
        identical, missing_config, missing_regs = compare_node_lists(configured, registrations)
        self.assertTrue(identical)


if __name__ == "__main__":
    unittest.main()
