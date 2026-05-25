#!/usr/bin/env python3
"""Bump the project version in pyproject.toml. Usage: bump_version.py [patch|minor]."""

import re
import sys

if len(sys.argv) != 2 or sys.argv[1] not in ("patch", "minor"):
    raise SystemExit("Usage: bump_version.py [patch|minor]")

bump_type = sys.argv[1]

with open("pyproject.toml") as f:
    content = f.read()

match = re.search(r'^version = "(\d+)\.(\d+)\.(\d+)"', content, re.MULTILINE)
if not match:
    raise SystemExit('version = "x.y.z" not found in pyproject.toml')

major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))

if bump_type == "patch":
    new_version = f"{major}.{minor}.{patch + 1}"
else:
    new_version = f"{major}.{minor + 1}.0"

new_content = re.sub(
    r'^version = "\d+\.\d+\.\d+"',
    f'version = "{new_version}"',
    content,
    count=1,
    flags=re.MULTILINE,
)

with open("pyproject.toml", "w") as f:
    f.write(new_content)

print(f"Bumped: {major}.{minor}.{patch} -> {new_version}")
