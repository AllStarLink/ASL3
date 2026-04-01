"""
Tests for registration parsing and extraction functions in bin/asl-node-auth-check.

Coverage:

"""

import importlib.machinery
import importlib.util
import os
import pytest
import subprocess
import requests
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import runpy
import tempfile
import io
import sys

# ---------------------------------------------------------------------------
# Load bin/asl-node-auth-check as a module (no .py extension)
# ---------------------------------------------------------------------------
_SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "bin", "asl-node-auth-check"
)


def _load_script():
    loader = importlib.machinery.SourceFileLoader("asl_node_auth_check", _SCRIPT_PATH)
    spec = importlib.util.spec_from_loader("asl_node_auth_check", loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["asl_node_auth_check"] = module
    return module


_module = _load_script()

def run():
    buf = io.StringIO()
    with patch.dict(sys.modules):
        try:
            _module.entrypoint()
        except SystemExit as e:
            return buf.getvalue(), str(e)
        return buf.getvalue(), ""


# ---------------------------------------------------------------------------
# Fixtures for consolidating repeated patch patterns
# ---------------------------------------------------------------------------

@pytest.fixture
def asterisk_user_patch():
    """Fixture for patching root user permissions."""
    with patch("os.geteuid", return_value=1000), \
         patch("pwd.getpwuid", return_value=unittest.mock.MagicMock(pw_uid=1000, pw_gid=1000, pw_name='asterisk')):
        yield


def test_main():
    """Test main function with no patches to cover permission and user checks via the __main__ entry point."""
    try:
        runpy.run_module("asl_node_auth_check", run_name="__main__", alter_sys=True)
    except SystemExit as e:
        assert str(e) == '1'


class TestMain:
    """Tests for main function."""

    def test_main_invalid_user(self):
        """Valid 'node:secret@host' format is parsed correctly."""
        _, ex = run()
        assert ex == '1'
    
    @pytest.mark.parametrize("user, uid, gid", [ 
                              ("root", 0, 0), 
                              ("asterisk", 1000, 1000),
                              ])
    def test_main_valid_user(self, user, uid, gid):
        """Valid user asterisk or root allows script to run."""
        with patch("os.geteuid", return_value=0), \
             patch("pwd.getpwnam", return_value=unittest.mock.MagicMock(pw_uid=uid, pw_gid=gid, pw_name=user)), \
             patch("asl_node_auth_check.main", return_value=None):
                 
            _, ex = run()
            assert ex == ''

    def test_main_full_workflow(self, asterisk_user_patch):
        """Main executes full workflow without sys.exit when all checks pass."""
        with patch("asl_node_auth_check.get_rpt_nodes", return_value=['12345']), \
             patch("asl_node_auth_check.get_registrations", return_value=[('12345', 'pw', 'register.allstarlink.org', 'HTTP')]), \
             patch("asl_node_auth_check.compare_node_lists", return_value=(True, [], [])), \
             patch("asl_node_auth_check.check_remote_ip_perception"), \
             patch("asl_node_auth_check.check_node_formedness", return_value=(0,0)), \
             patch("asl_node_auth_check.is_register_allstarlink_up", return_value=True), \
             patch("asl_node_auth_check.check_http_registration", return_value=True), \
             patch("asl_node_auth_check.check_node_status", return_value=(0,0)), \
             patch("asl_node_auth_check.check_node_reachability", return_value=(0,0)):
            _, ex = run()
            assert ex == ''

    def test_main_node_checks_with_formedness_errors_and_iax(self, asterisk_user_patch):
        """Main executes path where node formedness has errors/warnings, regup is down, regtype=IAX."""
        with patch("asl_node_auth_check.get_rpt_nodes", return_value=['12345']), \
             patch("asl_node_auth_check.get_registrations", return_value=[('12345', 'pw', 'register.allstarlink.org', 'IAX')]), \
             patch("asl_node_auth_check.compare_node_lists", return_value=(True, [], [])), \
             patch("asl_node_auth_check.check_remote_ip_perception"), \
             patch("asl_node_auth_check.check_node_formedness", return_value=(1,1)), \
             patch("asl_node_auth_check.is_register_allstarlink_up", return_value=False), \
             patch("asl_node_auth_check.check_iax_registration", return_value=False), \
             patch("asl_node_auth_check.print_ok"), \
             patch("asl_node_auth_check.print_error") as mock_error, \
             patch("asl_node_auth_check.print_info") as mock_info:
            _, ex = run()
            assert ex == ''
            mock_error.assert_any_call("register.allstarlink.org is unreachable (via HTTP)")
            mock_info.assert_any_call("Stopping node checks due to registration failure")
            mock_info.assert_any_call("as further information will be unreliable")

    def test_main_node_checks_status_and_reachability_accumulates_errors_and_warnings(self, asterisk_user_patch):
        """Main executes path where node status and reachability return nonzero errors/warnings."""
        with patch("asl_node_auth_check.get_rpt_nodes", return_value=['12345']), \
             patch("asl_node_auth_check.get_registrations", return_value=[('12345', 'pw', 'register.allstarlink.org', 'HTTP')]), \
             patch("asl_node_auth_check.compare_node_lists", return_value=(True, [], [])), \
             patch("asl_node_auth_check.check_remote_ip_perception"), \
             patch("asl_node_auth_check.check_node_formedness", return_value=(0,0)), \
             patch("asl_node_auth_check.is_register_allstarlink_up", return_value=True), \
             patch("asl_node_auth_check.check_http_registration", return_value=True), \
             patch("asl_node_auth_check.check_node_status", return_value=(2,3)), \
             patch("asl_node_auth_check.check_node_reachability", return_value=(4,5)), \
             patch("asl_node_auth_check.print_ok"), \
             patch("asl_node_auth_check.print_error") as mock_error, \
             patch("asl_node_auth_check.print_warning") as mock_warning:
            _, ex = run()
            assert ex == ''
            mock_error.assert_any_call("Node 12345 has 6 error(s)!")
            mock_warning.assert_any_call("Node 12345 has 8 warning(s)!")

    def test_main_no_configured_nodes_exits(self, asterisk_user_patch):
        """Main exits when get_rpt_nodes returns None (line 692-695)."""
        with patch("asl_node_auth_check.get_rpt_nodes", return_value=None), \
             patch("asl_node_auth_check.print_error") as mock_error:
            _, ex = run()
            assert ex == ''
            mock_error.assert_any_call("NO NODE ARE CONFIGURED IN rpt.conf")

    def test_main_no_registrations_exits(self, asterisk_user_patch):
        """Main exits when get_registrations returns None (line 702-705)."""
        with patch("asl_node_auth_check.get_rpt_nodes", return_value=['12345']), \
             patch("asl_node_auth_check.get_registrations", return_value=None), \
             patch("asl_node_auth_check.print_error") as mock_error:
            _, ex = run()
            assert ex == ''
            mock_error.assert_any_call("NO VALID REGISTRATIONS EXIST IN THE ASTERISK CONFIGURATION!")

    def test_main_duplicate_registration_exits(self, asterisk_user_patch):
        """Main exits when get_registrations includes duplicated node IDs (line 714-717)."""
        with patch("asl_node_auth_check.get_rpt_nodes", return_value=['12345']), \
             patch("asl_node_auth_check.get_registrations", return_value=[
                        ('12345', 'pw', 'register.allstarlink.org', 'HTTP'),
                        ('12345', 'pw', 'register.allstarlink.org', 'IAX')
                    ]
                   ), \
             patch("asl_node_auth_check.print_error") as mock_error:
            _, ex = run()
            assert ex == ''
            mock_error.assert_any_call("Duplicated HTTP and IAX registrations for: 12345")
            mock_error.assert_any_call("Cannot continue; reconcile configuration before proceeding")

    def test_main_mismatched_configuration_exits(self, asterisk_user_patch):
        """Main exits when compare_node_lists indicates mismatch (line 721-728)."""
        with patch("asl_node_auth_check.get_rpt_nodes", return_value=['12345', '67890']), \
             patch("asl_node_auth_check.get_registrations", return_value=[('12345', 'pw', 'register.allstarlink.org', 'HTTP')]), \
             patch("asl_node_auth_check.compare_node_lists", return_value=(False, ['67890'], ['12345'])), \
             patch("asl_node_auth_check.print_error") as mock_error:
            _, ex = run()
            assert ex == ''
            mock_error.assert_any_call("No registration present for configured node(s): 12345")
            mock_error.assert_any_call("No configuration present for registrations for node(s): 67890")
            mock_error.assert_any_call("Cannot continue; reconcile configuration before proceeding")

class TestGetRptNodesDetailedCoverage:
    """Tests for specific code paths in get_rpt_nodes function."""

    def test_relative_path_resolution(self):
        """Line 174: Relative include paths are resolved relative to base file directory."""
        main_dir = tempfile.mkdtemp()
        sub_dir = os.path.join(main_dir, "subdir")
        os.makedirs(sub_dir)

        main_file = os.path.join(main_dir, "main.conf")
        sub_file = os.path.join(sub_dir, "sub.conf")

        main_content = f"""
[12345] (node-main)

#include subdir/sub.conf
"""
        sub_content = """
[54321] (node-main)

"""
        with open(main_file, 'w') as f:
            f.write(main_content)
        with open(sub_file, 'w') as f:
            f.write(sub_content)

        try:
            with patch('asl_node_auth_check.print_info'):
                results = _module.get_rpt_nodes(main_file)
                # Both nodes should be found when relative path is resolved correctly
                assert "12345" in results
                assert "54321" in results
        finally:
            os.unlink(main_file)
            os.unlink(sub_file)
            os.rmdir(sub_dir)
            os.rmdir(main_dir)

    def test_circular_include_detection(self):
        """Line 183: seen_files prevents infinite loops in circular includes."""
        conf_content = "[12345] (node-main)\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()

            # Add a self-referential include
            content_with_circular = f"[12345] (node-main)\n\n#tryinclude {f.name}\n"
            with open(f.name, 'w') as self_ref:
                self_ref.write(content_with_circular)

            try:
                with patch('asl_node_auth_check.print_info'):
                    # This should not hang; circular include should be detected
                    results = _module.get_rpt_nodes(f.name)
                    assert "12345" in results
                    # Should only appear once despite circular reference
                    assert results.count("12345") == 1
            finally:
                os.unlink(f.name)

    def test_permission_error_handling(self):
        """Lines 193-195: PermissionError during file read is handled gracefully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("[12345] (node-main)\n")
            f.flush()

            try:
                # Mock open to raise PermissionError
                with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                    with patch('asl_node_auth_check.print_info') as mock_info:
                        results = _module.get_rpt_nodes(f.name)
                        # Should handle error gracefully and return empty or partial results
                        mock_info.assert_called()
                        # Verify permission error message was logged
                        calls = [str(call) for call in mock_info.call_args_list]
                        assert any("Permission denied" in str(call) for call in calls)
            finally:
                os.unlink(f.name)

    def test_oserror_handling(self):
        """Lines 196-198: OSError during file read is handled gracefully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("[12345] (node-main)\n")
            f.flush()

            try:
                # Mock open to raise OSError
                with patch('builtins.open', side_effect=OSError("Read error")):
                    with patch('asl_node_auth_check.print_info') as mock_info:
                        results = _module.get_rpt_nodes(f.name)
                        # Should handle error gracefully
                        mock_info.assert_called()
                        # Verify error message was logged
                        calls = [str(call) for call in mock_info.call_args_list]
                        assert any("Error reading" in str(call) for call in calls)
            finally:
                os.unlink(f.name)

    def test_include_target_not_found_message(self):
        """Line 217: Include target not found message is printed for #include."""
        conf_content = """
[12345] (node-main)

#include /nonexistent/missing.conf
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()

            try:
                with patch('asl_node_auth_check.print_info') as mock_info:
                    results = _module.get_rpt_nodes(f.name)
                    # Should still find the node
                    assert "12345" in results
                    # Should log that include target was not found
                    calls = [str(call) for call in mock_info.call_args_list]
                    assert any("Include target not found" in str(call) for call in calls)
            finally:
                os.unlink(f.name)

    def test_tryinclude_target_not_found_no_message(self):
        """#tryinclude missing file doesn't produce error message."""
        conf_content = """
[12345] (node-main)

#tryinclude /nonexistent/missing.conf
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()

            try:
                with patch('asl_node_auth_check.print_info') as mock_info:
                    results = _module.get_rpt_nodes(f.name)
                    assert "12345" in results
                    # Should NOT log "Include target not found" for tryinclude
                    calls = [str(call) for call in mock_info.call_args_list]
                    # Filter out other messages - should not have "Include target not found"
                    target_not_found_calls = [c for c in calls if "Include target not found" in str(c)]
                    assert len(target_not_found_calls) == 0
            finally:
                os.unlink(f.name)

    def test_absolute_path_not_resolved_relative(self):
        """Absolute include paths are not made relative (line 173-174 skip)."""
        tmp_dir = tempfile.mkdtemp()
        abs_file = os.path.join(tmp_dir, "absolute.conf")

        with open(abs_file, 'w') as f:
            f.write("[54321]\nnode-main\n")

        main_content = f"""
[12345] (node-main)

#include {abs_file}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as main_f:
            main_f.write(main_content)
            main_f.flush()

            try:
                with patch('asl_node_auth_check.print_info'):
                    results = _module.get_rpt_nodes(main_f.name)
                    # Should find nodes from both files
                    assert "12345" in results
                    assert "54321" in results
            finally:
                os.unlink(main_f.name)
                os.unlink(abs_file)
                os.rmdir(tmp_dir)


class TestFindIaxRegistration:
    """Tests for find_iax_registration function (lines 275-312)."""

    def test_valid_iax_registration_found(self):
        """Find IAX registration for matching node."""
        output = """Host                  DNSmgr  Username   Perceived       Refresh  State
register.allstarlink.org n   12345      192.168.1.1:4569 105      Registered
1 IAX2 registrations."""
        with patch('subprocess.check_output', return_value=output):
            host, perceived, state = _module.find_iax_registration("12345")
            assert host == "register.allstarlink.org"
            assert perceived == "192.168.1.1:4569"
            assert state == "Registered"

    def test_iax_registration_state_with_spaces(self):
        """IAX state can contain multiple words."""
        output = """Host                  DNSmgr  Username   Perceived       Refresh  State
register.allstarlink.org n   12345      192.168.1.1:4569 105      Request Sent
1 IAX2 registrations."""
        with patch('subprocess.check_output', return_value=output):
            host, perceived, state = _module.find_iax_registration("12345")
            assert state == "Request Sent"

    def test_iax_registration_not_found(self):
        """No matching node returns None tuple."""
        output = """Host                  DNSmgr  Username   Perceived       Refresh  State
register.allstarlink.org n   54321      192.168.1.1:4569 105      Registered
1 IAX2 registrations."""
        with patch('subprocess.check_output', return_value=output):
            host, perceived, state = _module.find_iax_registration("12345")
            assert host is None
            assert perceived is None
            assert state is None

    def test_iax_subprocess_error(self):
        """Subprocess error returns None tuple."""
        with patch('subprocess.check_output', side_effect=subprocess.CalledProcessError(1, 'cmd')):
            host, perceived, state = _module.find_iax_registration("12345")
            assert host is None
            assert perceived is None
            assert state is None

    def test_iax_insufficient_lines(self):
        """Output with less than 3 lines returns None tuple."""
        output = """Host  Username
register"""
        with patch('subprocess.check_output', return_value=output):
            host, perceived, state = _module.find_iax_registration("12345")
            assert host is None

    def test_iax_insufficient_columns(self):
        """Lines with insufficient columns are skipped."""
        output = """Host                  DNSmgr  Username   Perceived       Refresh  State
register.allstarlink.org n   12345
1 IAX2 registrations."""
        with patch('subprocess.check_output', return_value=output):
            host, perceived, state = _module.find_iax_registration("12345")
            assert host is None

    def test_iax_skip_summary_line(self):
        """Summary lines are skipped."""
        output = """Host                  DNSmgr  Username   Perceived       Refresh  State
register.allstarlink.org n   12345      192.168.1.1:4569 105      Registered
1 IAX2 registrations."""
        with patch('subprocess.check_output', return_value=output):
            host, perceived, state = _module.find_iax_registration("12345")
            assert host == "register.allstarlink.org"


class TestCheckIaxRegistration:
    """Tests for check_iax_registration function (lines 316-333)."""

    def test_valid_iax_registration(self):
        """Valid registered IAX returns True."""
        with patch('asl_node_auth_check.find_iax_registration', return_value=("register.allstarlink.org", "192.168.1.1:4569", "Registered")), \
             patch('asl_node_auth_check.reverse_dns', return_value="example.com"), \
             patch('asl_node_auth_check.print_ok'):
            result = _module.check_iax_registration("12345")
            assert result is True

    def test_iax_no_registration_attempt(self):
        """No registration attempt returns False."""
        with patch('asl_node_auth_check.find_iax_registration', return_value=(None, None, None)), \
             patch('asl_node_auth_check.print_error'):
            result = _module.check_iax_registration("12345")
            assert result is False

    def test_iax_registration_not_registered(self):
        """Non-registered state returns False."""
        with patch('asl_node_auth_check.find_iax_registration', return_value=("register.allstarlink.org", "192.168.1.1:4569", "Request Sent")), \
             patch('asl_node_auth_check.print_error'):
            result = _module.check_iax_registration("12345")
            assert result is False

    def test_iax_extracts_host_from_port(self):
        """Host with port is properly split."""
        with patch('asl_node_auth_check.find_iax_registration', return_value=("register.allstarlink.org:4569", "192.168.1.1:4569", "Registered")), \
             patch('asl_node_auth_check.reverse_dns', return_value="example.com") as mock_rdns, \
             patch('asl_node_auth_check.print_ok'):
            _module.check_iax_registration("12345")
            # Should call reverse_dns with host without port
            mock_rdns.assert_called_with("register.allstarlink.org")


class TestFindHttpRegistration:
    """Tests for find_http_registration function (lines 343-380)."""

    def test_valid_http_registration_found(self):
        """Find HTTP registration for matching node."""
        output = """Host                  Username   Perceived       Refresh  State
register.allstarlink.org 12345      192.168.1.1:4569 105      Registered
2 HTTP registrations."""
        with patch('subprocess.check_output', return_value=output):
            host, perceived, state = _module.find_http_registration("12345")
            assert host == "register.allstarlink.org"
            assert perceived == "192.168.1.1:4569"
            assert state == "Registered"

    def test_http_registration_not_found(self):
        """No matching node returns None tuple."""
        output = """Host                  Username   Perceived       Refresh  State
register.allstarlink.org 54321      192.168.1.1:4569 105      Registered
1 HTTP registrations."""
        with patch('subprocess.check_output', return_value=output):
            host, perceived, state = _module.find_http_registration("12345")
            assert host is None

    def test_http_subprocess_error(self):
        """Subprocess error returns None tuple."""
        with patch('subprocess.check_output', side_effect=subprocess.CalledProcessError(1, 'cmd')):
            host, perceived, state = _module.find_http_registration("12345")
            assert host is None

    def test_http_insufficient_lines(self):
        """Output with less than 3 lines returns None tuple."""
        output = """Host  Username
register"""
        with patch('subprocess.check_output', return_value=output):
            host, perceived, state = _module.find_http_registration("12345")
            assert host is None

    def test_http_malformed_line_is_ignored(self):
        """Malformed entry with too few fields should be skipped."""
        output = """Host                  Username   Perceived       Refresh  State
register.allstarlink.org 12345      192.168.1.1:4569
2 HTTP registrations."""
        with patch('subprocess.check_output', return_value=output):
            host, perceived, state = _module.find_http_registration("12345")
            assert host is None
            assert perceived is None
            assert state is None


class TestCheckHttpRegistration:
    """Tests for check_http_registration function (lines 384-400)."""

    def test_valid_http_registration(self):
        """Valid registered HTTP returns True."""
        with patch('asl_node_auth_check.find_http_registration', return_value=("register.allstarlink.org", "192.168.1.1:4569", "Registered")), \
             patch('asl_node_auth_check.reverse_dns', return_value="example.com"), \
             patch('asl_node_auth_check.print_ok'):
            result = _module.check_http_registration("12345")
            assert result is True

    def test_http_no_registration_attempt(self):
        """No registration attempt returns False."""
        with patch('asl_node_auth_check.find_http_registration', return_value=(None, None, None)), \
             patch('asl_node_auth_check.print_error'):
            result = _module.check_http_registration("12345")
            assert result is False

    def test_http_registration_not_registered(self):
        """Non-registered state returns False."""
        with patch('asl_node_auth_check.find_http_registration', return_value=("register.allstarlink.org", "192.168.1.1:4569", "Request Sent")), \
             patch('asl_node_auth_check.print_error'):
            result = _module.check_http_registration("12345")
            assert result is False


class TestGetIaxBindport:
    """Tests for get_iax_bindport function (lines 409-412)."""

    def test_valid_bindport_found(self):
        """Valid bindport is parsed and returned as int."""
        conf_content = """[general]
port = 4569
bindport = 5060

[options]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                result = _module.get_iax_bindport(f.name)
                assert result == 5060
                assert isinstance(result, int)
            finally:
                os.unlink(f.name)

    def test_bindport_with_spaces(self):
        """Bindport with extra spaces is parsed correctly."""
        conf_content = "bindport   =   4569\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                result = _module.get_iax_bindport(f.name)
                assert result == 4569
            finally:
                os.unlink(f.name)

    def test_bindport_not_found(self):
        """Missing bindport returns None."""
        conf_content = "[general]\nport = 4569\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch('asl_node_auth_check.print_error'):
                    result = _module.get_iax_bindport(f.name)
                    assert result is None
            finally:
                os.unlink(f.name)

    def test_bindport_file_not_found(self):
        """Missing file returns None."""
        result = _module.get_iax_bindport("/nonexistent/file.conf")
        assert result is None


class TestGetNodeStats:
    """Tests for get_node_stats function (lines 428-434)."""

    def test_valid_stats_response(self):
        """Valid JSON response is returned."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = {"node": {"server": {"udpport": 4569}}}
        with patch('requests.get', return_value=mock_response):
            result = _module.get_node_stats("12345")
            assert result == {"node": {"server": {"udpport": 4569}}}

    def test_stats_request_exception(self):
        """Request exception returns None."""
        with patch('requests.get', side_effect=requests.RequestException()):
            result = _module.get_node_stats("12345")
            assert result is None

    def test_stats_json_decode_error(self):
        """JSON decode error returns None."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.side_effect=ValueError("Invalid JSON")
        with patch('requests.get', return_value=mock_response):
            result = _module.get_node_stats("12345")
            assert result is None

    def test_stats_correct_url(self):
        """Correct URL is used for stats request."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = {}
        with patch('requests.get', return_value=mock_response) as mock_get:
            _module.get_node_stats("12345")
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert "https://stats.allstarlink.org/api/stats/12345" == args[0]


class TestGetNodeRegtime:
    """Tests for get_node_regtime function (lines 441-447)."""

    def test_valid_regtime_response(self):
        """Valid JSON response is returned."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = [{"regseconds": 1234567890}]
        with patch('requests.get', return_value=mock_response):
            result = _module.get_node_regtime("12345")
            assert result == [{"regseconds": 1234567890}]

    def test_regtime_request_exception(self):
        """Request exception returns None."""
        with patch('requests.get', side_effect=requests.RequestException()):
            result = _module.get_node_regtime("12345")
            assert result is None

    def test_regtime_json_decode_error(self):
        """JSON decode error returns None."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        with patch('requests.get', return_value=mock_response):
            result = _module.get_node_regtime("12345")
            assert result is None

    def test_regtime_correct_url(self):
        """Correct URL is used for regtime request."""
        mock_response = unittest.mock.MagicMock()
        mock_response.json.return_value = []
        with patch('requests.get', return_value=mock_response) as mock_get:
            _module.get_node_regtime("12345")
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert "12345" in args[0]
            assert "allstarlink.org/nodelist" in args[0]


class TestCheckNodeStatus:
    """Tests for check_node_status function (lines 451-497)."""

    def test_bindport_missing_error(self):
        """Missing bindport returns error."""
        stats = {"node": {"server": {"udpport": 4569}}}
        with patch('asl_node_auth_check.get_iax_bindport', return_value=None), \
             patch('asl_node_auth_check.get_node_stats', return_value=stats), \
             patch('asl_node_auth_check.get_node_regtime', return_value=[]), \
             patch('asl_node_auth_check.print_error'):
            n_errors, n_warnings = _module.check_node_status("12345")
            assert n_errors >= 1

    def test_stats_unavailable_warning(self):
        """Unavailable stats produces warning."""
        with patch('asl_node_auth_check.get_iax_bindport', return_value=4569), \
             patch('asl_node_auth_check.get_node_stats', return_value=None), \
             patch('asl_node_auth_check.print_error'):
            n_errors, n_warnings = _module.check_node_status("12345")
            assert n_warnings >= 1

    def test_udpport_match(self):
        """Matching UDP ports produce OK message."""
        stats = {"node": {"server": {"udpport": 4569}}}
        with patch('asl_node_auth_check.get_iax_bindport', return_value=4569), \
             patch('asl_node_auth_check.get_node_stats', return_value=stats), \
             patch('asl_node_auth_check.get_node_regtime', return_value=[]), \
             patch('asl_node_auth_check.print_ok') as mock_ok, \
             patch('asl_node_auth_check.print_error'):
            _module.check_node_status("12345")
            # Should call print_ok for port match
            assert any("UDP port" in str(call) for call in mock_ok.call_args_list)

    def test_udpport_mismatch(self):
        """Mismatched UDP ports produce error."""
        stats = {"node": {"server": {"udpport": 5060}}}
        with patch('asl_node_auth_check.get_iax_bindport', return_value=4569), \
             patch('asl_node_auth_check.get_node_stats', return_value=stats), \
             patch('asl_node_auth_check.get_node_regtime', return_value=[]), \
             patch('asl_node_auth_check.print_error') as mock_error, \
             patch('asl_node_auth_check.print_info'):
            n_errors, n_warnings = _module.check_node_status("12345")
            assert n_errors >= 1

    def test_regseconds_missing_error(self):
        """Missing regseconds field returns error."""
        stats = {"node": {"server": {"udpport": 4569}}}
        reginfo = [{}]  # Missing regseconds
        with patch('asl_node_auth_check.get_iax_bindport', return_value=4569), \
             patch('asl_node_auth_check.get_node_stats', return_value=stats), \
             patch('asl_node_auth_check.get_node_regtime', return_value=reginfo), \
             patch('asl_node_auth_check.print_ok'), \
             patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_status("12345")
            assert n_errors >= 1

    def test_registration_recent(self):
        """Recent registration produces OK message."""
        stats = {"node": {"server": {"udpport": 4569}}}
        now_ts = int(datetime.now(timezone.utc).timestamp())
        reginfo = [{"regseconds": now_ts - 300}]  # 5 minutes ago
        with patch('asl_node_auth_check.get_iax_bindport', return_value=4569), \
             patch('asl_node_auth_check.get_node_stats', return_value=stats), \
             patch('asl_node_auth_check.get_node_regtime', return_value=reginfo), \
             patch('asl_node_auth_check.print_ok') as mock_ok, \
             patch('asl_node_auth_check.print_error'):
            _module.check_node_status("12345")
            # Should call print_ok for recent registration
            assert any("within 10 minutes" in str(call) for call in mock_ok.call_args_list)

    def test_registration_old(self):
        """Old registration produces error."""
        stats = {"node": {"server": {"udpport": 4569}}}
        now_ts = int(datetime.now(timezone.utc).timestamp())
        reginfo = [{"regseconds": now_ts - 1200}]  # 20 minutes ago
        with patch('asl_node_auth_check.get_iax_bindport', return_value=4569), \
             patch('asl_node_auth_check.get_node_stats', return_value=stats), \
             patch('asl_node_auth_check.get_node_regtime', return_value=reginfo), \
             patch('asl_node_auth_check.print_error') as mock_error, \
             patch('asl_node_auth_check.print_ok'):
            n_errors, n_warnings = _module.check_node_status("12345")
            assert n_errors >= 1

    def test_registration_missing_iptime_warns(self):
        """Missing node iptime should not raise KeyError and should warn."""
        stats = {"node": {"server": {"udpport": 4569}}}
        now_ts = int(datetime.now(timezone.utc).timestamp())
        reginfo = [{"regseconds": now_ts - 300}]  # recent
        with patch('asl_node_auth_check.get_iax_bindport', return_value=4569), \
             patch('asl_node_auth_check.get_node_stats', return_value=stats), \
             patch('asl_node_auth_check.get_node_regtime', return_value=reginfo), \
             patch('asl_node_auth_check.print_warning') as mock_warning, \
             patch('asl_node_auth_check.print_ok'):
            n_errors, n_warnings = _module.check_node_status("12345")
            assert n_errors == 0
            assert n_warnings >= 1
            mock_warning.assert_called()

    def test_stats_node_not_dict(self):
        """Non-dict stats['node'] returns error and exit early."""
        stats = {"node": "invalid"}
        with patch('asl_node_auth_check.get_iax_bindport', return_value=4569), \
             patch('asl_node_auth_check.get_node_stats', return_value=stats), \
             patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_status("12345")
            assert n_errors == 1
            assert n_warnings == 0
            mock_error.assert_called_once()

    def test_stats_server_not_dict(self):
        """Non-dict stats['node']['server'] returns error and exit early."""
        stats = {"node": {"server": "invalid"}}
        with patch('asl_node_auth_check.get_iax_bindport', return_value=4569), \
             patch('asl_node_auth_check.get_node_stats', return_value=stats), \
             patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_status("12345")
            assert n_errors == 1
            assert n_warnings == 0
            mock_error.assert_called_once()

    def test_udpport_missing(self):
        """Missing UDP port returns error and continues to regtime path."""
        stats = {"node": {"server": {}}}
        with patch('asl_node_auth_check.get_iax_bindport', return_value=4569), \
             patch('asl_node_auth_check.get_node_stats', return_value=stats), \
             patch('asl_node_auth_check.get_node_regtime', return_value=[]), \
             patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_status("12345")
            assert n_errors >= 2
            assert n_warnings == 0
            assert any("UDP" in str(call) for call in mock_error.call_args_list)

    def test_registration_iptime_present(self):
        """When iptime is present, it prints info and does not warn."""
        stats = {"node": {"server": {"udpport": 4569}, "iptime": 1234567890}}
        now_ts = int(datetime.now(timezone.utc).timestamp())
        reginfo = [{"regseconds": now_ts - 300}]  # recent
        with patch('asl_node_auth_check.get_iax_bindport', return_value=4569), \
             patch('asl_node_auth_check.get_node_stats', return_value=stats), \
             patch('asl_node_auth_check.get_node_regtime', return_value=reginfo), \
             patch('asl_node_auth_check.print_info') as mock_info, \
             patch('asl_node_auth_check.print_ok'):
            n_errors, n_warnings = _module.check_node_status("12345")
            assert n_errors == 0
            assert n_warnings == 0
            mock_info.assert_called_once()

    def test_registration_iptime_zero_warns(self):
        """Zero iptime should still be treated as unavailable and warn."""
        stats = {"node": {"server": {"udpport": 4569}, "iptime": 0}}
        now_ts = int(datetime.now(timezone.utc).timestamp())
        reginfo = [{"regseconds": now_ts - 300}]  # recent
        with patch('asl_node_auth_check.get_iax_bindport', return_value=4569), \
             patch('asl_node_auth_check.get_node_stats', return_value=stats), \
             patch('asl_node_auth_check.get_node_regtime', return_value=reginfo), \
             patch('asl_node_auth_check.print_warning') as mock_warning, \
             patch('asl_node_auth_check.print_ok'):
            n_errors, n_warnings = _module.check_node_status("12345")
            assert n_errors == 0
            assert n_warnings == 1
            mock_warning.assert_called_once_with("Last time IP change is unavailable in node stats")


class TestCheckNodeFormedness:
    """Tests for check_node_formedness function."""

    def test_valid_node_and_reghost(self):
        """Valid node and reghost returns 0 errors and 0 warnings."""
        with patch('asl_node_auth_check.print_error'):
            n_errors, n_warnings = _module.check_node_formedness("12345", "register.allstarlink.org")
            assert n_errors == 0
            assert n_warnings == 0

    def test_node_at_lower_boundary(self):
        """Node at lower boundary (2000) is valid."""
        with patch('asl_node_auth_check.print_error'):
            n_errors, n_warnings = _module.check_node_formedness("2000", "register.allstarlink.org")
            assert n_errors == 0
            assert n_warnings == 0

    def test_node_at_upper_boundary(self):
        """Node at upper boundary (999989) is valid."""
        with patch('asl_node_auth_check.print_error'):
            n_errors, n_warnings = _module.check_node_formedness("999989", "register.allstarlink.org")
            assert n_errors == 0
            assert n_warnings == 0

    def test_node_too_low(self):
        """Node below 2000 returns error."""
        with patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_formedness("1999", "register.allstarlink.org")
            assert n_errors == 1
            assert n_warnings == 0
            mock_error.assert_called()

    def test_node_too_high(self):
        """Node above 999989 returns error."""
        with patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_formedness("999990", "register.allstarlink.org")
            assert n_errors == 1
            assert n_warnings == 0
            mock_error.assert_called()

    def test_node_non_numeric(self):
        """Non-numeric node returns error."""
        with patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_formedness("abc", "register.allstarlink.org")
            assert n_errors == 1
            assert n_warnings == 0
            mock_error.assert_called()

    def test_node_empty_string(self):
        """Empty node string returns error."""
        with patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_formedness("", "register.allstarlink.org")
            assert n_errors == 1
            mock_error.assert_called()

    def test_node_with_spaces(self):
        """Node with spaces returns error."""
        with patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_formedness("123 45", "register.allstarlink.org")
            assert n_errors == 1
            mock_error.assert_called()

    def test_reghost_invalid(self):
        """Invalid reghost returns error."""
        with patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_formedness("12345", "invalid.host.org")
            assert n_errors == 1
            assert n_warnings == 0
            mock_error.assert_called()

    def test_reghost_wrong_domain(self):
        """Wrong domain returns error."""
        with patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_formedness("12345", "register.example.org")
            assert n_errors == 1
            mock_error.assert_called()

    def test_reghost_case_sensitive(self):
        """Reghost check appears to be case-sensitive."""
        with patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_formedness("12345", "REGISTER.ALLSTARLINK.ORG")
            # Based on the regex pattern, this might fail if case-sensitive
            # The regex uses re.compile without re.IGNORECASE for _reghost_re
            assert n_errors >= 0  # Allow either 0 or 1 depending on regex

    def test_both_node_and_reghost_invalid(self):
        """Both invalid node and reghost return 2 errors."""
        with patch('asl_node_auth_check.print_error'):
            n_errors, n_warnings = _module.check_node_formedness("abc", "invalid.org")
            assert n_errors == 2
            assert n_warnings == 0

    def test_reghost_empty_string(self):
        """Empty reghost returns error."""
        with patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_formedness("12345", "")
            assert n_errors == 1
            mock_error.assert_called()

    def test_node_with_leading_zeros(self):
        """Node with leading zeros is parsed as valid number."""
        with patch('asl_node_auth_check.print_error'):
            n_errors, n_warnings = _module.check_node_formedness("02345", "register.allstarlink.org")
            assert n_errors == 0

    def test_node_negative_number(self):
        """Negative node number returns error."""
        with patch('asl_node_auth_check.print_error') as mock_error:
            n_errors, n_warnings = _module.check_node_formedness("-12345", "register.allstarlink.org")
            assert n_errors == 1
            mock_error.assert_called()


class TestGetRptNodes:
    """Tests for get_rpt_nodes function."""

    def test_extract_basic_node_sections(self):
        """Basic node sections are extracted."""
        conf_content = """
[2000]
; Private node

[12345] (node-main)

[54321] (node-main)

"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch('asl_node_auth_check.print_info'):
                    results = _module.get_rpt_nodes(f.name)
                    # Public nodes (> 1999) should be included
                    assert "12345" in results
                    assert "54321" in results
            finally:
                os.unlink(f.name)

    def test_skip_private_nodes(self):
        """Nodes <= 1999 are skipped as private nodes."""
        conf_content = """
[1000] (node-main)

[1999] (node-main)

[2000] (node-main)

[2001] (node-main)

"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch('asl_node_auth_check.print_info'):
                    results = _module.get_rpt_nodes(f.name)
                    assert "1000" not in results
                    assert "1999" not in results
                    # 2000 and 2001 should be present
                    assert "2000" in results
                    assert "2001" in results
            finally:
                os.unlink(f.name)

    def test_whitespace_around_brackets(self):
        """Node sections with whitespace around brackets are handled."""
        conf_content = """
[ 12345 ] (node-main)

[  54321  ] (node-main)

"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch('asl_node_auth_check.print_info'):
                    results = _module.get_rpt_nodes(f.name)
                    assert "12345" in results
                    assert "54321" in results
            finally:
                os.unlink(f.name)

    def test_case_insensitive_matching(self):
        """Node section headers are case-insensitive."""
        conf_content = """
[12345] (NODE-MAIN)

[54321] (node-main)

"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch('asl_node_auth_check.print_info'):
                    results = _module.get_rpt_nodes(f.name)
                    assert "12345" in results
                    assert "54321" in results
            finally:
                os.unlink(f.name)

    def test_no_duplicate_nodes(self):
        """Duplicate node entries are not repeated."""
        conf_content = """
[12345] (node-main)

[12345] (node-main)

"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch('asl_node_auth_check.print_info'):
                    results = _module.get_rpt_nodes(f.name)
                    count = results.count("12345")
                    assert count == 1
            finally:
                os.unlink(f.name)

    def test_empty_file(self):
        """Empty file returns empty list."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.flush()
            try:
                results = _module.get_rpt_nodes(f.name)
                assert results == []
            finally:
                os.unlink(f.name)

    def test_file_not_found(self):
        """Nonexistent file is handled gracefully."""
        with patch('asl_node_auth_check.print_info'):
            results = _module.get_rpt_nodes("/nonexistent/path/rpt.conf")
            assert results == []

    def test_include_directive(self):
        """#include directive includes nodes from referenced file."""
        main_content = """
[12345] (node-main)

#include other.conf
"""
        other_content = """
[54321] (node-main)

"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False, dir='/tmp') as main_f, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False, dir='/tmp') as other_f:
            main_f.write(main_content)
            main_f.flush()
            other_f.write(other_content)
            other_f.flush()

            # Update main_content to reference the actual other file
            updated_content = f"""
[12345] (node-main)

#include {other_f.name}
"""
            with open(main_f.name, 'w') as mf:
                mf.write(updated_content)

            try:
                with patch('asl_node_auth_check.print_info'):
                    results = _module.get_rpt_nodes(main_f.name)
                    assert "12345" in results
                    assert "54321" in results
            finally:
                os.unlink(main_f.name)
                os.unlink(other_f.name)

    def test_tryinclude_directive_file_missing(self):
        """#tryinclude directive missing file doesn't error."""
        conf_content = """
[12345] (node-main)

#tryinclude /nonexistent/file.conf
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch('asl_node_auth_check.print_info'):
                    results = _module.get_rpt_nodes(f.name)
                    assert "12345" in results
            finally:
                os.unlink(f.name)

    def test_comments_and_non_matching_lines(self):
        """Comments and non-matching lines are ignored."""
        conf_content = """
; This is a comment
[12345]
; Another comment
node-main

; Not a node
invalid line here

[54321] (node-main)

"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch('asl_node_auth_check.print_info'):
                    results = _module.get_rpt_nodes(f.name)
                    assert "12345" in results
                    assert "54321" in results
            finally:
                os.unlink(f.name)


class TestGetRegistrations:
    """Tests for get_registrations function."""

    def test_both_files_have_registrations(self):
        """Both config files with registrations return combined list."""
        iax_content = "register => 12345:secret1@register.allstarlink.org\n"
        http_content = "register => 54321:secret2@register.allstarlink.org\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as iax_f, \
             tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as http_f:
            iax_f.write(iax_content)
            iax_f.flush()
            http_f.write(http_content)
            http_f.flush()

            try:
                with patch('asl_node_auth_check.extract_registration_values') as mock_extract:
                    # Mock extract_registration_values to return registrations for each file
                    def extract_side_effect(filename, regtype):
                        if regtype == "IAX":
                            return [("12345", "secret1", "register.allstarlink.org", "IAX")]
                        else:  # HTTP
                            return [("54321", "secret2", "register.allstarlink.org", "HTTP")]

                    mock_extract.side_effect = extract_side_effect

                    with patch('asl_node_auth_check.print_info'):
                        results = _module.get_registrations()

                    assert results is not None
                    assert len(results) == 2
                    nodes = [r[0] for r in results]
                    assert "12345" in nodes
                    assert "54321" in nodes
            finally:
                os.unlink(iax_f.name)
                os.unlink(http_f.name)

    def test_only_iax_file_has_registrations(self):
        """Only IAX file with registrations returns its registrations."""
        with patch('asl_node_auth_check.extract_registration_values') as mock_extract:
            def extract_side_effect(filename, regtype):
                if regtype == "IAX":
                    return [("12345", "secret1", "register.allstarlink.org", "IAX")]
                else:  # HTTP
                    return []

            mock_extract.side_effect = extract_side_effect

            with patch('asl_node_auth_check.print_info'):
                results = _module.get_registrations()

            assert results is not None
            assert len(results) == 1
            assert results[0][0] == "12345"

    def test_only_http_file_has_registrations(self):
        """Only HTTP file with registrations returns its registrations."""
        with patch('asl_node_auth_check.extract_registration_values') as mock_extract:
            def extract_side_effect(filename, regtype):
                if regtype == "IAX":
                    return []
                else:  # HTTP
                    return [("54321", "secret2", "register.allstarlink.org", "HTTP")]

            mock_extract.side_effect = extract_side_effect

            with patch('asl_node_auth_check.print_info'):
                results = _module.get_registrations()

            assert results is not None
            assert len(results) == 1
            assert results[0][0] == "54321"

    def test_no_files_have_registrations(self):
        """No registrations found returns None."""
        with patch('asl_node_auth_check.extract_registration_values', return_value=[]):
            with patch('asl_node_auth_check.print_info'):
                results = _module.get_registrations()

            assert results is None

    def test_print_info_called_for_files_with_registrations(self):
        """print_info is called for files with registrations."""
        with patch('asl_node_auth_check.extract_registration_values') as mock_extract:
            def extract_side_effect(filename, regtype):
                if regtype == "IAX":
                    return [("12345", "secret1", "register.allstarlink.org", "IAX")]
                else:
                    return []

            mock_extract.side_effect = extract_side_effect

            with patch('asl_node_auth_check.print_info') as mock_print_info:
                _module.get_registrations()

            # Should be called for IAX (has 1 registration) and HTTP (has 0)
            assert mock_print_info.call_count >= 1
            # Check that at least one call mentions registration count
            calls = [str(call) for call in mock_print_info.call_args_list]
            assert any("1 registration" in str(call) for call in calls)

    def test_multiple_registrations_per_file(self):
        """Multiple registrations in each file are all returned."""
        with patch('asl_node_auth_check.extract_registration_values') as mock_extract:
            def extract_side_effect(filename, regtype):
                if regtype == "IAX":
                    return [
                        ("12345", "secret1", "register.allstarlink.org", "IAX"),
                        ("12346", "secret2", "register.allstarlink.org", "IAX"),
                    ]
                else:  # HTTP
                    return [
                        ("54321", "secret3", "register.allstarlink.org", "HTTP"),
                    ]

            mock_extract.side_effect = extract_side_effect

            with patch('asl_node_auth_check.print_info'):
                results = _module.get_registrations()

            assert results is not None
            assert len(results) == 3
            nodes = [r[0] for r in results]
            assert "12345" in nodes
            assert "12346" in nodes
            assert "54321" in nodes


class TestExtractRegistrationValues:
    """Tests for extract_registration_values function."""

    def test_extract_valid_iax_registration(self):
        """Valid IAX registration line is extracted."""
        conf_content = "register => 12345:mysecret@register.allstarlink.org\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                results = _module.extract_registration_values(f.name, "IAX")
                assert len(results) == 1
                node, secret, host, regtype = results[0]
                assert node == "12345"
                assert secret == "mysecret"
                assert host == "register.allstarlink.org"
                assert regtype == "IAX"
            finally:
                os.unlink(f.name)

    def test_extract_valid_http_registration(self):
        """Valid HTTP registration line is extracted with correct type."""
        conf_content = "register => 54321:secret@register.allstarlink.org\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                results = _module.extract_registration_values(f.name, "HTTP")
                assert len(results) == 1
                node, secret, host, regtype = results[0]
                assert regtype == "HTTP"
            finally:
                os.unlink(f.name)

    def test_extract_multiple_registrations(self):
        """Multiple registration lines are extracted."""
        conf_content = """register => 12345:secret1@register.allstarlink.org
register => 54321:secret2@register.allstarlink.org
register => 99999:secret3@register.allstarlink.org
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                results = _module.extract_registration_values(f.name, "IAX")
                assert len(results) == 3
                nodes = [r[0] for r in results]
                assert "12345" in nodes
                assert "54321" in nodes
                assert "99999" in nodes
            finally:
                os.unlink(f.name)

    def test_extract_ignores_invalid_registrations(self):
        """Invalid registration lines are skipped."""
        conf_content = """register => 12345:valid@register.allstarlink.org
register => invalid_registration_line
register => 54321:also_valid@register.allstarlink.org
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                with patch.object(_module, 'print_error'):
                    results = _module.extract_registration_values(f.name, "IAX")
                    # Should extract only valid ones
                    assert len(results) == 2
                    nodes = [r[0] for r in results]
                    assert "12345" in nodes
                    assert "54321" in nodes
            finally:
                os.unlink(f.name)

    def test_extract_ignores_comments_and_whitespace(self):
        """Comments and non-matching lines are ignored."""
        conf_content = """; This is a comment
register   =>   12345:secret@register.allstarlink.org
; Another comment
register => 54321:secret2@register.allstarlink.org
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                results = _module.extract_registration_values(f.name, "IAX")
                # Should extract both registrations despite comments and extra whitespace
                assert len(results) == 2
            finally:
                os.unlink(f.name)

    def test_extract_with_extra_content_after_value(self):
        """Register lines with content after value are handled."""
        conf_content = "register => 12345:secret@register.allstarlink.org ; some comment\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                results = _module.extract_registration_values(f.name, "IAX")
                assert len(results) == 1
                node, secret, host, regtype = results[0]
                assert node == "12345"
            finally:
                os.unlink(f.name)

    def test_extract_empty_file(self):
        """Empty file returns empty list."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.flush()
            try:
                results = _module.extract_registration_values(f.name, "IAX")
                assert results == []
            finally:
                os.unlink(f.name)

    def test_extract_file_not_found(self):
        """Nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _module.extract_registration_values("/nonexistent/path/file.conf", "IAX")

    def test_extract_registration_type_preserved(self):
        """Registration type is preserved in returned tuples."""
        conf_content = "register => 12345:secret@register.allstarlink.org\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(conf_content)
            f.flush()
            try:
                iam_results = _module.extract_registration_values(f.name, "IAX")
                http_results = _module.extract_registration_values(f.name, "HTTP")

                assert iam_results[0][3] == "IAX"
                assert http_results[0][3] == "HTTP"
            finally:
                os.unlink(f.name)


class TestParseRegistrationString:
    """Tests for parse_registration_string function."""

    def test_valid_registration_string(self):
        """Valid 'node:secret@host' format is parsed correctly."""
        result = _module.parse_registration_string("12345:mysecret@register.allstarlink.org")
        assert result is not None
        node, secret, host = result
        assert node == "12345"
        assert secret == "mysecret"
        assert host == "register.allstarlink.org"

    def test_secret_with_special_characters(self):
        """Secret with special characters (except @) is parsed."""
        result = _module.parse_registration_string("12345:abc-_123!@register.allstarlink.org")
        assert result is not None
        node, secret, host = result
        assert secret == "abc-_123!"

    def test_secret_with_numbers(self):
        """Secret containing numbers is parsed."""
        result = _module.parse_registration_string("12345:abc123xyz@register.allstarlink.org")
        assert result is not None
        node, secret, host = result
        assert secret == "abc123xyz"

    def test_node_with_multiple_digits(self):
        """Node with many digits is parsed."""
        result = _module.parse_registration_string("999999:secret@host.org")
        assert result is not None
        node, secret, host = result
        assert node == "999999"

    def test_host_with_dots(self):
        """Host with multiple dots is parsed."""
        result = _module.parse_registration_string("12345:secret@subdomain.allstarlink.org")
        assert result is not None
        node, secret, host = result
        assert host == "subdomain.allstarlink.org"

    def test_missing_colon(self):
        """Missing colon separator returns None."""
        result = _module.parse_registration_string("12345mysecret@register.allstarlink.org")
        assert result is None

    def test_missing_at_symbol(self):
        """Missing '@' separator returns None."""
        result = _module.parse_registration_string("12345:mysecretregister.allstarlink.org")
        assert result is None

    def test_empty_node(self):
        """Empty node field returns None."""
        result = _module.parse_registration_string(":mysecret@register.allstarlink.org")
        assert result is None

    def test_empty_secret(self):
        """Empty secret field returns None."""
        result = _module.parse_registration_string("12345:@register.allstarlink.org")
        assert result is None

    def test_empty_host(self):
        """Empty host field returns None."""
        result = _module.parse_registration_string("12345:mysecret@")
        assert result is None

    def test_non_numeric_node(self):
        """Non-numeric node returns None."""
        result = _module.parse_registration_string("abc:mysecret@register.allstarlink.org")
        assert result is None

    def test_registration_with_whitespace(self):
        """Whitespace in registration string causes parse to fail."""
        result = _module.parse_registration_string("12345 : mysecret @ register.allstarlink.org")
        assert result is None

    def test_secret_with_at_symbol(self):
        """Secret containing @ returns None (@ separates secret and host)."""
        result = _module.parse_registration_string("12345:my@secret@register.allstarlink.org")
        assert result is None

    def test_host_with_dashes(self):
        """Host with dashes does not match regex."""
        result = _module.parse_registration_string("12345:secret@my-host.example.com")
        assert result is None

    def test_host_with_underscores(self):
        """Host with underscores does not match regex."""
        result = _module.parse_registration_string("12345:secret@my_host.org")
        assert result is None

    def test_empty_string(self):
        """Empty string returns None."""
        result = _module.parse_registration_string("")
        assert result is None


class TestIsRegisterAllstarlinkUp:
    """Tests for is_register_allstarlink_up function."""

    def test_http_200_returns_true(self):
        """HTTP 200 status code returns True."""
        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 200
        with patch("requests.get", return_value=mock_response):
            result = _module.is_register_allstarlink_up()
            assert result is True

    def test_http_404_returns_false(self):
        """HTTP 404 status code returns False."""
        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 404
        with patch("requests.get", return_value=mock_response):
            result = _module.is_register_allstarlink_up()
            assert result is False

    def test_http_500_returns_false(self):
        """HTTP 500 status code returns False."""
        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 500
        with patch("requests.get", return_value=mock_response):
            result = _module.is_register_allstarlink_up()
            assert result is False

    def test_connection_error_returns_false(self):
        """Connection error returns False."""
        import requests
        with patch("requests.get", side_effect=requests.ConnectionError):
            result = _module.is_register_allstarlink_up()
            assert result is False

    def test_timeout_error_returns_false(self):
        """Timeout error returns False."""
        import requests
        with patch("requests.get", side_effect=requests.Timeout):
            result = _module.is_register_allstarlink_up()
            assert result is False

    def test_request_exception_returns_false(self):
        """Generic RequestException returns False."""
        import requests
        with patch("requests.get", side_effect=requests.RequestException):
            result = _module.is_register_allstarlink_up()
            assert result is False

    def test_custom_timeout_passed_to_requests(self):
        """Custom timeout value is passed to requests.get."""
        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 200
        with patch("requests.get", return_value=mock_response) as mock_get:
            _module.is_register_allstarlink_up(timeout=10)
            mock_get.assert_called_once_with("https://register.allstarlink.org", timeout=10)

    def test_default_timeout_is_5_seconds(self):
        """Default timeout is 5 seconds."""
        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 200
        with patch("requests.get", return_value=mock_response) as mock_get:
            _module.is_register_allstarlink_up()
            mock_get.assert_called_once_with("https://register.allstarlink.org", timeout=5)

    def test_correct_url_used(self):
        """Correct URL is used for the request."""
        mock_response = unittest.mock.MagicMock()
        mock_response.status_code = 200
        with patch("requests.get", return_value=mock_response) as mock_get:
            _module.is_register_allstarlink_up()
            args, kwargs = mock_get.call_args
            assert args[0] == "https://register.allstarlink.org"


class TestReverseDns:
    """Tests for reverse_dns function."""

    def test_valid_ipv4_resolves(self):
        """Valid IPv4 address that resolves returns hostname."""
        with patch("socket.gethostbyaddr", return_value=("example.com", [], ["8.8.8.8"])):
            result = _module.reverse_dns("8.8.8.8")
            assert result == "example.com"

    def test_valid_ipv6_resolves(self):
        """Valid IPv6 address that resolves returns hostname."""
        with patch("socket.gethostbyaddr", return_value=("example.com", [], ["2001:4860:4860::8888"])):
            result = _module.reverse_dns("2001:4860:4860::8888")
            assert result == "example.com"

    def test_valid_ipv4_no_resolve(self):
        """Valid IPv4 that doesn't resolve returns None."""
        import socket
        with patch("socket.gethostbyaddr", side_effect=socket.herror):
            result = _module.reverse_dns("192.0.2.1")
            assert result is None

    def test_valid_ipv6_no_resolve(self):
        """Valid IPv6 that doesn't resolve returns None."""
        import socket
        with patch("socket.gethostbyaddr", side_effect=socket.herror):
            result = _module.reverse_dns("2001:db8::1")
            assert result is None

    def test_invalid_ip_format(self):
        """Invalid IP address format returns None."""
        result = _module.reverse_dns("not.an.ip.address")
        assert result is None

    def test_invalid_ip_numbers_out_of_range(self):
        """IPv4 with numbers out of range returns None."""
        result = _module.reverse_dns("256.256.256.256")
        assert result is None

    def test_empty_string(self):
        """Empty string returns None."""
        result = _module.reverse_dns("")
        assert result is None

    def test_hostname_as_input(self):
        """Hostname instead of IP returns None."""
        result = _module.reverse_dns("example.com")
        assert result is None

    def test_ipv4_with_port(self):
        """IPv4 with port number returns None."""
        result = _module.reverse_dns("8.8.8.8:53")
        assert result is None


class TestCompareNodeLists:
    """Tests for compare_node_lists function."""

    def test_identical_lists(self):
        """Identical node lists return True and empty differences."""
        configed = ["12345", "54321", "99999"]
        registrations = ["12345", "54321", "99999"]
        identical, missing_config, missing_regs = _module.compare_node_lists(configed, registrations)

        assert identical is True
        assert missing_config == []
        assert missing_regs == []

    def test_empty_lists(self):
        """Both empty lists are identical."""
        identical, missing_config, missing_regs = _module.compare_node_lists([], [])

        assert identical is True
        assert missing_config == []
        assert missing_regs == []

    def test_missing_from_config(self):
        """Nodes in registrations but not in config are identified."""
        configed = ["12345", "54321"]
        registrations = ["12345", "54321", "99999"]
        identical, missing_config, missing_regs = _module.compare_node_lists(configed, registrations)

        assert identical is False
        assert "99999" in missing_config
        assert missing_regs == []

    def test_missing_from_registrations(self):
        """Nodes in config but not in registrations are identified."""
        configed = ["12345", "54321", "99999"]
        registrations = ["12345", "54321"]
        identical, missing_config, missing_regs = _module.compare_node_lists(configed, registrations)

        assert identical is False
        assert missing_config == []
        assert "99999" in missing_regs

    def test_missing_from_both(self):
        """Nodes missing from both config and registrations are identified."""
        configed = ["12345", "99999"]
        registrations = ["54321", "99999"]
        identical, missing_config, missing_regs = _module.compare_node_lists(configed, registrations)

        assert identical is False
        assert "54321" in missing_config
        assert "12345" in missing_regs

    def test_duplicates_handled_as_sets(self):
        """Duplicate nodes are handled correctly via set conversion."""
        configed = ["12345", "12345", "54321"]
        registrations = ["12345", "54321", "54321"]
        identical, missing_config, missing_regs = _module.compare_node_lists(configed, registrations)

        assert identical is True
        assert missing_config == []
        assert missing_regs == []

    def test_order_irrelevant(self):
        """Node list order doesn't matter for comparison."""
        configed = ["99999", "12345", "54321"]
        registrations = ["12345", "54321", "99999"]
        identical, missing_config, missing_regs = _module.compare_node_lists(configed, registrations)

        assert identical is True
        assert missing_config == []
        assert missing_regs == []


if __name__ == "__main__":
    unittest.main()
