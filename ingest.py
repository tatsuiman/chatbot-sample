import os
import click
import pickle
import tiktoken
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.faiss import FAISS

from langchain.document_loaders import (
    TextLoader,
    PDFMinerLoader,
    PyMuPDFLoader,
    UnstructuredPDFLoader,
    UnstructuredHTMLLoader,
    ReadTheDocsLoader,
    DirectoryLoader,
)

# Map loader class abbreviations to actual classes
FILE_LOADER_CLASSES = {
    'text': TextLoader,
    'pdf_miner': PDFMinerLoader,
    'pymupdf': PyMuPDFLoader,
    'pdf': UnstructuredPDFLoader,
    'html': UnstructuredHTMLLoader,
}

DIR_LOADER_CLASSES = {
    'directory': DirectoryLoader,
    'readthedocs': ReadTheDocsLoader,
}

@click.command()
@click.argument('target')
@click.option('--output-file', '-o', default='vectorstore.pkl', help='Output file name')
@click.option('--loader-cls', '-l', default='text', type=click.Choice(FILE_LOADER_CLASSES.keys()), help='Loader class to use')
@click.option('--dir-loader-cls', '-dl', default='directory', type=click.Choice(DIR_LOADER_CLASSES.keys()), help='Loader class to use for directories')
@click.option('--file-ext', '-e', default="*", help='file extention')
@click.option('--chunk-size', '-cs', default=1000, help='Size of text chunks')
@click.option('--chunk-overlap', '-co', default=200, help='Overlap between text chunks')
@click.option('--dry-run', '-d', is_flag=True, help='If set, does not actually add documents to vectorstore')
def ingest_docs(target, output_file, loader_cls, file_ext, chunk_size, chunk_overlap, dry_run, dir_loader_cls):
    """Get documents from the target directory using the specified loader class."""
    if dir_loader_cls == 'directory':
        loader_cls = FILE_LOADER_CLASSES[loader_cls]  # Get actual loader class from abbreviation
        loader = DirectoryLoader(target, glob=f"**/[!.]*.{file_ext}", loader_cls=loader_cls, silent_errors=True)
    else:
        loader_cls = DIR_LOADER_CLASSES[dir_loader_cls]
        loader = loader_cls(target)

    raw_documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    documents = text_splitter.split_documents(raw_documents)
    print(f"load {len(documents)} documents")
    encoding = tiktoken.encoding_for_model("text-embedding-ada-002")
    text = ""
    for doc in documents:
        text += doc.page_content.replace("\n", " ")
    token_count = len(encoding.encode(text, allowed_special='all'))
    # https://openai.com/pricing
    print(f"use {token_count} token")
    print(f"price {token_count*0.00000004} USD")
    if dry_run:
        print("Dry run mode enabled. Exiting without adding documents to vectorstore.")
        return
    if os.path.exists(output_file):
        with open(output_file, "rb") as f:
            vectorstore = pickle.load(f)
            vectorstore.add_documents(documents)
    else:
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.from_documents(documents, embeddings)

    # Save vectorstore
    with open(output_file, "wb") as f:
        pickle.dump(vectorstore, f)

if __name__ == "__main__":
    ingest_docs()

