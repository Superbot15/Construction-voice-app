import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Header, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY environment variable is required")

ACCESS_CODE = os.environ.get("ACCESS_CODE")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL") or "gemini-flash-latest"

client = genai.Client(api_key=GOOGLE_API_KEY)

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GOOGLE_API_KEY)
db = Chroma(persist_directory="chroma_db", embedding_function=embeddings)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def check_access(x_access_code: Optional[str]):
    if ACCESS_CODE and x_access_code != ACCESS_CODE:
        raise HTTPException(status_code=401, detail="Invalid access code")


@app.post("/api/ask")
async def ask(audio: UploadFile = File(...), x_access_code: Optional[str] = Header(default=None)):
    check_access(x_access_code)

    audio_bytes = await audio.read()
    mime_type = audio.content_type or "audio/webm"

    transcript_response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            "Transcribe the spoken words in this audio clip exactly. Reply with only the transcript text, nothing else.",
        ],
    )
    transcript = (transcript_response.text or "").strip()

    if not transcript:
        raise HTTPException(status_code=422, detail="Could not understand audio, please try again")

    search_results = db.similarity_search(transcript, k=3)
    context_text = "\n\n".join(doc.page_content for doc in search_results)

    prompt = f"""
    You are a construction site assistant. Answer the user's question using ONLY this specification context:
    {context_text}

    Keep your answer very short (1-3 sentences) so it can be easily read out loud on a noisy construction site.
    If the context does not contain the answer, say "I cannot find that requirement in the specifications."

    Question: {transcript}
    """

    answer_response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    reply = (answer_response.text or "").strip()

    return {"transcript": transcript, "reply": reply}


app.mount("/", StaticFiles(directory="web", html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
