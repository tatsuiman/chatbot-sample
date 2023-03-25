import os
import sys
import json
import time
from glob import glob
from typing import Any, Dict, List
from langchain.agents import load_tools
from langchain.chat_models import ChatOpenAI
from langchain.callbacks.base import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import VectorDBQA
from langchain.agents import initialize_agent, Tool
from http.server import BaseHTTPRequestHandler, HTTPServer
from langchain.memory import ConversationBufferWindowMemory

PORT = 5000
DB_DIR = os.environ.get("DB_DIR", "/data/")


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
def create_db_qa(sock, temperature=0.5):
    manager = CallbackManager([StreamingLLMCallbackHandler(sock)])
    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")
    streaming_llm = ChatOpenAI(
        streaming=True,
        model_name="gpt-3.5-turbo",
        callback_manager=manager,
        temperature=temperature,
        verbose=True,
    )

    embedding = OpenAIEmbeddings()
    # tools = load_tools(["python_repl", "terminal"], llm=llm)
    tools = []
    # DB_DIRのディレクトリに保存されたデータベースを読み込む
    for target in glob(DB_DIR + "/*"):
        if os.path.isdir(target):
            vectorstore = Chroma(persist_directory=target, embedding_function=embedding)
            chain = VectorDBQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                vectorstore=vectorstore,
                input_key="question",
            )
            title = os.path.basename(target)
            tools.append(
                Tool(
                    name=f"{title} qa database",
                    func=chain.run,
                    description=f"useful for when you need to answer questions about {title}. Input should be a fully formed question.",
                ),
            )
    agent = "chat-zero-shot-react-description"
    return initialize_agent(
        tools,
        streaming_llm,
        agent=agent,
        max_iterations=5,
        memory=ConversationBufferWindowMemory(memory_key="chat_history"),
    )


class ApiHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get("content-length"))
        post_body = self.rfile.read(content_len).decode("utf-8")
        post_data = json.loads(post_body)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

        # 質問の取り出し
        question = post_data["messages"][-1]["content"]
        temperature = float(post_data.get("temperature", 0.5))
        agent = create_db_qa(self, temperature=temperature)
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
