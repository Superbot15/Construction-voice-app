import json
import os
import time

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

SOURCE_DIR = "Document_Source"
PERSIST_DIR = "chroma_db"
MANIFEST_PATH = os.path.join(PERSIST_DIR, "ingested_files.json")
BATCH_SIZE = 50
# The free-tier Gemini embedding quota is flaky in practice (observed stalling well
# below the documented per-minute number), so pace conservatively and checkpoint
# after every batch so an interrupted run can resume later without re-embedding
# (and re-paying for) chunks that already succeeded.
PACE_DELAY_SECONDS = 30
MAX_RATE_LIMIT_RETRIES = 10
RATE_LIMIT_RETRY_DELAY_SECONDS = 60


def add_batch_with_retry(db, batch):
    for attempt in range(1, MAX_RATE_LIMIT_RETRIES + 1):
        try:
            db.add_documents(batch)
            return
        except Exception as e:
            message = str(e)
            if "RESOURCE_EXHAUSTED" in message or "429" in message:
                print(
                    f"  Rate limited, waiting {RATE_LIMIT_RETRY_DELAY_SECONDS}s "
                    f"before retry ({attempt}/{MAX_RATE_LIMIT_RETRIES})...",
                    flush=True,
                )
                time.sleep(RATE_LIMIT_RETRY_DELAY_SECONDS)
                continue
            raise
    raise RuntimeError(
        "Gave up on a batch after repeated rate-limit errors. This run's progress is "
        "saved - rerun ingest.py later (e.g. after the quota resets) to resume from here."
    )


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r") as f:
            return json.load(f)
    return {}


def save_manifest(manifest):
    os.makedirs(PERSIST_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def main():
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: GOOGLE_API_KEY environment variable is required.")
        return

    if not os.path.exists(SOURCE_DIR):
        print(f"Error: Missing '{SOURCE_DIR}' folder.")
        return

    manifest = load_manifest()
    pdf_files = sorted(f for f in os.listdir(SOURCE_DIR) if f.lower().endswith(".pdf"))
    pending_files = [f for f in pdf_files if not manifest.get(f, {}).get("complete")]

    if not pending_files:
        print("Nothing to do - every PDF in Document_Source has already been ingested.", flush=True)
        print(f"Already ingested: {', '.join(pdf_files) if pdf_files else '(none found)'}", flush=True)
        return

    print(f"Found {len(pending_files)} file(s) needing (more) ingestion: {', '.join(pending_files)}", flush=True)

    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=google_api_key)
    db = Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    for filename in pending_files:
        path = os.path.join(SOURCE_DIR, filename)
        entry = manifest.get(filename, {})
        chunks_done = entry.get("chunks_done", 0)

        print(f"Loading {filename}...", flush=True)
        pages = PyPDFLoader(path).load()
        chunks = text_splitter.split_documents(pages)
        print(f"  {len(pages)} pages -> {len(chunks)} chunks", flush=True)

        if chunks_done:
            print(f"  Resuming from chunk {chunks_done} (already indexed in an earlier run)", flush=True)

        for i in range(chunks_done, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            add_batch_with_retry(db, batch)
            chunks_done = min(i + BATCH_SIZE, len(chunks))
            print(f"  Indexed chunks {i} to {chunks_done} of {len(chunks)}", flush=True)

            # Checkpoint after every batch, not just at file end, so a rate-limit
            # failure loses at most one batch of progress instead of the whole file.
            manifest[filename] = {
                "pages": len(pages),
                "total_chunks": len(chunks),
                "chunks_done": chunks_done,
                "complete": chunks_done >= len(chunks),
            }
            save_manifest(manifest)

            if chunks_done < len(chunks):
                time.sleep(PACE_DELAY_SECONDS)

        print(f"Done with {filename}.", flush=True)

    print("All pending files ingested successfully.", flush=True)


if __name__ == "__main__":
    main()
