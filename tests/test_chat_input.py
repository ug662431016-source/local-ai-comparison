import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import call, patch

import chat_input


class ChatInputTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        source = patch.object(chat_input, "__file__", str(self.root / "chat_input.py"))
        source.start()
        self.addCleanup(source.stop)

    def record(self):
        return {
            "run_id": "test_run",
            "prompt": "ช่วยสรุปบทเรียน 🐳",
            "system": chat_input.SYSTEM,
            "options": chat_input.OPTIONS,
            "results": [{
                "model": chat_input.MODELS[0],
                "answer": "Docker ใช้รันโปรแกรมใน container ✅",
                "elapsed_seconds": 1.25,
                "load_seconds": 0.5,
                "truncated": False,
            }],
        }

    def run_main(self, inputs):
        output = io.StringIO()
        saved = []
        response = self.record()["results"][0]
        tags = {"models": [{"name": model} for model in chat_input.MODELS]}
        with patch("builtins.input", side_effect=inputs) as user_input, \
                patch.object(chat_input, "request_json", return_value=tags) as request, \
                patch.object(chat_input, "ask", return_value=response) as ask, \
                patch.object(chat_input, "save", side_effect=lambda record: (
                    saved.append(copy.deepcopy(record)) or self.root / "result.txt"
                )) as save, redirect_stdout(output):
            chat_input.main()
        request.assert_called_once_with("/api/tags")
        return output.getvalue(), user_input, ask, save, saved

    def test_exit_commands_do_not_call_models_or_save(self):
        for command in ("exit", "quit", "/bye"):
            with self.subTest(command=command):
                _, user_input, ask, save, _ = self.run_main([command])
                self.assertEqual(user_input.call_count, 1)
                ask.assert_not_called()
                save.assert_not_called()

    def test_corrupted_exit_is_rejected_before_next_valid_exit(self):
        output, user_input, ask, save, _ = self.run_main(["exit\udc80", "exit"])
        self.assertEqual(user_input.call_count, 2)
        ask.assert_not_called()
        save.assert_not_called()
        self.assertIn("อักขระ", output)

    def test_invalid_input_is_rejected_and_next_question_still_works(self):
        question = "Docker คืออะไร 🐳"
        output, _, ask, save, records = self.run_main(["เสีย\ud800", question, "exit"])
        self.assertIn("อักขระ", output)
        self.assertEqual(ask.call_args_list, [call(model, question) for model in chat_input.MODELS])
        self.assertEqual(save.call_count, len(chat_input.MODELS))
        self.assertTrue(all(record["prompt"] == question for record in records))
        self.assertEqual(len(records[-1]["results"]), len(chat_input.MODELS))

    def test_save_preserves_thai_emoji_and_json_values(self):
        record = self.record()
        text_path = chat_input.save(record)
        json_path = self.root / "results" / "test_run.json"
        self.assertEqual(json.loads(json_path.read_bytes().decode("utf-8")), record)
        text = text_path.read_bytes().decode("utf-8")
        self.assertIn(record["prompt"], text)
        self.assertIn(record["results"][0]["answer"], text)

    def test_save_escapes_invalid_model_text_without_losing_json_values(self):
        record = self.record()
        record["results"][0]["answer"] = "คำตอบ 🐳\udc80\ud800"
        record["results"].append({"model": chat_input.MODELS[1], "error": "ผิดพลาด\udfff"})
        text_path = chat_input.save(record)
        json_path = self.root / "results" / "test_run.json"
        self.assertEqual(json.loads(json_path.read_bytes().decode("utf-8")), record)
        text = text_path.read_bytes().decode("utf-8")
        self.assertIn("คำตอบ 🐳\\udc80\\ud800", text)
        self.assertIn("ผิดพลาด\\udfff", text)

    def test_failed_atomic_replace_preserves_existing_json_and_cleans_temporary(self):
        record = self.record()
        chat_input.save(record)
        folder = self.root / "results"
        original = {path.name: path.read_bytes() for path in folder.iterdir()}
        record["results"][0]["answer"] = "คำตอบใหม่"
        with patch.object(Path, "replace", side_effect=OSError("disk write failed")), \
                self.assertRaisesRegex(OSError, "disk write failed"):
            chat_input.save(record)
        self.assertEqual({path.name: path.read_bytes() for path in folder.iterdir()}, original)


if __name__ == "__main__":
    unittest.main()
