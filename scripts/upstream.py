#!/usr/bin/env python3
"""Track Print Handy releases: pin the app to the newest published image.

Reads the newest Print Handy release (GitHub's "latest", so never a draft or
pre-release), checks that its image is published on GHCR for every app
architecture, and rewrites the three places that name the version:

- print_handy/Dockerfile: PRINT_HANDY_VERSION and PRINT_HANDY_DIGEST (the
  multi-arch index digest, so a rebuild of one app version is the same image)
- print_handy/config.yaml: version (the tag the Supervisor pulls)
- print_handy/CHANGELOG.md: a new entry linking the release notes

Standard library only. Usage:

    python3 scripts/upstream.py            # update the files if a newer release exists
    python3 scripts/upstream.py --check    # report only, change nothing
    python3 scripts/upstream.py --version 2.3.2   # pin a specific release

Writes ``changed``, ``version`` and ``previous`` to $GITHUB_OUTPUT when set.
Exit codes: 0 done (changed or not), 1 an error worth a red run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

UPSTREAM_REPO = "catduckgnaf/print-handy"
UPSTREAM_IMAGE = "catduckgnaf/print-handy"
# Print Handy publishes amd64 and arm64; Home Assistant calls arm64 aarch64.
REQUIRED_PLATFORMS = {"amd64", "arm64"}

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "print_handy"
DOCKERFILE = APP / "Dockerfile"
CONFIG = APP / "config.yaml"
CHANGELOG = APP / "CHANGELOG.md"

INDEX_TYPES = ", ".join(
    (
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
    )
)


class UpstreamError(Exception):
    """Something about the upstream release or image is not usable."""


def _get(url: str, headers: dict[str, str] | None = None) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read(), {k.lower(): v for k, v in response.headers.items()}
    except urllib.error.HTTPError as err:
        raise UpstreamError(f"{url} answered HTTP {err.code}") from err
    except urllib.error.URLError as err:
        raise UpstreamError(f"{url} unreachable: {err.reason}") from err


def version_tuple(version: str) -> tuple[int, ...]:
    """'2.3.2' -> (2, 3, 2); a leading 'v' is ignored."""
    match = re.fullmatch(r"v?(\d+(?:\.\d+)*)", version.strip())
    if not match:
        raise UpstreamError(f"not a release version: {version!r}")
    return tuple(int(part) for part in match.group(1).split("."))


def latest_release() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body, _ = _get(f"https://api.github.com/repos/{UPSTREAM_REPO}/releases/latest", headers)
    return json.loads(body)


def release_for(version: str) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body, _ = _get(
        f"https://api.github.com/repos/{UPSTREAM_REPO}/releases/tags/{version}", headers
    )
    return json.loads(body)


def image_digest(tag: str) -> str:
    """The multi-arch index digest of ghcr.io/<image>:<tag>, checked for every platform."""
    token_body, _ = _get(
        f"https://ghcr.io/token?scope=repository:{UPSTREAM_IMAGE}:pull&service=ghcr.io"
    )
    token = json.loads(token_body)["token"]
    body, headers = _get(
        f"https://ghcr.io/v2/{UPSTREAM_IMAGE}/manifests/{tag}",
        {"Authorization": f"Bearer {token}", "Accept": INDEX_TYPES},
    )
    digest = headers.get("docker-content-digest", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise UpstreamError(f"ghcr.io/{UPSTREAM_IMAGE}:{tag} has no usable digest")
    index = json.loads(body)
    platforms = {
        (row.get("platform") or {}).get("architecture")
        for row in index.get("manifests") or []
        if (row.get("platform") or {}).get("os") == "linux"
    }
    missing = REQUIRED_PLATFORMS - platforms
    if missing:
        raise UpstreamError(
            f"ghcr.io/{UPSTREAM_IMAGE}:{tag} is not published for {sorted(missing)} yet"
        )
    return digest


def current() -> tuple[str, str, str]:
    """(app version, pinned Print Handy version, pinned digest)."""
    config = CONFIG.read_text(encoding="utf-8")
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    app = re.search(r'^version: "([^"]+)"$', config, re.M)
    pinned = re.search(r"^ARG PRINT_HANDY_VERSION=(\S+)$", dockerfile, re.M)
    digest = re.search(r"^ARG PRINT_HANDY_DIGEST=(\S+)$", dockerfile, re.M)
    if not (app and pinned and digest):
        raise UpstreamError("could not find the pinned versions in config.yaml / Dockerfile")
    return app.group(1), pinned.group(1), digest.group(1)


def _replace_line(text: str, pattern: str, line: str) -> str:
    new, count = re.subn(pattern, line, text, count=1, flags=re.M)
    if count != 1:
        raise UpstreamError(f"pattern not found: {pattern}")
    return new


def write(version: str, digest: str, release: dict) -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    dockerfile = _replace_line(
        dockerfile, r"^ARG PRINT_HANDY_VERSION=\S+$", f"ARG PRINT_HANDY_VERSION={version}"
    )
    dockerfile = _replace_line(
        dockerfile, r"^ARG PRINT_HANDY_DIGEST=\S+$", f"ARG PRINT_HANDY_DIGEST={digest}"
    )
    DOCKERFILE.write_text(dockerfile, encoding="utf-8", newline="\n")

    config = CONFIG.read_text(encoding="utf-8")
    config = _replace_line(config, r'^version: "[^"]+"$', f'version: "{version}"')
    CONFIG.write_text(config, encoding="utf-8", newline="\n")

    title = str(release.get("name") or version).strip()
    # Release names read "Print Handy 2.3.2: <tagline>"; keep the tagline.
    title = re.sub(rf"^Print Handy {re.escape(version)}\s*[:-]\s*", "", title) or version
    url = release.get("html_url") or f"https://github.com/{UPSTREAM_REPO}/releases/tag/{version}"
    entry = (
        f"## {version}\n\n"
        f"- Print Handy [{version}]({url}): {title}\n"
        f"- Image `ghcr.io/{UPSTREAM_IMAGE}:{version}@{digest}`\n\n"
    )
    log = CHANGELOG.read_text(encoding="utf-8")
    marker = "<!-- releases -->\n\n"
    if marker not in log:
        raise UpstreamError("CHANGELOG.md has no <!-- releases --> marker")
    CHANGELOG.write_text(log.replace(marker, marker + entry, 1), encoding="utf-8", newline="\n")


def output(**values: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    for key, value in values.items():
        print(f"{key}={value}")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            for key, value in values.items():
                handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report only, change nothing")
    parser.add_argument("--version", help="pin this Print Handy release instead of the latest")
    args = parser.parse_args()

    try:
        app_version, pinned, _ = current()
        release = release_for(args.version) if args.version else latest_release()
        if release.get("draft") or release.get("prerelease"):
            raise UpstreamError(f"{release.get('tag_name')} is a draft or pre-release")
        version = str(release["tag_name"]).lstrip("v")
        newer = version_tuple(version) > version_tuple(pinned)
        if not args.version and not newer:
            print(f"Up to date: app {app_version} runs Print Handy {pinned}; latest is {version}")
            output(changed="false", version=app_version, previous=app_version)
            return 0
        digest = image_digest(version)
        print(f"Print Handy {version} is published ({digest}); app is on {pinned}")
        if args.check:
            output(changed="false", version=version, previous=app_version)
            return 0
        write(version, digest, release)
        output(changed="true", version=version, previous=app_version)
        return 0
    except UpstreamError as err:
        print(f"::error::{err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
