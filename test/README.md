# Homework 4

🛠 **What to Do**

- Use pytest or a custom script to test app behavior
- (Optional) Add a GitHub workflow to run tests on PR
- Add or expand tracing/logging:
    - Use an SDK or tracing framework (e.g. Burr)
    - Log prompt versions, input/output metadata
- Implement a simple guardrail:
    - Input validation (e.g. profanity, injection)
    - Output validation (e.g. format patterns or banned terms)
- (Optional) Rewrite your app using a framework of your choice


1. Start by writting a simple test for the app_pdf_profile.py file, here we started by testing the extract_profile_data function, to make sure it read the pdf file correctly, check the test_app_pdf_profile.py file for more details.

```python
def test_process_pdf_simple():
    pdf_path = "../data/hugo_bowne_profile.pdf"
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
```

2. Add logging to the app_pdf_profile.py file, we used the logging_setup.py file to set up the logging and burr. 


3. Log prompt versions, input/output metadata, we used the log_interaction function to log the prompt versions, input/output metadata are already implemented in the datasette. 

4. In the app_pdf_profile.py file, we implemented the guardrail to check for profanity, injection, and banned terms. We also implemented the output validation to check for format patterns or banned terms.

5. Optional: Set up a GitHub workflow to run the tests on PR.
```yaml
name: Run Python tests

on:
  pull_request:
    branches: [ "main", "master" ]
  push:
    branches: [ "main", "master" ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pymupdf gradio openai tiktoken
      - name: Run tests
        run: pytest -vv 
```