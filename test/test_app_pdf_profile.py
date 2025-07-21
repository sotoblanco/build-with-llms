"""
To run:
> pytest -vv test_app_pdf_profile.py
"""
import io
import json
import pytest
#import fitz  # PyMuPDF
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.app_pdf_profile import app_pdf_profile

# --- Helpers

def make_sample_pdf(text="Name: John Doe\nSkills: Python, ML"):
    """Create a simple PDF in memory with the given text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes

# --- (1) Test extract_text_chunks

def test_extract_text_chunks():
    pdf_bytes = make_sample_pdf("Test page one.\nSecond line.")
    chunks = app_pdf_profile.extract_text_chunks(pdf_bytes)
    assert isinstance(chunks, list)
    assert len(chunks) == 1
    assert "Test page one" in chunks[0]["text"]

# --- (2) Test simple_keyword_ranking

@pytest.mark.parametrize(
    "chunks,query,expected_text", [
        (
            [
                {"page": 1, "chunk_id": 1, "text": "Python developer with AI experience."},
                {"page": 2, "chunk_id": 2, "text": "Experienced in Java and cloud."}
            ],
            "Python AI",
            "Python developer with AI experience."
        ),
        (
            [
                {"page": 1, "chunk_id": 1, "text": "Data scientist, ML, Python."},
                {"page": 2, "chunk_id": 2, "text": "Java developer."}
            ],
            "ML Python",
            "Data scientist, ML, Python."
        ),
])
def test_simple_keyword_ranking(chunks, query, expected_text):
    ranked = app_pdf_profile.simple_keyword_ranking(chunks, query)
    assert len(ranked) >= 1
    assert expected_text in ranked[0]["text"]

# --- (3) Test prompt generation

def test_generate_prompt_extract():
    query = "Extract candidate info"
    context = "Name: John Doe\nSkills: Python, ML"
    prompt = app_pdf_profile.generate_prompt(query, context, "Extract")
    assert "JSON" in prompt
    assert "CONTEXT" in prompt

def test_generate_prompt_email():
    query = "Write an email"
    context = "Name: Jane Smith\nSkills: Data Science"
    prompt = app_pdf_profile.generate_prompt(query, context, "Email")
    assert "email" in prompt.lower()
    assert "CONTEXT" in prompt

# --- (4) Test validate_json

@pytest.mark.parametrize(
    "output,expected", [
        ('{"name": "John"}', True),
        ('{name: John}', False),
        ('[1, 2, 3]', True),
        ('not a json', False),
])
def test_validate_json(output, expected):
    assert app_pdf_profile.validate_json(output) is expected

# --- (5) Test process_pdf (mocking LLM)

def test_process_pdf(monkeypatch):
    # Patch llm to return a valid JSON string
    monkeypatch.setattr(app_pdf_profile, "llm", lambda *a, **kw: '{"name": "Test"}')
    pdf_bytes = make_sample_pdf("Name: Test\nSkills: Python")
    response, interaction_id = app_pdf_profile.process_pdf(
        pdf_bytes, "Extract candidate info", "openai-gpt", "Extract", 0.1, 1.0
    )
    assert "Test" in response
    assert interaction_id is not None

# --- (6) Test process_pdf with empty PDF

def test_process_pdf_empty_pdf(monkeypatch):
    monkeypatch.setattr(app_pdf_profile, "llm", lambda *a, **kw: '{"name": "Nobody"}')
    # Empty PDF
    doc = fitz.open()
    pdf_bytes = doc.write()
    doc.close()
    response, interaction_id = app_pdf_profile.process_pdf(
        pdf_bytes, "Extract candidate info", "openai-gpt", "Extract", 0.1, 1.0
    )
    assert "error" in response.lower() or "please" in response.lower() or response  # Should handle gracefully

# --- (7) Test process_pdf with missing query

def test_process_pdf_missing_query():
    pdf_bytes = make_sample_pdf("Name: Test\nSkills: Python")
    response, interaction_id = app_pdf_profile.process_pdf(
        pdf_bytes, "", "openai-gpt", "Extract", 0.1, 1.0
    )
    assert "please enter a valid query" in response.lower()

# --- (8) Test process_pdf with missing PDF

def test_process_pdf_missing_pdf():
    response, interaction_id = app_pdf_profile.process_pdf(
        None, "Extract candidate info", "openai-gpt", "Extract", 0.1, 1.0
    )
    assert "please upload a pdf" in response.lower()