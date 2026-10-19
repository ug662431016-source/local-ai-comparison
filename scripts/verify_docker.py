#!/usr/bin/env python3
"""Run new disposable agent/MCP containers against an existing Ollama container.

Build first with: docker compose -p devops-review build agent mcp
This does not stop, recreate or alter the existing Ollama container/volume.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", choices=["native", "json"], default="native")
    parser.add_argument("--model", choices=["llama3.2:3b", "qwen2.5-coder:1.5b"], action="append")
    parser.add_argument("--skip-mcp", action="store_true", help="Skip a previously verified MCP probe")
    parser.add_argument("--host", action="store_true", help="Also run the agent client directly on the host")
    args = parser.parse_args()
    (ROOT / "evidence").mkdir(exist_ok=True)
    for name in ("agent_workspace", "agent_results", "mcp_workspace"):
        (ROOT / name).mkdir(exist_ok=True)
    record = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "runs": []}
    commands = [["docker", "compose", "-p", "devops-review", "-f", "compose.yaml", "config", "--quiet"]]
    for model in (args.model or ("llama3.2:3b", "qwen2.5-coder:1.5b")):
        commands.append(["docker", "run", "--rm", "--network", "container:ollama",
            "-v", str(ROOT / "agent_workspace") + ":/app/agent_workspace",
            "-v", str(ROOT / "agent_results") + ":/app/agent_results",
            "--entrypoint", "python", "devops-review-agent", "local_agent.py",
            "--demo", "--model", model, "--runtime", "docker", "--protocol", args.protocol])
    if args.host:
        commands.append([sys.executable, "local_agent.py", "--demo", "--runtime", "docker",
            "--model", "qwen2.5-coder:1.5b", "--protocol", args.protocol,
            "--base-url", "http://127.0.0.1:11434"])
    if not args.skip_mcp:
        commands.append([sys.executable, "scripts/probe_mcp.py", "--output", "evidence/mcp-probe.json",
            "--", "docker", "compose", "-p", "devops-review", "-f", "compose.yaml",
            "run", "--rm", "--no-deps", "-T", "mcp"])
    failed = False
    for command in commands:
        print("Running: " + " ".join(command), flush=True)
        result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=1200)
        print(result.stdout, flush=True)
        record["runs"].append({"command": command, "returncode": result.returncode, "output": result.stdout})
        failed = failed or result.returncode != 0
        (ROOT / "evidence" / ("docker-verification-" + args.protocol + ".json")).write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
