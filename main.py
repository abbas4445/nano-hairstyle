import asyncio
import base64
import json
import os
from io import BytesIO
from typing import Optional
from google.genai import types
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from google import genai
from PIL import Image
from loguru import logger

load_dotenv()

app = FastAPI()

_client: Optional[genai.Client] = None
SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png"}
DEFAULT_PROMPT = "Change my hairstyle keep my face same"
MAX_STREAM_COUNT = int(os.environ.get("MAX_STREAM_COUNT", "6"))
MAX_STREAM_RETRY_ATTEMPTS = int(os.environ.get("MAX_STREAM_RETRY_ATTEMPTS", "0"))
STREAM_RETRY_DELAY_SECONDS = float(os.environ.get("STREAM_RETRY_DELAY_SECONDS", "1.0"))



def get_client() -> genai.Client:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable is not set.")
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY environment variable is not set.")

    global _client
    if _client is None:
        logger.info("Initializing Google GenAI client.")
        _client = genai.Client(api_key=api_key)
    else:
        logger.debug("Reusing cached Google GenAI client.")
    return _client


def _get_model_sequence() -> list[str]:
    models = [
        os.environ.get("MAIN_MODEL"),
        os.environ.get("FALLBACK_MODEL"),
    ]
    filtered_models = [model for model in models if model]
    if not filtered_models:
        filtered_models.append("gemini-2.5-flash-image-preview")
    return filtered_models


def _generate_hairstyle_bytes(image_bytes: bytes, prompt: str) -> bytes:
    try:
        pil_image = Image.open(BytesIO(image_bytes))
        pil_image.load()
        logger.debug(
            "Validated input image; mode={}, size={}x{}",
            pil_image.mode,
            pil_image.size[0],
            pil_image.size[1],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load the uploaded image.")
        raise ValueError("The uploaded file is not a valid image.") from exc

    client = get_client()
    last_error: Optional[Exception] = None
    response: Optional[types.GenerateContentResponse] = None

    model_sequence = _get_model_sequence()
    logger.debug("Attempting generation using models: {}", model_sequence)

    for model_name in model_sequence:
        try:
            logger.debug("Calling model '{}' for hairstyle generation.", model_name)
            response = client.models.generate_content(
                model=model_name,
                contents=[pil_image, prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                ),
            )
            logger.info("Model '{}' returned a response.", model_name)
            break
        except Exception as exc:  # noqa: BLE001
            logger.warning("Model '{}' failed to generate content: {}", model_name, exc)
            last_error = exc
            continue

    if response is None:
        logger.error("All configured models failed to generate content.")
        raise RuntimeError("All configured models failed to generate content.") from last_error

    image_parts = [
        part.inline_data.data
        for part in response.candidates[0].content.parts
        if getattr(part, "inline_data", None)
    ]

    if not image_parts:
        logger.error("Model response did not contain an image payload.")
        raise RuntimeError("No image was returned by the model.")

    generated_bytes = image_parts[0]
    if isinstance(generated_bytes, str):
        generated_bytes = base64.b64decode(generated_bytes)

    logger.debug("Generated image ready for response; size={} bytes.", len(generated_bytes))
    return generated_bytes


@app.get("/health")
def health_check() -> dict[str, str]:
    logger.debug("Health check endpoint called.")
    return {"status": "ok"}


@app.post("/hairstyle")
async def generate_hairstyle(
    image: UploadFile = File(...),
    prompt: str = Form(DEFAULT_PROMPT),
) -> Response:
    logger.info(
        "Received /hairstyle request; filename={}, content_type={}, prompt_len={}",
        image.filename,
        image.content_type,
        len(prompt),
    )

    if image.content_type not in SUPPORTED_CONTENT_TYPES:
        logger.warning("Unsupported content type received: {}", image.content_type)
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are supported.")

    image_bytes = await image.read()
    logger.debug("Uploaded image bytes read; size={} bytes.", len(image_bytes))

    try:
        generated_bytes = await asyncio.to_thread(_generate_hairstyle_bytes, image_bytes, prompt)
    except ValueError as exc:
        logger.warning("Invalid image data for /hairstyle request: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.error("Generation failed for /hairstyle request: {}", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info("Generated hairstyle image ({} bytes).", len(generated_bytes))
    return Response(content=generated_bytes, media_type="image/png")


@app.post("/hairstyles/stream")
async def generate_hairstyles_stream(
    image: UploadFile = File(...),
    prompt: str = Form(DEFAULT_PROMPT),
    count: int = Form(3),
) -> StreamingResponse:
    logger.info(
        "Received /hairstyles/stream request; filename={}, content_type={}, prompt_len={}, count={}",
        image.filename,
        image.content_type,
        len(prompt),
        count,
    )

    if image.content_type not in SUPPORTED_CONTENT_TYPES:
        logger.warning("Unsupported content type received for streaming: {}", image.content_type)
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are supported.")

    if count < 1:
        logger.warning("Stream count less than 1 received: {}", count)
        raise HTTPException(status_code=400, detail="count must be at least 1.")

    if count > MAX_STREAM_COUNT:
        logger.warning("Stream count exceeded limit ({}): {}", MAX_STREAM_COUNT, count)
        raise HTTPException(status_code=400, detail=f"count cannot exceed {MAX_STREAM_COUNT}.")

    image_bytes = await image.read()
    logger.debug("Uploaded image bytes read for stream; size={} bytes.", len(image_bytes))

    try:
        with Image.open(BytesIO(image_bytes)) as tmp_image:
            tmp_image.load()
            logger.debug(
                "Validated streaming image; mode={}, size={}x{}",
                tmp_image.mode,
                tmp_image.size[0],
                tmp_image.size[1],
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load the uploaded image for streaming.")
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.") from exc

    async def event_stream():
        max_attempts = MAX_STREAM_RETRY_ATTEMPTS + 1 if MAX_STREAM_RETRY_ATTEMPTS else 0
        logger.debug("Starting stream generation; count={}, max_attempts={}", count, max_attempts)

        for index in range(count):
            attempt = 0
            while True:
                attempt += 1
                logger.debug("Generating stream item {}; attempt {}", index, attempt)
                try:
                    generated_bytes = await asyncio.to_thread(_generate_hairstyle_bytes, image_bytes, prompt)
                except ValueError as exc:  # Invalid input image
                    logger.warning("Invalid input image during stream generation at index {}: {}", index, exc)
                    payload = json.dumps({"index": index, "error": str(exc)})
                    yield payload.encode("utf-8") + b"\n"
                    return
                except RuntimeError as exc:  # Model returned no image
                    logger.warning("Model returned no image for stream index {}: {}", index, exc)
                    if max_attempts and attempt >= max_attempts:
                        payload = json.dumps({"index": index, "error": str(exc)})
                        yield payload.encode("utf-8") + b"\n"
                        return

                    await asyncio.sleep(STREAM_RETRY_DELAY_SECONDS)
                    continue
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "Unexpected error generating stream index {} on attempt {}.",
                        index,
                        attempt,
                    )
                    if max_attempts and attempt >= max_attempts:
                        payload = json.dumps({"index": index, "error": "Unexpected error generating hairstyle."})
                        yield payload.encode("utf-8") + b"\n"
                        return

                    await asyncio.sleep(STREAM_RETRY_DELAY_SECONDS)
                    continue

                payload = json.dumps(
                    {
                        "index": index,
                        "image_base64": base64.b64encode(generated_bytes).decode("utf-8"),
                    }
                )
                logger.info("Stream index {} generated successfully.", index)
                yield payload.encode("utf-8") + b"\n"
                break

    return StreamingResponse(event_stream(), media_type="application/jsonl")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting uvicorn server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
