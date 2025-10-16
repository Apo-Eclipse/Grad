# app.py

import streamlit as st
import base64
import os
from agent import FinancialAgent # Import your existing agent

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Financial Transaction Extractor",
    page_icon="💸",
    layout="centered",
)

# --- AGENT INITIALIZATION ---
# Use Streamlit's caching to load the agent only once, improving performance.
@st.cache_resource
def load_agent():
    """Loads the FinancialAgent."""
    print("Initializing Financial Agent for the first time...")
    return FinancialAgent()

agent = load_agent()

# --- UI COMPONENTS ---
st.title("Financial Transaction Extractor 💸")
st.write(
    "Upload a receipt, an audio recording, or type in a transaction "
    "to automatically extract the vendor, amount, and all purchased items."
)

# Create tabs for different input methods
tab1, tab2, tab3 = st.tabs(["📝 Text Input", "🖼️ Receipt Image", "🎙️ Audio File"])

# --- TAB 1: TEXT INPUT ---
with tab1:
    st.header("Extract from Text")
    text_input = st.text_area("Enter transaction details:", "I bought a large pizza and a coke for $25.99 at Domino's.")
    
    if st.button("Process Text", key="text_button"):
        if text_input:
            with st.spinner("Analyzing text..."):
                try:
                    response = agent.invoke({"text": text_input})
                    st.success("Transaction Extracted!")
                    # .dict() converts the Pydantic object to a dictionary for st.json
                    st.json(response.dict())
                except Exception as e:
                    st.error(f"An error occurred: {e}")
        else:
            st.warning("Please enter some text.")

# --- TAB 2: IMAGE INPUT ---
with tab2:
    st.header("Extract from Receipt Image")
    uploaded_image = st.file_uploader(
        "Upload a receipt image:", type=["png", "jpg", "jpeg"]
    )
    
    if st.button("Process Image", key="image_button"):
        if uploaded_image is not None:
            with st.spinner("Analyzing image..."):
                try:
                    # Read image bytes and encode in base64
                    image_bytes = uploaded_image.getvalue()
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    
                    response = agent.invoke({"image_data": image_base64})
                    st.success("Transaction Extracted!")
                    st.json(response.dict())
                except Exception as e:
                    st.error(f"An error occurred: {e}")
        else:
            st.warning("Please upload an image file.")


# --- TAB 3: AUDIO INPUT ---
with tab3:
    st.header("Extract from Audio")
    uploaded_audio = st.file_uploader(
        "Upload a transaction recording:", type=["wav", "mp3", "m4a"]
    )
    
    if st.button("Process Audio", key="audio_button"):
        if uploaded_audio is not None:
            with st.spinner("Transcribing and analyzing audio..."):
                # The audio tool expects a file path, so we save a temporary file
                temp_dir = "temp"
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)
                
                temp_audio_path = os.path.join(temp_dir, uploaded_audio.name)
                with open(temp_audio_path, "wb") as f:
                    f.write(uploaded_audio.getvalue())
                
                try:
                    response = agent.invoke({"audio_path": temp_audio_path})
                    st.success("Transaction Extracted!")
                    # The audio agent returns a dict, so we can display it directly
                    st.json(response)
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_audio_path):
                        os.remove(temp_audio_path)
        else:
            st.warning("Please upload an audio file.")