import streamlit as st
from langchain_core.messages import HumanMessage
from streamlit_chat_backend import chatbot



CONFIG = {"configurable": {"thread_id": "thread-1"}}

def stream_text():
    for message_chunk, _ in chatbot.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=CONFIG,
        stream_mode="messages",
    ):
        content = message_chunk.content

        if isinstance(content, str):
            if content:
                yield content
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text")
                    if text:
                        yield text

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.text(message["message"])


user_input = st.chat_input("type here")


if user_input:

    st.session_state["message_history"].append({"role": "user", "message": user_input})
    with st.chat_message("user"):
        st.text(user_input)

    with st.chat_message("assistant"):
        ai_message = st.write_stream(stream_text())
        
    st.session_state["message_history"].append(
        {"role": "assistant", "message": ai_message}
    )
