#!/usr/bin/env python3
"""Exercise a real Docker MCP server over stdio using only Python stdlib."""
import argparse
import json
import queue
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path


def probe(command, timeout=45):
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, bufsize=1)
    lines, errors = queue.Queue(), []

    def read_stdout():
        for line in process.stdout:
            lines.put(line)
        lines.put(None)

    def read_stderr():
        for line in process.stderr:
            errors.append(line.rstrip())

    threading.Thread(target=read_stdout, daemon=True).start()
    threading.Thread(target=read_stderr, daemon=True).start()
    transcript = []

    def send(message):
        transcript.append({"direction": "request", "message": message})
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    def request(number, method, params):
        send({"jsonrpc": "2.0", "id": number, "method": method, "params": params})
        while True:
            line = lines.get(timeout=timeout)
            if line is None:
                raise RuntimeError("MCP process closed stdout: " + "\n".join(errors))
            message = json.loads(line)
            transcript.append({"direction": "response", "message": message})
            if message.get("id") == number:
                if "error" in message:
                    raise RuntimeError(str(message["error"]))
                return message["result"]

    try:
        initialize = request(1, "initialize", {"protocolVersion": "2024-11-05",
            "capabilities": {}, "clientInfo": {"name": "devops-terminal-probe", "version": "1.0"}})
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        tools = request(2, "tools/list", {})
        assert {"list_files", "read_file", "write_file"} <= {t["name"] for t in tools["tools"]}
        name = "probe-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".txt"
        content = "MCP round-trip succeeded.\n"
        written = request(3, "tools/call", {"name": "write_file", "arguments": {"path": name, "content": content}})
        read = request(4, "tools/call", {"name": "read_file", "arguments": {"path": name}})
        if written.get("isError") or read.get("isError"):
            raise RuntimeError("MCP tool returned an error")
        actual = read.get("structuredContent") or json.loads(read["content"][0]["text"])
        if actual.get("content") != content:
            raise RuntimeError("MCP content read back differs from content written")
        escaped = request(5, "tools/call", {"name": "read_file", "arguments": {"path": "../outside.txt"}})
        if not escaped.get("isError"):
            raise RuntimeError("Path traversal should have been rejected")
        return {"captured_at_utc": datetime.now(timezone.utc).isoformat(), "status": "passed",
            "command": command, "server": initialize, "round_trip": True,
            "path_traversal_rejected": True, "transcript": transcript}
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evidence/mcp-probe.json"))
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        command = ["docker", "compose", "run", "--rm", "--no-deps", "-T", "mcp"]
    record = probe(command)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print("MCP initialize, tools/list, write/read and path traversal checks passed")
    print("Saved " + str(args.output))


if __name__ == "__main__":
    main()
