# Zantech AI Chat

A bilingual (Bangla + English) chatbot that answers questions using a
JSON knowledge base you control, with an optional Gemini API step to
make answers more fluent.

## How it works

1. **Knowledge base** — `data/knowledge_base.json` holds entries of the
   form `{ "title": "...", "content": "...", "tags": [...] }`. Add,
   edit, import, or export entries from the sidebar in the app.
2. **Retrieval (RAG)** — `rag_engine.py` builds a character n-gram
   TF-IDF index over the knowledge base and retrieves the most relevant
   entries for each question (works for both Bangla and English text).
3. **Refinement (optional)** — if you paste a Gemini API key in the
   sidebar, `gemini_refine.py` sends the retrieved entries + your
   question to Gemini so it can rewrite the answer fluently in whichever
   language you asked in. Without a key, the app still answers directly
   from the retrieved entries.

## Setup

```bash
cd "AI chat bot"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

## Get a Gemini API key

Free key: https://aistudio.google.com/apikey — paste it into the
sidebar and click **Save key**. It's stored locally in
`config_local.json` (gitignored) so you don't have to repaste it every
run. Click **Clear key** to remove it.

## Adding data

Use the **Knowledge base → Add new entry** form in the sidebar, or
upload a JSON file (a list of `{title, content, tags}` objects) via
**Import / export JSON**. You can also edit `data/knowledge_base.json`
directly.
