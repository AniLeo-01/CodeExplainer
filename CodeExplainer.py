from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
import streamlit as st
from streamlit_chat import message
import dataloader
from langchain.chains import RetrievalQA
from langchain.embeddings import OpenAIEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()

def get_user_input_query():
    return st.text_input(label='Enter your question', key="input")

def search_db(user_input, db):
    print(user_input)
    retriever = dataloader.get_deeplake_retriever(db)
    model = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    qa = RetrievalQA.from_llm(model, retriever=retriever, return_source_documents=True)
    return qa({"query": user_input})

def display_conversation(history):
    for i in range(len(history["generated"])):
        message(history["past"][i], is_user=True, key=str(i) + "_user")
        message(history["generated"][i], key=str(i))

def run_streamlit():
    # Initialize Streamlit app with a title
    st.title(" CodeExplainer 👨‍💻💻")
    db = dataloader.load_deeplake(activeloop_org_id=os.getenv('ACTIVELOOP_ORG_ID'), embeddings=OpenAIEmbeddings())
    # Get user input from text input or audio transcription
    user_input = get_user_input_query()

    # Initialize session state for generated responses and past messages
    if "generated" not in st.session_state:
        st.session_state["generated"] = ["Hi! Ask me any question related to your repositories and I'll answer them."]
    if "past" not in st.session_state:
        st.session_state["past"] = ["Hey there!"]
        
    # Search the database for a response based on user input and update the session state
    if user_input:
        output = search_db(user_input, db)
        st.session_state.past.append(user_input)
        response = str(output["result"])
        st.session_state.generated.append(response)

    # Display conversation history using Streamlit messages
    if st.session_state["generated"]:
        display_conversation(st.session_state)
    
    st.sidebar.success("Navigation Menu")

# Run the main function when the script is executed
if __name__ == "__main__":
    run_streamlit()