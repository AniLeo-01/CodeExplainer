from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
import streamlit as st
from streamlit_chat import message
import dataloader
from langchain.chains import RetrievalQA
from langchain.embeddings import OpenAIEmbeddings
import os
from dotenv import load_dotenv
import openai
import deeplake
from logger import logger
from authentication import authentication_form
from config.config import PROJECT_URL, APP_NAME, PAGE_ICON

load_dotenv()


def initialize_session_state():
    # Initialise all session state variables with defaults
    SESSION_DEFAULTS = {
        "auth_ok": False,
        "openai_api_key": None,
        "activeloop_token": None,
        "activeloop_id": None
    }

    for k, v in SESSION_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

def app_can_be_started():
    # Only start App if authentication is OK or Local Mode
    return st.session_state["auth_ok"]

def authentication_and_options_side_bar():
    # Sidebar with Authentication and Advanced Options
    with st.sidebar:
        authentication_form()

        st.info(f"Learn how it works [here]({PROJECT_URL})")
        if not app_can_be_started():
            st.stop()

def get_user_input_query():
    return st.text_input(label='Enter your question', key="input")

def search_db(user_input, db):
    print(user_input)
    retriever = dataloader.get_deeplake_retriever(db)
    model = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0, openai_api_key=st.session_state['openai_api_key'])
    qa = RetrievalQA.from_llm(model, retriever=retriever, return_source_documents=True)
    return qa({"query": user_input})

def display_conversation(history):
    for i in range(len(history["generated"])):
        message(history["past"][i], is_user=True, key=str(i) + "_user")
        message(history["generated"][i], key=str(i))

def run_streamlit():
    # Initialize session state for generated responses and past messages
    if "generated" not in st.session_state:
        st.session_state["generated"] = ["Hi! Ask me any question related to your repositories and I'll answer them."]
    if "past" not in st.session_state:
        st.session_state["past"] = ["Hey there!"]
    # Display conversation history using Streamlit messages
    
    user_input = get_user_input_query()
    if user_input:
        # Search the database for a response based on user input and update the session state
        db = dataloader.load_deeplake(activeloop_org_id=st.session_state['activeloop_id'], embeddings=OpenAIEmbeddings(openai_api_key=st.session_state['openai_api_key']), token=st.session_state['activeloop_token'])
        output = search_db(user_input, db)
        st.session_state.past.append(user_input)
        response = str(output["result"])
        st.session_state.generated.append(response)
    if st.session_state["generated"]:
        display_conversation(st.session_state)


# Run the main function when the script is executed
if __name__ == "__main__":
    initialize_session_state()
    st.set_option("client.showErrorDetails", True)
    st.set_page_config(
        page_title=APP_NAME,
        page_icon=PAGE_ICON,
        initial_sidebar_state="expanded",
        layout="centered",
    )
    st.title(f'CodeExplainer {PAGE_ICON}')
    if st.session_state['auth_ok'] == False:
        st.write("Please complete the authentication to continue...")
    authentication_and_options_side_bar()
    # user_input = get_user_input_query()
    run_streamlit()