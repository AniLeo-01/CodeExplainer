import streamlit as st
import os
import dataloader
from langchain.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

def git_clone_repository_and_return_files(repo_url: str):
    repo_name = repo_url.split('/')[-1].split('.git')[0]
    if os.path.exists(f'./{repo_name}'):
        st.write('Repository already exists!')
        return None
    command = f'git clone {repo_url}'
    os.system(command)
    texts = dataloader.index_and_split_codebase(repository_name=repo_name)
    return texts


if __name__ == '__main__':
    with st.form(key='repository_form'):
        repo_url = st.text_input(label='Repository URL', key="repo_url")
        submit_button = st.form_submit_button(label='Submit')

    if submit_button and repo_url.strip() != '':
        with st.spinner("Parsing the repository..."):
            texts = git_clone_repository_and_return_files(repo_url=repo_url)
            if texts:
                db = dataloader.create_deeplake(activeloop_org_id=os.getenv('ACTIVELOOP_ORG_ID'), embeddings=OpenAIEmbeddings(disallowed_special=()), texts=texts)
                if db:
                    st.write('Repository added successfully!')