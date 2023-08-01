import streamlit as st
import os
import openai
import deeplake
from logger import logger
from config.config import AUTHENTICATION_HELP, OPENAI_HELP, ACTIVELOOP_HELP, PROJECT_URL

def initialize_session_state():
    # Initialise all session state variables with defaults
    SESSION_DEFAULTS = {
        "past": [],
        "generated": [],
        "auth_ok": False,
        "openai_api_key": None,
        "activeloop_token": None,
        "activeloop_id": None
    }

    for k, v in SESSION_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

def authentication_form() -> None:
    # widget for authentication input form
    st.title("Authentication", help=AUTHENTICATION_HELP)
    with st.form("authentication"):
        openai_api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help=OPENAI_HELP,
            placeholder="This field is mandatory",
        )
        activeloop_token = st.text_input(
            "ActiveLoop Token",
            type="password",
            help=ACTIVELOOP_HELP,
            placeholder="Optional, using ours if empty",
        )
        activeloop_id = st.text_input(
            "ActiveLoop Organisation Name",
            help=ACTIVELOOP_HELP,
            placeholder="Optional, using ours if empty",
        )
        submitted = st.form_submit_button("Submit")
        if submitted:
            authenticate(openai_api_key, activeloop_token, activeloop_id)

def authenticate(
        openai_api_key: str, activeloop_token: str, activeloop_id: str
) -> None:
    #validate all credentials
    openai_api_key = (
        openai_api_key
        or os.environ.get("OPENAI_API_KEY")
    )
    activeloop_id = (
        activeloop_id
        or os.environ.get("ACTIVELOOP_ID")
    )
    activeloop_token = (
        activeloop_token
        or os.environ.get("ACTIVELOOP_TOKEN")
    )
    if not (openai_api_key and activeloop_id and activeloop_token):
        st.session_state['auth_ok'] = False
        st.error("Credentials neither set nor stored")
        return
    try:
        with st.spinner("Authenticating..."):
            openai.api_key = openai_api_key
            openai.Model.list()
            deeplake.exists(
                f"hub://{activeloop_id}/CodeExplainer",
                token=activeloop_token
            )
    except Exception as e:
        logger.error(f"Authentication failed with {e}")
        st.session_state["auth_ok"] = False
        st.error("Authentication failed")
        return
    st.session_state['auth_ok'] = True
    st.session_state['openai_api_key'] = openai_api_key
    st.session_state['activeloop_token'] = activeloop_token
    st.session_state['activeloop_id'] = activeloop_id
    logger.info('Authentication successful!')