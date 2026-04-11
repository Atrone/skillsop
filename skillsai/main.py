"""Runtime entrypoint for the SkillsAI FastAPI backend."""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

# Block comment:
# This startup guard normalizes imports for packaged and flattened runtime entrypoints.
if __package__ in {None, ""}:
    # Line comment: resolve the package directory and add its parent as the package import root.
    package_dir = Path(__file__).resolve().parent
    repo_root = package_dir.parent
    # Line comment: detect whether the file is running from the real skillsai package directory.
    is_package_layout = (package_dir / "__init__.py").exists()
    if is_package_layout:
        # Line comment: remove entries that can shadow Python stdlib modules with local files.
        sys.path = [entry for entry in sys.path if Path(entry or ".").resolve() != package_dir]
        # Line comment: prepend the repository root so skillsai imports resolve consistently.
        sys.path.insert(0, str(repo_root))
    else:
        # Line comment: register a synthetic skillsai package when deployment flattens package files into one directory.
        synthetic_package = types.ModuleType("skillsai")
        synthetic_package.__path__ = [str(package_dir)]
        sys.modules.setdefault("skillsai", synthetic_package)

import uvicorn

from skillsai.app import app


# Block comment:
# This helper reads host and port values for local backend startup.
def read_server_config() -> tuple[str, int]:
    """Read server host and port configuration from environment."""
    # Line comment: default to localhost binding used by local frontend development.
    host = os.getenv("SKILLSAI_HOST", "0.0.0.0")
    # Line comment: parse integer port with a stable fallback.
    port = int(os.getenv("SKILLSAI_PORT", "8000"))
    return host, port


# Block comment:
# This function starts the FastAPI application via the uvicorn ASGI server.
def run() -> None:
    """Run the SkillsAI FastAPI app with uvicorn."""
    # Line comment: read host/port before launching uvicorn process.
    host, port = read_server_config()
    # Line comment: launch the already-imported application object without relying on module path resolution.
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    # Line comment: execute startup when the module is launched as a script.
    run()
