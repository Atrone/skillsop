"""Runtime entrypoint for the SkillsAI FastAPI backend."""

from __future__ import annotations

import os

import uvicorn


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
    # Line comment: launch the application module-level app object.
    uvicorn.run("skillsai.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    # Line comment: execute startup when the module is launched as a script.
    run()
