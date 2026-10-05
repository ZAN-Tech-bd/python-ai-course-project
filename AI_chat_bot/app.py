"""Bilingual (Bangla + English) RAG chatbot with an optional Gemini
refinement step, built with Streamlit.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import json

import streamlit as st

import config_store
from gemini_refine import refine_answer
from rag_engine import RagEngine, detect_language

st.set_page_config(page_title="Zantech AI Chat", page_icon="🤖", layout="wide")

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .main { background: radial-gradient(1200px 600px at 10% -10%, #1e293b 0%, #0f172a 60%, #0f172a 100%); }
    .block-container { padding-top: 2rem; max-width: 900px; }
    #MainMenu, footer { visibility: hidden; }

    .app-header {
        display: flex; align-items: center; gap: .75rem;
        padding: 1.1rem 1.4rem; margin-bottom: 1.2rem;
        border-radius: 16px;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
        box-shadow: 0 8px 30px rgba(99,102,241,.35);
    }
    .app-header h1 { color: #fff; font-size: 1.5rem; margin: 0; font-weight: 700; }
    .app-header p { color: rgba(255,255,255,.9); margin: 0; font-size: .85rem; }

    div[data-testid="stChatMessage"] {
        border-radius: 14px; padding: .3rem .5rem; margin-bottom: .4rem;
    }

    .src-pill {
        display: inline-block; padding: 2px 10px; margin: 2px 4px 2px 0;
        border-radius: 999px; background: rgba(99,102,241,.15);
        color: #a5b4fc; font-size: .72rem; border: 1px solid rgba(99,102,241,.3);
    }
    .status-badge {
        padding: 3px 10px; border-radius: 999px; font-size: .75rem; font-weight: 600;
    }
    .status-on { background: rgba(34,197,94,.15); color: #4ade80; border: 1px solid rgba(34,197,94,.35); }
    .status-off { background: rgba(148,163,184,.15); color: #94a3b8; border: 1px solid rgba(148,163,184,.35); }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="app-header">
        <div style="font-size:2.2rem;">🤖</div>
        <div>
            <h1>Zantech AI Chat</h1>
            <p>Bangla &amp; English · JSON knowledge base · Retrieval-augmented answers</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
if "engine" not in st.session_state:
    st.session_state.engine = RagEngine()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_key" not in st.session_state:
    st.session_state.api_key = config_store.load_api_key()

engine: RagEngine = st.session_state.engine

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.subheader("⚙️ Gemini refinement")
    st.caption("Optional. Adds fluent, natural phrasing on top of retrieved data.")

    key_input = st.text_input(
        "Gemini API key",
        value=st.session_state.api_key,
        type="password",
        placeholder="AIza...",
        help="Get a free key at https://aistudio.google.com/apikey",
    )
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Save key", use_container_width=True):
            st.session_state.api_key = key_input.strip()
            config_store.save_api_key(st.session_state.api_key)
            st.success("Saved")
    with col_b:
        if st.button("Clear key", use_container_width=True):
            st.session_state.api_key = ""
            config_store.clear_api_key()
            st.rerun()

    if st.session_state.api_key:
        st.markdown('<span class="status-badge status-on">● Gemini enabled</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-badge status-off">○ Retrieval-only mode</span>', unsafe_allow_html=True)

    st.divider()
    st.subheader("📚 Knowledge base")
    st.caption(f"{len(engine.entries)} entries loaded")

    with st.expander("➕ Add new entry", expanded=False):
        with st.form("add_entry_form", clear_on_submit=True):
            title = st.text_input("Title")
            content = st.text_area("Content / Answer", height=120)
            tags = st.text_input("Tags (comma separated)")
            submitted = st.form_submit_button("Add to knowledge base")
            if submitted:
                if content.strip():
                    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
                    engine.add_entry(title or "Untitled", content, tag_list)
                    st.success("Entry added")
                    st.rerun()
                else:
                    st.warning("Content can't be empty")

    with st.expander("📄 View / delete entries", expanded=False):
        for e in list(engine.entries):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"**{e.get('title') or 'Untitled'}**")
                st.caption(e.get("content", "")[:120] + ("…" if len(e.get("content", "")) > 120 else ""))
            with c2:
                if st.button("🗑️", key=f"del_{e['id']}"):
                    engine.delete_entry(e["id"])
                    st.rerun()

    with st.expander("⇅ Import / export JSON", expanded=False):
        uploaded = st.file_uploader("Upload JSON (list of {title, content, tags})", type=["json"])
        if uploaded is not None:
            try:
                data = json.loads(uploaded.read().decode("utf-8"))
                mode = st.radio("Import mode", ["Merge with existing", "Replace all"], horizontal=True)
                if st.button("Import"):
                    if mode == "Replace all":
                        engine.replace_all(data)
                    else:
                        engine.merge(data)
                    st.success("Imported")
                    st.rerun()
            except (json.JSONDecodeError, TypeError) as ex:
                st.error(f"Invalid JSON: {ex}")

        st.download_button(
            "⬇ Download current knowledge_base.json",
            data=json.dumps(engine.entries, ensure_ascii=False, indent=2),
            file_name="knowledge_base.json",
            mime="application/json",
            use_container_width=True,
        )

    st.divider()
    if st.button("🧹 Clear chat history", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            pills = "".join(f'<span class="src-pill">{s}</span>' for s in msg["sources"])
            st.markdown(pills, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Answering logic
# ---------------------------------------------------------------------------

def answer_question(question: str) -> tuple[str, list[str]]:
    lang = detect_language(question)
    results = engine.search(question, top_k=3)
    sources = [e.get("title") or "Untitled" for e, _ in results]

    if st.session_state.api_key:
        try:
            text = refine_answer(st.session_state.api_key, question, results)
            return text, sources
        except Exception as ex:  # noqa: BLE001 - surface any Gemini/network error to the user
            fallback_note = (
                f"⚠️ Gemini refinement failed ({ex}). Showing raw retrieval instead.\n\n"
                if lang == "en"
                else f"⚠️ জেমিনি রিফাইনমেন্ট ব্যর্থ হয়েছে ({ex})। কাঁচা তথ্য দেখানো হচ্ছে।\n\n"
            )
            return fallback_note + _plain_answer(results, lang), sources

    return _plain_answer(results, lang), sources


def _plain_answer(results, lang: str) -> str:
    if not results:
        return (
            "I couldn't find anything relevant in the knowledge base yet. "
            "Try adding some data from the sidebar."
            if lang == "en"
            else "নলেজ বেসে প্রাসঙ্গিক কিছু পাওয়া যায়নি। সাইডবার থেকে কিছু তথ্য যোগ করুন।"
        )
    header = "Here's what I found:" if lang == "en" else "যা পাওয়া গেছে:"
    parts = [header]
    for entry, score in results:
        parts.append(f"\n**{entry.get('title') or 'Untitled'}**\n{entry.get('content', '')}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
placeholder = "Ask me anything in Bangla or English…"
question = st.chat_input(placeholder)

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            answer, sources = answer_question(question)
        st.markdown(answer)
        if sources:
            pills = "".join(f'<span class="src-pill">{s}</span>' for s in sources)
            st.markdown(pills, unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
