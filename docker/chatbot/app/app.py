import os
import sys
import json
import time
import openai
import requests
from glob import glob
from typing import Any, Dict, List, Optional
from langchain.agents import load_tools
from langchain.tools import AIPluginTool
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.callbacks.base import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.schema import AgentAction, AgentFinish, LLMResult
from langchain.callbacks.tracers import LangChainTracer
from langchain.utilities import GoogleSearchAPIWrapper
from langchain.agents import initialize_agent, Tool
from http.server import BaseHTTPRequestHandler, HTTPServer
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

PORT = 5000
DB_DIR = os.environ.get("DB_DIR", "/data/")

system_template = '''Use the following pieces of context to answer the users question. 
If you don't know the answer, just say that you don't know, don't try to make up an answer.

Context: """
{context}
"""
'''
messages = [
    SystemMessagePromptTemplate.from_template(system_template),
    HumanMessagePromptTemplate.from_template("{question}"),
]
BASE_PROMPT = ChatPromptTemplate.from_messages(messages)

PREFIX = """\n\nHuman: Answer the following questions as best you can. You have access to the following tools:"""
SUFFIX = '''CHAT HISTORY: """
{chat_history}
"""
Question: """
{input}
"""
Thought: """
{agent_scratchpad}
"""
'''

class StreamingLLMCallbackHandler(StreamingStdOutCallbackHandler):
    """Callback handler for streaming. Only works with LLMs that support streaming."""

    def __init__(self, sock):
        self.sock = sock

    def on_llm_new_token(self, token: str, **kwargs: Any) -> Any:
        data = {
            "id": "chatcmpl",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-3.5-turbo",
            "choices": [{"delta": {"content": token}, "index": 0, "finish_reason": None}],
        }
        self.sock.wfile.write(b"data: " + json.dumps(data).encode() + b"\n\n")
        self.sock.wfile.flush()

    def on_tool_end(
        self,
        output: str,
        observation_prefix: Optional[str] = None,
        llm_prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """If not the final action, print out observation."""
        data = {
            "id": "chatcmpl",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-3.5-turbo",
            "choices": [
                {"delta": {"content": f"{observation_prefix}{output} {llm_prefix}"}, "index": 0, "finish_reason": None}
            ],
        }
        self.sock.wfile.write(b"data: " + json.dumps(data).encode() + b"\n\n")
        self.sock.wfile.flush()

    def on_llm_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        data = {
            "id": "chatcmpl",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-3.5-turbo",
            "choices": [{"delta": {"content": "\n\n"}, "index": 0, "finish_reason": None}],
        }
        self.sock.wfile.write(b"data: " + json.dumps(data).encode() + b"\n\n")
        self.sock.wfile.flush()


# Agent VectorDB Question Answering
def create_db_qa(sock, api_key, temperature=0.5):
    manager = CallbackManager([StreamingLLMCallbackHandler(sock)])
    tracer = LangChainTracer()
    tracer.load_default_session()
    manager.add_handler(tracer)
    streaming_llm = ChatOpenAI(
        streaming=True,
        model_name="gpt-3.5-turbo",
        callback_manager=manager,
        temperature=temperature,
        openai_api_key=api_key,
        verbose=True,
    )

    embedding = OpenAIEmbeddings(openai_api_key=api_key)
    #tools = []
    tools = load_tools(["terminal", "requests"], llm=streaming_llm)
    PLUGIN_TOOL = AIPluginTool.from_plugin_url("http://plugin:5000/openai")
    tools.append(PLUGIN_TOOL)

    if os.environ.get("GOOGLE_CSE_ID") and os.environ.get("GOOGLE_API_KEY"):
        google_search = GoogleSearchAPIWrapper(k=5)
        tools.append(Tool(name="Google Search", func=google_search.run, description="最新の話題について答える場合に利用することができます。"))

    # DB_DIRのディレクトリに保存されたデータベースを読み込む
    for target in glob(DB_DIR + "/*"):
        if os.path.isdir(target):
            vectorstore = Chroma(persist_directory=target, embedding_function=embedding)
            chain_type_kwargs = {"prompt": BASE_PROMPT}
            chain = RetrievalQA.from_chain_type(
                llm=streaming_llm,
                chain_type="stuff",
                callback_manager=manager,
                retriever=vectorstore.as_retriever(),
                chain_type_kwargs=chain_type_kwargs,
            )
            title = os.path.basename(target)
            tools.append(
                Tool(
                    name=f"{title} qa database",
                    func=chain.run,
                    description=f"useful for when you need to answer questions about {title}. Input should be a fully formed question.",
                ),
            )
    # agent = "conversational-react-description"
    agent = os.environ.get("AGENT", "chat-zero-shot-react-description")
    memory = ConversationBufferWindowMemory(
        memory_key="chat_history", 
        # return_messages=True,
        input_key="input",
        output_key="output",
        ai_prefix="AI",
        human_prefix="User",
    )
    return initialize_agent(
        tools,
        streaming_llm,
        agent=agent,
        max_iterations=5,
        callback_manager=manager,
        agent_kwargs={
            "input_variables": ["input", "agent_scratchpad", "chat_history"],
            "prefix": PREFIX,
            "suffix": SUFFIX,
        },
        memory=memory
    )


class ApiHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/v1/models":
            headers = {"Authorization": self.headers.get("Authorization"), "Content-Type": "application/json"}
            r = requests.get("https://api.openai.com/v1/models", headers=headers)
            resp = r.content
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("content-length", len(resp))
            self.send_header("openai-organization", self.headers.get("openai-organization", ""))
            self.send_header("openai-version", self.headers.get("openai-version", ""))
            self.send_header("openai-processing-ms", int(self.headers.get("processing-ms", 0)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp)

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            openai_api_key = self.headers.get("Authorization").replace("Bearer ", "")
            content_len = int(self.headers.get("content-length"))
            post_body = self.rfile.read(content_len).decode("utf-8")
            post_data = json.loads(post_body)

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # 質問の取り出し
            question = post_data["messages"][-1]["content"]
            temperature = float(post_data.get("temperature", 0.5))
            agent = create_db_qa(self, openai_api_key, temperature=temperature)
            try:
                agent.run(question)
            except Exception as e:
                data = {
                    "id": "chatcmpl",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-3.5-turbo",
                    "choices": [{"delta": {"content": str(e)}, "index": 0, "finish_reason": None}],
                }
                self.wfile.write(b"data: " + json.dumps(data).encode() + b"\n\n")
                self.wfile.flush()

            self.wfile.write(b"data: [DONE]\n\n")


if __name__ == "__main__":
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, ApiHandler)
    httpd.serve_forever()
