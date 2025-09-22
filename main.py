from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

client = genai.Client(api_key='AIzaSyB8j4cgD3TQiDnRhefZeNA55H_n9riOH18')

city_image = Image.open('my_image.jpg')
text_input = """Change my hairstyle keep my face same"""

response = client.models.generate_content(
    model="gemini-2.5-flash-image-preview",
    contents=[city_image, text_input],
)

image_parts = [
    part.inline_data.data
    for part in response.candidates[0].content.parts
    if part.inline_data
]

if image_parts:
    image = Image.open(BytesIO(image_parts[0]))
    image.save('hairstyle.png')
    image.show()