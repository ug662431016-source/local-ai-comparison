#!/usr/bin/env python3
"""Capture local Ollama metadata and a real inference without downloading models."""
import argparse
import json
import platform
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


def capture(base_url, runtime):
    parsed = urlsplit(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1", "ollama"}:
        raise ValueError("Only a local Ollama endpoint is allowed")
    http = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(base_url.rstrip("/") + path, data=data,
                                     headers={"Content-Type": "application/json"})
        with http.open(req, timeout=180) as response:
            return json.load(response)

    record = {"captured_at_utc": datetime.now(timezone.utc).isoformat(),
              "runtime_declared": runtime, "endpoint": base_url,
              "platform": platform.platform(), "python": sys.version,
              "ollama_version": request("/api/version"), "tags": request("/api/tags"),
              "models": []}
    for name in ("qwen2.5-coder:1.5b", "llama3.2:3b"):
        print("Inspecting and testing " + name, flush=True)
        info = request("/api/show", {"model": name})
        # The model template is long; details and model_info preserve runtime metadata.
        info.pop("template", None)
        info.pop("license", None)
        answer = request("/api/generate", {"model": name,
            "prompt": "What is 10 + 10? Reply with only the number.", "stream": False,
            "keep_alive": 0, "options": {"temperature": 0, "seed": 42, "num_predict": 32}})
        record["models"].append({"model": name, "show": info, "inference": answer,
                                 "arithmetic_passed": answer.get("response", "").strip() == "20"})
    if runtime == "docker":
        record["docker_commands"] = {}
        for key, args in {"version": ["docker", "version", "--format", "{{json .}}"],
                          "compose": ["docker", "compose", "version"],
                          "container": ["docker", "inspect", "ollama", "--format",
                              "{{json .Config.Image}} {{json .Image}} {{json .State.Status}}"]}.items():
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
            record["docker_commands"][key] = {"returncode": result.returncode,
                "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--runtime", choices=["docker", "native"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = capture(args.base_url, args.runtime)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print("Saved " + str(args.output))
    return 0 if all(m["arithmetic_passed"] for m in record["models"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
