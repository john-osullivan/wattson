"""push_if_stale: the remote record must not lag the local record by more
than PUSH_STALE_MINUTES. Verified against a local bare repo as the remote."""
import email.utils
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from vault_digest import PUSH_STALE_MINUTES, push_if_stale  # noqa: E402


def _git(cwd, *args):
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    assert r.returncode == 0, f"git {' '.join(args)}: {r.stderr}"
    return r.stdout.strip()


def _date(mins_ago):
    return email.utils.formatdate(time.time() - mins_ago * 60, usegmt=True)


def _commit(work, msg, date, env_extra):
    import os
    env = {**os.environ, "GIT_COMMITTER_DATE": date, **env_extra}
    r = subprocess.run(["git", "-C", str(work), "commit", "-q", "-m", msg, "--date", date],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr


def _make_repo(tmp_path, remote_tip_mins_ago, local_tip_mins_ago):
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    work = tmp_path / "work"
    _git(tmp_path, "init", "-q", "-b", "main", str(work))
    _git(work, "config", "user.name", "T")
    _git(work, "config", "user.email", "t@t.local")
    _git(work, "remote", "add", "origin", str(remote))
    d1 = _date(remote_tip_mins_ago)
    (work / "f").write_text("a\n")
    _git(work, "add", "f")
    _commit(work, "c1", d1, {})
    _git(work, "push", "-q", "origin", "main")
    d2 = _date(local_tip_mins_ago)
    (work / "f").write_text("ab\n")
    r = subprocess.run(["git", "-C", str(work), "commit", "-qam", "c2", "--date", d2],
                       capture_output=True, text=True,
                       env={**__import__("os").environ, "GIT_COMMITTER_DATE": d2})
    assert r.returncode == 0, r.stderr
    return work


def test_pushes_when_remote_is_stale(tmp_path):
    work = _make_repo(tmp_path, remote_tip_mins_ago=30, local_tip_mins_ago=0)
    assert push_if_stale(work) == "pushed to origin " \
        f"(remote was {PUSH_STALE_MINUTES}+ min behind)"
    _git(work, "fetch", "-q", "origin", "main")
    assert _git(work, "rev-parse", "origin/main") == _git(work, "rev-parse", "HEAD")


def test_no_push_when_remote_is_fresh(tmp_path):
    work = _make_repo(tmp_path, remote_tip_mins_ago=2, local_tip_mins_ago=0)
    assert push_if_stale(work) is None


def test_no_push_when_up_to_date(tmp_path):
    work = _make_repo(tmp_path, remote_tip_mins_ago=30, local_tip_mins_ago=0)
    _git(work, "push", "-q", "origin", "main")
    assert push_if_stale(work) is None


def test_no_push_without_remote(tmp_path):
    work = _make_repo(tmp_path, remote_tip_mins_ago=30, local_tip_mins_ago=0)
    _git(work, "remote", "remove", "origin")
    assert push_if_stale(work) is None


def test_no_push_when_local_behind_remote(tmp_path):
    # remote tip is NEWER than local tip (pushed elsewhere) — never push over it
    work = _make_repo(tmp_path, remote_tip_mins_ago=0, local_tip_mins_ago=30)
    assert push_if_stale(work) is None
