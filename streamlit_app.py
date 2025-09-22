import os
from io import BytesIO

import requests
import streamlit as st
from PIL import Image

API_BASE_URL = os.environ.get("FASTAPI_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Nano Hairstyle Studio")
st.title("Nano Hairstyle Studio")
st.write(
    "Upload a portrait or snap one with your webcam to generate a new hairstyle while keeping the face intact."
)

with st.sidebar:
    st.header("Settings")
    prompt = st.text_area(
        "Prompt",
        "Change my hairstyle keep my face same",
        help="Describe the hairstyle changes you want the model to apply.",
    )
    api_url = st.text_input("FastAPI URL", f"{API_BASE_URL}/hairstyle")

uploaded_file = st.file_uploader(
    "Upload an image", type=["png", "jpg", "jpeg"], accept_multiple_files=False
)

taken_photo = st.camera_input("Or take a picture", key="camera")

image_source = None
image_bytes = None
image_mime = "image/png"

if taken_photo is not None:
    image_source = taken_photo
elif uploaded_file is not None:
    image_source = uploaded_file

if image_source is not None:
    image_bytes = image_source.getvalue()
    detected_type = Image.open(BytesIO(image_bytes)).format
    if detected_type:
        image_mime = f"image/{detected_type.lower()}"
    st.image(image_bytes, caption="Selected image", use_column_width=True)

if st.button("Generate hairstyle", disabled=image_bytes is None):
    if not prompt.strip():
        st.warning("Please enter a prompt before generating a hairstyle.")
    elif image_bytes is None:
        st.warning("Please upload or capture an image first.")
    else:
        try:
            with st.spinner("Calling FastAPI service..."):
                response = requests.post(
                    api_url,
                    files={"image": (image_source.name, image_bytes, image_mime)},
                    data={"prompt": prompt},
                    timeout=120,
                )
            if response.status_code != 200:
                st.error(
                    f"Request failed with status "
                    f"{response.status_code}: {response.text or 'No details provided.'}"
                )
            else:
                result_image = Image.open(BytesIO(response.content))
                st.success("New hairstyle generated!")
                st.image(result_image, caption="Generated style", use_column_width=True)
        except requests.RequestException as exc:
            st.error(f"Error contacting FastAPI service: {exc}")
