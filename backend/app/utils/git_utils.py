"""Git clone and repository utilities."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger()


def clone_repository(
    url: str,
    destination: str,
    branch: str = "main",
    github_token: Optional[str] = None,
) -> str:
    """Clone a GitHub repository and return the local path."""
    import git

    # Inject token into URL if provided
    if github_token and "github.com" in url:
        url = url.replace("https://", f"https://{github_token}@")

    dest_path = Path(destination)
    if dest_path.exists():
        shutil.rmtree(dest_path)

    logger.info("Cloning repository", url=url.replace(github_token or "", "***"), branch=branch)

    try:
        repo = git.Repo.clone_from(
            url,
            str(dest_path),
            branch=branch,
            depth=1,  # Shallow clone for speed
        )
    except git.GitCommandError:
        # Retry without specifying branch (some repos use 'master')
        repo = git.Repo.clone_from(url, str(dest_path), depth=1)

    logger.info("Repository cloned", path=str(dest_path))
    return str(dest_path)


def get_repo_size_mb(repo_path: str) -> float:
    total = 0
    for dirpath, _, filenames in os.walk(repo_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total / (1024 * 1024)


def extract_repo_name(url: str) -> str:
    """Extract 'owner/repo' from a GitHub URL."""
    url = url.rstrip("/").replace(".git", "")
    parts = url.split("/")
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return parts[-1]


def cleanup_repository(repo_path: str) -> None:
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path, ignore_errors=True)
        logger.info("Cleaned up repository", path=repo_path)
