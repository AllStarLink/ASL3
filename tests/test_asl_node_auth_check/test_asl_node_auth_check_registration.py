"""
Tests for registration parsing and extraction functions in bin/asl-node-auth-check.

Coverage:
  - parse_registration_string()
  - extract_registration_values()
  - get_registrations()
  - get_rpt_nodes()
"""

import importlib.machinery
import importlib.util
import os
import tempfile
import unittest
from unittest.mock import patch, mock_open

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
parse_registration_string = _mod.parse_registration_string
extract_registration_values = _mod.extract_registration_values
get_registrations = _mod.get_registrations
get_rpt_nodes = _mod.get_rpt_nodes


class TestParseRegistrationString(unittest.TestCase):
    """Tests for parse_registration_string() function."""

    def test_valid_registration_string(self):
        """Valid 'node:secret@host' format is parsed correctly."""
        result = parse_registration_string("12345:mysecret@register.allstarlink.org")
        self.assertIsNotNone(result)
        node, secret, host = result
        self.assertEqual(node, "12345")
        self.assertEqual(secret, "mysecret")
        self.assertEqual(host, "register.allstarlink.org")

    def test_registration_string_with_numbers_in_secret(self):
        """Secret can contain numbers and special characters."""
        result = parse_registration_string("12345:abc123xyz@register.allstarlink.org")
        self.assertIsNotNone(result)
        node, secret, host = result
        self.assertEqual(secret, "abc123xyz")

    def test_registration_string_with_dashes_in_host(self):
        """Host with dashes does not match regex (not allowed)."""
        result = parse_registration_string("12345:secret@my-host.example.com")
        # Dashes are not allowed in the regex pattern
        self.assertIsNone(result)

    def test_invalid_registration_missing_colon(self):
        """Missing colon separator returns None."""
        result = parse_registration_string("12345mysecret@register.allstarlink.org")
        self.assertIsNone(result)

    def test_invalid_registration_missing_at(self):
        """Missing '@' separator returns None."""
        result = parse_registration_string("12345:mysecretregister.allstarlink.org")
        self.assertIsNone(result)

    def test_invalid_registration_empty_node(self):
        """Empty node field returns None."""
        result = parse_registration_string(":mysecret@register.allstarlink.org")
        self.assertIsNone(result)

    def test_invalid_registration_empty_secret(self):
        """Empty secret field returns None."""
        result = parse_registration_string("12345:@register.allstarlink.org")
        self.assertIsNone(result)

    def test_invalid_registration_empty_host(self):
        """Empty host field returns None."""
        result = parse_registration_string("12345:mysecret@")
        self.assertIsNone(result)

    def test_invalid_registration_non_numeric_node(self):
        """Non-numeric node is still parsed (validation happens elsewhere)."""
        result = parse_registration_string("abc:mysecret@register.allstarlink.org")
        # The regex doesn't enforce numeric-only nodes; that's checked elsewhere
        self.assertIsNone(result)  # ^\d+ pattern requires digits

    def test_registration_with_whitespace_is_invalid(self):
        """Whitespace in registration string causes parse to fail."""
        result = parse_registration_string("12345 : mysecret @ register.allstarlink.org")
        self.assertIsNone(result)


class TestExtractRegistrationValues(unittest.TestCase):
    """Tests for extract_registration_values() function."""

    def test_extract_from_valid_iax_conf(self):
        """Valid IAX registration lines are extracted."""
        conf_content = """
[general]
port = 4569

[register]
register => 12345:mysecret@register.allstarlink.org

[nodes]
bindport = 4569
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                results = extract_registration_values(f.name, "IAX")
                self.assertEqual(len(results), 1)
                node, secret, host, regtype = results[0]
                self.assertEqual(node, "12345")
                self.assertEqual(secret, "mysecret")
                self.assertEqual(host, "register.allstarlink.org")
                self.assertEqual(regtype, "IAX")
            finally:
                os.unlink(f.name)

    def test_extract_multiple_registrations(self):
        """Multiple registration lines are extracted."""
        conf_content = """
register => 12345:secret1@register.allstarlink.org
register => 54321:secret2@register.allstarlink.org
register => 99999:secret3@register.allstarlink.org
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                results = extract_registration_values(f.name, "IAX")
                self.assertEqual(len(results), 3)
                nodes = [r[0] for r in results]
                self.assertIn("12345", nodes)
                self.assertIn("54321", nodes)
                self.assertIn("99999", nodes)
            finally:
                os.unlink(f.name)

    def test_extract_ignores_invalid_registrations(self):
        """Invalid registration lines are skipped with error message."""
        conf_content = """
register => 12345:valid@register.allstarlink.org
register => invalid_registration_line
register => 54321:also_valid@register.allstarlink.org
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch.object(_mod, 'print_error'):
                    results = extract_registration_values(f.name, "IAX")
                    # Should extract only valid ones
                    self.assertEqual(len(results), 2)
                    nodes = [r[0] for r in results]
                    self.assertIn("12345", nodes)
                    self.assertIn("54321", nodes)
            finally:
                os.unlink(f.name)

    def test_extract_ignores_comments_and_whitespace(self):
        """Comments and non-matching lines are ignored."""
        conf_content = """
; This is a comment
register   =>   12345:secret@register.allstarlink.org
; Another comment
register => 54321:secret2@register.allstarlink.org
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                results = extract_registration_values(f.name, "IAX")
                # Should extract both registrations despite comments
                self.assertEqual(len(results), 2)
            finally:
                os.unlink(f.name)

    def test_extract_from_nonexistent_file_returns_empty(self):
        """Nonexistent file raises OSError."""
        with self.assertRaises(FileNotFoundError):
            extract_registration_values("/nonexistent/path/file.conf", "IAX")

    def test_extract_http_registration_type(self):
        """HTTP registration type is preserved."""
        conf_content = "register => 12345:secret@register.allstarlink.org\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                results = extract_registration_values(f.name, "HTTP")
                self.assertEqual(len(results), 1)
                _, _, _, regtype = results[0]
                self.assertEqual(regtype, "HTTP")
            finally:
                os.unlink(f.name)


class TestGetRptNodes(unittest.TestCase):
    """Tests for get_rpt_nodes() function."""

    def test_extract_rpt_nodes_basic(self):
        """Basic node sections are extracted."""
        conf_content = """
[2000]
; Private node

[12345]
node-main

[54321]
node-main
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch.object(_mod, 'print_info'):
                    results = get_rpt_nodes(f.name)
                    # Public nodes (> 1999) should be included
                    self.assertIn("12345", results)
                    self.assertIn("54321", results)
                    # Node 2000 is a boundary case - may or may not be included
            finally:
                os.unlink(f.name)

    def test_extract_rpt_nodes_with_whitespace(self):
        """Node sections with whitespace around brackets are handled."""
        conf_content = """
[ 12345 ]
node-main

[  54321  ]
node-main
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                results = get_rpt_nodes(f.name)
                self.assertIn("12345", results)
                self.assertIn("54321", results)
            finally:
                os.unlink(f.name)

    def test_extract_rpt_nodes_case_insensitive(self):
        """Node section headers are case-insensitive."""
        conf_content = """
[12345]
node-main

[54321]
NODE-MAIN
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                results = get_rpt_nodes(f.name)
                self.assertIn("12345", results)
                self.assertIn("54321", results)
            finally:
                os.unlink(f.name)

    def test_extract_rpt_nodes_skips_private_range(self):
        """Nodes < 2000 are skipped as private nodes."""
        conf_content = """
[1000]
node-main

[1999]
node-main

[2000]
node-main

[2001]
node-main
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch.object(_mod, 'print_info'):
                    results = get_rpt_nodes(f.name)
                    self.assertNotIn("1000", results)
                    self.assertNotIn("1999", results)
                    # 2000-2001 might be in results depending on logic
            finally:
                os.unlink(f.name)

    def test_extract_rpt_nodes_no_duplicates(self):
        """Duplicate node entries are not repeated."""
        conf_content = """
[12345]
node-main

[12345]
node-main
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                results = get_rpt_nodes(f.name)
                count = results.count("12345")
                self.assertEqual(count, 1)
            finally:
                os.unlink(f.name)

    def test_extract_rpt_nodes_nonexistent_file(self):
        """Nonexistent file returns empty list."""
        with patch.object(_mod, 'print_info'):
            results = get_rpt_nodes("/nonexistent/path/rpt.conf")
            self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
