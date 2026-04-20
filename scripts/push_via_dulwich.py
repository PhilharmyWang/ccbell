#!/usr/bin/env python3
"""
Push local git repo to GitHub using dulwich (pure-Python git).
Supports force push for history rewrites.

Usage:
    export GITHUB_TOKEN="ghp_..."
    python scripts/push_via_dulwich.py [--force]

- Reads token ONLY from os.environ["GITHUB_TOKEN"] (never to/from disk).
- Pushes main branch and all tags.
"""

import hashlib
import os
import sys

REPO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OWNER = "PhilharmyWang"
REPO = "ccbell"


def real_sha(obj) -> str:
    return hashlib.sha1(obj.as_raw_string()).hexdigest()


def main():
    force = "--force" in sys.argv

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("ERROR: GITHUB_TOKEN env var is empty or not set.", file=sys.stderr)
        sys.exit(1)

    from dulwich.repo import Repo
    from dulwich.porcelain import push

    repo = Repo(REPO_PATH)
    remote_url = f"https://{token}@github.com/{OWNER}/{REPO}.git"
    print(f"Remote URL: https://***@github.com/{OWNER}/{REPO}.git")
    print(f"Force mode: {force}")

    # Collect all tags
    tags = [k for k in repo.refs.keys() if k.startswith(b"refs/tags/")]
    print(f"Tags found: {[t.decode() for t in tags]}")

    # Build refspecs
    refspecs = []
    prefix = b"+" if force else b""
    refspecs.append(prefix + b"refs/heads/main:refs/heads/main")
    for tag in tags:
        refspecs.append(prefix + tag + b":" + tag)

    print(f"Refspecs: {[rs.decode() for rs in refspecs]}")

    # Push all at once
    print(f"\nPushing {len(refspecs)} refs ...")
    try:
        push(repo, remote_url, refspecs=refspecs)
        print("All refs pushed OK")
    except Exception as e:
        print(f"Push FAILED: {e}", file=sys.stderr)
        sys.exit(1)

    # Summary
    head = repo.refs[b'refs/heads/main']
    head_sha = real_sha(repo[head])
    print(f"\n--- Summary ---")
    print(f"main: {head_sha[:12]}")
    for tag in tags:
        tag_obj = repo.refs[tag]
        tag_sha = real_sha(repo[tag_obj])
        print(f"{tag.decode()}: {tag_sha[:12]}")
    print("Done.")


if __name__ == "__main__":
    main()
