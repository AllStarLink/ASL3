from datetime import timedelta, datetime as dt

import contextlib
import pytest
import importlib.machinery
import importlib.util
import sys
import io
from unittest.mock import patch, MagicMock
import os

_SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "bin", "asl-play-arn"
)

def _load_play_arn():
    loader = importlib.machinery.SourceFileLoader("play_arn", _SCRIPT_PATH)
    spec = importlib.util.spec_from_loader("play_arn", loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Make module importable for patch()
    sys.modules["play_arn"] = module
    print("DEBUG datetime =", module.datetime, type(module.datetime))
    return module


@pytest.fixture
def play_arn_runner():
    play_arn = _load_play_arn()

    p_geteuid = patch("play_arn.os.geteuid", return_value=0)
    p_getpwnam = patch("play_arn.pwd.getpwnam", return_value=MagicMock())
    p_requests = patch("play_arn.requests.get", return_value=MagicMock(content=b"FAKE_MP3_DATA"))
    p_subproc = patch("play_arn.subprocess.run", return_value=MagicMock(returncode=0, stdout=iter([])))
    p_sleep = patch("play_arn.sleep", return_value=None)


    patchers = [p_geteuid, p_getpwnam, p_requests, p_subproc, p_sleep]
    active_mocks = [p.start() for p in patchers]

    def run(argv):
        buf = io.StringIO()
        with patch.object(sys, "argv", argv):
            with contextlib.redirect_stderr(buf):
                try:
                    play_arn.main()
                except SystemExit as e:
                    return buf.getvalue(), str(e)
                return buf.getvalue(), ""
    yield run

    for p in patchers:
        p.stop()

def test_missing_node(play_arn_runner):
    stderr, _ = play_arn_runner(["asl-play-arn"])
    assert "required" in stderr.lower()
    
def test_invalid_node_short(play_arn_runner):
    _, exit_msg = play_arn_runner(["asl-play-arn", "--node", "12"])
    assert "four to six digits" in exit_msg.lower()
    
def test_normal(play_arn_runner):
    stderr, exit_msg = play_arn_runner(
        ["asl-play-arn", "--node", "1234"]
    )
    print(f"{stderr}, {exit_msg}")
    assert exit_msg == ""

def test_normal_wait(play_arn_runner):
    when = (dt.now() + timedelta(minutes=10)).strftime("%H%M")
    stderr, exit_msg = play_arn_runner(
        ["asl-play-arn", "--node", "1234", "--when", when]
    )
    print(f"{stderr}, {exit_msg}")
    assert exit_msg == ""
    
def test_normal_wait_past(play_arn_runner):
    when = (dt.now() - timedelta(minutes=10)).strftime("%H%M")
    stderr, exit_msg = play_arn_runner(
        ["asl-play-arn", "--node", "1234", "--when", when]
    )
    print(f"{stderr}, {exit_msg}")
    assert "in the future" in exit_msg.lower()