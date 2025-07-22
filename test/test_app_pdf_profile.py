import pytest
from datetime import datetime
import concurrent.futures

import pytest

from logic import extract_profile_data

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from app_pdf_profile import process_pdf

def test_process_pdf_simple():
    pdf_path = "data/hugo_bowne_profile.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
        class DummyFile:
            def __init__(self, bytes_data, name):
                self.bytes_data = bytes_data
                self.name = name
            def __getattr__(self, attr):
                if attr == 'name':
                    return self.name
                raise AttributeError(attr)
            def __bytes__(self):
                return self.bytes_data
        dummy_pdf = DummyFile(pdf_bytes, pdf_path)
        # Use a simple query and default params
        query = "What is the name of the person in this profile?"
        model_name = "gpt-3.5-turbo"  # or any available model in your setup
        task = "Extract"
        temperature = 0.1
        top_p = 1.0
        response, interaction_id = process_pdf(dummy_pdf.bytes_data, query, model_name, task, temperature, top_p)
        print("Response:", response)
        assert response is not None