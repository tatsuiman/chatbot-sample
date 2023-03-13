import os
import sys
import pickle
import logging
import click
import openai
from langchain.chains.llm import LLMChain
from langchain.callbacks.base import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.openai_info import OpenAICallbackHandler
from langchain.chains.chat_vector_db.prompts import CONDENSE_QUESTION_PROMPT, QA_PROMPT
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.llms import OpenAIChat
from langchain.vectorstores.base import VectorStore
from langchain.chains import ChatVectorDBChain
from langchain.prompts.prompt import PromptTemplate


logger = logging.getLogger()
logger.setLevel(logging.INFO)

@click.command()
@click.option('--pkl-path', '-f', default='/data/vectorstore.pkl', type=click.Path(exists=True), help='Path to the vectorstore pkl file')
def main(pkl_path):
    with open(pkl_path, "rb") as f:
        vectorstore = pickle.load(f)

    manager = CallbackManager([StreamingStdOutCallbackHandler(), OpenAICallbackHandler()])

    streaming_llm = OpenAIChat(streaming=True, callback_manager=manager, verbose=True, temperature=0.5)
    question_gen_llm = OpenAIChat(temperature=0, verbose=True, callback_manager=manager)

    question_generator = LLMChain(llm=question_gen_llm, prompt=CONDENSE_QUESTION_PROMPT)

    # 回答に情報ソースを表示する場合
    #doc_chain = load_qa_with_sources_chain(
    #    streaming_llm, 
    #    chain_type="stuff",
    #    callback_manager=manager,
    #)

    prompt_template = """Use the following pieces of context to answer the question at the end.
{context}
Question: {question}
Helpful Answer:"""
    QA_PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    doc_chain = load_qa_chain(streaming_llm, chain_type="stuff", prompt=QA_PROMPT)

    chat_history = []
    messages = []
    qa = ChatVectorDBChain(vectorstore=vectorstore, combine_docs_chain=doc_chain, question_generator=question_generator)

    answer = ""
    while True:
        try:
            question = input("[You]: ")
            # 質問に答えられなかったり、チャットの履歴を使ってMarkdownで図を書く場合は「>」を入力してから質問する
            if question.find(">") == 0:
                question = question[1:]
                messages.append({"role": "user", "content": question})
                print("[AI]:")
                report = []
                for resp in openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=messages,
                        temperature=0.5,
                        stream=True,
                    ):
                    token = resp["choices"][0]["delta"].get("content", "")
                    report.append(token)
                    answer = "".join(report).strip()
                    answer = answer.replace("\n", "")
                    sys.stdout.write(token)
                    sys.stdout.flush()
            else:
                messages.append({"role": "user", "content": question})
                print("[AI]:")
                result = qa({"question": question, "chat_history": chat_history})
                answer = result["answer"]
                chat_history.append((question, answer))

            messages.append({"role": "assistant", "content": answer})
            print("\n")
        except Exception as e:
            logger.exception(e)

if __name__ == '__main__':
    main()

