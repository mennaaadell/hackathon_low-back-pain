# MedGuide

## Run

1. In Supabase SQL Editor, run (or rerun) `supabase_schema.sql`.
2. Copy `.env.example` to `.env` and set the project URL and service-role key. Never expose the service-role key in frontend code.
3. Install dependencies: `pip install -r requirements.txt`.
4. Start the API from this folder: `uvicorn main:app --reload --port 8000`.
5. Serve this folder with a static server, for example `python -m http.server 5500`.

The API uses Supabase Auth. Enable email/password in Supabase Authentication. Index the included guideline with `python ingest_guideline.py low-back-pain.pdf` after installing the requirements. The backend then retrieves matching page chunks from `guideline_chunks` and returns the answer, page, section, chunk number, and normalized confidence. Greetings are answered conversationally and saved like every other message.
