"""ZIP archive extraction for uploaded repositories."""
from __future__ import annotations

import os
import zipfile
import shutil
from pathlib import Path

import structlog

logger = structlog.get_logger()


def extract_zip(zip_path: str, destination: str) -> str:
    """Extract a ZIP file and return the root directory of its contents."""
    if os.path.exists(destination):
        shutil.rmtree(destination)
    os.makedirs(destination)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(destination)

    # If the ZIP has a single top-level directory, descend into it
    entries = os.listdir(destination)
    if len(entries) == 1 and os.path.isdir(os.path.join(destination, entries[0])):
        root = os.path.join(destination, entries[0])
    else:
        root = destination

    logger.info("ZIP extracted", destination=root)
    return root


def validate_zip(zip_path: str, max_mb: int = 500) -> bool:
    try:
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        if size_mb > max_mb:
            return False
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad = zf.testzip()
            return bad is None
    except zipfile.BadZipFile:
        return False
