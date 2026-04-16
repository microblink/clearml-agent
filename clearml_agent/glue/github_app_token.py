"""
Fetch a GitHub App installation access token using a mounted private key.

Usage (from pod init script):
    export CLEARML_AGENT_GIT_USER=x-access-token
    export CLEARML_AGENT_GIT_PASS=$(python3 /path/to/github_app_token.py)

The private key must be mounted at /clearml-github-app-key/github_app_clearml_key.
"""

import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.request

GITHUB_APP_ID = "3387038"
GITHUB_APP_INSTALLATION_ID = "124164407"
PRIVATE_KEY_PATH = "/clearml-github-app-key/github_app_clearml_key"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_jwt(private_key: str) -> str:
    now = int(time.time())
    header = _b64url(b'{"alg":"RS256","typ":"JWT"}')
    payload = _b64url(json.dumps({"iat": now - 60, "exp": now + 540, "iss": GITHUB_APP_ID}).encode())
    signing_input = f"{header}.{payload}".encode()

    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="w") as kf:
        kf.write(private_key)
        kf_path = kf.name

    try:
        result = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", kf_path],
            input=signing_input,
            capture_output=True,
            check=True,
        )
    finally:
        os.unlink(kf_path)

    sig = _b64url(result.stdout)
    return f"{header}.{payload}.{sig}"


def fetch_token() -> str:
    with open(PRIVATE_KEY_PATH) as f:
        private_key = f.read()

    jwt = _make_jwt(private_key)

    req = urllib.request.Request(
        f"https://api.github.com/app/installations/{GITHUB_APP_INSTALLATION_ID}/access_tokens",
        method="POST",
        headers={
            "Authorization": f"Bearer {jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        data=b"",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["token"]


if __name__ == "__main__":
    print(fetch_token(), end="")
