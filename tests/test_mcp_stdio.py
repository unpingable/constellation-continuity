"""Focused subprocess checks for the supported MCP stdio initialization path."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("protocol_version", ["2025-03-26", "2024-11-05"])
def test_stdio_initialize_and_list_tools(
    tmp_path: Path,
    protocol_version: str,
) -> None:
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "continuity-test", "version": "1"},
            },
        },
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    input_text = "".join(json.dumps(request) + "\n" for request in requests)
    env = os.environ.copy()
    env["HOME"] = str(tmp_path / "home")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "continuity.mcp",
            "--db",
            str(tmp_path / "continuity.db"),
        ],
        input=input_text,
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    responses = [json.loads(line) for line in completed.stdout.splitlines()]
    assert len(responses) == 2
    assert responses[0]["id"] == 1
    assert responses[0]["result"]["protocolVersion"] == protocol_version
    assert responses[1]["id"] == 2
    tool_names = {tool["name"] for tool in responses[1]["result"]["tools"]}
    assert "memory_observe" in tool_names
