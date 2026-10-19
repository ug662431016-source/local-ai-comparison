import copy
import json
import tempfile
import unittest
from pathlib import Path

from local_agent import DEMO_NOTES, DEMO_TASK, local_url, run_agent
from workspace_tools import WorkspaceTools


CHECKLIST = "- [ ] Study Docker\n- [ ] Run local AI with Ollama\n- [ ] Save experiment results\n"


def native(name=None, arguments=None, answer=""):
    message = {"role": "assistant", "content": answer}
    if name is not None:
        message["tool_calls"] = [{"function": {"name": name, "arguments": arguments}}]
    return {"done": True, "done_reason": "stop", "message": message}


def action(name, path="", content="", answer=""):
    return native(answer=json.dumps({"action": name, "path": path,
                                    "content": content, "answer": answer}))


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def request(self, path, payload):
        self.requests.append((path, copy.deepcopy(payload)))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name)
        self.tools = WorkspaceTools(self.workspace)
        self.tools.write_file("notes.txt", DEMO_NOTES)

    def run_demo(self, responses, protocol="native", max_steps=8):
        client = FakeClient(responses)
        result = run_agent(client, "llama3.2:3b", DEMO_TASK, self.workspace,
                           protocol=protocol, max_steps=max_steps, demo=True)
        return result, client

    def test_native_loop_executes_real_files_and_returns_observations(self):
        result, client = self.run_demo([
            native("read_file", {"path": "notes.txt"}),
            native("write_file", {"path": "checklist.md", "content": CHECKLIST}),
            native("read_file", {"path": "checklist.md"}),
            native(answer="Created and checked checklist.md"),
        ])
        self.assertEqual(result["status"], "passed")
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(self.tools.read_file("checklist.md")["content"], CHECKLIST)
        second_messages = client.requests[1][1]["messages"]
        self.assertEqual(second_messages[-1]["role"], "tool")
        self.assertIn("Study Docker", second_messages[-1]["content"])
        self.assertIn("tools", client.requests[0][1])
        self.assertNotIn("format", client.requests[0][1])

    def test_explicit_json_loop_uses_schema_and_real_tools(self):
        result, client = self.run_demo([
            action("read_file", "notes.txt"),
            action("write_file", "checklist.md", CHECKLIST),
            action("read_file", "checklist.md"),
            action("finish", answer="Created and checked checklist.md"),
        ], protocol="json")
        self.assertEqual(result["status"], "passed")
        self.assertIn("format", client.requests[0][1])
        self.assertNotIn("tools", client.requests[0][1])
        self.assertIn("Tool observation", client.requests[1][1]["messages"][-1]["content"])

    def test_premature_finish_is_incomplete_even_if_model_claims_success(self):
        result, _ = self.run_demo([native(answer="I created checklist.md successfully")])
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["checks"]["file_written"])
        self.assertFalse((self.workspace / "checklist.md").exists())

    def test_read_before_write_does_not_count_as_readback(self):
        self.tools.write_file("checklist.md", CHECKLIST)
        result, _ = self.run_demo([
            native("read_file", {"path": "notes.txt"}),
            native("read_file", {"path": "checklist.md"}),
            native("write_file", {"path": "checklist.md", "content": CHECKLIST}),
            native(answer="done"),
        ])
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["checks"]["written_file_read_back"])

    def test_independent_verification_rejects_invented_or_missing_tasks(self):
        incorrect = CHECKLIST + "- [ ] Deploy the production system\n"
        result, _ = self.run_demo([
            native("read_file", {"path": "notes.txt"}),
            native("write_file", {"path": "checklist.md", "content": incorrect}),
            native("read_file", {"path": "checklist.md"}),
            native(answer="The checklist is correct"),
        ])
        self.assertEqual(result["status"], "incomplete")
        self.assertTrue(result["checks"]["written_file_read_back"])
        self.assertFalse(result["checks"]["exact_three_tasks_in_order"])

    def test_max_steps_and_tool_errors_are_preserved(self):
        result, client = self.run_demo([
            native("read_file", {"path": "../outside"}),
            native("read_file", {"path": "notes.txt"}),
        ], max_steps=2)
        self.assertEqual(result["stop_reason"], "max_steps")
        self.assertEqual(result["status"], "incomplete")
        errors = [e for e in result["events"] if e["type"] == "tool" and not e["ok"]]
        self.assertEqual(len(errors), 1)
        self.assertIn("traversal", errors[0]["result"]["error"])
        self.assertIn("error", client.requests[1][1]["messages"][-1]["content"])

    def test_request_failure_does_not_fabricate_a_completed_run(self):
        result, _ = self.run_demo([RuntimeError("HTTP 400 model does not support tools")])
        self.assertEqual(result["stop_reason"], "request_error")
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("does not support tools", result["error"])

    def test_truncated_output_is_not_executed(self):
        response = native("write_file", {"path": "checklist.md", "content": CHECKLIST})
        response["done_reason"] = "length"
        result, _ = self.run_demo([response])
        self.assertEqual(result["stop_reason"], "truncated")
        self.assertFalse((self.workspace / "checklist.md").exists())

    def test_malformed_tool_call_is_logged_as_tool_error(self):
        response = native()
        response["message"]["tool_calls"] = [{"function": ["bad"]}]
        result, _ = self.run_demo([response], max_steps=1)
        self.assertEqual(result["status"], "incomplete")
        errors = [e for e in result["events"] if e["type"] == "tool"]
        self.assertFalse(errors[0]["ok"])

    def test_json_bad_action_does_not_silently_switch_protocol(self):
        result, _ = self.run_demo([native(answer='{"action":"shell"}')], protocol="json")
        self.assertEqual(result["stop_reason"], "invalid_response")
        self.assertEqual(result["status"], "incomplete")

    def test_only_local_endpoint_names_are_accepted(self):
        for url in ("http://localhost:11434", "http://127.0.0.1:11435/",
                    "http://[::1]:11434", "http://ollama:11434"):
            self.assertTrue(local_url(url).startswith("http://"))
        for url in ("https://ollama.com", "http://example.com:11434", "http://localhost.evil",
                    "http://localhost/api/chat", "http://user@localhost", "http://localhost?redirect=evil",
                    "file:///tmp/ollama", "http://localhost:99999"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                local_url(url)

    def test_custom_task_must_read_back_every_written_file(self):
        client = FakeClient([
            native("write_file", {"path": "a.txt", "content": "A"}),
            native("read_file", {"path": "a.txt"}),
            native("write_file", {"path": "b.txt", "content": "B"}),
            native(answer="Both files done"),
        ])
        result = run_agent(client, "llama3.2:3b", "Create two files", self.workspace)
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["checks"]["written_file_read_back"])

    def test_empty_json_finish_requests_model_correction_without_fabricating_answer(self):
        result, client = self.run_demo([
            action("read_file", "notes.txt"),
            action("write_file", "checklist.md", CHECKLIST),
            action("read_file", "checklist.md"),
            action("finish", "checklist.md"),
            action("finish", answer="Created and checked checklist.md"),
        ], protocol="json")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["final_answer"], "Created and checked checklist.md")
        self.assertIn("nonempty answer", client.requests[4][1]["messages"][-1]["content"])

    def test_custom_task_readback_must_follow_final_revision(self):
        client = FakeClient([
            native("write_file", {"path": "a.txt", "content": "first"}),
            native("read_file", {"path": "a.txt"}),
            native("write_file", {"path": "a.txt", "content": "revised"}),
            native(answer="Revised file done"),
        ])
        result = run_agent(client, "llama3.2:3b", "Revise a file", self.workspace)
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["checks"]["written_file_read_back"])


if __name__ == "__main__":
    unittest.main()
