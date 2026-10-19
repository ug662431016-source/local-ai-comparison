"""Small text-file tools shared by the Ollama agent and the MCP server."""

import os
import stat
import tempfile
from pathlib import Path


MAX_TEXT_BYTES = 32768
MAX_DIRECTORY_ENTRIES = 256

TOOL_DEFINITIONS = [
    {"type": "function", "function": {
        "name": "list_files",
        "description": "List immediate files and directories in the workspace. Paths are relative.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                       "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a UTF-8 text file inside the workspace, maximum 32768 bytes.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}},
                       "required": ["path"], "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Create or replace a UTF-8 text file inside the workspace. Parent directories are allowed.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"], "additionalProperties": False},
    }},
]


class WorkspaceTools:
    """Restrict tools to one directory; no shell execution or symlink following.

    This is an application-level boundary for a single local user, not an OS
    sandbox against other processes concurrently replacing directories.
    """

    def __init__(self, root):
        root = Path(root).absolute()
        if root.is_symlink():
            raise ValueError("Workspace root must not be a symlink")
        root.mkdir(parents=True, exist_ok=True)
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Workspace root must be a directory")

    def _path(self, path, allow_root=False):
        if not isinstance(path, str) or not path or "\x00" in path or "\\" in path:
            raise ValueError("Path must be a nonempty relative path using / separators")
        relative = Path(path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Absolute paths and parent traversal are not allowed")
        target = self.root
        for part in relative.parts:
            target = target / part
            if target.is_symlink():
                raise ValueError("Symlinks are not allowed")
        target.resolve(strict=False).relative_to(self.root)
        if target == self.root and not allow_root:
            raise ValueError("A file path is required")
        return target

    def list_files(self, path="."):
        target = self._path(path, allow_root=True)
        if not target.is_dir():
            raise ValueError("Directory does not exist")
        files, directories, omitted = [], [], 0
        for index, entry in enumerate(target.iterdir()):
            if index >= MAX_DIRECTORY_ENTRIES:
                raise ValueError("Directory contains too many entries")
            relative = entry.relative_to(self.root).as_posix()
            if entry.is_symlink():
                omitted += 1
            elif entry.is_dir():
                directories.append(relative)
            elif entry.is_file():
                files.append(relative)
        return {"path": target.relative_to(self.root).as_posix(),
                "files": sorted(files), "directories": sorted(directories),
                "omitted_symlinks": omitted}

    def read_file(self, path):
        target = self._path(path)
        if not stat.S_ISREG(target.stat().st_mode):
            raise ValueError("Only regular text files can be read")
        with target.open("rb") as stream:
            data = stream.read(MAX_TEXT_BYTES + 1)
        if len(data) > MAX_TEXT_BYTES:
            raise ValueError("File exceeds the text size limit")
        return {"path": target.relative_to(self.root).as_posix(),
                "content": data.decode("utf-8")}

    def write_file(self, path, content):
        if not isinstance(content, str):
            raise ValueError("content must be text")
        data = content.encode("utf-8")
        if len(data) > MAX_TEXT_BYTES:
            raise ValueError("Content exceeds the text size limit")
        target = self._path(path)
        if target.exists() and not stat.S_ISREG(target.stat().st_mode):
            raise ValueError("Only regular text files can be replaced")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Validate parents again after creating any new directories.
        self._path(path)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".agent-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
            os.replace(temporary, target)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        return {"path": target.relative_to(self.root).as_posix(), "bytes": len(data)}

    def execute(self, name, arguments):
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object")
        functions = {"list_files": self.list_files, "read_file": self.read_file,
                     "write_file": self.write_file}
        if name not in functions:
            raise ValueError("Unknown tool: %s" % name)
        try:
            return functions[name](**arguments)
        except TypeError as exc:
            raise ValueError("Invalid arguments for %s: %s" % (name, exc)) from exc
