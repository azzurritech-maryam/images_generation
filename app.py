import json
import requests
import time
import os
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("API key not found in .env file.")

authorization = f"Bearer {api_key}"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": authorization
}

def get_presigned_url():
    """Get a presigned URL for uploading an image."""
    init_image_url = "https://cloud.leonardo.ai/api/rest/v1/init-image"
    payload = {"extension": "jpg"}
    response = requests.post(init_image_url, json=payload, headers=headers)
    response.raise_for_status()
    upload_data = response.json()["uploadInitImage"]
    return upload_data["url"], json.loads(upload_data["fields"]), upload_data["id"]

def upload_image(upload_url, fields, image_file_path):
    """Upload the image to the presigned URL."""
    with open(image_file_path, "rb") as image_file:
        files = {"file": image_file}
        response = requests.post(upload_url, data=fields, files=files)
        response.raise_for_status()
    return True

def generate_image(prompt, image_id):
    """Generate an image using the uploaded image ID and prompt."""
    generation_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    payload = {
        "height": 512,
        "modelId": "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3",  # Leonardo Creative model
        "prompt": prompt,
        "width": 512,
        "imagePrompts": [image_id],  # Pass the uploaded image ID
        "num_images": 1  # Limit to one output image
    }
    print("Generation Payload:", json.dumps(payload, indent=2))  # Debug payload
    response = requests.post(generation_url, json=payload, headers=headers)
    print("Generation Response:", response.text)  # Debug response
    response.raise_for_status()
    return response.json()["sdGenerationJob"]["generationId"]

def get_generation_result(generation_id):
    """Retrieve the generation result."""
    generation_status_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
    time.sleep(20)  # Wait for generation to complete
    response = requests.get(generation_status_url, headers=headers)
    print("Generation Result Response:", response.text)  # Debug result response
    response.raise_for_status()

    result = response.json()
    
    # Access nested "generated_images" key
    generated_images = result.get("generations_by_pk", {}).get("generated_images", [])
    if not generated_images:
        print("No images were generated. Please verify input parameters.")
        raise ValueError("No images generated.")

    return generated_images[0]["url"]  # Return the URL of the first image

def save_image(image_url, output_path):
    """Save the generated image to the specified path."""
    response = requests.get(image_url, stream=True)
    response.raise_for_status()
    with open(output_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

def main():
    # Inputs
    image_file_path = input("Enter the path to the input image: ")
    if not os.path.exists(image_file_path):
        print("Input image file does not exist. Exiting.")
        return

    prompt = input("Enter the prompt for the new image: ")
    output_path = "./generated_image.png"

    # Get presigned URL and upload image
    print("Getting presigned URL...")
    upload_url, fields, image_id = get_presigned_url()
    print(f"Uploading image with ID: {image_id}...")
    upload_image(upload_url, fields, image_file_path)

    # Generate the image
    print("Generating image...")
    generation_id = generate_image(prompt, image_id)

    # Get the result and save the image
    print("Fetching generated image...")
    try:
        image_url = get_generation_result(generation_id)
        print(f"Generated image URL: {image_url}")

        print("Saving the generated image...")
        save_image(image_url, output_path)
        print(f"Generated image saved at: {output_path}")
    except ValueError as e:
        print(str(e))

if __name__ == "__main__":
    main()
