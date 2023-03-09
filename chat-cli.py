import os
import pickle
import logging
import click
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

logger = logging.getLogger()
logger.setLevel(logging.INFO)

@click.command()
@click.option('--vectorstore-path', '-f', type=click.Path(exists=True), help='Path to the vectorstore pkl file')
def main(vectorstore_path):
    with open(vectorstore_path, "rb") as f:
        vectorstore = pickle.load(f)

    manager = CallbackManager([StreamingStdOutCallbackHandler(), OpenAICallbackHandler()])

    streaming_llm = OpenAIChat(streaming=True, callback_manager=manager, verbose=True, temperature=0)
    question_gen_llm = OpenAIChat(temperature=0, verbose=True, callback_manager=manager)

    question_generator = LLMChain(llm=question_gen_llm, prompt=CONDENSE_QUESTION_PROMPT)

    # 回答に情報ソースを表示する場合
    doc_chain = load_qa_with_sources_chain(
        streaming_llm, 
        chain_type="stuff",
        callback_manager=manager,
    )
    #doc_chain = load_qa_chain(streaming_llm, chain_type="stuff", prompt=QA_PROMPT)

    chat_history = []
    qa = ChatVectorDBChain(vectorstore=vectorstore, combine_docs_chain=doc_chain, question_generator=question_generator)

    while True:
        try:
            try:
                question = input("You: ")
                print("AI:")
                result = qa({"question": question, "chat_history": chat_history})
                chat_history.append((question, result["answer"]))
                print("\n")
            except Exception as e:
                logger.exception(e)
        except KeyboardInterrupt:
            break

if __name__ == '__main__':
    main()

