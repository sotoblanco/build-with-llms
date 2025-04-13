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

DB_FILE = "pdf_qa_logs4.db"

# Initialize the database


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS interactions (
                 id TEXT PRIMARY KEY,
                 timestamp TEXT,
                 model TEXT,
                 temperature REAL,
                 top_p REAL,
                 max_tokens INTEGER,
                 pdf_name TEXT,
                 prompt_version TEXT,
                 query TEXT,
                 response TEXT,
                 token_prompt INTEGER,
                 token_answer INTEGER,
                 evaluation TEXT,
                 feedback TEXT)''')
    # Add the evaluation column if it doesn't exist
    c.execute("PRAGMA table_info(interactions)")
    columns = [row[1] for row in c.fetchall()]
    if "evaluation" not in columns:
        c.execute("ALTER TABLE interactions ADD COLUMN evaluation TEXT")
    if "feedback" not in columns:
        c.execute("ALTER TABLE interactions ADD COLUMN feedback TEXT")
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

AVAILABLE_MODELS = [
    "gpt-o3-mini",
    "gpt-4o",
    "gpt-4o-mini"
]
default_model = "gpt-4o-mini"
encoding = tiktoken.encoding_for_model(default_model)


def llm(prompt, model_name, temperature=0.1, top_p=1.0):
    response = client.chat.completions.create(
        model=model_name,
        temperature=temperature,
        top_p=top_p,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content



# Log to SQLite
def log_interaction(pdf_name, prompt_version, query, response,
                    token_prompt, token_answer, temperature, top_p, model_name, evaluation=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    interaction_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    c.execute("INSERT INTO interactions (id, timestamp, model, temperature, top_p, max_tokens, pdf_name, prompt_version, query, response, token_prompt, token_answer, evaluation) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (interaction_id, timestamp, model_name, temperature, top_p, None, pdf_name, prompt_version, query, response, token_prompt, token_answer, evaluation))
    conn.commit()
    conn.close()
    return interaction_id  # Return the interaction ID


# Function to generate the prompt based on the version
def generate_prompt(query, extracted_text, prompt_version):
    if prompt_version == "V1":
        return build_prompt_v1(query, extracted_text)
    elif prompt_version == "V2":
        return build_prompt_v2(query, extracted_text)
    else:
        raise ValueError("Invalid prompt version selected")

# Updated process_pdf function to separate prompt generation and response


def process_pdf(pdf_file, query, model_name, prompt_version, temperature, top_p, evaluation=None):
    if pdf_file is None:
        return "Please upload a PDF.", None
    if not query.strip():
        return "Please enter a valid query.", None
    
    try:
        # Extract text from the uploaded PDF
        extracted_text = extract_text_from_pdf(pdf_file)

        # Generate the prompt
        prompt = generate_prompt(query, extracted_text, prompt_version)

        # Generate response using the LLM
        response = llm(prompt, model_name, temperature, top_p)
        token_prompt = len(encoding.encode(prompt))
        token_answer = len(encoding.encode(response))

        pdf_name = pdf_file.name if hasattr(pdf_file, 'name') else "Uploaded PDF"

        # Log the interaction and get the interaction ID
        interaction_id = log_interaction(pdf_name, prompt_version, query,
                                         response, token_prompt, token_answer,
                                         temperature, top_p, model_name)
        print(f"Generated interaction_id: {interaction_id}")  # Debugging
        return response, interaction_id  # Return both response and interaction ID
    except Exception as e:
        print(f"Error in process_pdf: {e}")  # Debugging
        return f"An error occurred: {str(e)}", None

# Function to log evaluation
def log_evaluation(interaction_id, evaluation, feedback=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if feedback:
        c.execute("UPDATE interactions SET evaluation = ?, feedback = ? WHERE id = ?", 
                 (evaluation, feedback, interaction_id))
    else:
        c.execute("UPDATE interactions SET evaluation = ? WHERE id = ?", 
                 (evaluation, interaction_id))
    conn.commit()
    conn.close()

# Gradio interface setup with prompt preview
with gr.Blocks() as app:
    pdf_upload = gr.File(label="Upload PDF", type="binary")
    query_input = gr.Textbox(label="Ask a question about the PDF")
    
    prompt_version_dropdown = gr.Dropdown(
        label="Select Prompt Version",
        choices=["V1", "V2"],
        value="V1"  # Default value
    )
        # Add the model selector
    model_dropdown = gr.Dropdown(
        label="Select Model",
        choices=AVAILABLE_MODELS,
        value=default_model
    )
    temperature_slider = gr.Slider(
        label="Temperature",
        minimum=0.0,
        maximum=2.0,
        value=0.1,
        step=0.01
    )
    top_p_slider = gr.Slider(
        label="Top P",
        minimum=0.0,
        maximum=1.0,
        value=0.3,
        step=0.01
    )
    prompt_preview = gr.Textbox(
        label="Generated Prompt (Preview)", interactive=False)
    output = gr.Textbox(label="Answer")

    # Buttons for thumbs-up and thumbs-down (initially hidden)
    thumbs_up_button = gr.Button("👍", visible=False)
    thumbs_down_button = gr.Button("👎", visible=False)

    # Interaction ID placeholder (to track the current interaction)
    interaction_id = gr.State()

        # Function to process the PDF and show evaluation buttons after response
    def process_pdf_and_show_evaluation(pdf_file, query, prompt_version, temperature, top_p, model_name):
        response, interaction_id_value = process_pdf(pdf_file, query, model_name, prompt_version, temperature, top_p, evaluation=None)
        if interaction_id_value is None:
            return response, gr.update(visible=False), gr.update(visible=False), None
        return response, gr.update(visible=True), gr.update(visible=True), interaction_id_value
        
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
        process_pdf_and_show_evaluation,
        inputs=[pdf_upload, query_input, prompt_version_dropdown, temperature_slider, top_p_slider, model_dropdown],
        outputs=[output, thumbs_up_button, thumbs_down_button, interaction_id]
    )
    feedback_text = gr.Textbox(
        label="Why did it fail? (Optional)",
        visible=False,
        interactive=True
    )

    # Handle thumbs-up click
    thumbs_up_button.click(
        lambda id: log_evaluation(id, "up"),
        inputs=[interaction_id],
        outputs=[]  # Remove None from outputs
    ).then(
        lambda: (gr.update(visible=False), gr.update(visible=False)),
        outputs=[thumbs_up_button, thumbs_down_button]
    )

    # Handle thumbs-down click
    thumbs_down_button.click(
        lambda id: log_evaluation(id, "down"),
        inputs=[interaction_id],
        outputs=[]
    ).then(
        lambda: (gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)),
        outputs=[thumbs_up_button, thumbs_down_button, feedback_text]
    )

    # Add a submit feedback button
    feedback_submit = gr.Button("Submit Feedback", visible=False)
    # Inside the gr.Blocks() context
    feedback_submit.click(
        lambda id, text: log_evaluation(id, "down", feedback=text),
        inputs=[interaction_id, feedback_text],
        outputs=[]
    ).then(
        lambda: (gr.update(visible=False), gr.update(visible=False)),
        outputs=[feedback_text, feedback_submit]
    )

    # Show submit button when feedback is entered
    feedback_text.change(
        lambda: gr.update(visible=True),
        outputs=feedback_submit
    )

if __name__ == "__main__":
    app.launch()
