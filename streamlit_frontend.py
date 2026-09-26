import streamlit as st
from langchain_core.messages import HumanMessage
from streamlit_chat_backend import chatbot
import uuid

# Utils
def generate_thread_id():
    thread_id = uuid.uuid4()
    st.session_state["thread_list"].append(thread_id)
    return thread_id


def resest_chat():
    st.session_state["thread_id"] = generate_thread_id()
    st.session_state["message_history"] = []

def load_chat(thread_id):
    st.session_state["thread_id"] = thread_id
    state = chatbot.get_state(
        config={"configurable": {"thread_id": thread_id}}
    )
    return state.values.get("messages", [])

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


# Session state
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_list" not in st.session_state:
    st.session_state["thread_list"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()


# Configs
CONFIG = {"configurable": {"thread_id": st.session_state["thread_id"]}}


# UI

st.sidebar.title("Regular chatbot")

if st.sidebar.button("new chat"):
    resest_chat()

st.sidebar.header("My conversations")
for thread_id in st.session_state["thread_list"][::-1]:
    if st.sidebar.button(thread_id):
        messages = load_chat(thread_id)

        temp_messages = []

        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            else:
                role = "assistant"

            temp_messages.append({"role": role, "message": msg.content})
        st.session_state["message_history"] = temp_messages

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
