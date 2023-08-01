import os
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import DeepLake
from typing import Optional

def create_deeplake(activeloop_org_id: str, embeddings, texts, token: Optional[str]):
    db = DeepLake(dataset_path=f"hub://{activeloop_org_id}/CodeExplainer", embedding_function=embeddings, token=token)
    db.add_documents(texts)
    return db

def load_deeplake(activeloop_org_id: str, embeddings, token: Optional[str]):
    db = DeepLake(dataset_path=f"hub://{activeloop_org_id}/CodeExplainer", embedding_function=embeddings, read_only=True, token=token)
    return db

def index_and_split_codebase(repository_name: str):
    root_dir = f'./{repository_name}'
    docs = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for file in filenames:
            try: 
                loader = TextLoader(os.path.join(dirpath, file), encoding='utf-8')
                docs.extend(loader.load_and_split())
            except Exception as e: 
                pass

    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(docs)
    return texts

def get_deeplake_retriever(db: DeepLake):
    retriever = db.as_retriever()
    retriever.search_kwargs['distance_metric'] = 'cos'
    retriever.search_kwargs['fetch_k'] = 100
    retriever.search_kwargs['maximal_marginal_relevance'] = True
    retriever.search_kwargs['k'] = 10
    return retriever


#create_datalake



#load_datalake
