# write your own prompt using:
# 1. Intructions for the model
# 2. Pdf content
# 3. user's query

from openai import OpenAI
import os
import gradio as gr
import fitz  # PyMuPDF
import sqlite3
# from llama_index.core import VectorStoreIndex, Document
from datetime import datetime
import uuid
import tiktoken

client = OpenAI()

DB_FILE = "pdf_qa_logs_hw1b.db"

# Initialize the database


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS interactions (
                 id TEXT PRIMARY KEY,
                 timestamp TEXT,
                 model TEXT,
                 pdf_name TEXT,
                 prompt_version TEXT,
                 query TEXT,
                 response TEXT,
                 token_prompt INTEGER,
                 token_answer INTEGER)''')
    conn.commit()
    conn.close()


init_db()

# Extract text from PDF


def extract_text_from_pdf(pdf_bytes):
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page_num in range(pdf_doc.page_count):
        page = pdf_doc.load_page(page_num)
        text += page.get_text("text")
    return text


def build_prompt_v1(query, extracted_text):
    prompt_template = f"""
Answer the QUESTION based on the context from the extracted file. Use only the facts from the CONTEXT when answering the QUESTION

QUESTION: {query}

CONTEXT: {extracted_text}

"""
    return prompt_template


def build_prompt_v2(query, extracted_text):
    return f"""
You are an AI assistant. Answer the QUESTION using only the information provided in the CONTEXT. Be concise and factual.

QUESTION: {query}

CONTEXT: {extracted_text}
"""


model = "gpt-4o"
encoding = tiktoken.encoding_for_model(model)


def llm(prompt, model):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


# Log to SQLite
def log_interaction(pdf_name, prompt, query, response, token_prompt, token_answer):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    interaction_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    c.execute("INSERT INTO interactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (interaction_id, timestamp, model, pdf_name, prompt, query, response, token_prompt, token_answer))
    conn.commit()
    conn.close()

# Function to process the uploaded PDF and create an index


# Function to generate the prompt based on the version
def generate_prompt(query, extracted_text, prompt_version):
    if prompt_version == "V1":
        return build_prompt_v1(query, extracted_text)
    elif prompt_version == "V2":
        return build_prompt_v2(query, extracted_text)
    else:
        raise ValueError("Invalid prompt version selected")

# Updated process_pdf function to separate prompt generation and response


def process_pdf(pdf_file, query, prompt_version):
    # Extract text from the uploaded PDF
    extracted_text = extract_text_from_pdf(pdf_file)

    # Generate the prompt
    prompt = generate_prompt(query, extracted_text, prompt_version)

    # Generate response using the LLM
    response = llm(prompt, model)
    token_prompt = len(encoding.encode(prompt))
    token_answer = len(encoding.encode(response))

    pdf_name = pdf_file.name if hasattr(pdf_file, 'name') else "Uploaded PDF"

    # Log the interaction with the selected prompt version
    log_interaction(pdf_name, prompt_version, query,
                    response, token_prompt, token_answer)
    return response


# Gradio interface setup with prompt preview
with gr.Blocks() as app:
    pdf_upload = gr.File(label="Upload PDF", type="binary")
    query_input = gr.Textbox(label="Ask a question about the PDF")
    prompt_version_dropdown = gr.Dropdown(
        label="Select Prompt Version",
        choices=["V1", "V2"],
        value="V1"  # Default value
    )
    prompt_preview = gr.Textbox(
        label="Generated Prompt (Preview)", interactive=False)
    output = gr.Textbox(label="Answer")

    # Button to generate and preview the prompt
    preview_button = gr.Button("Preview Prompt")
    preview_button.click(
        lambda pdf_file, query, prompt_version: generate_prompt(
            query, extract_text_from_pdf(pdf_file), prompt_version
        ),
        inputs=[pdf_upload, query_input, prompt_version_dropdown],
        outputs=prompt_preview
    )

    # Button to submit the query and get the response
    query_button = gr.Button("Submit")
    query_button.click(
        process_pdf,
        inputs=[pdf_upload, query_input, prompt_version_dropdown],
        outputs=output
    )

if __name__ == "__main__":
    app.launch()
