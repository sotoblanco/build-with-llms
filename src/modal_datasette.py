from pathlib import Path

import modal

DB_FILE = "pdf_qa_logs4.db"  # same as in app_log_frontend/modal_wrapper_log

app = modal.App("pdf-query-datasette")

image = modal.Image.debian_slim().pip_install("datasette")

db_storage = modal.Volume.from_name("pdf-query-logs", create_if_missing=True)

@app.function(
    image=image,
    volumes={"/db": db_storage},
    allow_concurrent_inputs=16,
)
@modal.asgi_app()
def ui():
    import asyncio

    from datasette.app import Datasette

    remote_db_path = Path("/db") / DB_FILE
    local_db_path = Path(".") / DB_FILE
    local_db_path.write_bytes(remote_db_path.read_bytes())

    ds = Datasette(files=[local_db_path], settings={"sql_time_limit_ms": 10000})
    asyncio.run(ds.invoke_startup())
    return ds.app()
