from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
import os


load_dotenv()


api_key = os.environ.get("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)


#dress_image = Image.open('dress.png')
#model_image = Image.open('model.png')
first_image = Image.open('first.jpg')
second_image = Image.open('second.jpg')


#text_input = """Create a professional e-commerce fashion photo. Take the blue floral dress from the first image and let the woman from the second image wear it. Generate a realistic, full-body shot of the woman wearing the dress, with the lighting and shadows adjusted to match the outdoor environment."""
text_input = """ "Create a professional hairstyling concept image. Using the person from the first image as a model, demonstrate how they would look with the hairstyle shown in the second image. . Focus on replicating the haircut style, length, and texture from the reference image. Maintain the original hair color from the first image.or else i will kill you"""


response = client.models.generate_content(
    model="gemini-2.5-flash-image-preview",
    #contents=[dress_image, model_image, text_input],
    contents=[first_image,second_image],
)

image_parts = [
    part.inline_data.data
    for part in response.candidates[0].content.parts
    if part.inline_data
]

if image_parts:
    image = Image.open(BytesIO(image_parts[0]))
    image.save('fashion_ecommerce_shot.png')
    image.show()