from datetime import timedelta, datetime as dt

import contextlib
import pytest
import importlib.machinery
import importlib.util
import io
from requests import Response
import sys
import os
import runpy
import subprocess
from unittest.mock import patch, MagicMock

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

    p_geteuid = patch("os.geteuid", return_value=0)
    p_getpwnam = patch("pwd.getpwnam", return_value=MagicMock(pw_uid=1000, pw_gid=1000, pw_name="asterisk"))
    p_requests = patch("requests.get", return_value=MagicMock(content=b"FAKE_MP3_DATA"))
    p_subproc = patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=iter([])))
    p_sleep = patch("time.sleep", return_value=None)


    patchers = [p_geteuid, p_getpwnam, p_requests, p_subproc, p_sleep]
    m_geteuid, m_getpwnam, m_requests_get, m_subproc, m_sleep = [p.start() for p in patchers]
   
    def run(argv):
        buf = io.StringIO()
        with patch.object(sys, "argv", argv):
            with contextlib.redirect_stderr(buf):
                try:
                    runpy.run_module("play_arn", run_name="__main__", alter_sys=True)
                    #play_arn.main()
                except SystemExit as e:
                    return buf.getvalue(), str(e)
                return buf.getvalue(), ""
    yield run, {
        "geteuid": m_geteuid,
        "getpwnam": m_getpwnam,
        "requests_get": m_requests_get,
        "subprocess_run": m_subproc,
        "sleep": m_sleep,
    }

    for p in patchers:
        p.stop()

def test_normal(play_arn_runner):
    run, _ = play_arn_runner
    _, exit_msg = run(
        ["asl-play-arn", "--node", "1234"]
    )
    assert exit_msg == ""

def test_normal_wait(play_arn_runner):
    run, _ = play_arn_runner
    when = (dt.now() + timedelta(minutes=10)).strftime("%H%M")
    _, exit_msg = run(
        ["asl-play-arn", "--node", "1234", "--when", when]
    )
    assert exit_msg == ""
    
def test_normal_wait_past(play_arn_runner):
    run, _ = play_arn_runner
    when = (dt.now() - timedelta(minutes=10)).strftime("%H%M")
    _, exit_msg = run(
        ["asl-play-arn", "--node", "1234", "--when", when]
    )
    assert "in the future" in exit_msg.lower()

def test_missing_node(play_arn_runner):
    run, _ = play_arn_runner
    stderr, _ = run(["asl-play-arn"])
    assert "required" in stderr.lower()
    
def test_invalid_node_short(play_arn_runner):
    run, _ = play_arn_runner
    _, exit_msg = run(["asl-play-arn", "--node", "12"])
    assert "four to six digits" in exit_msg.lower()
    
def test_debug(play_arn_runner):
    run, _ = play_arn_runner
    _, exit_msg = run(
        ["asl-play-arn", "--node", "1234", "--debug"]
    )
    assert exit_msg == ""

def  test_wrong_user_id(play_arn_runner):
    run, patch = play_arn_runner
    patch["geteuid"].return_value = 1001 
    _, exit_msg = run(
        ["asl-play-arn", "--node", "1234", "--debug"]
    )
    assert "this script must be run as" in exit_msg.lower()
    
def  test_wrong_user(play_arn_runner):
    run, patch = play_arn_runner
    patch["getpwnam"].side_effect = KeyError("user not found")
    _, exit_msg = run(
        ["asl-play-arn", "--node", "1234", "--debug"]
    )
    assert "required user" in exit_msg.lower()
    
def test_bad_when(play_arn_runner):
    run, _ = play_arn_runner
    _, exit_msg = run(
        ["asl-play-arn", "--node", "1234", "--when", "ABC"]
    )
    assert "error: time format must be nnnn" in exit_msg.lower()

def test_bad_URL(play_arn_runner):
    run, patch = play_arn_runner
   
    # Make the response "falsy"

    resp = Response()
    resp.status_code = 404

    patch["requests_get"].return_value = resp
    
    _, exit_mesg = run(["asl-play-arn", "--node", "1234"])
    assert "failed to retrieve arn file" in exit_mesg.lower()

def test_conversion_wav_split_failed(play_arn_runner):
    run, patch = play_arn_runner
   
    # Make the response "falsy"
    patch["subprocess_run"].side_effect = subprocess.CompletedProcess(
            args=["lame -h -S --decode input.mp3 output.wav"],
            returncode=1,
            stdout=b"",
            stderr=b"",
        ),

    _, exit_mesg = run(["asl-play-arn", "--node", "1234"])
    assert "error: command: lame -h -s --decode " in exit_mesg.lower()
    
def test_conversion_sox_failed(play_arn_runner):
    run, patch = play_arn_runner
   
    # Make the response "falsy"
    patch["subprocess_run"].side_effect = [
        subprocess.CompletedProcess(
            args=["lame -h -S --decode input.mp3 output.wav"],
            returncode=0,
            stdout=b"",
            stderr=b"",
        ),
        subprocess.CompletedProcess(
            args=["sox -v 0.7 input.wav -r 8k -c 1 -t ul output.ulaw"],
            returncode=1,
            stdout=b"",
            stderr=b"",
        ),
    ]
    _, exit_mesg = run(["asl-play-arn", "--node", "1234"])
    print(patch["subprocess_run"].call_args_list)
    assert "error: command: sox -v 0.7 " in exit_mesg.lower()

def test_conversion_ast_play_failed(play_arn_runner):
    run, patch = play_arn_runner
   
    # Make the response "falsy"
    patch["subprocess_run"].side_effect = [
        subprocess.CompletedProcess(
            args=["lame -h -S --decode input.mp3 output.wav"],
            returncode=0,
            stdout=b"",
            stderr=b"",
        ),
        subprocess.CompletedProcess(
            args=["sox -v 0.7 input.wav -r 8k -c 1 -t ul output.ulaw"],
            returncode=0,
            stdout=b"",
            stderr=b"",
        ),
        subprocess.CompletedProcess(
            args=["/usr/sbin/asterisk",
            "-rx",
            "rpt playback 12345 output"],
            returncode=1,
            stdout=b"",
            stderr=b"",
        ),
    ]
    
    _, exit_mesg = run(["asl-play-arn", "--node", "1234"])    
    print(patch["subprocess_run"].call_args_list)
    print(exit_mesg)
    assert "error: command: /usr/sbin/asterisk -rx rpt playback 1234 " in exit_mesg.lower()

def test_keyboard_interrupt(play_arn_runner):
    run, patch = play_arn_runner
    patch["sleep"].side_effect = KeyboardInterrupt()
    _, exit_mesg = run(["asl-play-arn", "--node", "1234"])
    assert "interrupted by user" in exit_mesg.lower()
