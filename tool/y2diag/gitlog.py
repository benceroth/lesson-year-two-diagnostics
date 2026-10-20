"""Thin wrapper over the git CLI. No network access is ever needed."""

import fnmatch
import posixpath
import subprocess
from dataclasses import dataclass


class GitError(RuntimeError):
    pass


@dataclass(frozen=True)
class Commit:
    sha: str
    email: str  # used only to map to a team; never written to reports
    ts: int
    files: tuple


def run_git(repo, *args):
    proc = subprocess.run(
        ["git", "-c", "core.quotepath=false", "-C", str(repo), *args],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise GitError(proc.stderr.decode("utf-8", errors="replace").strip())
    return proc.stdout.decode("utf-8", errors="replace")


def is_ignored(path, patterns):
    base = posixpath.basename(path)
    for pat in patterns:
        if pat.endswith("/"):
            if path.startswith(pat) or ("/" + pat) in ("/" + path):
                return True
        elif fnmatch.fnmatchcase(path, pat) or fnmatch.fnmatchcase(base, pat):
            return True
    return False


def read_history(repo, since=None, until=None, paths=(), ignore=(), max_commits=None):
    args = [
        "log", "--no-merges", "--no-renames", "--name-only",
        "--format=%x1e%H%x1f%ae%x1f%at",
    ]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    if max_commits:
        args.append(f"--max-count={int(max_commits)}")
    if paths:
        args += ["--", *paths]
    out = run_git(repo, *args)
    commits = []
    for chunk in out.split("\x1e")[1:]:
        header, _, body = chunk.partition("\n")
        sha, email, ts = header.strip().split("\x1f")
        files = tuple(
            line.strip() for line in body.splitlines()
            if line.strip() and not is_ignored(line.strip(), ignore)
        )
        if files:
            commits.append(Commit(sha, email, int(ts), files))
    return commits


def tracked_files(repo, paths=(), ignore=()):
    args = ["ls-files", "-z"]
    if paths:
        args += ["--", *paths]
    out = run_git(repo, *args)
    return sorted(f for f in out.split("\0") if f and not is_ignored(f, ignore))
