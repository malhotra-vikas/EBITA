import boto3
import json
import os
import sys
from openai import OpenAI

import dotenv
import logging
from datetime import datetime

dotenv.load_dotenv()

AWS_REGION_NAME = os.environ.get("AWS_REGION_NAME")
DYNAMODB_TABLE_NAME=os.environ.get("DYNAMODB_TABLE_NAME")
# Get today's date in the format YYYYMMDD
today_date = datetime.now().strftime("%Y%m%d")
# Append today's date to the DDB Table
DYNAMODB_TABLE_NAME = f"{DYNAMODB_TABLE_NAME}-{today_date}"

OPENAI_KEY = os.environ.get("OPENAI_KEY")

filePath = "/Users/vikas/builderspace/EBITA/files/"+DYNAMODB_TABLE_NAME

# Configure AWS and OpenAI credentials
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION_NAME)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)
dotenv.load_dotenv()

client = OpenAI(
    api_key=OPENAI_KEY
)

def generate_readable_description(business_description):
    prompt = (f"Convert the following verbose business description into a concise, "
              f"human-readable description in 3 paragraphs:\n\n{business_description}")

    # Create a chat completion using the OpenAI API
    chat_completion = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Ensure this model is available or update as necessary
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200
    )

    print(f"Updated readable_description {chat_completion}.")

    readable_description = chat_completion.choices[0].message. content.strip()

    return readable_description
