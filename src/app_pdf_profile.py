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

######## Database Setup ########
################################

DB_FILE = "pdf_qa_logs.db"

# Initialize the database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS interactions (
                 id TEXT PRIMARY KEY,
                 timestamp TEXT,
                 model TEXT,
                 prompt TEXT,
                 temperature REAL,
                 top_p REAL,
                 max_tokens INTEGER,
                 pdf_name TEXT,
                 task TEXT,
                 query TEXT,
                 response TEXT,
                 token_prompt INTEGER,
                 token_answer INTEGER,
                 evaluation TEXT,
                 feedback TEXT,
                 valid_json TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Log to SQLite
def log_interaction(pdf_name, task, query, response, prompt,
                    token_prompt, token_answer, temperature, top_p, model_name, evaluation=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    interaction_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    # Fix: Add correct number of placeholders and values
    c.execute("""INSERT INTO interactions 
              (id, timestamp, model, prompt, temperature, top_p, max_tokens, 
               pdf_name, task, query, response, token_prompt, token_answer, 
               evaluation, feedback) 
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (interaction_id, timestamp, model_name, prompt, temperature, 
               top_p, None, pdf_name, task, query, response, token_prompt, 
               token_answer, evaluation, None))
    conn.commit()
    conn.close()
    return interaction_id

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

#######################################################

######### PDF Processing Functions #########
############################################

def extract_text_chunks(pdf_bytes):
    """Extract text from PDF as chunks, with page numbers."""
    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    chunks = []
    for page_num in range(pdf_doc.page_count):
        page = pdf_doc.load_page(page_num)
        text = page.get_text("text").strip()
        if text:
            # Split page into smaller chunks if too long
            words = text.split()
            chunk_size = 500  # approximately 500 words per chunk
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                chunks.append({
                    "page": page_num + 1,
                    "chunk_id": len(chunks) + 1,
                    "text": chunk
                })
    return chunks

def simple_keyword_ranking(chunks, query, top_k=3):
    """Rank chunks based on keyword matching with the query."""
    # Preprocess query
    query_words = set(query.lower().split())
    
    # Score chunks based on keyword matches
    scored_chunks = []
    for chunk in chunks:
        chunk_text = chunk["text"].lower()
        score = sum(word in chunk_text for word in query_words)
        if score > 0:  # Only include chunks with matches
            scored_chunks.append((score, chunk))
    
    # Sort by score and return top_k chunks
    ranked = sorted(scored_chunks, key=lambda x: x[0], reverse=True)
    return [chunk for score, chunk in ranked[:top_k]]
######################################################################

######### Prompt Functions #########
#####################################
def prompt_extract_json(extracted_text, query):
    prompt_extract = f'''
    Extract the information from the PDF file attached extracting as JSON file
    - name
    - current job title
    - skills of expertise
    - highest degree
    - years of experience

    Do not use markdown or any other formatting. Just return the JSON file with the information extracted from the PDF.

    CONTEXT: {extracted_text}
    QUESTION: {query}
    '''
    return prompt_extract

def prompt_email(extracted_text, query):
    prompt_email = f'''

    Extract the information from the PDF file, this is the information of the candidate. Write an email specific to the candidate skills offering a position in our company.
    The email should be professional and concise, highlighting the skills and experience that match the job description by addressing the role that the candidate will play in the company specific to their profile.
    Fill out all the candidate information in the email.
    The position of the role will be decided based on the candidate's skills and experience, and the level of the job will be specify based on the experience either Junio, Mid or Senior.
    Highlight skills, requirements, nice to have and responsabilities on the role that match with the canidates abilities

    CONTEXT: {extracted_text}
    QUESTION: {query}
    '''
    return prompt_email

# Function to generate the prompt based on the version
def generate_prompt(query, extracted_text, task):
    if task == "Extract":
        return prompt_extract_json(query, extracted_text)
    elif task == "Email":
        return prompt_email(query, extracted_text)
    else:
        raise ValueError("Invalid prompt version selected")

######################################


######## Model functions ############
#####################################

AVAILABLE_MODELS = [
    "openai-gpt",
    "anthropic-claude",
    "gemini",
]
default_model = "openai-gpt"
encoding = tiktoken.encoding_for_model("gpt-4o-mini")

def oai_chat(prompt, temperature=0.1, top_p=1.0):
    client = OpenAI()
        
    completion = client.chat.completions.create(
        model="gpt-4.1-nano",
        temperature=temperature,
        top_p=top_p,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return completion.choices[0].message.content

def anthropic_chat(prompt, temperature=0.1, top_p=1.0):
    import anthropic
    anthropic_client = anthropic.Anthropic()
    response = anthropic_client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1000,
        temperature=temperature,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.content[0].text

def gemini_chat(prompt, temperature=0.1, top_p=1.0):
    from google import genai
    from google.genai import types
    # Send the prompt to Gemini
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=500,
            temperature=temperature
        )
    )
    return response.text

def llm(full_prompt, model_name, temperature, top_p):
    if model_name == "openai-gpt":
        return oai_chat(full_prompt, temperature, top_p)
    elif model_name == "anthropic-claude":
        return anthropic_chat(full_prompt, temperature, top_p)
    elif model_name == "gemini":
        return gemini_chat(full_prompt, temperature, top_p)
    else:
        raise ValueError(f"Unknown model: {model_name}")

#########################################

# Validation of the data output #
import json
def validate_json(output):
    """
    Validate whether a string is valid JSON.

    Args:
        output (str): Raw output string to validate.

    Returns:
        bool: True if valid JSON, False otherwise.
    """
    try:
        json.loads(output)  # Try parsing the JSON
        print("Valid JSON")  # Log success
        return True  # Return True for valid JSON
    except json.JSONDecodeError as e:
        print(f"Not valid JSON: {e}")  # Log error
        return False  # Return False for invalid JSON

#### Process PDF Function ############
#######################################
def process_pdf(pdf_file, query, model_name, task, temperature, top_p, evaluation=None):
    if pdf_file is None:
        return "Please upload a PDF.", None
    if not query.strip():
        return "Please enter a valid query.", None
    
    try:
        # Extract text chunks from the PDF
        chunks = extract_text_chunks(pdf_file)
        
        # Rank and select relevant chunks
        relevant_chunks = simple_keyword_ranking(chunks, query)
        
        # Combine relevant chunks with page references
        context = "\n\n".join([
            f"[Page {chunk['page']}]: {chunk['text']}"
            for chunk in relevant_chunks
        ])
        
        # Generate the prompt with the relevant context
        prompt = generate_prompt(query, context, task)
        
        # Rest of your existing code...
        response = llm(prompt, model_name, temperature, top_p)
        # Validate the response
        valid_json =  validate_json(response)
        # Calculate token counts
        token_prompt = len(encoding.encode(prompt))
        token_answer = len(encoding.encode(response))
        # Log the interaction
        pdf_name = pdf_file.name if hasattr(pdf_file, 'name') else "Uploaded PDF"
        interaction_id = log_interaction(pdf_name, task, query, response, prompt,
                                         token_prompt, token_answer, temperature, top_p, model_name, valid_json)
        return response, interaction_id
        
    except Exception as e:
        print(f"Error in process_pdf: {e}")
        return f"An error occurred: {str(e)}", None
#########################################

#########################################



############################################


# Gradio interface setup with prompt preview
with gr.Blocks() as app:
    pdf_upload = gr.File(label="Upload PDF", type="binary")
    query_input = gr.Textbox(label="Ask a question about the PDF")
    
    task_dropdown = gr.Dropdown(
        label="Select Task",
        choices=["Extract", "Email"],
        value="Extract"  # Default value
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
    def process_pdf_and_show_evaluation(pdf_file, query, task, temperature, top_p, model_name):
        response, interaction_id_value = process_pdf(pdf_file, query, model_name, task, temperature, top_p, evaluation=None)
        if interaction_id_value is None:
            return response, gr.update(visible=False), gr.update(visible=False), None
        return response, gr.update(visible=True), gr.update(visible=True), interaction_id_value
        
    # Button to generate and preview the prompt
    preview_button = gr.Button("Preview Prompt")
    # Replace the preview button click handler with this:
    preview_button.click(
        lambda pdf_file, query, task: generate_prompt(
            query,
            "\n".join(chunk["text"] for chunk in extract_text_chunks(pdf_file)),
            task
        ),
        inputs=[pdf_upload, query_input, task_dropdown],
        outputs=prompt_preview
    )
    # Button to submit the query and get the response
    query_button = gr.Button("Submit")
    query_button.click(
        process_pdf_and_show_evaluation,
        inputs=[pdf_upload, query_input, task_dropdown, temperature_slider, top_p_slider, model_dropdown],
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
