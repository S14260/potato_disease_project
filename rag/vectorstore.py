import os
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

CHROMA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "chroma_db"
)

COLLECTION_NAME = "potato_knowledge"


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5"
    )


def get_vectorstore():
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=get_embeddings(),
        collection_name=COLLECTION_NAME,
    )
