"""Runtime entrypoint for the SkillsAI FastAPI backend."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Block comment:
# This startup guard normalizes imports for direct script execution from inside the package directory.
if __package__ in {None, ""}:
    # Line comment: resolve the package directory and add its parent as the package import root.
    package_dir = Path(__file__).resolve().parent
    repo_root = package_dir.parent
    # Line comment: remove entries that can shadow Python stdlib modules with local files.
    sys.path = [entry for entry in sys.path if Path(entry or ".").resolve() != package_dir]
    # Line comment: prepend the repository root so skillsai imports resolve consistently.
    sys.path.insert(0, str(repo_root))

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
