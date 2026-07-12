import streamlit as st
import requests

API_URL = "http://localhost:5000/question"
FEEDBACK_URL = "http://localhost:5000/feedback"

st.set_page_config(page_title="NHS Patient Assistant", page_icon="🩺")

st.title("🩺 NHS Patient Assistant")
st.caption("⚠️ This assistant uses AI and is not a substitute for professional medical advice.")

# ---------------- SESSION STATE ----------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- DISPLAY CHAT HISTORY ----------------

for i, msg in enumerate(st.session_state.messages):

    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Show feedback buttons for assistant replies
        if msg["role"] == "assistant":

            conversation_id = msg["conversation_id"]

            col1, col2 = st.columns(2)

            with col1:
                if st.button("👍 Yes", key=f"{conversation_id}_up"):

                    res = requests.post(
                        FEEDBACK_URL,
                        json={
                            "conversation_id": conversation_id,
                            "feedback": 1,
                        },
                    )

                    if res.status_code == 200:
                        st.success("Thanks for your feedback!")
                    else:
                        st.error("Failed to save feedback")
                        st.write(res.text)

            with col2:
                if st.button("👎 No", key=f"{conversation_id}_down"):

                    res = requests.post(
                        FEEDBACK_URL,
                        json={
                            "conversation_id": conversation_id,
                            "feedback": -1,
                        },
                    )

                    if res.status_code == 200:
                        st.success("Thanks for your feedback!")
                    else:
                        st.error("Failed to save feedback")
                        st.write(res.text)

# ---------------- CHAT INPUT ----------------

prompt = st.chat_input("Ask a health question...")

if prompt:

    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    # Call backend
    res = requests.post(API_URL, json={"question": prompt})

    if res.status_code != 200:
        st.error("API error")
        st.write(res.text)
        st.stop()

    data = res.json()

    answer = data["answer"]
    conversation_id = data["conversation_id"]

    # Display assistant response
    with st.chat_message("assistant"):
        st.markdown(answer)

    # Save assistant message INCLUDING conversation_id
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "conversation_id": conversation_id,
        }
    )

    # Rerun so the new assistant message (with feedback buttons)
    # is rendered from the history loop.
    st.rerun()
	
	