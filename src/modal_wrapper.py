from pathlib import Path  # Python stdlib module for ergonomic file/path mgmt
from fastapi import FastAPI  # FastAPI for building the API layer
from gradio.routes import mount_gradio_app  # Allows embedding Gradio inside FastAPI
import modal  # Modal for serverless deployment

from app_pdf_profile import app as blocks  # Import Gradio app
from app_pdf_profile import DB_FILE 

# Create a lightweight Modal image (Debian-based) with required dependencies
image = modal.Image.debian_slim().pip_install(
    "gradio<6",  # Use Gradio version below 6 (v6 may break compatibility)
    "pymupdf",  # PDF processing library
    "openai",  # OpenAI API client
    "tiktoken"
)

# Define the Modal app container
app = modal.App("pdf-query-app2", image=image)

# Define a cloud file system for our logs DB
db_storage = modal.Volume.from_name("pdf-query-logs", create_if_missing=True)


@app.function(
    concurrency_limit=1,  # Only one instance (Gradio uses local file storage, preventing multiple replicas)
    allow_concurrent_inputs=1000,  # Async handling for up to 1000 concurrent requests within a single instance
    secrets=[modal.Secret.from_name("openai-secret")],  # Fetch OpenAI API key from Modal secrets
    volumes={"/db": db_storage},  # Attach remote storage for our logs DB file (only between container spin-up/down)
)
@modal.asgi_app()  # Register this as an ASGI app (compatible with FastAPI)
def serve() -> FastAPI:
    """
    Main server function:
    - Handles movement of our logs DB to and from remote storage on Modal
    - Wraps Gradio inside FastAPI
    - Deploys the API through Modal with a single instance for session consistency
    """
    from contextlib import asynccontextmanager  # Use a contextmanager to handle shudown

    remote_db_path = Path("/db") / DB_FILE
    local_db_path = Path(".") / DB_FILE
    if remote_db_path.exists():  # If we have a logs db
        # Copy it from remote storage to our cloud instance
        local_db_path.write_bytes(remote_db_path.read_bytes())

    import asyncio

    def persist():
        print("Persisting db")
        remote_db_path.write_bytes(local_db_path.read_bytes())
        db_storage.commit()

    async def persist_background():
        while True:
            persist()
            await asyncio.sleep(60)

    @asynccontextmanager
    async def lifespan(api: FastAPI):
        asyncio.create_task(persist_background())
        yield
        persist()

    api = FastAPI(lifespan=lifespan)

    @api.get("/sync")
    def sync():
        print("Persisting db on sync")
        persist()
        return {"status": "synced"}
    return mount_gradio_app(app=api, blocks=blocks, path="/")  # Mount Gradio app at root path


@app.local_entrypoint()
def main():
    """
    Local development entry point:
    - Allows running the app locally for testing
    - Prints the type of Gradio app to confirm readiness
    """
    print(f"{type(blocks)} is ready to go!")