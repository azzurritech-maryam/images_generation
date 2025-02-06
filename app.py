import json
import requests
import time
from dotenv import load_dotenv
import os
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change "*" to frontend domain if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Load API key from .env file
load_dotenv()
api_key = os.getenv("API_KEY")
authorization = "Bearer %s" % api_key

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": authorization,
}


@app.post("/generate-image/")
async def generate_image(
    image: UploadFile, prompt: str = Form(...), num_images: int = Form(...)
):
    # Step 1: Get a presigned URL for uploading an image
    url = "https://cloud.leonardo.ai/api/rest/v1/init-image"
    payload = {"extension": image.filename.split(".")[-1]}

    response = requests.post(url, json=payload, headers=headers)
    response_data = response.json()
    print("Init Image Response:", response_data)  # Debugging print

    fields = response_data.get("uploadInitImage", {}).get("fields", {})
    upload_url = response_data.get("uploadInitImage", {}).get("url", "")
    uploaded_image_id = response_data.get("uploadInitImage", {}).get("id", "")

    if not fields or not upload_url or not uploaded_image_id:
        return JSONResponse(
            content={"error": "Invalid response structure for init image upload"},
            status_code=500,
        )

    # Convert fields to dictionary if it is not already
    if isinstance(fields, str):
        fields = json.loads(fields)

    # Step 2: Upload the image via the presigned URL
    files = {"file": await image.read()}
    upload_response = requests.post(upload_url, data=fields, files=files)
    print(
        "Upload Response:", upload_response.status_code, upload_response.content
    )  # Debugging print

    # Step 3: Generate an image
    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    payload = {
        "height": 896,
        "modelId": "1e60896f-3c26-4296-8ecc-53e2afecc132",  # Leonardo Kino XL
        "prompt": prompt,
        "width": 896,
        "imagePrompts": [uploaded_image_id],
        "num_images": 1,
        "init_strength": 0.5,
        "alchemy": True,
    }

    response = requests.post(url, json=payload, headers=headers)
    response_data = response.json()
    print("Generation Response 1:", response_data)  # Debugging print

    generation_id = response_data.get("sdGenerationJob", {}).get("generationId", "")

    if not generation_id:
        return JSONResponse(
            content={"error": "Invalid response structure for image generation"},
            status_code=500,
        )

    # Step 4: Get the generated image
    url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
    time.sleep(30)  # Wait for the image to be generated
    response = requests.get(url, headers=headers)
    response_data = response.json()
    print("Get Images Response 1:", response_data)  # Debugging print

    generated_image_id = (
        response_data.get("generations_by_pk", {})
        .get("generated_images", [{}])[0]
        .get("id", "")
    )

    if not generated_image_id:
        return JSONResponse(
            content={"error": "No images generated in the first request"},
            status_code=500,
        )

    # Step 5: Combine both uploaded and generated images
    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    payload = {
        "height": 896,
        "presetStyle": "DYNAMIC",
        "modelId": "aa77f04e-3eec-4034-9c07-d0f619684628",  # Leonardo Kino XL
        "prompt": "Replace the hairstyle of a character in the reference image with a new hairstyle, ensuring perfect alignment with the character's head shape and facial features. Preserve the original lighting, shadows, and background for a realistic look. Blend the new hairstyle seamlessly, ensuring consistent textures, colors, and proportions for a natural integration without altering the character's facial expressions or outfit",
        "width": 896,
        "num_images": num_images,  # Updated to allow multiple images
        "alchemy": True,
        "controlnets": [
            {
                "initImageId": uploaded_image_id,
                "initImageType": "UPLOADED",
                "preprocessorId": 133,  # Character Reference Id
                "strengthType": "Mid",
            },
            {
                "initImageId": generated_image_id,
                "initImageType": "GENERATED",
                "preprocessorId": 67,  # Style Reference Id
                "strengthType": "High",
            },
        ],
    }

    response = requests.post(url, json=payload, headers=headers)
    response_data = response.json()
    print("Generation Response 2:", response_data)  # Debugging print

    final_generation_id = response_data.get("sdGenerationJob", {}).get(
        "generationId", ""
    )

    if not final_generation_id:
        return JSONResponse(
            content={"error": "Invalid response structure for final image generation"},
            status_code=500,
        )

    # Step 6: Get the final combined images
    url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{final_generation_id}"
    time.sleep(60)  # Wait for the images to be generated
    response = requests.get(url, headers=headers)
    response_data = response.json()
    print("Get Images Response 2:", response_data)  # Debugging print

    # Extract URLs of the combined images
    combined_image_urls = [
        image.get("url", "")
        for image in response_data.get("generations_by_pk", {}).get(
            "generated_images", []
        )
    ]

    if not combined_image_urls:
        return JSONResponse(
            content={"error": "No combined images generated"}, status_code=500
        )

    return JSONResponse(content={"combined_image_urls": combined_image_urls})


# Run FastAPI
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
