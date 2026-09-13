from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.messages import BaseMessage

from typing import TypedDict, Annotated
from dotenv import load_dotenv

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash")


class Chatstate(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: Chatstate):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


checkpointer = InMemorySaver()

graph = StateGraph(Chatstate)

graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)