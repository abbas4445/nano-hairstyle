import asyncio
import base64
import json
import os
from io import BytesIO
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from google import genai
from PIL import Image

load_dotenv()


app = FastAPI()

_client: Optional[genai.Client] = None
SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png"}
DEFAULT_PROMPT = "Change my hairstyle keep my face same"
MAX_STREAM_COUNT = int(os.environ.get("MAX_STREAM_COUNT", "6"))


def get_client() -> genai.Client:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY environment variable is not set.")

    global _client
    if _client is None:
        _client = genai.Client(api_key=api_key)
    return _client


def _generate_hairstyle_bytes(image_bytes: bytes, prompt: str) -> bytes:
    try:
        pil_image = Image.open(BytesIO(image_bytes))
        pil_image.load()
    except Exception as exc:  # noqa: BLE001
        raise ValueError("The uploaded file is not a valid image.") from exc

    client = get_client()
    response = client.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents=[pil_image, prompt],
    )

    image_parts = [
        part.inline_data.data
        for part in response.candidates[0].content.parts
        if getattr(part, "inline_data", None)
    ]

    if not image_parts:
        raise RuntimeError("No image was returned by the model.")

    generated_bytes = image_parts[0]
    if isinstance(generated_bytes, str):
        generated_bytes = base64.b64decode(generated_bytes)

    return generated_bytes


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/hairstyle")
async def generate_hairstyle(
    image: UploadFile = File(...),
    prompt: str = Form(DEFAULT_PROMPT),
) -> Response:
    if image.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are supported.")

    image_bytes = await image.read()

    try:
        generated_bytes = await asyncio.to_thread(_generate_hairstyle_bytes, image_bytes, prompt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return Response(content=generated_bytes, media_type="image/png")


@app.post("/hairstyles/stream")
async def generate_hairstyles_stream(
    image: UploadFile = File(...),
    prompt: str = Form(DEFAULT_PROMPT),
    count: int = Form(3),
) -> StreamingResponse:
    if image.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are supported.")

    if count < 1:
        raise HTTPException(status_code=400, detail="count must be at least 1.")

    if count > MAX_STREAM_COUNT:
        raise HTTPException(status_code=400, detail=f"count cannot exceed {MAX_STREAM_COUNT}.")

    image_bytes = await image.read()

    try:
        with Image.open(BytesIO(image_bytes)) as tmp_image:
            tmp_image.load()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.") from exc

    async def event_stream():
        for index in range(count):
            try:
                generated_bytes = await asyncio.to_thread(_generate_hairstyle_bytes, image_bytes, prompt)
            except ValueError as exc:  # Invalid input image
                payload = json.dumps({"index": index, "error": str(exc)})
                yield payload.encode("utf-8") + b"\n"
                break
            except RuntimeError as exc:  # Model returned no image
                payload = json.dumps({"index": index, "error": str(exc)})
                yield payload.encode("utf-8") + b"\n"
                break
            except Exception:  # noqa: BLE001
                payload = json.dumps({"index": index, "error": "Unexpected error generating hairstyle."})
                yield payload.encode("utf-8") + b"\n"
                break

            payload = json.dumps(
                {
                    "index": index,
                    "image_base64": base64.b64encode(generated_bytes).decode("utf-8"),
                }
            )
            yield payload.encode("utf-8") + b"\n"

    return StreamingResponse(event_stream(), media_type="application/jsonl")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
