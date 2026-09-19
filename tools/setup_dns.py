"""Point a name.com domain at GitHub Pages.

Run this where your credentials live, not in a shared session. The token can
manage every domain on the account, so it is read from the environment and
never passed on the command line:

    export NAMECOM_USER=inigorodriguezbt
    export NAMECOM_TOKEN=...              # Account Settings -> Security -> API Tokens
    python tools/setup_dns.py             # dry run: shows the plan, changes nothing
    python tools/setup_dns.py --apply     # makes the changes

Dry run is the default on purpose. DNS mistakes take a TTL to undo and can take
mail down with them.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.name.com/v4"

# GitHub Pages apex addresses, published by GitHub.
PAGES_IPS = ["185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153"]


def call(method: str, path: str, user: str, token: str, body: dict | None = None):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    auth = base64.b64encode(f"{user}:{token}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise SystemExit(f"name.com {method} {path} failed: HTTP {exc.code}\n  {detail}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Point a domain at GitHub Pages.")
    ap.add_argument("--domain", default="theaipost.net")
    ap.add_argument("--pages-host", default="inigorodriguezbt-lang.github.io")
    ap.add_argument("--apply", action="store_true", help="make the changes")
    args = ap.parse_args()

    user = os.environ.get("NAMECOM_USER")
    token = os.environ.get("NAMECOM_TOKEN")
    if not (user and token):
        sys.exit("Set NAMECOM_USER and NAMECOM_TOKEN first. See this file's docstring.")

    existing = call("GET", f"/domains/{args.domain}/records", user, token).get("records", [])
    print(f"{args.domain}: {len(existing)} records currently\n")

    # Only apex A records and the www CNAME are ours to touch. Anything else --
    # MX, TXT, SPF, DKIM -- belongs to mail or verification and stays put.
    def is_apex_a(r):
        return r.get("type") == "A" and not r.get("host")

    def is_www_cname(r):
        return r.get("type") == "CNAME" and r.get("host") == "www"

    remove = [r for r in existing if is_apex_a(r) or is_www_cname(r)]
    keep = [r for r in existing if r not in remove]

    for r in keep:
        host = r.get("host") or "@"
        print(f"  keep    {r['type']:<6} {host:<8} {str(r.get('answer'))[:44]}")
    for r in remove:
        host = r.get("host") or "@"
        print(f"  DELETE  {r['type']:<6} {host:<8} {str(r.get('answer'))[:44]}")

    planned = [{"host": "", "type": "A", "answer": ip, "ttl": 300} for ip in PAGES_IPS]
    planned.append({"host": "www", "type": "CNAME", "answer": args.pages_host + ".", "ttl": 300})
    for r in planned:
        print(f"  CREATE  {r['type']:<6} {(r['host'] or '@'):<8} {r['answer']}")

    if not args.apply:
        print("\nDry run. Nothing changed. Re-run with --apply to make it so.")
        return

    for r in remove:
        call("DELETE", f"/domains/{args.domain}/records/{r['id']}", user, token)
        print(f"  deleted {r['type']} {r.get('host') or '@'}")
    for r in planned:
        call("POST", f"/domains/{args.domain}/records", user, token, r)
        print(f"  created {r['type']} {r['host'] or '@'} -> {r['answer']}")

    print("\nDone. DNS takes 10-30 minutes to propagate.")
    print("Next: GitHub -> Settings -> Pages -> Custom domain -> " + args.domain)
    print("Then tick Enforce HTTPS once it is no longer greyed out.")
    print("\nCheck propagation with:")
    print(f"  dig +short {args.domain}")
    print(f"  dig +short www.{args.domain}")


if __name__ == "__main__":
    main()
