"""
Tests for --json, --node and the exit status of bin/asl-node-auth-check.

Coverage:
- --help lists --json and --node
- JSON output: one document on stdout, schema, sections, counts, result
- Aborted runs (no nodes, duplicate registrations, unknown --node,
  permission denied, unexpected exceptions) still produce a full document
- Exit status 0/1/2/3
- Registration failure marks the node section incomplete
- --node limits the node sections
"""

import importlib.machinery
import importlib.util
import io
import json
import os
import sys
import time
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

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


_mod = _load_script()

HTTP_REG = ("12345", "pw", "register.allstarlink.org", "HTTP")
IAX_REG = ("67890", "pw", "register.allstarlink.org", "IAX")


def run(argv, user="asterisk"):
    """ run entrypoint with argv; return (stdout, exit status) """
    buf = io.StringIO()
    with patch("os.geteuid", return_value=1000), \
         patch("pwd.getpwuid", return_value=MagicMock(pw_name=user)), \
         patch("sys.stdout", buf):
        try:
            _mod.entrypoint(argv)
        except SystemExit as e:
            return buf.getvalue(), e.code
    return buf.getvalue(), None


def healthy_node(stack, registrations=(HTTP_REG,)):
    """ patch every outside dependency for a run with no problems """
    nodes = [r[0] for r in registrations]
    for name, value in [
        ("get_rpt_nodes", nodes),
        ("get_registrations", list(registrations)),
        ("get_remote_ip_http", "203.0.113.5"),
        ("udp_ping", "203.0.113.5"),
        ("is_register_allstarlink_up", True),
        ("find_http_registration", ("198.51.100.1:443", "203.0.113.5:4569", "Registered")),
        ("find_iax_registration", ("198.51.100.1:4569", "203.0.113.5:4569", "Registered")),
        ("reverse_dns", "register.allstarlink.org"),
        ("get_iax_bindport", 4569),
        ("get_node_stats", {"node": {"server": {"udpport": 4569},
                                     "iptime": "2026-03-18 18:16:29"}}),
        ("get_node_regtime", [{"regseconds": int(time.time())}]),
        ("get_node_ping", {"ipv4": {"status": "ok", "rc": 0, "pingms": 42}}),
    ]:
        stack.enter_context(patch.object(_mod, name, return_value=value))


def findings(doc, section_id=None):
    return [f for s in doc["sections"]
            if section_id is None or s["id"] == section_id
            for f in s["findings"]]


class TestHelp:
    def test_help_lists_options(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf), pytest.raises(SystemExit) as e:
            _mod.parse_args(["--help"])
        assert e.value.code == 0
        assert "--json" in buf.getvalue()
        assert "--node" in buf.getvalue()


class TestJsonHealthy:
    def test_document(self):
        with ExitStack() as stack:
            healthy_node(stack)
            out, status = run(["--json"])

        doc = json.loads(out)  # stdout holds nothing but the document
        assert status == 0
        assert doc["schema"] == 1
        assert doc["result"] == "ok"
        assert doc["started"].endswith("Z") and doc["finished"].endswith("Z")
        assert [(s["id"], s["node"]) for s in doc["sections"]] == [
            ("config", None), ("public_ip", None), ("node", "12345")]
        assert all(s["complete"] for s in doc["sections"])
        assert doc["counts"]["error"] == 0
        assert doc["counts"]["warning"] == 0
        assert sum(doc["counts"].values()) == len(findings(doc))

    def test_finding_ids_and_data(self):
        with ExitStack() as stack:
            healthy_node(stack)
            out, _ = run(["--json"])
        doc = json.loads(out)
        by_id = {f["id"]: f for f in findings(doc)}

        assert by_id["config.nodes"]["data"] == {"nodes": ["12345"]}
        assert by_id["public_ip.http_consensus"]["data"] == {"ips": ["203.0.113.5"]}
        assert by_id["node.registration_type"]["data"] == {"type": "HTTP"}
        assert by_id["node.registration_state"]["data"] == {"type": "HTTP", "state": "Registered"}
        assert by_id["node.perceived_address"]["data"] == {"address": "203.0.113.5:4569"}
        assert by_id["node.registrar"]["data"] == {"name": "register.allstarlink.org",
                                                   "ip": "198.51.100.1"}
        assert by_id["node.udp_port"]["data"] == {"registered_port": 4569, "bindport": 4569}
        assert by_id["node.registered_recently"]["level"] == "ok"
        assert by_id["node.ip_last_changed"]["data"] == {"changed_at": "2026-03-18T18:16:29Z"}
        assert by_id["node.inbound_reachability"]["data"] == {"status": "ok", "rtt_ms": 42}
        for f in findings(doc):
            assert f["level"] in ("ok", "info", "warning", "error")
            assert isinstance(f["message"], str) and f["message"]
            assert isinstance(f["data"], dict)

    def test_http_perceived_label(self):
        """The perceived address line names the registration type."""
        with ExitStack() as stack:
            healthy_node(stack)
            out, _ = run(["--json"])
        msg = {f["id"]: f for f in findings(json.loads(out))}["node.perceived_address"]["message"]
        assert msg.startswith("Perceived HTTP IP:PORT")

    def test_text_mode_has_no_json(self):
        with ExitStack() as stack:
            healthy_node(stack)
            out, status = run([])
        assert status == 0
        assert "AllStarLink Node Authentication Check" in out
        assert "No problems detected with node 12345" in out
        assert '"schema"' not in out


class TestJsonProblems:
    def test_errors_exit_1(self):
        with ExitStack() as stack:
            healthy_node(stack)
            stack.enter_context(patch.object(_mod, "get_node_ping",
                return_value={"ipv4": {"status": "unreachable", "rc": 0}}))
            out, status = run(["--json"])
        doc = json.loads(out)
        assert status == 1
        assert doc["result"] == "error"
        assert doc["counts"]["error"] == 1

    def test_warnings_alone_exit_0(self):
        with ExitStack() as stack:
            healthy_node(stack)
            stack.enter_context(patch.object(_mod, "get_node_ping", return_value=None))
            out, status = run(["--json"])
        doc = json.loads(out)
        assert status == 0
        assert doc["result"] == "warning"
        reach = [f for f in findings(doc) if f["id"] == "node.inbound_reachability"]
        assert reach[0]["data"]["status"] == "nodeping_unavailable"

    def test_registration_failure_stops_section(self):
        with ExitStack() as stack:
            healthy_node(stack)
            stack.enter_context(patch.object(_mod, "find_http_registration",
                return_value=(None, None, None)))
            out, status = run(["--json"])
        doc = json.loads(out)
        node = doc["sections"][-1]
        assert status == 1
        assert node["complete"] is False
        ids = [f["id"] for f in node["findings"]]
        assert ids[-1] == "node.checks_stopped"
        state = [f for f in node["findings"] if f["id"] == "node.registration_state"][0]
        assert state["level"] == "error"
        assert state["data"] == {"type": "HTTP", "state": None}


class TestAborted:
    @pytest.mark.parametrize("nodes", [[], None])
    def test_no_nodes(self, nodes):
        with patch.object(_mod, "get_rpt_nodes", return_value=nodes):
            out, status = run(["--json"])
        doc = json.loads(out)
        assert status == 2
        assert doc["result"] == "aborted"
        assert [s["id"] for s in doc["sections"]] == ["config"]
        assert doc["sections"][0]["complete"] is False
        assert findings(doc)[-1]["id"] == "config.no_nodes"

    def test_no_nodes_text_mode(self):
        with patch.object(_mod, "get_rpt_nodes", return_value=[]):
            out, status = run([])
        assert status == 2
        assert "NO NODE ARE CONFIGURED IN rpt.conf" in out

    def test_no_registrations(self):
        with patch.object(_mod, "get_rpt_nodes", return_value=["12345"]), \
             patch.object(_mod, "get_registrations", return_value=None):
            out, status = run(["--json"])
        doc = json.loads(out)
        assert status == 2
        assert findings(doc)[-1]["id"] == "config.no_registrations"

    def test_duplicate_registrations(self):
        dup = [HTTP_REG, ("12345", "pw", "register.allstarlink.org", "IAX")]
        with patch.object(_mod, "get_rpt_nodes", return_value=["12345"]), \
             patch.object(_mod, "get_registrations", return_value=dup):
            out, status = run(["--json"])
        doc = json.loads(out)
        assert status == 2
        assert doc["result"] == "aborted"
        assert [s["id"] for s in doc["sections"]] == ["config"]
        last = findings(doc)[-1]
        assert last["id"] == "config.duplicate_registrations"
        assert last["data"] == {"nodes": ["12345"]}

    def test_missing_registration_and_configuration(self):
        with patch.object(_mod, "get_rpt_nodes", return_value=["12345", "11111"]), \
             patch.object(_mod, "get_registrations", return_value=[HTTP_REG, IAX_REG]):
            out, status = run(["--json"])
        doc = json.loads(out)
        by_id = {f["id"]: f for f in findings(doc)}
        assert status == 2
        assert by_id["config.missing_registration"]["data"] == {"nodes": ["11111"]}
        assert by_id["config.missing_configuration"]["data"] == {"nodes": ["67890"]}

    def test_permission_denied(self):
        out, status = run(["--json"], user="nobody")
        doc = json.loads(out)
        assert status == 3
        assert doc["result"] == "aborted"
        f = findings(doc)
        assert len(f) == 1
        assert f[0]["id"] == "run.permission_denied"
        assert f[0]["data"] == {"user": "nobody"}

    def test_permission_denied_text_mode(self):
        out, status = run([], user="nobody")
        assert status == 3
        assert "Access denied" in out

    def test_unexpected_exception_still_emits_json(self):
        with patch.object(_mod, "get_rpt_nodes", side_effect=RuntimeError("boom")):
            out, status = run(["--json"])
        doc = json.loads(out)
        assert status == 2
        assert doc["result"] == "aborted"
        assert findings(doc)[-1]["id"] == "run.internal_error"


class TestOnlyNode:
    def test_only_named_node_is_checked(self):
        with ExitStack() as stack:
            healthy_node(stack, registrations=(HTTP_REG, IAX_REG))
            out, status = run(["--json", "--node", "67890"])
        doc = json.loads(out)
        assert status == 0
        assert [(s["id"], s["node"]) for s in doc["sections"]] == [
            ("config", None), ("public_ip", None), ("node", "67890")]
        # the configuration checks still cover every node
        assert {f["id"]: f for f in findings(doc, "config")}["config.nodes"]["data"] == \
            {"nodes": ["12345", "67890"]}

    def test_unknown_node_aborts(self):
        with ExitStack() as stack:
            healthy_node(stack)
            out, status = run(["--json", "--node", "99999"])
        doc = json.loads(out)
        assert status == 2
        last = findings(doc)[-1]
        assert last["id"] == "config.node_not_found"
        assert last["data"] == {"node": "99999"}


if __name__ == "__main__":
    unittest.main()
