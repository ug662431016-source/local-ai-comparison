import tempfile
import unittest
from pathlib import Path

from workspace_tools import MAX_TEXT_BYTES, WorkspaceTools


class WorkspaceToolsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "workspace"
        self.tools = WorkspaceTools(self.root)

    def test_roundtrip_nested_file_and_listing(self):
        result = self.tools.write_file("drafts/งาน.md", "- [ ] อ่าน Docker\n")
        self.assertGreater(result["bytes"], 0)
        self.assertEqual(self.tools.read_file("drafts/งาน.md")["content"], "- [ ] อ่าน Docker\n")
        self.assertEqual(self.tools.list_files()["directories"], ["drafts"])
        self.assertEqual(self.tools.list_files("drafts")["files"], ["drafts/งาน.md"])

    def test_reject_traversal_absolute_and_backslash_paths(self):
        for path in ("../escape", "dir/../../escape", "/tmp/escape", "dir\\escape", ""):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.tools.write_file(path, "bad")
        self.assertFalse((self.root.parent / "escape").exists())

    def test_refuse_symlink_file_and_parent(self):
        outside = self.root.parent / "outside.txt"
        outside.write_text("original", encoding="utf-8")
        (self.root / "link.txt").symlink_to(outside)
        (self.root / "outside-dir").symlink_to(self.root.parent, target_is_directory=True)
        for path in ("link.txt", "outside-dir/outside.txt"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    self.tools.read_file(path)
                with self.assertRaises(ValueError):
                    self.tools.write_file(path, "changed")
        self.assertEqual(outside.read_text(encoding="utf-8"), "original")
        self.assertEqual(self.tools.list_files()["omitted_symlinks"], 2)

    def test_refuse_dangling_symlink_and_symlink_root(self):
        (self.root / "dangling").symlink_to(self.root.parent / "missing")
        with self.assertRaises(ValueError):
            self.tools.write_file("dangling", "bad")
        root_link = self.root.parent / "root-link"
        root_link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            WorkspaceTools(root_link)

    def test_limit_counts_utf8_bytes_and_read_size(self):
        with self.assertRaises(ValueError):
            self.tools.write_file("too-large.txt", "ก" * MAX_TEXT_BYTES)
        self.assertFalse((self.root / "too-large.txt").exists())
        (self.root / "large.txt").write_bytes(b"x" * (MAX_TEXT_BYTES + 1))
        with self.assertRaises(ValueError):
            self.tools.read_file("large.txt")

    def test_refuse_non_text_and_directory_overwrite(self):
        (self.root / "binary").write_bytes(b"\xff")
        with self.assertRaises(UnicodeDecodeError):
            self.tools.read_file("binary")
        (self.root / "folder").mkdir()
        with self.assertRaises(ValueError):
            self.tools.write_file("folder", "bad")

    def test_unknown_tool_or_bad_arguments_cannot_execute(self):
        for name, arguments in (("shell", {"command": "touch bad"}),
                                ("write_file", {"path": "bad"}),
                                ("read_file", {"path": "bad", "extra": True}),
                                ("read_file", [])):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.tools.execute(name, arguments)
        self.assertEqual(self.tools.list_files()["files"], [])


if __name__ == "__main__":
    unittest.main()
