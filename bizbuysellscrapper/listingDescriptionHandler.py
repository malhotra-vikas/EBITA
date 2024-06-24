import boto3
import json
import os
import sys
from openai import OpenAI
import requests
import base64
from botocore.exceptions import NoCredentialsError

import dotenv
import logging
from datetime import datetime

dotenv.load_dotenv()

AWS_REGION_NAME = os.environ.get("AWS_REGION_NAME")
DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME")
# Get today's date in the format YYYYMMDD
today_date = datetime.now().strftime("%Y%m%d")
# Append today's date to the DDB Table
DYNAMODB_TABLE_NAME = f"{DYNAMODB_TABLE_NAME}-{today_date}"

OPENAI_KEY = os.environ.get("OPENAI_KEY")
IMAGE_STABILITY_AI_API_KEY = os.environ.get("IMAGE_STABILITY_AI_API_KEY")

filePath = "/Users/vikas/builderspace/EBITA/files/" + DYNAMODB_TABLE_NAME

# Configure AWS and OpenAI credentials
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION_NAME)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)
dotenv.load_dotenv()

client = OpenAI(api_key=OPENAI_KEY)


def generate_image_from_AI(business_description, article_id):
    # Define the API key and endpoint
    api_key = IMAGE_STABILITY_AI_API_KEY
    api_url = "https://api.stability.ai/v1/generate"

    # Define the S3 bucket and object key
    s3_bucket_name = os.environ.get("IMAGE_STABILITY_AI_GENERATED_S3_Bucket_KEY")
    s3_object_key = 'generated_images/'+article_id+'_BBS.png'

    # Define the prompt
    prompt = (
        "Create a profile image for use on an online marketplace of businesses for sale. The business is: "
        + business_description
    )


    # Set the headers for the request
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Set the payload for the request
    payload = {
        "prompt": prompt,
        "width": 512,
        "height": 512,
        "samples": 1,
        "num_inference_steps": 50,
        "guidance_scale": 7.5,
    }

    # Make the request to the API
    response = requests.post(api_url, headers=headers, data=json.dumps(payload))

    # Check if the request was successful
    if response.status_code == 200:
        # Get the generated image from the response
        response_data = response.json()
        image_data = response_data['images'][0]['base64']

        # Decode the base64 image data
        image_bytes = base64.b64decode(image_data)

        # Save the image to a file
        local_image_path = 'generated_image.png'
        with open(local_image_path, 'wb') as image_file:
            image_file.write(image_bytes)
        
        print('Image generated and saved as generated_image.png')
        
        # Upload the image to S3
        s3_client = boto3.client('s3')

        try:
            s3_client.upload_file(local_image_path, s3_bucket_name, s3_object_key)
            print(f'Image uploaded to S3 bucket {s3_bucket_name} with key {s3_object_key}')
            
            # Generate the S3 URL
            s3_url = f'https://{s3_bucket_name}.s3.amazonaws.com/{s3_object_key}'
            print(f'S3 URL: {s3_url}')

            return s3_url
            
        except FileNotFoundError:
            print('The file was not found')
        except NoCredentialsError:
            print('Credentials not available')
        except Exception as e:
            print(f'An error occurred: {e}')
    else:
        print('Failed to generate image')
        print('Status code:', response.status_code)
        print('Response:', response.text)


def generate_readable_description(business_description):
    prompt = (
        f"Convert the following verbose business description into a concise, "
        f"human-readable description in 3 paragraphs:\n\n{business_description}"
    )

    # Create a chat completion using the OpenAI API
    chat_completion = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Ensure this model is available or update as necessary
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=200,
    )

    print(f"Updated readable_description {chat_completion}.")

    readable_description = chat_completion.choices[0].message.content.strip()

    return readable_description


def generate_readable_title_withAI(business_description):

    prompt = (
        f"Convert the following verbose business description into a concise, human-readable and factual headline for what the business/product is with its location, in 6 words or less. "
        f"Exclude the word opportunity and subjective words like thriving from results, just say what it is:\n\n{business_description}"
    )

    # Create a chat completion using the OpenAI API
    chat_completion = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Ensure this model is available or update as necessary
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=200,
    )

    print(f"Updated title {chat_completion}.")

    generated_title = chat_completion.choices[0].message.content.strip()

    # Remove quotation marks if present
    generated_title = generated_title.replace('"', "").replace("'", "")

    return generated_title
