from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import requests
from pydantic import BaseModel
from PIL import Image, ImageDraw
from io import BytesIO
import os
import easyocr
import base64
from typing import List

app = FastAPI()

reader = easyocr.Reader(['en'])


class ImageRequest(BaseModel):
    image_urls: List[str]


def easyocr_to_pillow(detected_coordinates):
    pillow_coordinates = []
    for rect in detected_coordinates:
        pillow_coordinates.extend(rect)


    return pillow_coordinates



def extract_text(image_data):

    # Perform OCR on the image
    result = reader.readtext(image_data, paragraph=True)

    # Extract the detected text and coordinates
    detected_text = [detection[1] for detection in result]
    easyocr_coordinates = [detection[0] for detection in result]

    # Return the extracted text and coordinates
    return detected_text, easyocr_coordinates



def remove_text(image_data, text_detections):

    image = Image.open(BytesIO(image_data)).convert("RGBA")
    draw = ImageDraw.Draw(image)

    # Find the bounding box of detected text
    bounding_boxes = [easyocr_to_pillow(coordinates) for coordinates in text_detections]
    print(bounding_boxes)

    # Find the minimum bounding box that contains all text
    min_x = min(min(box[::2]) for box in bounding_boxes)
    min_y = min(min(box[1::2]) for box in bounding_boxes)
    max_x = max(max(box[::2]) for box in bounding_boxes)
    max_y = max(max(box[1::2]) for box in bounding_boxes)

    # Crop the image to exclude the bottom part with text
    cropped_image = image.crop((0, 0, image.width, min_y))



    return cropped_image




@app.post("/image_to_text")
async def image_to_text(request: ImageRequest):
    try:
        processed_images = []

        for image_url in request.image_urls:

            # Download the image from the provided URL
            image_response = requests.get(image_url)
            original_image_data = image_response.content

            # Extract text from the original image using EasyOCR
            detected_text, easyocr_coordinates = extract_text(original_image_data)

            image_without_text = remove_text(original_image_data, easyocr_coordinates)

            
            modified_image_io = BytesIO()
            image_without_text.save(modified_image_io, format='PNG')
            modified_image_io.seek(0)

            # Create a new BytesIO object for reading
            modified_image_io_copy = BytesIO(modified_image_io.read())
            modified_image_base64 = base64.b64encode(modified_image_io_copy.read()).decode('utf-8')
        
            

            # Debug prints
            #print(f"Processing: {image_url}")
            #print(f"Detected Text: {detected_text}")
            #print(f"Base64 Length: {len(modified_image_base64)}")
            

            response_data = {
                "image_url": image_url,
                "images_text": detected_text,
                "cropped_image_url": f"data:image/png;base64,{modified_image_base64}"
            }

            processed_images.append(response_data)
            #print(processed_images)



        return JSONResponse(content={"processed_images": processed_images}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
