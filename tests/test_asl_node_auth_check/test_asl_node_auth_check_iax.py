"""
Tests for IAX registration checking functions in bin/asl-node-auth-check.

Coverage:
  - check_iax_registration()
  - find_iax_registration()
  - check_node_formedness()
"""

import importlib.machinery
import importlib.util
import os
import unittest
from unittest.mock import patch

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
check_iax_registration = _mod.check_iax_registration
find_iax_registration = _mod.find_iax_registration
check_node_formedness = _mod.check_node_formedness


class TestFindIaxRegistration(unittest.TestCase):
    """Tests for find_iax_registration() function."""

    def test_find_iax_registration_found(self):
        """Valid IAX registration output returns correct tuple."""
        iax_output = """
Host                DNSmgr  Username        Perceived IP:Port  Refresh  State
register.allst      N       12345           44.15.4.13:4569    105      Registered
register.allst      N       54321           44.15.4.14:4569    105      Registered
2 IAX2 registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=iax_output):
            host, perceived, state = find_iax_registration("12345")
            self.assertEqual(host, "register.allst")
            self.assertEqual(perceived, "44.15.4.13:4569")
            self.assertEqual(state, "Registered")

    def test_find_iax_registration_not_found(self):
        """Node not in registry returns None tuple."""
        iax_output = """
Host                DNSmgr  Username        Perceived IP:Port  Refresh  State
register.allst      N       54321           44.15.4.14:4569    105      Registered
1 IAX2 registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=iax_output.strip()):
            host, perceived, state = find_iax_registration("12345")
            self.assertIsNone(host)
            self.assertIsNone(perceived)
            self.assertIsNone(state)

    def test_find_iax_registration_command_fails(self):
        """Failed asterisk command returns None tuple."""
        import subprocess as real_subprocess
        with patch.object(_mod.subprocess, 'check_output', side_effect=real_subprocess.CalledProcessError(1, 'asterisk')):
            host, perceived, state = find_iax_registration("12345")
            self.assertIsNone(host)
            self.assertIsNone(perceived)
            self.assertIsNone(state)

    def test_find_iax_registration_empty_output(self):
        """Empty output (no registrations) returns None tuple."""
        with patch.object(_mod.subprocess, 'check_output', return_value="".strip()):
            host, perceived, state = find_iax_registration("12345")
            self.assertIsNone(host)
            self.assertIsNone(perceived)
            self.assertIsNone(state)

    def test_find_iax_registration_with_state_containing_spaces(self):
        """State value with multiple words is captured correctly."""
        iax_output = """
Host                DNSmgr  Username        Perceived IP:Port  Refresh  State
register.allst      N       12345           44.15.4.13:4569    105      Request sent
1 IAX2 registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=iax_output.strip()):
            host, perceived, state = find_iax_registration("12345")
            self.assertEqual(state, "Request sent")


class TestCheckIaxRegistration(unittest.TestCase):
    """Tests for check_iax_registration() function."""

    def test_check_iax_registration_success(self):
        """Successful registration returns True."""
        iax_output = """
Host                DNSmgr  Username        Perceived IP:Port  Refresh  State
register.allst      N       12345           44.15.4.13:4569    105      Registered
1 IAX2 registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=iax_output.strip()), \
             patch.object(_mod, 'reverse_dns', return_value='register.allstarlink.org'), \
             patch.object(_mod, 'print_ok'), \
             patch.object(_mod, 'print_error'):
            result = check_iax_registration("12345")
            self.assertTrue(result)

    def test_check_iax_registration_not_found(self):
        """Registration not found returns False."""
        iax_output = """
1 IAX2 registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=iax_output.strip()), \
             patch.object(_mod, 'print_error') as mock_err:
            result = check_iax_registration("12345")
            self.assertFalse(result)
            mock_err.assert_called_once()

    def test_check_iax_registration_not_registered_state(self):
        """Non-registered state returns False."""
        iax_output = """
Host                DNSmgr  Username        Perceived IP:Port  Refresh  State
register.allst      N       12345           44.15.4.13:4569    105      Request sent
1 IAX2 registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=iax_output.strip()), \
             patch.object(_mod, 'print_error') as mock_err:
            result = check_iax_registration("12345")
            self.assertFalse(result)
            # Should report the non-Registered state
            error_call = mock_err.call_args_list[0]
            self.assertIn("Request sent", error_call[0][0])

    def test_check_iax_registration_prints_ok_messages(self):
        """Successful registration prints OK messages."""
        iax_output = """
Host                DNSmgr  Username        Perceived IP:Port  Refresh  State
register.allst      N       12345           44.15.4.13:4569    105      Registered
1 IAX2 registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=iax_output.strip()), \
             patch.object(_mod, 'reverse_dns', return_value='register.allstarlink.org'), \
             patch.object(_mod, 'print_ok') as mock_ok:
            check_iax_registration("12345")
            # Should have multiple OK messages
            self.assertGreaterEqual(mock_ok.call_count, 2)


class TestCheckNodeFormedness(unittest.TestCase):
    """Tests for check_node_formedness() function."""

    def test_node_formedness_valid(self):
        """Valid node and reghost produce no errors."""
        n_errors, n_warnings = check_node_formedness("12345", "register.allstarlink.org")
        self.assertEqual(n_errors, 0)
        self.assertEqual(n_warnings, 0)

    def test_node_formedness_node_too_low(self):
        """Node below 2000 produces error."""
        with patch.object(_mod, 'print_error'):
            n_errors, n_warnings = check_node_formedness("1999", "register.allstarlink.org")
            self.assertGreater(n_errors, 0)

    def test_node_formedness_node_too_high(self):
        """Node above 999989 produces error."""
        with patch.object(_mod, 'print_error'):
            n_errors, n_warnings = check_node_formedness("999990", "register.allstarlink.org")
            self.assertGreater(n_errors, 0)

    def test_node_formedness_node_edge_valid_low(self):
        """Node at lower boundary (2000) is valid."""
        n_errors, n_warnings = check_node_formedness("2000", "register.allstarlink.org")
        self.assertEqual(n_errors, 0)

    def test_node_formedness_node_edge_valid_high(self):
        """Node at upper boundary (999989) is valid."""
        n_errors, n_warnings = check_node_formedness("999989", "register.allstarlink.org")
        self.assertEqual(n_errors, 0)

    def test_node_formedness_node_non_numeric(self):
        """Non-numeric node produces error."""
        with patch.object(_mod, 'print_error'):
            n_errors, n_warnings = check_node_formedness("abc", "register.allstarlink.org")
            self.assertGreater(n_errors, 0)

    def test_node_formedness_invalid_reghost(self):
        """Invalid reghost produces error."""
        with patch.object(_mod, 'print_error'):
            n_errors, n_warnings = check_node_formedness("12345", "invalid.host.org")
            self.assertGreater(n_errors, 0)

    def test_node_formedness_both_invalid(self):
        """Both invalid node and reghost produce multiple errors."""
        with patch.object(_mod, 'print_error'):
            n_errors, n_warnings = check_node_formedness("1999", "invalid.host.org")
            self.assertGreaterEqual(n_errors, 2)

    def test_node_formedness_reghost_exact_match_required(self):
        """Reghost must be exactly 'register.allstarlink.org'."""
        with patch.object(_mod, 'print_error'):
            n_errors, _ = check_node_formedness("12345", "register.allstarlink.org.com")
            self.assertGreater(n_errors, 0)

    def test_node_formedness_returns_tuple(self):
        """Function returns tuple of (errors, warnings)."""
        result = check_node_formedness("12345", "register.allstarlink.org")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
