import streamlit as st
import openai
import base64 # Add base64 for image encoding
import io     # Add io for handling byte streams
import platform
import subprocess
import tempfile
import os
from PIL import Image


# Set page config
st.set_page_config(page_title="OpenRouter Chatbot", page_icon="📖", layout="wide")

st.title("💬 ChatFlex – Your Personal Chatbot Companion")
st.caption("🚀 A Streamlit chatbot powered by OpenRouter's free models")

# --- Helper function for API call ---
def get_assistant_response(client, model, messages_for_api):
    """Calls the OpenAI API and returns the assistant's response."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages_for_api
        )
        # Add checks for the response structure
        if response and response.choices:
            first_choice = response.choices[0]
            if first_choice and first_choice.message:
                return first_choice.message.content
            else:
                st.error("API response structure is invalid (missing message).")
                return None
        else:
            st.error("API response structure is invalid (missing choices).")
            return None
    except Exception as e:
        # Log the actual error for debugging, but show a generic message to the user
        print(f"Detailed API Error: {e}") # Optional: Log detailed error to console/log file
        st.error(f"An error occurred during API call. Please check your API key and model selection.")
        return None

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Configuration")
    openrouter_api_key = st.text_input("Enter OpenRouter API Key", type="password")
    st.markdown("Get your free API key from [OpenRouter.ai](https://openrouter.ai/)")

    # --- Model Selection with Short Names ---
    # Define the mapping from short name to full model identifier
    model_mapping = {
        "Llama 4 Maverick": "meta-llama/llama-4-maverick:free",
        "Mistral 7B Instruct": "mistralai/mistral-7b-instruct:free",
        "Qwen QWQ 32B": "arliai/qwq-32b-arliai-rpr-v1:free",
        "Nvidia Nemotron Ultra": "nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
        "Deepseek Chat V3": "deepseek/deepseek-chat-v3-0324:free",
        "Bytedance UI Tars 72B": "bytedance-research/ui-tars-72b:free",
        "Google Gemini 2.0 Flash Exp": "google/gemini-2.0-flash-exp:free",
        "Google Gemma 3 27B IT": "google/gemma-3-27b-it:free",
        "Qwen 2.5 VL 3B Instruct": "qwen/qwen2.5-vl-3b-instruct:free"
    }
    # Get the list of short names to display
    short_model_names = list(model_mapping.keys())

    # Use short names in the selectbox
    selected_short_name = st.selectbox(
        "Choose a free model:",
        options=short_model_names,
        index=0 # Default to the first model in the list
    )
    # Get the corresponding full model identifier based on the selection
    selected_model = model_mapping[selected_short_name]

    # Display the selected *short* name for clarity
    st.markdown(f"**Selected Model:** `{selected_short_name}`") # Display short name
    # The 'selected_model' variable now holds the full identifier needed for the API

    uploaded_image = st.file_uploader(
        "Upload an image (optional)",
        type=["png", "jpg", "jpeg", "gif", "webp"],
        key="sidebar_file_uploader"
    )

    # --- Remove Rerun Button from sidebar ---
    # st.divider()
    # rerun_button = st.button("🔄 Rerun Last Response") # REMOVED


# --- Remove Clipboard Paste Handler ---
# This section should be completely removed
# js_code = """ ... """ # REMOVED
# js_result = streamlit_js_eval(...) # REMOVED
# pasted_image_data = None # REMOVED
# query_params = ... # REMOVED
# if pasted_image_data: ... # REMOVED

# --- Chat History Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Rerun Logic Trigger Check ---
if "messages" not in st.session_state:
    st.session_state.messages = []
