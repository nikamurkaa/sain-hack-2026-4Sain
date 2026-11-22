"""Issue one temporary browser token from an operator terminal."""
import argparse
import getpass
import os
from urllib.parse import urlparse

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", choices=["final", "dev"])
    parser.add_argument("--origin", default="http://127.0.0.1:8765")
    parser.add_argument("--stay")
    parser.add_argument("--dataset", default="case2-dev-v1")
    args = parser.parse_args()
    origin = urlparse(args.origin)
    local = origin.hostname in ("127.0.0.1", "localhost", "::1")
    if (origin.scheme != "https" and not (local and origin.scheme == "http")) or origin.username or origin.query or origin.fragment or origin.path not in ("", "/"):
        parser.error("Specify an HTTPS origin or a loopback origin")
    if not local and origin.hostname != "team25.hack.be-healthy.tech":
        parser.error("Unknown team backend")
    body = {"source": args.source}
    if args.source == "dev":
        if not args.stay:
            parser.error("--stay is required for dev")
        body.update(stay_id=args.stay, dataset_code=args.dataset)
    rehearsal = local and origin.port == 8765
    token = "offline-team" if rehearsal else os.getenv("HACK_TEAM_TOKEN") or getpass.getpass("Командный токен: ")
    with httpx.Client(timeout=120, trust_env=False) as client:
        response = client.post(args.origin.rstrip("/") + "/api/v1/sessions", json=body,
                               headers={"Authorization": "Bearer " + token})
    if response.is_error:
        raise SystemExit(f"Session creation failed: HTTP {response.status_code}")
    print(response.json()["session_token"])


if __name__ == "__main__":
    main()
