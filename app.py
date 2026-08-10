import base64
import io
import json
import os
import re
import wave
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Header, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

SENTENCE_END_RE = re.compile(r"[.!?]+(?:\s+|$)")

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY environment variable is required")

ACCESS_CODE = os.environ.get("ACCESS_CODE")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL") or "gemini-flash-latest"
TTS_MODEL = os.environ.get("TTS_MODEL") or "gemini-2.5-flash-preview-tts"
TTS_VOICE = os.environ.get("TTS_VOICE") or "Kore"

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


def synthesize_speech_wav_base64(text):
    """Generate natural-sounding speech via Gemini TTS, wrapped as a playable WAV.
    Returns None on failure so the frontend can fall back to on-device TTS instead
    of breaking the whole answer over what's a nice-to-have.
    """
    try:
        tts_response = client.models.generate_content(
            model=TTS_MODEL,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=TTS_VOICE)
                    )
                ),
            ),
        )
        part = tts_response.candidates[0].content.parts[0]
        pcm_bytes = part.inline_data.data

        sample_rate = 24000
        for piece in (part.inline_data.mime_type or "").split(";"):
            if piece.strip().startswith("rate="):
                sample_rate = int(piece.strip().split("=")[1])

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_bytes)

        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


@app.get("/api/health")
def health():
    return {"status": "ok"}


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

    def event_stream():
        # Stream the answer sentence-by-sentence and synthesize + emit each sentence's
        # audio as soon as it's complete, instead of waiting for the entire answer to be
        # written and the entire reply synthesized before any sound can play. This is
        # what actually moves the needle on perceived latency, since answers are only
        # ever 1-3 sentences but each Gemini round trip still takes real time.
        yield json.dumps({"type": "transcript", "text": transcript}) + "\n"

        buffer = ""
        try:
            for chunk in client.models.generate_content_stream(model=GEMINI_MODEL, contents=prompt):
                buffer += chunk.text or ""
                while True:
                    match = SENTENCE_END_RE.search(buffer)
                    if not match:
                        break
                    sentence = buffer[: match.end()].strip()
                    buffer = buffer[match.end() :]
                    if sentence:
                        audio_b64 = synthesize_speech_wav_base64(sentence)
                        yield json.dumps({"type": "sentence", "text": sentence, "audio_base64": audio_b64}) + "\n"

            leftover = buffer.strip()
            if leftover:
                audio_b64 = synthesize_speech_wav_base64(leftover)
                yield json.dumps({"type": "sentence", "text": leftover, "audio_base64": audio_b64}) + "\n"

            yield json.dumps({"type": "done"}) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "detail": str(e)}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


app.mount("/", StaticFiles(directory="web", html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
