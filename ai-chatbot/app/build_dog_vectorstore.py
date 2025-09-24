import os
import glob
from pathlib import Path
from typing import List

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.docstore.document import Document
from langchain_chroma import Chroma


def load_markdown_documents(docs_dir: str) -> List[Document]:
    """
    Read all .md files under docs_dir and wrap as LangChain Documents.
    Metadata: filename, rel_path.
    """
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        raise FileNotFoundError(f"Documents directory not found: {docs_dir}")

    md_files = glob.glob(str(docs_path / "**" / "*.md"), recursive=True)
    documents: List[Document] = []
    for fp in md_files:
        try:
            text = Path(fp).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback with errors ignore
            text = Path(fp).read_text(encoding="utf-8", errors="ignore")
        rel = os.path.relpath(fp, docs_dir)
        documents.append(Document(page_content=text, metadata={"source": rel, "filename": Path(fp).name}))
    return documents


def split_documents(documents: List[Document]) -> List[Document]:
    """
    Chunk documents for embedding.
    Adjust chunk_size/chunk_overlap depending on retrieval granularity.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(documents)


def build_vector_store(
    docs_dir: str = "ai-chatbot/dog_documents",
    persist_dir: str = "ai-chatbot/dog_vector_store",
    collection_name: str = "dog_knowledge",
    embedding_model: str = None,
    force_rebuild: bool = False,
):
    """
    Build (or reuse) a Chroma vector store from markdown documents.
    Set force_rebuild=True to delete and recreate.

    Environment:
        OPENAI_API_KEY (필수)
        DOG_EMBED_MODEL (선택, 기본: text-embedding-3-large)

    Returns:
        Chroma vector store instance.
    """
    os.environ.get("OPENAI_API_KEY") or raise_missing_key()

    embedding_model = embedding_model or os.getenv("DOG_EMBED_MODEL", "text-embedding-3-large")
    persist_path = Path(persist_dir)

    if force_rebuild and persist_path.exists():
        # Danger: remove previous index
        for f in persist_path.glob("*"):
            if f.is_file():
                f.unlink()
            else:
                # shallow delete
                for sf in f.glob("*"):
                    if sf.is_file():
                        sf.unlink()
        # Optionally remove directory itself (kept for simplicity)

    if persist_path.exists() and not force_rebuild:
        # Reuse existing store
        print(f"[INFO] Using existing Chroma store at {persist_dir}")
        embeddings = OpenAIEmbeddings(model=embedding_model)
        return Chroma(
            embedding_function=embeddings,
            collection_name=collection_name,
            persist_directory=persist_dir,
        )

    print(f"[INFO] Loading markdown documents from: {docs_dir}")
    raw_docs = load_markdown_documents(docs_dir)
    print(f"[INFO] Loaded {len(raw_docs)} documents")

    print("[INFO] Splitting documents into chunks...")
    chunks = split_documents(raw_docs)
    print(f"[INFO] Created {len(chunks)} chunks")

    print(f"[INFO] Embedding with model: {embedding_model}")
    embeddings = OpenAIEmbeddings(model=embedding_model)

    print(f"[INFO] Building Chroma store (collection={collection_name})")
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_dir,
    )

    print(f"[SUCCESS] Vector store persisted at: {persist_dir}")
    return vector_store


def raise_missing_key():
    raise EnvironmentError("OPENAI_API_KEY is not set. Export it before running.")


if __name__ == "__main__":
    # Adjust paths if running from repository root.
    build_vector_store(
        docs_dir="ai-chatbot/dog_documents",
        persist_dir="ai-chatbot/dog_vector_store",
        collection_name="dog_knowledge",
        force_rebuild=False,
    )