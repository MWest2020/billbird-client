"""Drive the billbird-mcp server over stdio against a live Billbird.

Reusable smoke / deploy canary. Reads ``BILLBIRD_API_URL`` and
``BILLBIRD_API_TOKEN`` from env, spawns ``billbird-mcp``, completes
the MCP handshake, lists tools, and invokes
``billbird_plan_vs_actual`` plus ``billbird_hours_summary``.

Exits non-zero on any tool error so the script doubles as a CI canary.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time


def send(proc: subprocess.Popen, payload: dict) -> None:
    proc.stdin.write((json.dumps(payload) + "\n").encode())
    proc.stdin.flush()


def recv(proc: subprocess.Popen, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.05)
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise TimeoutError("no MCP response within timeout")


def call_tool(proc: subprocess.Popen, name: str, args: dict, request_id: int) -> dict:
    send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": args},
        },
    )
    resp = recv(proc, timeout=20.0)
    text = resp["result"]["content"][0]["text"]
    return json.loads(text)


def main() -> int:
    for required in ("BILLBIRD_API_URL", "BILLBIRD_API_TOKEN"):
        if not os.environ.get(required):
            print(f"missing env var: {required}", file=sys.stderr)
            return 2

    cmd = ["uv", "run", "billbird-mcp"]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        env=os.environ.copy(),
    )

    failures: list[str] = []
    try:
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "mcp_smoke", "version": "1.0"},
                },
            },
        )
        init = recv(proc)
        print("== initialize ==")
        print(json.dumps(init, indent=2)[:400])

        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = recv(proc)
        names = [t["name"] for t in tools["result"]["tools"]]
        expected = {
            "billbird_hours_summary",
            "billbird_plan_vs_actual",
            "billbird_recent_activity",
            "billbird_cycle_time",
        }
        missing = expected - set(names)
        if missing:
            failures.append(f"tools/list missing: {sorted(missing)}")
        print(f"\n== tools/list ({len(names)}) ==")
        for n in names:
            print(f"  {n}")

        result = call_tool(proc, "billbird_plan_vs_actual", {}, 3)
        print("\n== billbird_plan_vs_actual ==")
        print(json.dumps(result, indent=2)[:600])
        if result.get("error"):
            failures.append(f"plan_vs_actual returned error: {result['error']}")

        result = call_tool(
            proc,
            "billbird_hours_summary",
            {"period": "last-30d", "group_by": "user"},
            4,
        )
        print("\n== billbird_hours_summary ==")
        print(json.dumps(result, indent=2)[:500])
        if result.get("error"):
            failures.append(f"hours_summary returned error: {result['error']}")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        err = proc.stderr.read().decode(errors="replace")
        if err.strip():
            print("\n== mcp stderr ==", file=sys.stderr)
            print(err[:2000], file=sys.stderr)

    if failures:
        print("\nFAIL", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("\nOK — round-trip complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
