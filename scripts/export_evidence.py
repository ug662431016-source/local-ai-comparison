#!/usr/bin/env python3
"""Index all real agent runs and export a successful run's original text artifacts."""
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows, passed = [], []
    for path in sorted((ROOT / "agent_results").glob("*.json")):
        record = json.loads(path.read_text())
        tools = [e for e in record["events"] if e["type"] == "tool"]
        rows.append(f'| [{record["run_id"]}](../agent_results/{path.name}) | '
            f'{record["model"]} | {record["protocol"]} | {record["status"]} | '
            f'{len(tools)} | {record.get("elapsed_seconds", "-")} |')
        if record["status"] == "passed":
            passed.append((path, record))
    text = ["# ผลทดสอบ Agent จริง", "",
        "ผลทุกครั้งถูกรักษาไว้ รวมรอบที่ไม่ผ่าน ตารางนี้แยกจากผลเปรียบเทียบถาม–ตอบใน results/", "",
        "| รอบ | โมเดล | Protocol | ผลตรวจ | Tool calls | วินาที |",
        "|---|---|---|---|---:|---:|", *rows, "",
        "`passed` หมายถึงผ่านตัวตรวจงานสาธิตในรอบนั้น ไม่ได้ยืนยันว่าจะสำเร็จทุกครั้ง", "",
        "`native` ในคอลัมน์ Protocol หมายถึง Ollama tool_calls; ไม่ได้หมายถึงติดตั้ง Ollama นอก Docker", ""]
    if passed:
        path, record = passed[-1]
        if not re.fullmatch(r"\d{8}_\d{6}_\d{6}", record["run_id"]):
            raise ValueError("Unexpected run ID")
        source = ROOT / "agent_workspace" / record["run_id"]
        dest = ROOT / "evidence" / "demo-success"
        dest.mkdir(parents=True, exist_ok=True)
        files = []
        for name in ("notes.txt", "checklist.md"):
            shutil.copy2(source / name, dest / name)
            files.append({"name": name, "sha256": sha(dest / name),
                          "run_file": f'agent_workspace/{record["run_id"]}/{name}',
                          "export_file": f"evidence/demo-success/{name}"})
        provenance = {"run_id": record["run_id"], "evidence_log": str(path.relative_to(ROOT)),
            "evidence_log_sha256": sha(path), "original_workspace": record["workspace"],
            "files": files, "source_sha256_at_run": record.get("source_sha256", {}),
            "note": "Exported from actual workspace files after a passed run; not regenerated from model prose."}
        (dest / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n")
        text += ["ไฟล์จริงจากรอบที่ผ่านล่าสุด: [โน้ตต้นฉบับ](demo-success/notes.txt), "
                 "[checklist ที่ Agent สร้าง](demo-success/checklist.md), "
                 "[ที่มาและ SHA-256](demo-success/provenance.json)", ""]
    (ROOT / "evidence" / "AGENT-RUNS.md").write_text("\n".join(text))
    print(f"Indexed {len(rows)} real runs; {len(passed)} passed")


if __name__ == "__main__":
    main()
