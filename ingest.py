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
# The free-tier Gemini embedding quota is ~100 requests/minute and the API issues
# roughly one request per chunk, so pace batches to stay under that instead of
# racing ahead and getting 429'd.
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
                    f"before retry ({attempt}/{MAX_RATE_LIMIT_RETRIES})..."
                )
                time.sleep(RATE_LIMIT_RETRY_DELAY_SECONDS)
                continue
            raise
    raise RuntimeError("Gave up on a batch after repeated rate-limit errors")


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
    new_files = [f for f in pdf_files if f not in manifest]

    if not new_files:
        print("Nothing to do - every PDF in Document_Source has already been ingested.")
        print(f"Already ingested: {', '.join(pdf_files) if pdf_files else '(none found)'}")
        return

    print(f"Found {len(new_files)} new file(s) to ingest: {', '.join(new_files)}")

    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=google_api_key)
    db = Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    for filename in new_files:
        path = os.path.join(SOURCE_DIR, filename)
        print(f"Loading {filename}...")
        pages = PyPDFLoader(path).load()
        chunks = text_splitter.split_documents(pages)
        print(f"  {len(pages)} pages -> {len(chunks)} chunks")

        # Small batches so a rate-limit hiccup partway through doesn't lose earlier progress
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            add_batch_with_retry(db, batch)
            print(f"  Indexed chunks {i} to {min(i + BATCH_SIZE, len(chunks))} of {len(chunks)}")
            if i + BATCH_SIZE < len(chunks):
                time.sleep(PACE_DELAY_SECONDS)

        # Mark this file done only after all its chunks are indexed, so a crash mid-file
        # re-ingests that file next run instead of silently skipping the rest of it
        manifest[filename] = {"pages": len(pages), "chunks": len(chunks)}
        save_manifest(manifest)
        print(f"Done with {filename}, progress saved.")

    print("All new files ingested successfully.")


if __name__ == "__main__":
    main()
