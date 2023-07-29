# CodeExplainer
Can't understand your codebase or need to understand a github repository? CodeExplainer is what you need! This application uses GPT-3.5 at it's heart to understand the codebase line-by-line so that you don't have to do the hardwork, and answers to all your questions related to the codebase.

## Installation
```pip install -r requirements.txt```

## Usage
Initialize the environment variables in the .env file:
```
ACTIVELOOP_TOKEN=<activeloop_token_id>
OPENAI_API_KEY=<openai_api_key>
ACTIVELOOP_ORG_ID=<datalake_path>
```

Run the streamlit server using the following command:
```streamlit run CodeExplainer.py```
