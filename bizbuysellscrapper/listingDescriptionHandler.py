import boto3
import json
import os
import sys
from openai import OpenAI
import requests
import base64
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

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

def check_s3_file_exists(bucketname, key):
    # Initialize S3 client
    s3 = boto3.client('s3')
    fileExists = False

    try:
        # Try to get the object from the S3 bucket
        s3.head_object(Bucket=bucketname, Key=key)
        fileExists = True
    except s3.exceptions.NoSuchKey:
        fileExists = False
    except (NoCredentialsError, PartialCredentialsError) as e:
        return f"Credentials error: {str(e)}"
    except Exception as e:
        return f"Error accessing S3: {str(e)}"
    return fileExists

def generate_image_from_AI(business_description, article_id, businesses_title):

    # Define the prompt
    prompt = (
        "Create a profile image for use on an online marketplace of businesses for sale. The business category is " 
        + businesses_title + ". The business description is :" 
        + business_description
    )

    api_key = IMAGE_STABILITY_AI_API_KEY

    if api_key is None:
        raise Exception("Missing Stability API key.")
    
    # Define the S3 bucket and object key
    s3_bucket_name = os.environ.get("IMAGE_STABILITY_AI_GENERATED_S3_Bucket_KEY")
    s3_object_key = article_id+'_BBS.png'
    print(f"s3_bucket_name {s3_bucket_name}, amd key {s3_object_key}.")
    print(f"api_key {api_key}.")
    print(f"prompt {prompt}.")

    # Generate the S3 URL
    s3_url = f'https://{s3_bucket_name}.s3.amazonaws.com/{s3_object_key}'
    print(f'S3 URL: {s3_url}')
    
    generatedFileExistsForThisListing = check_s3_file_exists(s3_bucket_name, s3_object_key)

    if (generatedFileExistsForThisListing):
        return s3_url

    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/generate/core",
        headers={
            "authorization": f"Bearer {IMAGE_STABILITY_AI_API_KEY}",
            "accept": "image/*"
        },
        files={"none": ''},
        data={
            "prompt": {prompt},
        },
    )

    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))
    
    # Check if the request was successful
    if response.status_code == 200:
        # Save the image to a file
        local_image_path = 'generated_image.png'

        with open(local_image_path, 'wb') as file:
            file.write(response.content)
    
        print('Image generated and saved as', local_image_path)

        # Upload the image to S3
        s3_client = boto3.client('s3')

        try:
            s3_client.upload_file(local_image_path, s3_bucket_name, s3_object_key)
            print(f'Image uploaded to S3 bucket {s3_bucket_name} with key {s3_object_key}')

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
        f"Exclude any punctuation except when showing city and state. Always show state abbreviated if city is also shown, else show full state name. "
        f"Exclude the word opportunity and subjective words like thriving from results, just say what it is: {business_description}"
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



