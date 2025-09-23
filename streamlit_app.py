import base64
import json
from io import BytesIO

import requests
import streamlit as st
from PIL import Image


API_BASE_URL = st.secrets.get("FASTAPI_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
MAX_STREAM_COUNT = int(st.secrets.get("MAX_STREAM_COUNT", "6"))

st.set_page_config(page_title="Nano Hairstyle Studio")
st.title("Nano Hairstyle Studio")
st.write(
    "Upload a portrait or snap one with your webcam to generate fresh hairstyle ideas while keeping the face intact."
)

with st.sidebar:
    st.header("Settings")
    prompt = st.text_area(
        "Prompt",
        "Change my hairstyle keep my face same",
        help="Describe how you want the hairstyle to change.",
    )
    count = st.number_input(
        "Number of hairstyles",
        min_value=1,
        max_value=MAX_STREAM_COUNT,
        value=1,
        step=1,
    )
    base_url_input = st.text_input("FastAPI base URL", API_BASE_URL)
    st.caption("Single result: /hairstyle. Streaming variants: /hairstyles/stream.")

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
    detected_type = "png"
    try:
        with Image.open(BytesIO(image_bytes)) as preview:
            if preview.format:
                detected_type = preview.format.lower()
    except Exception:  # noqa: BLE001
        detected_type = "png"
    image_mime = f"image/{detected_type}"
    st.image(image_bytes, caption="Selected image", use_column_width=True)

button_label = "Generate hairstyles" if count > 1 else "Generate hairstyle"

if st.button(button_label, disabled=image_bytes is None):
    if not prompt.strip():
        st.warning("Please enter a prompt before generating a hairstyle.")
    elif image_bytes is None:
        st.warning("Please upload or capture an image first.")
    else:
        base_url = base_url_input.rstrip("/") or API_BASE_URL
        single_url = f"{base_url}/hairstyle"
        stream_url = f"{base_url}/hairstyles/stream"
        filename = getattr(image_source, "name", "uploaded.png") or "uploaded.png"

        if count == 1:
            try:
                with st.spinner("Calling FastAPI service..."):
                    response = requests.post(
                        single_url,
                        files={"image": (filename, image_bytes, image_mime)},
                        data={"prompt": prompt},
                        timeout=(10, 300),
                    )
                if response.status_code != 200:
                    st.error(
                        f"Request failed with status "
                        f"{response.status_code}: {response.text or 'No details provided.'}"
                    )
                else:
                    st.success("New hairstyle generated!")
                    st.image(response.content, caption="Generated style", use_column_width=True)
            except requests.RequestException as exc:
                st.error(f"Error contacting FastAPI service: {exc}")
        else:
            images = []  # Collect (index, image bytes) for ordered display
            error_message = None
            try:
                with st.spinner("Generating hairstyles..."):
                    with requests.post(
                        stream_url,
                        files={"image": (filename, image_bytes, image_mime)},
                        data={"prompt": prompt, "count": str(count)},
                        stream=True,
                        timeout=(10, 600),
                    ) as response:
                        if response.status_code != 200:
                            error_message = (
                                f"Request failed with status "
                                f"{response.status_code}: {response.text or 'No details provided.'}"
                            )
                        else:
                            for line in response.iter_lines(decode_unicode=True):
                                if not line:
                                    continue
                                try:
                                    payload = json.loads(line)
                                except json.JSONDecodeError:
                                    continue
                                if "error" in payload:
                                    error_message = payload["error"]
                                    break
                                image_b64 = payload.get("image_base64")
                                if not image_b64:
                                    continue
                                try:
                                    image_data = base64.b64decode(image_b64)
                                except (ValueError, TypeError):
                                    continue
                                try:
                                    index = int(payload.get("index", len(images)))
                                except (TypeError, ValueError):
                                    index = len(images)
                                images.append((index, image_data))
            except requests.RequestException as exc:
                st.error(f"Error contacting FastAPI service: {exc}")
            else:
                if error_message:
                    st.error(error_message)
                elif not images:
                    st.info("No images were returned by the service.")
                else:
                    gallery = st.container()
                    for display_index, (_, image_data) in enumerate(
                        sorted(images, key=lambda item: item[0]),
                        start=1,
                    ):
                        gallery.image(
                            image_data,
                            caption=f"Generated style {display_index}",
                            use_column_width=True,
                        )

