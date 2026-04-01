"""
Tests for HTTP registration checking functions in bin/asl-node-auth-check.

Coverage:
  - check_http_registration()
  - find_http_registration()
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
check_http_registration = _mod.check_http_registration
find_http_registration = _mod.find_http_registration


class TestFindHttpRegistration(unittest.TestCase):
    """Tests for find_http_registration() function."""

    def test_find_http_registration_found(self):
        """Valid HTTP registration output returns correct tuple."""
        http_output = """
Host            Username        Perceived IP:Port  Refresh  State
register.allst  12345           44.15.4.13:4569    104      Registered
register.allst  54321           44.15.4.14:4569    104      Registered
2 HTTP registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=http_output.strip()):
            host, perceived, state = find_http_registration("12345")
            self.assertEqual(host, "register.allst")
            self.assertEqual(perceived, "44.15.4.13:4569")
            self.assertEqual(state, "Registered")

    def test_find_http_registration_not_found(self):
        """Node not in registry returns None tuple."""
        http_output = """
Host            Username        Perceived IP:Port  Refresh  State
register.allst  54321           44.15.4.14:4569    104      Registered
1 HTTP registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=http_output.strip()):
            host, perceived, state = find_http_registration("12345")
            self.assertIsNone(host)
            self.assertIsNone(perceived)
            self.assertIsNone(state)

    def test_find_http_registration_command_fails(self):
        """Failed asterisk command returns None tuple."""
        import subprocess as real_subprocess
        with patch.object(_mod.subprocess, 'check_output', side_effect=real_subprocess.CalledProcessError(1, 'asterisk')):
            host, perceived, state = find_http_registration("12345")
            self.assertIsNone(host)
            self.assertIsNone(perceived)
            self.assertIsNone(state)

    def test_find_http_registration_empty_output(self):
        """Empty output (no registrations) returns None tuple."""
        with patch.object(_mod.subprocess, 'check_output', return_value="".strip()):
            host, perceived, state = find_http_registration("12345")
            self.assertIsNone(host)
            self.assertIsNone(perceived)
            self.assertIsNone(state)

    def test_find_http_registration_with_state_multiple_words(self):
        """State value with multiple words is captured correctly."""
        http_output = """
Host            Username        Perceived IP:Port  Refresh  State
register.allst  12345           44.15.4.13:4569    104      Request sent
1 HTTP registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=http_output.strip()):
            host, perceived, state = find_http_registration("12345")
            self.assertEqual(state, "Request sent")

    def test_find_http_registration_multiple_nodes(self):
        """Multiple registrations are searched correctly."""
        http_output = """
Host            Username        Perceived IP:Port  Refresh  State
register.allst  54321           44.15.4.14:4569    104      Registered
register.allst  12345           44.15.4.13:4569    104      Registered
register.allst  99999           44.15.4.15:4569    104      Registered
3 HTTP registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=http_output.strip()):
            host, perceived, state = find_http_registration("12345")
            self.assertEqual(host, "register.allst")
            self.assertEqual(perceived, "44.15.4.13:4569")

    def test_find_http_registration_malformed_line_ignored(self):
        """Malformed registration lines with too few columns are ignored."""
        http_output = """
Host            Username        Perceived IP:Port  Refresh  State
register.allst  12345           44.15.4.13:4569
2 HTTP registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=http_output.strip()):
            host, perceived, state = find_http_registration("12345")
            self.assertIsNone(host)
            self.assertIsNone(perceived)
            self.assertIsNone(state)


class TestCheckHttpRegistration(unittest.TestCase):
    """Tests for check_http_registration() function."""

    def test_check_http_registration_success(self):
        """Successful registration returns True."""
        http_output = """
Host            Username        Perceived IP:Port  Refresh  State
register.allst  12345           44.15.4.13:4569    104      Registered
1 HTTP registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=http_output.strip()), \
             patch.object(_mod, 'reverse_dns', return_value='register.allstarlink.org'), \
             patch.object(_mod, 'print_ok'), \
             patch.object(_mod, 'print_error'):
            result = check_http_registration("12345")
            self.assertTrue(result)

    def test_check_http_registration_not_found(self):
        """Registration not found returns False."""
        http_output = """
1 HTTP registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=http_output.strip()), \
             patch.object(_mod, 'print_error') as mock_err:
            result = check_http_registration("12345")
            self.assertFalse(result)
            mock_err.assert_called_once()

    def test_check_http_registration_not_registered_state(self):
        """Non-registered state returns False."""
        http_output = """
Host            Username        Perceived IP:Port  Refresh  State
register.allst  12345           44.15.4.13:4569    104      Request sent
1 HTTP registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=http_output.strip()), \
             patch.object(_mod, 'print_error') as mock_err:
            result = check_http_registration("12345")
            self.assertFalse(result)
            # Should report the non-Registered state
            error_call = mock_err.call_args_list[0]
            self.assertIn("Request sent", error_call[0][0])

    def test_check_http_registration_prints_ok_messages(self):
        """Successful registration prints OK messages."""
        http_output = """
Host            Username        Perceived IP:Port  Refresh  State
register.allst  12345           44.15.4.13:4569    104      Registered
1 HTTP registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=http_output.strip()), \
             patch.object(_mod, 'reverse_dns', return_value='register.allstarlink.org'), \
             patch.object(_mod, 'print_ok') as mock_ok:
            check_http_registration("12345")
            # Should have multiple OK messages
            self.assertGreaterEqual(mock_ok.call_count, 2)

    def test_check_http_registration_handles_missing_reghost(self):
        """Missing reverse DNS result is handled gracefully."""
        http_output = """
Host            Username        Perceived IP:Port  Refresh  State
register.allst  12345           44.15.4.13:4569    104      Registered
1 HTTP registrations.
        """
        with patch.object(_mod.subprocess, 'check_output', return_value=http_output.strip()), \
             patch.object(_mod, 'reverse_dns', return_value='No PTR record'), \
             patch.object(_mod, 'print_ok'):
            result = check_http_registration("12345")
            # Should still return True even with DNS issues
            self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
