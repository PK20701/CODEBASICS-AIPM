"""ShopMate chat UI. Run from this folder: streamlit run app.py"""

import streamlit as st

import db
from agent import Session, run_turn
from config import ServiceBusy

st.set_page_config(page_title="ShopMate", page_icon="🛒")
st.title("🛒 ShopMate")
st.caption("Tell me what you want, or attach a photo of it.")

db.ensure_preferences_table()

if "session" not in st.session_state:
    st.session_state.session = Session()
    st.session_state.transcript = []  # [{"role", "text", "image"}]

for turn in st.session_state.transcript:
    with st.chat_message(turn["role"]):
        if turn.get("image"):
            st.image(turn["image"], width=160)
        st.text(turn["text"])

prompt = st.chat_input("e.g. organic honey under $20", accept_file=True, file_type=["png", "jpg", "jpeg", "webp"])

if prompt:
    text = prompt.text or ""
    image = prompt.files[0] if prompt.files else None
    image_bytes = image.getvalue() if image else None

    st.session_state.transcript.append({"role": "user", "text": text or "(photo)", "image": image_bytes})
    with st.chat_message("user"):
        if image_bytes:
            st.image(image_bytes, width=160)
        st.text(text or "(photo)")

    with st.chat_message("assistant"):
        with st.spinner("Looking..."):
            try:
                reply = run_turn(st.session_state.session, text, image_bytes, image.type if image else None).reply
            except ServiceBusy as exc:
                reply = str(exc)
            except Exception as exc:  # show the problem instead of a blank screen
                reply = f"Something went wrong: {exc}"
        st.text(reply)

    st.session_state.transcript.append({"role": "assistant", "text": reply})
