import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from streamlit_chat_backend import chatbot, retrieve_threads
import uuid

# Utils
def generate_thread_id():
    thread_id = uuid.uuid4()
    st.session_state["thread_list"].append(thread_id)
    return thread_id

def message_to_text(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for block in content:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    text_parts.append(text)

        return "".join(text_parts)

    return ""

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
    st.session_state["thread_list"] = retrieve_threads()

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()


# Configs
CONFIG = {"configurable": {"thread_id": st.session_state["thread_id"]},
          "metadata": {"thread_id": st.session_state["thread_id"]},
          "run_name": "chat_turn"}


# UI

st.sidebar.title("Chatbot")

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
            elif isinstance(msg, AIMessage):
                role = "assistant"
            else:
                continue

            content = message_to_text(msg.content)

            if content:
                temp_messages.append(
                    {"role": role, "message": content}
                )

        st.session_state["message_history"] = temp_messages

for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["message"])


user_input = st.chat_input("type here")


if user_input:
    st.session_state["message_history"].append(
        {"role": "user", "message": user_input}
    )

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        status_box = [None]

        def ai_only_stream():
            for message_chunk, _ in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                if isinstance(message_chunk, ToolMessage):
                    if status_box[0] is None:
                        status_box[0] = st.status(
                            f"Using `{message_chunk.name or 'tool'}`...",
                            expanded=True,
                        )
                    continue

                if isinstance(message_chunk, AIMessage):
                    content = message_chunk.content

                    if isinstance(content, str):
                        if content:
                            yield content

                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict):
                                text = block.get("text", "")
                                if text:
                                    yield text

        ai_message = st.write_stream(ai_only_stream())

        if status_box[0] is not None:
            status_box[0].update(
                label="Tool finished",
                state="complete",
                expanded=False,
            )

    if (
        not st.session_state["message_history"]
        or st.session_state["message_history"][-1]["message"] != ai_message
    ):
        st.session_state["message_history"].append(
            {"role": "assistant", "message": ai_message}
        )