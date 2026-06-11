import re
from pathlib import Path
from typing import Dict, List, Optional

EXTENSION_MAP: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".lua": "lua",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
}

SUPPORTED_LANGUAGES: List[str] = [
    "python",
    "javascript",
    "typescript",
    "java",
    "go",
    "rust",
    "cpp",
    "c",
    "ruby",
    "php",
]

FRAMEWORK_PATTERNS: Dict[str, List[str]] = {
    "fastapi": ["from fastapi", "import fastapi", "FastAPI()"],
    "django": ["from django", "import django", "DJANGO_SETTINGS"],
    "flask": ["from flask", "import flask", "Flask(__name__)"],
    "express": ["require('express')", "from 'express'", "express()"],
    "react": ["import React", "from 'react'", "useState", "useEffect"],
    "nextjs": ["next/", "getServerSideProps", "getStaticProps"],
    "spring": ["@SpringBootApplication", "@RestController", "springframework"],
    "gin": ["gin.Default()", "gin.New()", '"github.com/gin-gonic/gin"'],
    "sqlalchemy": ["from sqlalchemy", "import sqlalchemy"],
    "prisma": ["@prisma/client", "PrismaClient"],
    "graphql": ["GraphQL", "graphql", "schema {", "type Query"],
    "langchain": ["from langchain", "import langchain"],
    "pytorch": ["import torch", "from torch"],
    "tensorflow": ["import tensorflow", "from tensorflow"],
}

IGNORED_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    "env",
    ".env",
    "vendor",
    "coverage",
    ".coverage",
    ".mypy_cache",
    "__mocks__",
    ".cache",
    "tmp",
    "temp",
}

IGNORED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".class",
    ".jar",
    ".war",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".mp3",
    ".zip",
    ".tar",
    ".gz",
    ".lock",
    ".sum",
}


def detect_language(file_path: str) -> Optional[str]:
    ext = Path(file_path).suffix.lower()
    return EXTENSION_MAP.get(ext)


def is_supported_language(language: Optional[str]) -> bool:
    return language in SUPPORTED_LANGUAGES


def should_index_file(file_path: str) -> bool:
    path = Path(file_path)
    if path.suffix.lower() in IGNORED_EXTENSIONS:
        return False
    for part in path.parts:
        if part in IGNORED_DIRS:
            return False
    return True


def detect_frameworks(content: str) -> List[str]:
    frameworks = []
    for framework, patterns in FRAMEWORK_PATTERNS.items():
        if any(pattern in content for pattern in patterns):
            frameworks.append(framework)
    return frameworks


def get_dominant_language(file_counts: Dict[str, int]) -> Optional[str]:
    if not file_counts:
        return None
    return max(file_counts, key=file_counts.get)
