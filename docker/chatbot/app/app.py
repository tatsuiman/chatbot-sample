import os
import sys
import json
import time
import pickle
import openai
from typing import Any, Dict, List
from langchain.chat_models import ChatOpenAI
from langchain.chains.llm import LLMChain
from langchain.callbacks.base import CallbackManager
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains.chat_vector_db.prompts import CONDENSE_QUESTION_PROMPT, QA_PROMPT
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.vectorstores.base import VectorStore
from langchain.chains import ChatVectorDBChain
from langchain.prompts.prompt import PromptTemplate
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 5000
if os.path.exists(sys.argv[1]):
    with open(sys.argv[1], "rb") as f:
        vectorstore = pickle.load(f)


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


def create_qa(sock, temperature=0.5):
    manager = CallbackManager([StreamingLLMCallbackHandler(sock)])
    question_gen_llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", verbose=True)
    streaming_llm = ChatOpenAI(
        streaming=True,
        model_name="gpt-3.5-turbo",
        callback_manager=manager,
        temperature=temperature,
        verbose=True,
    )

    prompt_template = """Use the following pieces of context to answer the question at the end.
{context}
Question: {question}
Helpful Answer:"""
    QA_PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    # doc_chain = load_qa_with_sources_chain(
    #    streaming_llm,
    #    chain_type="stuff"
    # )
    doc_chain = load_qa_chain(streaming_llm, chain_type="stuff", prompt=QA_PROMPT)
    question_generator = LLMChain(llm=question_gen_llm, prompt=CONDENSE_QUESTION_PROMPT)
    qa = ChatVectorDBChain(
        vectorstore=vectorstore, combine_docs_chain=doc_chain, question_generator=question_generator
    )
    return qa


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
        report = []
        # 質問に答えられなかったり、チャットの履歴を使ってMarkdownで図を書く場合は「>」を入力してから質問する
        if question.find(">") == 0:
            for resp in openai.ChatCompletion.create(
                model=post_data["model"],
                messages=post_data["messages"],
                temperature=temperature,
                stream=True,
            ):
                token = resp["choices"][0]["delta"].get("content", "")
                report.append(token)
                data = {
                    "id": "chatcmpl",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": post_data["model"],
                    "choices": [{"delta": {"content": token}, "index": 0, "finish_reason": None}],
                }
                self.wfile.write(b"data: " + json.dumps(data).encode() + b"\n\n")
                self.wfile.flush()
            answer = "".join(report).strip().replace("\n", "")
        else:
            chat_history = []
            for elem in post_data["messages"][:-1]:
                if elem["role"] == "system":
                    continue
                elif elem["role"] == "user":
                    prev_user_content = elem["content"]
                elif elem["role"] == "assistant":
                    chat_history.append((prev_user_content, elem["content"]))
            qa = create_qa(self, temperature)
            qa({"question": question, "chat_history": chat_history})
        self.wfile.write(b"data: [DONE]\n\n")


if __name__ == "__main__":
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, ApiHandler)
    httpd.serve_forever()
