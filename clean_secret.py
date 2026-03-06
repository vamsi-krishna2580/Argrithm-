"""Temporary script to replace API key in all files for git filter-branch."""
import os
import sys

SECRET = "REMOVED_API_KEY"
REPLACEMENT = "REMOVED_API_KEY"

for root, dirs, files in os.walk("."):
    # Skip .git directory
    dirs[:] = [d for d in dirs if d != ".git"]
    for fname in files:
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if SECRET in content:
                content = content.replace(SECRET, REPLACEMENT)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception:
            pass
