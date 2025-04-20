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

# --- Rerun Logic ---
# Trigger the rerun logic if the specific button was pressed
if rerun_triggered: # Check the flag set earlier
    # No need for the 'else' warning here, as the button shouldn't appear if conditions aren't met

# --- User Input Handling ---
if prompt := st.chat_input("What is up?"):
    if not openrouter_api_key:
        st.info("Please add your OpenRouter API key to continue.")
        st.stop()

    # --- Process Input (Text and Image) ---
    user_message_content = []
    display_items = []

    if prompt:
        user_message_content.append({"type": "text", "text": prompt})
        display_items.append(prompt)

    # Handle uploaded image (from file uploader)
    if uploaded_image is not None:
        image_bytes = uploaded_image.getvalue()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        # Determine image type for the data URL
        img_type = uploaded_image.type.split('/')[-1]
        if img_type == "jpeg": # Common variation
            img_type = "jpg"
        image_url = f"data:image/{img_type};base64,{base64_image}"
        user_message_content.append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })
        display_items.append(uploaded_image) # Keep UploadedFile object for st.image

    # Check if any input was provided
    if not prompt and uploaded_image is None:
        st.warning("Please enter a prompt or upload an image.")
        st.stop()

    # Display user message in chat message container
    with st.chat_message("user"):
        for item in display_items:
            if isinstance(item, str):
                st.markdown(item)
            elif hasattr(item, 'getvalue'): # Check if it's an uploaded file object
                st.image(item, width=200)
            # Add else clause if other types are possible

    # Add user message to chat history
    # Structure depends on whether text, image, or both are present
    if prompt and uploaded_image:
        # Multimodal message
        st.session_state.messages.append({"role": "user", "content": user_message_content})
    elif prompt:
        # Text-only message
        st.session_state.messages.append({"role": "user", "content": prompt})
    elif uploaded_image:
        # Image-only message - Ensure content is a list as per OpenAI spec
        image_content_for_history = next((item for item in user_message_content if item["type"] == "image_url"), None)
        if image_content_for_history:
             st.session_state.messages.append({"role": "user", "content": [image_content_for_history]})
        else:
             st.error("Internal error: Could not format image message for history.")
             st.stop()


    # --- API Call ---
    try:
        client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )

        # Prepare messages for API call, ensuring correct format
        api_messages = []
        for msg in st.session_state.messages:
            role = msg["role"]
            content = msg["content"]
            if isinstance(content, str): # Text-only message from history
                api_messages.append({"role": role, "content": [{"type": "text", "text": content}]})
            elif isinstance(content, list): # Already multimodal or image-only list
                api_messages.append({"role": role, "content": content})
            # Add more checks if other content types are possible

        # Use the helper function for the API call
        assistant_response = get_assistant_response(client, selected_model, api_messages)

        if assistant_response:
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})

            # --- Rerun to update display ---
            # Clear the uploaded image state ONLY if it was part of THIS message turn
            # This prevents clearing if user uploads image but doesn't send yet
            if uploaded_image is not None:
                 # A simple way is to trigger a rerun which naturally resets the uploader state
                 # if the key isn't carefully managed across runs.
                 # Or, explicitly clear it if needed, but rerun is often sufficient.
                 pass # Let Streamlit's rerun handle the uploader state for now

            st.rerun() # Rerun to show the new messages

    except Exception as e:
        st.error(f"An unexpected error occurred during API call: {e}")

# --- Final check: Display history if no input/rerun happened ---
# (This part might already be implicitly handled by Streamlit's flow,
# but ensures history is shown on initial load or if other logic paths exit early)
# This should technically be placed *before* the user input handling if you want
# history displayed before the input box, which is standard.
# Let's assume the existing Display Chat History loop handles this correctly.
