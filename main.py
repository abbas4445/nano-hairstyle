import base64
import os
from io import BytesIO
from typing import Optional
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from google import genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()


app = FastAPI()

_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY environment variable is not set.")

    global _client
    if _client is None:
        _client = genai.Client(api_key=api_key)
    return _client


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/hairstyle")
async def generate_hairstyle(
    image: UploadFile = File(...),
    prompt: str = Form("Change my hairstyle keep my face same"),
) -> Response:
    if image.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are supported.")

    image_bytes = await image.read()
    try:
        pil_image = Image.open(BytesIO(image_bytes))
        pil_image.load()  # Ensure the image data is fully read.
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.") from exc

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
        raise HTTPException(status_code=500, detail="No image was returned by the model.")

    generated_bytes = image_parts[0]
    if isinstance(generated_bytes, str):
        generated_bytes = base64.b64decode(generated_bytes)

    return Response(content=generated_bytes, media_type="image/png")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)