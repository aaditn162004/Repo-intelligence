"""Tests for the AST parsing pipeline."""
import pytest
from app.parsers.ast_parser import ASTParser
from app.parsers.language_detector import detect_language, should_index_file
from app.models.code_chunk import ChunkType

PYTHON_SAMPLE = '''
import os
from pathlib import Path

class UserService:
    """Handles user operations."""

    def __init__(self, db):
        self.db = db

    def get_user(self, user_id: int):
        """Fetch user by ID."""
        return self.db.query(user_id)

    async def create_user(self, username: str, email: str):
        user = {"username": username, "email": email}
        return await self.db.insert(user)

def helper_func(x, y):
    return x + y
'''

JS_SAMPLE = '''
import React, { useState } from 'react';

class AuthService {
  constructor(apiUrl) {
    this.apiUrl = apiUrl;
  }

  async login(credentials) {
    const response = await fetch(this.apiUrl + '/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    return response.json();
  }
}

function useAuth() {
  const [user, setUser] = useState(null);
  return { user, setUser };
}

export default AuthService;
'''


@pytest.fixture
def parser():
    return ASTParser()


def test_python_functions(parser):
    chunks = parser.parse_file("service.py", PYTHON_SAMPLE, "python", "repo-test")
    func_chunks = [c for c in chunks if c.chunk_type == ChunkType.FUNCTION]
    method_chunks = [c for c in chunks if c.chunk_type == ChunkType.METHOD]
    assert any(c.name == "helper_func" for c in func_chunks)
    assert any(c.name in ("get_user", "create_user") for c in method_chunks)


def test_python_classes(parser):
    chunks = parser.parse_file("service.py", PYTHON_SAMPLE, "python", "repo-test")
    class_chunks = [c for c in chunks if c.chunk_type == ChunkType.CLASS]
    assert any(c.name == "UserService" for c in class_chunks)


def test_python_module_chunk(parser):
    chunks = parser.parse_file("service.py", PYTHON_SAMPLE, "python", "repo-test")
    module_chunks = [c for c in chunks if c.chunk_type == ChunkType.MODULE]
    assert len(module_chunks) >= 1


def test_language_detection():
    assert detect_language("main.py") == "python"
    assert detect_language("app.ts") == "typescript"
    assert detect_language("Main.java") == "java"
    assert detect_language("server.go") == "go"
    assert detect_language("unknown.xyz") is None


def test_should_index_file():
    assert should_index_file("src/main.py") is True
    assert should_index_file("node_modules/pkg/index.js") is False
    assert should_index_file("dist/bundle.js") is False
    assert should_index_file("app.pyc") is False


def test_chunk_line_numbers(parser):
    chunks = parser.parse_file("service.py", PYTHON_SAMPLE, "python", "repo-test")
    for chunk in chunks:
        assert chunk.start_line >= 1
        assert chunk.end_line >= chunk.start_line
