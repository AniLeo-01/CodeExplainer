import streamlit as st
import os
import dataloader
from langchain.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv
from CodeExplainer import authentication_and_options_side_bar, initialize_session_state

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
    initialize_session_state()
    authentication_and_options_side_bar()
    with st.form(key='repository_form'):
        repo_url = st.text_input(label='Repository URL', key="repo_url")
        submit_button = st.form_submit_button(label='Submit')

    if submit_button and repo_url.strip() != '':
        with st.spinner("Parsing the repository..."):
            texts = git_clone_repository_and_return_files(repo_url=repo_url)
            if texts:
                db = dataloader.create_deeplake(activeloop_org_id=st.session_state['activeloop_id'], embeddings=OpenAIEmbeddings(disallowed_special=()), texts=texts, token=st.session_state['activeloop_token'])
                if db:
                    st.write('Repository added successfully!')