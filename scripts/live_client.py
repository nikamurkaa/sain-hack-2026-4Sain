"""Local-only LIVE AI + synthetic room simulator. No official dev/final simulator mutations.

Requires only an authorized Bifrost AI key in the operator process env.
Browser receives an ephemeral LOCAL GUEST token, not the provider key.
"""
import os
import uvicorn
from scripts.rehearse_client import build_rehearsal

if __name__ == "__main__":
    for key in ("LLM_API_KEY", "LLM_MODEL"):
        if not os.getenv(key):
            raise SystemExit(f"Missing {key}. Set it in this terminal; never paste it in the UI.")
    os.environ.setdefault("LLM_BASE_URL", "https://bifrost.be-healthy.tech/v1")
    uvicorn.run(build_rehearsal(live=True), host="127.0.0.1", port=8765, access_log=False)
