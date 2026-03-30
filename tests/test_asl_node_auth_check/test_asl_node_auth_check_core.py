"""
Tests for core utility and configuration functions in bin/asl-node-auth-check.

Focused on functions that don't require complex mocking of external processes.
"""

import importlib.machinery
import importlib.util
import os
import socket
import tempfile
import unittest
from unittest.mock import patch, MagicMock

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


class TestNodeFormednessValidation(unittest.TestCase):
    """Tests for node validation logic."""

    def test_valid_node_range(self):
        """Nodes in valid range 2000-999989 are accepted."""
        check_node_formedness = _mod.check_node_formedness
        
        # Test boundary low
        n_errors, _ = check_node_formedness("2000", "register.allstarlink.org")
        self.assertEqual(n_errors, 0)
        
        # Test middle range
        n_errors, _ = check_node_formedness("12345", "register.allstarlink.org")
        self.assertEqual(n_errors, 0)
        
        # Test boundary high
        n_errors, _ = check_node_formedness("999989", "register.allstarlink.org")
        self.assertEqual(n_errors, 0)

    def test_invalid_node_below_range(self):
        """Nodes below 2000 are rejected."""
        check_node_formedness = _mod.check_node_formedness
        with patch.object(_mod, 'print_error'):
            n_errors, _ = check_node_formedness("1999", "register.allstarlink.org")
            self.assertGreater(n_errors, 0)

    def test_invalid_node_above_range(self):
        """Nodes above 999989 are rejected."""
        check_node_formedness = _mod.check_node_formedness
        with patch.object(_mod, 'print_error'):
            n_errors, _ = check_node_formedness("999990", "register.allstarlink.org")
            self.assertGreater(n_errors, 0)

    def test_invalid_reghost(self):
        """Only 'register.allstarlink.org' is accepted as reghost."""
        check_node_formedness = _mod.check_node_formedness
        with patch.object(_mod, 'print_error'):
            n_errors, _ = check_node_formedness("12345", "other.host.org")
            self.assertGreater(n_errors, 0)

    def test_valid_reghost(self):
        """'register.allstarlink.org' is accepted."""
        check_node_formedness = _mod.check_node_formedness
        n_errors, _ = check_node_formedness("12345", "register.allstarlink.org")
        self.assertEqual(n_errors, 0)


class TestNodeListComparison(unittest.TestCase):
    """Tests for compare_node_lists() function."""

    def test_identical_lists(self):
        """Identical node lists return True."""
        compare_node_lists = _mod.compare_node_lists
        configured = ["12345", "54321"]
        registrations = ["12345", "54321"]
        
        identical, missing_config, missing_regs = compare_node_lists(configured, registrations)
        self.assertTrue(identical)
        self.assertEqual(len(missing_config), 0)
        self.assertEqual(len(missing_regs), 0)

    def test_missing_in_config(self):
        """Nodes in registrations but not config are identified."""
        compare_node_lists = _mod.compare_node_lists
        configured = ["12345"]
        registrations = ["12345", "54321"]
        
        identical, missing_config, missing_regs = compare_node_lists(configured, registrations)
        self.assertFalse(identical)
        self.assertIn("54321", missing_config)

    def test_missing_in_registrations(self):
        """Nodes in config but not registrations are identified."""
        compare_node_lists = _mod.compare_node_lists
        configured = ["12345", "54321"]
        registrations = ["12345"]
        
        identical, missing_config, missing_regs = compare_node_lists(configured, registrations)
        self.assertFalse(identical)
        self.assertIn("54321", missing_regs)

    def test_order_independent(self):
        """Node list order doesn't matter."""
        compare_node_lists = _mod.compare_node_lists
        configured = ["99999", "12345", "54321"]
        registrations = ["54321", "12345", "99999"]
        
        identical, _, _ = compare_node_lists(configured, registrations)
        self.assertTrue(identical)


class TestRegistrationParsing(unittest.TestCase):
    """Tests for registration string parsing."""

    def test_valid_registration_string(self):
        """Valid registration string is parsed correctly."""
        parse_registration_string = _mod.parse_registration_string
        result = parse_registration_string("12345:mysecret@register.allstarlink.org")
        
        self.assertIsNotNone(result)
        node, secret, host = result
        self.assertEqual(node, "12345")
        self.assertEqual(secret, "mysecret")
        self.assertEqual(host, "register.allstarlink.org")

    def test_invalid_registration_missing_separator(self):
        """Missing separators cause parse to fail."""
        parse_registration_string = _mod.parse_registration_string
        
        self.assertIsNone(parse_registration_string("12345mysecret@register.allstarlink.org"))
        self.assertIsNone(parse_registration_string("12345:mysecretregister.allstarlink.org"))

    def test_registration_with_alphanumeric_host(self):
        """Registered hosts with alphanumeric character ares supported."""
        parse_registration_string = _mod.parse_registration_string
        result = parse_registration_string("12345:secret@register.allstarlink.org")
        self.assertIsNotNone(result)


class TestIaxBindportExtraction(unittest.TestCase):
    """Tests for IAX bindport configuration extraction."""

    def test_extract_valid_bindport(self):
        """Valid bindport configuration is extracted as integer."""
        get_iax_bindport = _mod.get_iax_bindport
        
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

    def test_bindport_with_spaces(self):
        """Bindport with whitespace around equals is handled."""
        get_iax_bindport = _mod.get_iax_bindport
        
        conf_content = "bindport   =   4569\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                result = get_iax_bindport(f.name)
                self.assertEqual(result, 4569)
            finally:
                os.unlink(f.name)

    def test_bindport_missing(self):
        """Missing bindport line returns None."""
        get_iax_bindport = _mod.get_iax_bindport
        
        conf_content = "[general]\nport = 5060\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch.object(_mod, 'print_error'):
                    result = get_iax_bindport(f.name)
                    self.assertIsNone(result)
            finally:
                os.unlink(f.name)


class TestRemoteDnsLookup(unittest.TestCase):
    """Tests for reverse DNS functionality."""

    def test_valid_ipv4_reverse_dns(self):
        """Valid IPv4 address performs reverse DNS lookup."""
        reverse_dns = _mod.reverse_dns
        
        with patch('socket.gethostbyaddr') as mock_gethostbyaddr:
            mock_gethostbyaddr.return_value = ('example.com', [], ['10.0.0.1'])
            result = reverse_dns("10.0.0.1")
            self.assertEqual(result, 'example.com')

    def test_invalid_ip_address(self):
        """Invalid IP address returns None."""
        reverse_dns = _mod.reverse_dns
        result = reverse_dns("not-an-ip")
        self.assertIsNone(result)

    def test_dns_lookup_failure(self):
        """Failed DNS lookup returns None."""
        reverse_dns = _mod.reverse_dns
        
        with patch('socket.gethostbyaddr', side_effect=socket.herror("DNS error")):
            result = reverse_dns("10.0.0.1")
            self.assertIsNone(result)


class TestRegisterServiceHealthCheck(unittest.TestCase):
    """Tests for register.allstarlink.org availability check."""

    def test_service_online(self):
        """HTTP 200 response means service is up."""
        is_register_allstarlink_up = _mod.is_register_allstarlink_up
        
        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = is_register_allstarlink_up()
            self.assertTrue(result)

    def test_service_offline_404(self):
        """HTTP 404 response means service is down."""
        is_register_allstarlink_up = _mod.is_register_allstarlink_up
        
        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            result = is_register_allstarlink_up()
            self.assertFalse(result)

    def test_service_offline_500(self):
        """HTTP 500 response means service is down."""
        is_register_allstarlink_up = _mod.is_register_allstarlink_up
        
        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            
            result = is_register_allstarlink_up()
            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
