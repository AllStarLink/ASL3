"""
Tests for the changes in check_node_status() in bin/asl-node-auth-check.

PR changes covered:
  1. node_reginfo is None or len(node_reginfo) == 0  -> error + early return
  2. reg_since (regseconds) is None                  -> error + early return
"""

import importlib.machinery
import importlib.util
import os
import sys
import unittest
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, patch

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
check_node_status = _mod.check_node_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A recent timestamp (5 minutes ago) – well within the 10-minute window
def _recent_regseconds():
    return int((datetime.now(UTC) - timedelta(minutes=5)).timestamp())

# An old timestamp (15 minutes ago) – outside the 10-minute window
def _old_regseconds():
    return int((datetime.now(UTC) - timedelta(minutes=15)).timestamp())

# A stats response that satisfies all checks other than the regtime path

_VALID_STATS = {"stats":{"id":51941,
          "node":12345,
          "data":{"apprptuptime":"92435",
                  "totalexecdcommands":"22",
                  "totalkeyups":"36",
                  "totaltxtime":"219",
                  "apprptvers":"3.8.3",
                  "timeouts":"0",
                  "links":["287893"],
                  "keyed":False,
                  "time":"1774631643",
                  "seqno":"1551",
                  "nodes":"T287893",
                  "totalkerchunks":"3",
                  "keytime":"87920",
                  "linkedNodes":[{"Node_ID":39151,
                                  "User_ID ":"K8SN",
                                  "Status":"Active",
                                  "name":287893,
                                  "ipaddr":"127.0.0.1",
                                  "port":4569,
                                  "regseconds":1774628887,
                                  "iptime":"2024-03-24 15:34:42",
                                  "node_frequency":"31269 Link WMTG",
                                  "node_tone":"TS2 CC1",
                                  "node_remotebase":False,
                                  "node_freqagile":"0",
                                  "callsign":"WM8TG\\DMR",
                                  "access_reverseautopatch":"0",
                                  "access_telephoneportal":"0",
                                  "access_webtransceiver":"1",
                                  "access_functionlist":"1",
                                  "is_nnx":"Yes",
                                  "server":{"Server_ID":1783,
                                            "User_ID":"K8SN",
                                            "Server_Name":"WMTG Hub Nodes",
                                            "Affiliation":"West Michigan Technical Group",
                                            "SiteName":"WMTG Hub Server Room",
                                            "Logitude":"-85.703622",
                                            "Latitude":"42.855955","Location":"Wyoming MI",
                                            "TimeZone":"-5.0","udpport":4569,
                                            "proxy_ip":None}}]},
          "created_at":"2026-02-27T14:20:37.000000Z",
          "updated_at":"2026-03-27T17:14:03.000000Z",
          "user_node":{"Node_ID":94880,
                       "User_ID":"WB6NIL",
                       "Status":"Active",
                       "name":12345,
                       "ipaddr":"127.0.0.1",
                       "port":4569,"regseconds":1774099899,
                       "iptime":"2026-03-18 18:16:29",
                       "node_frequency":"",
                       "node_tone":"",
                       "node_remotebase":False,
                       "node_freqagile":"0",
                       "callsign":"WB6NIL",
                       "access_reverseautopatch":"0",
                       "access_telephoneportal":"0",
                       "access_webtransceiver":"1",
                       "access_functionlist":"1",
                       "is_nnx":"No",
                       "server":{"Server_ID":42270,
                                 "User_ID":"WB6NIL",
                                 "Server_Name":"WB6NIL",
                                 "Affiliation":"",
                                 "SiteName":"Climax",
                                 "Logitude":"-85.81169",
                                 "Latitude":"42.926929",
                                 "Location":"Climax, MI",
                                 "TimeZone":None,
                                 "udpport":4569,
                                 "proxy_ip":None}}},
 "node":{"Node_ID":94880,
         "User_ID":"WB6NIL",
         "Status":"Active",
         "name":12345,
         "ipaddr":"44.15.4.13",
         "port":4569,
         "regseconds":1774628260,
         "iptime":"2026-03-18 18:16:29",
         "node_frequency":"",
         "node_tone":"",
         "node_remotebase":False,
         "node_freqagile":"0",
         "callsign":"WB6NIL",
         "access_reverseautopatch":"0",
         "access_telephoneportal":"0",
         "access_webtransceiver":"1",
         "access_functionlist":"1",
         "is_nnx":"No",
         "server":{"Server_ID":42270,
                   "User_ID":"WB6NIL",
                   "Server_Name":"WB6NIL",
                   "Affiliation":"",
                   "SiteName":"Climax",
                   "Logitude":"-85.81169",
                   "Latitude":"42.926929",
                   "Location":"Climax, MI",
                   "TimeZone":None,
                   "udpport":4569,
                   "proxy_ip":None}},
 "keyups":[],
 "time":1.786947250366211,
 }

_REGISTRATION = [
        {
            "name": 12345,
            "User_ID": "WB6NIL",
            "callsign": "WB6NIL",
            "node_frequency": "",
            "node_tone": "",
            "Location": "Climax, MI",
            "SiteName": "Climax",
            "Affiliation": "",
            "regseconds":  _recent_regseconds(),
            "access_webtransceiver": "1",
            "access_telephoneportal": "0"
        }
    ]

class TestCheckNodeStatusReginfo(unittest.TestCase):
    """Tests focused on the node_reginfo guard (None / empty list)."""

    # ------------------------------------------------------------------
    # Patch targets living inside the loaded module
    # ------------------------------------------------------------------
    _MODULE = "asl_node_auth_check"

    def _run(self, bindport, stats, reginfo):
        """Run check_node_status with the given mock return values."""
        with patch.object(_mod, "get_iax_bindport", return_value=bindport), \
             patch.object(_mod, "get_node_stats",   return_value=stats), \
             patch.object(_mod, "get_node_regtime", return_value=reginfo), \
             patch.object(_mod, "print_error")  as mock_err, \
             patch.object(_mod, "print_ok")     as mock_ok, \
             patch.object(_mod, "print_info"):
            result = check_node_status("12345")
            return result, mock_err, mock_ok

    # --- node_reginfo is None -------------------------------------------

    def test_reginfo_none_returns_error_and_early_exit(self):
        """When get_node_regtime returns None, one error is added and the
        function returns without attempting further processing."""
        (n_errors, n_warnings), mock_err, _ = self._run(
            bindport=4569,
            stats=_VALID_STATS,
            reginfo=None,
        )
        self.assertEqual(n_errors, 1)
        self.assertEqual(n_warnings, 0)

    def test_reginfo_none_prints_error_message(self):
        """When get_node_regtime returns None, an error message is printed."""
        _, mock_err, _ = self._run(
            bindport=4569,
            stats=_VALID_STATS,
            reginfo=None,
        )
        mock_err.assert_called_once()
        args, _ = mock_err.call_args
        self.assertIn("No registration information available", args[0])

    # --- node_reginfo is empty list (NEW behaviour) ---------------------

    def test_reginfo_empty_list_returns_error_and_early_exit(self):
        """When get_node_regtime returns an empty list, one error is added
        and the function exits early (new guard added in this PR)."""
        (n_errors, n_warnings), mock_err, _ = self._run(
            bindport=4569,
            stats=_VALID_STATS,
            reginfo=[],
        )
        self.assertEqual(n_errors, 1)
        self.assertEqual(n_warnings, 0)

    def test_reginfo_empty_list_prints_error_message(self):
        """When get_node_regtime returns [], an appropriate error is printed."""
        _, mock_err, _ = self._run(
            bindport=4569,
            stats=_VALID_STATS,
            reginfo=[],
        )
        mock_err.assert_called_once()
        args, _ = mock_err.call_args
        self.assertIn("No registration information available", args[0])

    def test_reginfo_empty_list_does_not_raise(self):
        """Empty list must not cause an IndexError or similar exception
        (regression: previously the code would crash before this PR)."""
        try:
            self._run(bindport=4569, stats=_VALID_STATS, reginfo=[])
        except (IndexError, TypeError) as exc:
            self.fail(f"check_node_status raised {type(exc).__name__} for empty reginfo")

    # --- Boundary: single-element list (must NOT trigger empty-list guard) --

    def test_reginfo_single_element_not_treated_as_empty(self):
        """A list with one element is valid and must pass the empty-list guard."""
        (n_errors, _), _, _ = self._run(
            bindport=4569,
            stats=_VALID_STATS,
            reginfo=_REGISTRATION,
        )
        # UDP port matches, reg is recent → no errors
        self.assertEqual(n_errors, 0)


class TestCheckNodeStatusRegseconds(unittest.TestCase):
    """Tests focused on the regseconds (reg_since) None guard (new in this PR)."""

    def _run(self, reginfo):
        with patch.object(_mod, "get_iax_bindport", return_value=4569), \
             patch.object(_mod, "get_node_stats",   return_value=_VALID_STATS), \
             patch.object(_mod, "get_node_regtime", return_value=reginfo), \
             patch.object(_mod, "print_error")  as mock_err, \
             patch.object(_mod, "print_ok"), \
             patch.object(_mod, "print_info"):
            result = check_node_status("12345")
            return result, mock_err

    # --- regseconds missing (key absent) --------------------------------

    def test_regseconds_none_returns_error_and_early_exit(self):
        """When the first reginfo element has no 'regseconds' key (get returns
        None), one error is recorded and the function exits early."""
        reginfo = [{}]  # 'regseconds' key absent → .get() returns None
        (n_errors, n_warnings), mock_err = self._run(reginfo)
        self.assertEqual(n_errors, 1)
        self.assertEqual(n_warnings, 0)

    def test_regseconds_none_prints_error_message(self):
        """When 'regseconds' is missing, the correct error message is printed."""
        reginfo = [{}]
        _, mock_err = self._run(reginfo)
        # Expect exactly one call for the missing-regseconds error.
        # (There might also be a UDP-port error, but the regseconds error
        # must be present.)
        error_msgs = [call.args[0] for call in mock_err.call_args_list]
        self.assertTrue(
            any("regseconds" in m for m in error_msgs),
            f"Expected a 'regseconds' error but got: {error_msgs}",
        )

    def test_regseconds_explicitly_none_returns_error(self):
        """When 'regseconds' is present but explicitly set to None, treat it
        the same as absent."""
        reginfo = [{"regseconds": None}]
        (n_errors, _), mock_err = self._run(reginfo)
        self.assertEqual(n_errors, 1)
        error_msgs = [call.args[0] for call in mock_err.call_args_list]
        self.assertTrue(
            any("regseconds" in m for m in error_msgs),
            f"Expected a 'regseconds' error but got: {error_msgs}",
        )

    def test_regseconds_none_does_not_raise(self):
        """Missing 'regseconds' must not cause a TypeError or similar crash
        (regression guard)."""
        reginfo = [{"other_key": "value"}]
        try:
            self._run(reginfo)
        except (TypeError, KeyError) as exc:
            self.fail(
                f"check_node_status raised {type(exc).__name__} for missing regseconds"
            )

    # --- regseconds present and valid -----------------------------------

    def test_regseconds_recent_no_error(self):
        """Valid, recent 'regseconds' value produces no registration error."""
        reginfo = [{"regseconds": _recent_regseconds()}]
        (n_errors, _), _ = self._run(reginfo)
        self.assertEqual(n_errors, 0)

    def test_regseconds_old_produces_error(self):
        """A 'regseconds' value older than 10 minutes triggers an error."""
        reginfo = [{"regseconds": _old_regseconds()}]
        (n_errors, _), _ = self._run(reginfo)
        self.assertGreater(n_errors, 0)

    # --- Extra fields in reginfo element are ignored --------------------

    def test_extra_fields_in_reginfo_element_are_ignored(self):
        """Additional keys in the reginfo dict do not cause errors."""
        reginfo = [{"regseconds": _recent_regseconds(), "node": "12345", "extra": True}]
        (n_errors, _), _ = self._run(reginfo)
        self.assertEqual(n_errors, 0)


class TestCheckNodeStatusReginfoCombined(unittest.TestCase):
    """Combined / edge-case tests that cross the None and empty-list guards."""

    def _run(self, bindport, stats, reginfo):
        with patch.object(_mod, "get_iax_bindport", return_value=bindport), \
             patch.object(_mod, "get_node_stats",   return_value=stats), \
             patch.object(_mod, "get_node_regtime", return_value=reginfo), \
             patch.object(_mod, "print_error"), \
             patch.object(_mod, "print_ok"), \
             patch.object(_mod, "print_info"):
            return check_node_status("12345")

    def test_stats_none_does_not_reach_reginfo_check(self):
        """When stats is None, the function returns before checking reginfo,
        so an empty reginfo list does not matter."""
        n_errors, n_warnings = self._run(
            bindport=4569,
            stats=None,
            reginfo=[],
        )
        # stats=None gives a warning and early return
        self.assertEqual(n_warnings, 1)

    def test_none_reginfo_and_none_bindport_accumulates_errors(self):
        """Both a missing bindport and a None reginfo contribute errors; the
        final count must be >= 2 (bindport failures + reginfo failure)."""
        n_errors, n_warnings = self._run(
            bindport=None,
            stats=_VALID_STATS,
            reginfo=None,
        )
        # bindport=None triggers 2 errors (None check + UDP-port mismatch),
        # and reginfo=None triggers 1 more → total >= 2
        self.assertGreaterEqual(n_errors, 2)

    def test_empty_reginfo_and_none_bindport_accumulates_errors(self):
        """Both a missing bindport and an empty reginfo contribute errors; the
        final count must be >= 2."""
        n_errors, n_warnings = self._run(
            bindport=None,
            stats=_VALID_STATS,
            reginfo=[],
        )
        self.assertGreaterEqual(n_errors, 2)

    def test_missing_regseconds_and_none_bindport_accumulates_errors(self):
        """Both a missing bindport and missing 'regseconds' contribute errors; the
        final count must be >= 2."""
        n_errors, n_warnings = self._run(
            bindport=None,
            stats=_VALID_STATS,
            reginfo=[{}],
        )
        self.assertGreaterEqual(n_errors, 2)


if __name__ == "__main__":
    unittest.main()