import os
import re
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from supabase import Client, create_client
from dotenv import load_dotenv

load_dotenv(override=True)

app = FastAPI(title="MedGuide API", version="1.0.0")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")
FRONTEND_ORIGINS = [origin.strip() for origin in FRONTEND_ORIGIN.split(",") if origin.strip()]
supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
    else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS if FRONTEND_ORIGIN != "*" else ["*"],
    allow_credentials=FRONTEND_ORIGIN != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserInput(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


class SignUpInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = None
    age: int | None = Field(default=None, ge=13, le=120)
    gender: str | None = None


class LoginInput(BaseModel):
    email: EmailStr
    password: str


GREETING_PATTERN = re.compile(
    r"^\s*(hi|hello|hey|hiya|good morning|good afternoon|good evening|greetings)[!.,\s]*$",
    re.IGNORECASE,
)
QUESTION_WORDS = {
    "are", "can", "could", "does", "how", "is", "may", "should", "what",
    "when", "where", "which", "why", "recommended", "recommend", "managing",
    "about", "an", "and", "a", "for", "from", "in", "on", "or", "the", "to",
    "with", "without",
}


def is_greeting(message: str) -> bool:
    return bool(GREETING_PATTERN.match(message))


def grounded_answer(question: str, chunks: list[dict[str, Any]]) -> str:
    query_terms = {
        term.lower()
        for term in re.findall(r"[a-zA-Z]{3,}", question)
        if term.lower() not in {"what", "when", "where", "which", "does", "about", "with", "the"}
    }
    candidates: list[tuple[int, str]] = []
    for chunk in chunks:
        for sentence in re.split(r"(?<=[.!?])\s+", chunk.get("content", "")):
            clean_sentence = " ".join(sentence.split()).strip()
            if len(clean_sentence) < 25:
                continue
            overlap = len(query_terms & {term.lower() for term in re.findall(r"[a-zA-Z]{3,}", clean_sentence)})
            candidates.append((overlap, clean_sentence))
    candidates.sort(key=lambda item: item[0], reverse=True)
    selected = [sentence for score, sentence in candidates[:4] if score > 0]
    if not selected:
        selected = [" ".join(chunk.get("content", "").split())[:500] for chunk in chunks[:2]]
    return "According to the indexed NICE guideline:\n\n" + " ".join(selected)


def normalize_retrieval(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for index, chunk in enumerate(chunks, start=1):
        item = dict(chunk)
        item["section"] = item.get("section") or "General"
        item["chunk_number"] = item.get("chunk_number") or index
        item["confidence"] = item.get("confidence", item.get("rank", 0)) or 0
        normalized.append(item)
    return normalized


def retrieve_chunks(client: Client, question: str) -> list[dict[str, Any]]:
    exact = client.rpc("search_guideline_chunks", {"query_text": question, "match_count": 5}).execute().data or []
    if exact:
        return normalize_retrieval(exact)

    keywords = [
        term for term in re.findall(r"[a-zA-Z]{3,}", question.lower())
        if term not in QUESTION_WORDS
    ]
    keyword_query = " ".join(keywords)
    candidates = [keyword_query]
    candidates.extend(" ".join(keywords[index:index + 2]) for index in range(len(keywords) - 1))
    merged: dict[str, dict[str, Any]] = {}
    for candidate in candidates[:10]:
        if not candidate:
            continue
        results = client.rpc("search_guideline_chunks", {"query_text": candidate, "match_count": 5}).execute().data or []
        for result in results:
            merged[result["id"]] = result
        if len(merged) >= 5:
            break
    return normalize_retrieval(list(merged.values()))[:5]


def get_supabase() -> Client:
    if supabase is None:
        raise HTTPException(status_code=500, detail="Supabase is not configured")
    return supabase


def require_user(
    authorization: str | None = Header(default=None),
    client: Client = Depends(get_supabase),
) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="A valid access token is required")
    try:
        user = client.auth.get_user(authorization.split(" ", 1)[1]).user
    except Exception as error:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from error
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    return {"id": user.id, "email": user.email or ""}


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "MedGuide API is running",
        "supabase_configured": supabase is not None,
    }


@app.post("/api/auth/signup")
async def signup(data: SignUpInput, client: Client = Depends(get_supabase)):
    try:
        result = client.auth.sign_up({"email": data.email, "password": data.password})
        user = result.user
        if user is None:
            raise HTTPException(status_code=400, detail="Could not create account")
        client.table("profiles").upsert({
            "id": user.id,
            "name": data.name,
            "phone": data.phone,
            "age": data.age,
            "gender": data.gender,
        }).execute()
        return {
            "user": {"id": user.id, "name": data.name, "email": user.email},
            "access_token": result.session.access_token if result.session else None,
            "email_confirmation_required": result.session is None,
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/auth/login")
async def login(data: LoginInput, client: Client = Depends(get_supabase)):
    try:
        result = client.auth.sign_in_with_password({"email": data.email, "password": data.password})
        if result.user is None or result.session is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        profile = client.table("profiles").select("name").eq("id", result.user.id).maybe_single().execute()
        name = (profile.data or {}).get("name") or (result.user.email or "User").split("@")[0]
        return {"access_token": result.session.access_token, "user": {"id": result.user.id, "name": name, "email": result.user.email}}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=401, detail="Invalid email or password") from error


@app.post("/api/chat")
async def chat_endpoint(
    data: UserInput,
    user: dict[str, Any] = Depends(require_user),
    client: Client = Depends(get_supabase),
):
    conversation_id = data.conversation_id
    if conversation_id:
        existing = client.table("conversations").select("id").eq("id", conversation_id).eq("user_id", user["id"]).maybe_single().execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        created = client.table("conversations").insert({"user_id": user["id"], "title": data.message[:80]}).execute()
        conversation_id = created.data[0]["id"]

    client.table("messages").insert({"conversation_id": conversation_id, "user_id": user["id"], "role": "user", "content": data.message}).execute()
    if is_greeting(data.message):
        answer = "Hello! I am MedGuide AI. Ask me a question about low back pain or sciatica, and I will search the NICE guideline."
        retrieved = []
    else:
        retrieved = retrieve_chunks(client, data.message)
        answer = grounded_answer(data.message, retrieved) if retrieved else "I could not find a relevant passage in the indexed PDF. Please try another question or consult a qualified healthcare professional."
    client.table("messages").insert({"conversation_id": conversation_id, "user_id": user["id"], "role": "assistant", "content": answer, "sources": retrieved}).execute()
    return {
        "reply": answer,
        "conversation_id": conversation_id,
        "sources": retrieved,
        "retrieval": retrieved,
        "confidence": retrieved[0].get("confidence", 0) if retrieved else 0,
    }


@app.get("/api/conversations")
async def conversations(user: dict[str, Any] = Depends(require_user), client: Client = Depends(get_supabase)):
    result = client.table("conversations").select("id,title,created_at,updated_at").eq("user_id", user["id"]).order("updated_at", desc=True).execute()
    return {"conversations": result.data or []}


@app.get("/api/conversations/{conversation_id}/messages")
async def conversation_messages(
    conversation_id: str,
    user: dict[str, Any] = Depends(require_user),
    client: Client = Depends(get_supabase),
):
    conversation = (
        client.table("conversations")
        .select("id")
        .eq("id", conversation_id)
        .eq("user_id", user["id"])
        .maybe_single()
        .execute()
    )
    if not conversation.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = (
        client.table("messages")
        .select("id,role,content,sources,created_at")
        .eq("conversation_id", conversation_id)
        .eq("user_id", user["id"])
        .order("created_at")
        .execute()
    )
    return {"messages": result.data or []}
