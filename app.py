import streamlit as st
import openai
import base64 # Add base64 for image encoding
import io     # Add io for handling byte streams
import platform
import subprocess
import tempfile
import os
from PIL import Image

# Add this import
from streamlit_js_eval import streamlit_js_eval

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
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"An error occurred during API call: {e}")
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


# --- Clipboard Paste Handler ---
# This will inject JS to listen for paste events and send image data to Streamlit
js_code = """
document.addEventListener('paste', async function(event) {
    const items = (event.clipboardData || event.originalEvent.clipboardData).items;
    for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
            const blob = items[i].getAsFile();
            const reader = new FileReader();
            reader.onload = function(event) {
                window.parent.postMessage({
                    type: 'STREAMLIT:PASTE_IMAGE',
                    data: event.target.result
                }, '*');
            };
            reader.readAsDataURL(blob);
        }
    }
});
"""

# Run the JS code and get the result if an image is pasted
js_result = streamlit_js_eval(js_expressions=js_code, key="paste_image_js", want_return_value=False, debounce_time=0)

# Listen for the custom message from JS
pasted_image_data = st.experimental_get_query_params().get("pasted_image", [None])[0]
if pasted_image_data:
    # Remove the query param after reading
    st.experimental_set_query_params(pasted_image=None)

# --- Chat History Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Rerun Logic Trigger Check ---
# We need to know the index of the last message to check its button state later
last_message_index = len(st.session_state.messages) - 1
rerun_triggered = False
if last_message_index >= 1 and st.session_state.messages[last_message_index]["role"] == "assistant":
    # Check if the button corresponding to the last assistant message was clicked
    if st.session_state.get(f"rerun_{last_message_index}"):
        rerun_triggered = True

# --- Display Chat History ---
# Use enumerate to get the index of each message
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        # Handle potential multimodal content display
        if isinstance(message["content"], list):
            for item in message["content"]:
                if item["type"] == "text":
                    st.markdown(item["text"])
                elif item["type"] == "image_url":
                    st.markdown("*(Image sent by user)*") # Updated indication
        else:
            st.markdown(message["content"]) # Original text-only handling

        # --- Add Rerun Button next to the LAST assistant message ---
        if message["role"] == "assistant" and idx == last_message_index:
            # Use columns to place button beside the text (optional, can place below)
            # col1, col2 = st.columns([0.9, 0.1]) # Adjust ratio as needed
            # with col1:
            #     pass # Content is already displayed above
            # with col2:
            # Add the button with a unique key based on its index
            st.button("🔄", key=f"rerun_{idx}", help="Rerun this response")


# --- Rerun Logic ---
# Trigger the rerun logic if the specific button was pressed
if rerun_triggered: # Check the flag set earlier
    if not openrouter_api_key:
        st.info("Please add your OpenRouter API key to continue.")
        st.stop()
    # Check if there are enough messages to rerun (should be guaranteed by where the button is placed)
    if len(st.session_state.messages) >= 2 and st.session_state.messages[-1]["role"] == "assistant":
        # Remove the last assistant message
        st.session_state.messages.pop()
        # Get the messages to send (all messages up to the last user message)
        messages_for_rerun = st.session_state.messages[:] # Create a copy

        try:
            client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key,
            )
            # Call the API using the helper function
            assistant_response = get_assistant_response(client, selected_model, messages_for_rerun)

            if assistant_response:
                # Add new assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            # Rerun the script to update the display
            # Important: Reset the button state after processing to prevent infinite loop
            st.session_state[f"rerun_{last_message_index}"] = False
            st.rerun()

        except Exception as e:
            st.error(f"An error occurred during rerun: {e}")
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

    # Handle pasted image (from clipboard)
    pasted_image = None
    if pasted_image_data:
        header, base64_data = pasted_image_data.split(",", 1)
        image_bytes = base64.b64decode(base64_data)
        pasted_image = Image.open(io.BytesIO(image_bytes))
        user_message_content.append({
            "type": "image_url",
            "image_url": {"url": pasted_image_data}
        })
        display_items.append(pasted_image)

    # Handle uploaded image (from file uploader)
    if uploaded_image is not None:
        image_bytes = uploaded_image.getvalue()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        image_url = f"data:image/{uploaded_image.type.split('/')[-1]};base64,{base64_image}"
        user_message_content.append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })
        display_items.append(uploaded_image)

    if not user_message_content:
        st.warning("Please enter a prompt or upload an image.")
        st.stop()

    # Display user message in chat message container
    with st.chat_message("user"):
        for item in display_items:
            if isinstance(item, str):
                st.markdown(item)
            else:
                st.image(item, width=200)

    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_message_content})

    # --- API Call ---
    try:
        client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )

        # Prepare messages for API (already handled correctly in your existing code)
        api_messages = st.session_state.messages[:] # Send the current history

        # Use the helper function for the initial call as well
        assistant_response = get_assistant_response(client, selected_model, api_messages)

        if assistant_response:
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})

            # --- Force a rerun to update the display and show the button ---
            st.rerun() # ADDED HERE

            # Clear the uploaded image state after processing IF it was used in this turn
            if uploaded_image is not None:
                pass # Decide on image clearing strategy later

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
