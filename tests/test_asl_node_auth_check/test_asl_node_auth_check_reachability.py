"""
Tests for node reachability checking functions in bin/asl-node-auth-check.

Coverage:
  - check_node_reachability()
  - get_node_ping()
"""

import importlib.machinery
import importlib.util
import json
import os
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
check_node_reachability = _mod.check_node_reachability
get_node_ping = _mod.get_node_ping


class TestGetNodePing(unittest.TestCase):
    """Tests for get_node_ping() function."""

    def test_get_node_ping_success(self):
        """Successful node ping returns valid JSON."""
        ping_response = {
            "ipv4": {
                "status": "ok",
                "rc": 0,
                "pingms": 45
            }
        }
        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = ping_response
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = get_node_ping("12345")
            self.assertEqual(result, ping_response)

    def test_get_node_ping_uses_expected_url_and_timeout(self):
        """get_node_ping should call requests.get with the node parameter and timeout."""
        ping_response = {
            "ipv4": {
                "status": "ok",
                "rc": 0,
                "pingms": 10
            }
        }

        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = ping_response
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = get_node_ping("12345")

            self.assertEqual(result, ping_response)
            mock_get.assert_called_once_with("https://nodeping.allstarlink.org?node=12345", timeout=5)

    def test_get_node_ping_timeout(self):
        """Network timeout returns None."""
        with patch.object(_mod.requests, 'get', side_effect=requests.Timeout("Connection timeout")):
            result = get_node_ping("12345")
            self.assertIsNone(result)

    def test_get_node_ping_invalid_json(self):
        """Invalid JSON response returns None."""
        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_get.return_value = mock_response
            
            result = get_node_ping("12345")
            self.assertIsNone(result)

    def test_get_node_ping_http_error(self):
        """HTTP error response returns None."""
        with patch.object(_mod.requests, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
            mock_get.return_value = mock_response
            
            result = get_node_ping("12345")
            self.assertIsNone(result)


class TestCheckNodeReachability(unittest.TestCase):
    """Tests for check_node_reachability() function."""

    def test_check_node_reachability_success(self):
        """Node is reachable and ping is successful."""
        ping_response = {
            "ipv4": {
                "status": "ok",
                "rc": 0,
                "pingms": 45
            }
        }
        with patch.object(_mod, 'get_node_ping', return_value=ping_response), \
             patch.object(_mod, 'print_ok') as mock_ok, \
             patch.object(_mod, 'print_info'):
            n_errors, n_warnings = check_node_reachability("12345")
            self.assertEqual(n_errors, 0)
            self.assertEqual(n_warnings, 0)
            # Should print OK for successful ping
            self.assertGreater(mock_ok.call_count, 0)

    def test_check_node_reachability_unreachable(self):
        """Node is unreachable produces error."""
        ping_response = {
            "ipv4": {
                "status": "unreachable",
                "rc": -1,
                "pingms": 0
            }
        }
        with patch.object(_mod, 'get_node_ping', return_value=ping_response), \
             patch.object(_mod, 'print_error') as mock_err:
            n_errors, n_warnings = check_node_reachability("12345")
            self.assertEqual(n_errors, 1)
            self.assertEqual(n_warnings, 0)
            mock_err.assert_called_once()

    def test_check_node_reachability_unregistered(self):
        """Unregistered node produces warning."""
        ping_response = {
            "ipv4": {
                "status": "unregistered",
                "rc": -9
            }
        }
        with patch.object(_mod, 'get_node_ping', return_value=ping_response), \
             patch.object(_mod, 'print_warning') as mock_warn:
            n_errors, n_warnings = check_node_reachability("12345")
            self.assertEqual(n_errors, 0)
            self.assertEqual(n_warnings, 1)
            mock_warn.assert_called_once()

    def test_check_node_reachability_unregistered_with_rc_minus_9(self):
        """RC code -9 (unregistered) produces warning."""
        ping_response = {
            "ipv4": {
                "status": "other",
                "rc": -9
            }
        }
        with patch.object(_mod, 'get_node_ping', return_value=ping_response), \
             patch.object(_mod, 'print_warning') as mock_warn:
            n_errors, n_warnings = check_node_reachability("12345")
            self.assertEqual(n_errors, 0)
            self.assertEqual(n_warnings, 1)

    def test_check_node_reachability_nodeping_down(self):
        """Nodeping service is down produces warning."""
        with patch.object(_mod, 'get_node_ping', return_value=None), \
             patch.object(_mod, 'print_warning') as mock_warn:
            n_errors, n_warnings = check_node_reachability("12345")
            self.assertEqual(n_errors, 0)
            self.assertEqual(n_warnings, 1)
            # Should mention rate-limiting or service down
            call_args = mock_warn.call_args[0][0]
            self.assertIn("Nodeping", call_args)

    def test_check_node_reachability_unknown_status(self):
        """Unknown status from nodeping produces warning."""
        ping_response = {
            "ipv4": {
                "status": "unknown_status",
                "rc": 999
            }
        }
        with patch.object(_mod, 'get_node_ping', return_value=ping_response), \
             patch.object(_mod, 'print_warning') as mock_warn:
            n_errors, n_warnings = check_node_reachability("12345")
            self.assertEqual(n_errors, 0)
            self.assertEqual(n_warnings, 1)
            # Should indicate something unexpected
            call_args = mock_warn.call_args[0][0]
            self.assertIn("don't understand", call_args)

    def test_check_node_reachability_ping_time_reported(self):
        """Ping time in milliseconds is reported."""
        ping_response = {
            "ipv4": {
                "status": "ok",
                "rc": 0,
                "pingms": 123
            }
        }
        with patch.object(_mod, 'get_node_ping', return_value=ping_response), \
             patch.object(_mod, 'print_ok'), \
             patch.object(_mod, 'print_info') as mock_info:
            check_node_reachability("12345")
            # Should report the ping time
            call_args = mock_info.call_args[0][0]
            self.assertIn("123", call_args)

    def test_check_node_reachability_returns_tuple(self):
        """Function returns tuple of (errors, warnings)."""
        ping_response = {
            "ipv4": {
                "status": "ok",
                "rc": 0,
                "pingms": 45
            }
        }
        with patch.object(_mod, 'get_node_ping', return_value=ping_response), \
             patch.object(_mod, 'print_ok'), \
             patch.object(_mod, 'print_info'):
            result = check_node_reachability("12345")
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
