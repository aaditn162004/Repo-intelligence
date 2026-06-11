"""File scanning and content reading utilities."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple, Dict
import structlog

from app.core.config import settings
from app.parsers.language_detector import (
    detect_language, should_index_file, IGNORED_DIRS
)

logger = structlog.get_logger()


def scan_repository(repo_path: str) -> List[Tuple[str, str]]:
    """
    Walk the repository and return (absolute_path, relative_path) for indexable files.
    Skips ignored directories and files exceeding size limits.
    """
    results = []
    max_bytes = settings.MAX_FILE_SIZE_KB * 1024

    for root, dirs, files in os.walk(repo_path):
        # Prune ignored directories in-place to avoid descending
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

        for fname in files:
            abs_path = os.path.join(root, fname)
            rel_path = os.path.relpath(abs_path, repo_path)

            if not should_index_file(rel_path):
                continue

            try:
                file_size = os.path.getsize(abs_path)
                if file_size > max_bytes:
                    continue
                if file_size == 0:
                    continue
            except OSError:
                continue

            results.append((abs_path, rel_path))

    return results


def read_file_safe(path: str) -> str:
    """Read a file with encoding fallback."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    return ""


def count_languages(file_list: List[Tuple[str, str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for _, rel_path in file_list:
        lang = detect_language(rel_path)
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    return counts
