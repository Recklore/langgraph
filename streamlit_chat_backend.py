from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import BaseMessage

from typing import TypedDict, Annotated
from dotenv import load_dotenv
import sqlite3

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash")
search_tool = DuckDuckGoSearchRun(region="us-en")
llm = llm.bind_tools([search_tool])

class Chatstate(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: Chatstate):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

from langgraph.prebuilt import ToolNode

def handle_tool_error(error):
    return (
        "The web search tool is currently unavailable. "
        "Please answer using your existing knowledge or ask the user to try again."
    )

tool_node = ToolNode(
    [search_tool],
    handle_tool_errors=handle_tool_error,
)

conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)

checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(Chatstate)

graph.add_node("chat_node", chat_node)
graph.add_node("tool_node", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges(
    "chat_node",
    tools_condition,
    {
        "tools": "tool_node",
        END: END,
    },
)
graph.add_edge("tool_node", "chat_node")

chatbot = graph.compile(checkpointer=checkpointer)


def retrieve_threads():
    threads = set()
    for checkpoint in checkpointer.list(None):
        threads.add(checkpoint.config["configurable"]["thread_id"])

    return list(threads)