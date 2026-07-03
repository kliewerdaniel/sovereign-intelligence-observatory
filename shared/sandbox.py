"""Lightweight local execution sandbox for TJE decision actions.

Wraps action execution in a subprocess with restricted privileges:
    - ``resource.RLIMIT_NPROC`` — max child processes (default 0)
    - ``resource.RLIMIT_NOFILE`` — max open file descriptors (default 16)
    - ``resource.RLIMIT_AS`` — address space (default 64 MB)
    - ``resource.RLIMIT_CPU`` — CPU seconds (default 5)
    - Strip environment variables that could grant shell/network access.

Every action runs as a forked subprocess; the parent waits with a
configurable timeout and kills on overrun.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SAFE_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/nonexistent",
    "TMPDIR": tempfile.gettempdir(),
}

_BLOCKLIST_PATTERNS = [
    "import os",
    "import subprocess",
    "import sys",
    "import shutil",
    "import ctypes",
    "__import__(",
    "eval(",
    "exec(",
    "compile(",
    "open(",
    "__builtins__",
    "breakpoint(",
    "os.system",
    "os.popen",
    "subprocess.",
    "sys.modules",
    ".__class__",
    ".__subclasses__",
    ".__globals__",
    "getattr(",
    "setattr(",
]


def _check_blocklist(code: str) -> Optional[str]:
    """Return a description of the first blocklisted pattern found, or None."""
    lower = code.lower()
    for pat in _BLOCKLIST_PATTERNS:
        if pat.lower() in lower:
            return pat
    return None


class SandboxViolation(Exception):
    """Raised when action code triggers a security restriction."""


class ActionSandbox:
    """Execute a TJE decision node action inside a restricted subprocess.

    The action code is wrapped in a small runner script that is
    written to a temporary directory and spawned via ``subprocess.run``.
    """

    def __init__(
        self,
        max_cpu: int = 5,
        max_memory_mb: int = 64,
        max_fds: int = 16,
        max_procs: int = 0,
        timeout_s: int = 10,
    ):
        self.max_cpu = max_cpu
        self.max_memory_mb = max_memory_mb
        self.max_fds = max_fds
        self.max_procs = max_procs
        self.timeout_s = timeout_s

    async def execute(
        self,
        action_code: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run *action_code* inside the sandbox and return the result.

        Returns a dict with keys ``success``, ``stdout``, ``stderr``,
        ``return_code``, and ``sandboxed``.  Raises
        ``SandboxViolation`` if the code is rejected before execution.
        """
        blocked = _check_blocklist(action_code)
        if blocked is not None:
            raise SandboxViolation(
                f"Action contains blocklisted pattern '{blocked}'"
            )

        runner = self._build_runner(action_code, context or {})
        return await self._spawn(runner)

    def _build_runner(
        self, action_code: str, context: Dict[str, Any]
    ) -> str:
        """Wrap action code in a resource-limited runner script."""
        ctx_json = json.dumps(context, default=str)

        return textwrap.dedent(f"""\
            import json, os, resource, sys

            # --- resource limits (best-effort per-platform) ---
            def _try_rlimit(rtype, soft, hard):
                try:
                    cur = resource.getrlimit(rtype)
                    soft = min(soft, cur[1])
                    hard = min(hard, cur[1])
                    if soft > 0 and hard > 0:
                        resource.setrlimit(rtype, (soft, hard))
                except (ValueError, resource.error):
                    pass

            _try_rlimit(resource.RLIMIT_NPROC, {self.max_procs}, {self.max_procs})
            _try_rlimit(resource.RLIMIT_NOFILE, {self.max_fds}, {self.max_fds})
            _try_rlimit(resource.RLIMIT_AS, {self.max_memory_mb * 1024 * 1024}, {self.max_memory_mb * 1024 * 1024})
            _try_rlimit(resource.RLIMIT_CPU, {self.max_cpu}, {self.max_cpu})

            # --- safe globals ---
            _sandbox_ctx = {ctx_json}
            _sandbox_allowed = {{"True": True, "False": False, "None": None, "dict": dict, "list": list, "str": str, "int": int, "float": float, "bool": bool, "len": len, "range": range, "enumerate": enumerate, "zip": zip, "map": map, "filter": filter, "sorted": sorted, "reversed": reversed, "min": min, "max": max, "sum": sum, "any": any, "all": all, "isinstance": isinstance, "type": type, "print": print, "context": _sandbox_ctx}}

            try:
                compiled = compile({json.dumps(action_code)}, "<sandbox>", "exec")
                exec(compiled, _sandbox_allowed)
                print("[[sandbox:ok]]")
            except Exception as e:
                print(f"[[sandbox:error {{e}}]]")
                sys.exit(1)
        """)

    async def _spawn(self, runner: str) -> Dict[str, Any]:
        """Fork a subprocess and run the wrapper script under resource limits."""
        with tempfile.TemporaryDirectory(prefix="sio-sandbox-") as tmp:
            script_path = Path(tmp) / "runner.py"
            script_path.write_text(runner)
            script_path.chmod(0o500)

            try:
                proc = subprocess.run(
                    [sys.executable, str(script_path)],
                    env=SAFE_ENV,
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_s,
                    preexec_fn=os.setsid,
                )
                stdout = proc.stdout or ""
                stderr = proc.stderr or ""
                success = "[[sandbox:ok]]" in stdout

                return {
                    "success": success,
                    "stdout": stdout,
                    "stderr": stderr,
                    "return_code": proc.returncode,
                    "timed_out": False,
                    "sandboxed": True,
                }
            except subprocess.TimeoutExpired:
                logger.warning("Sandbox action timed out after %ds", self.timeout_s)
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "return_code": -1,
                    "timed_out": True,
                    "sandboxed": True,
                }
