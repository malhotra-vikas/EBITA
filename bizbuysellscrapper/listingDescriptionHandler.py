import boto3
import json
import os
import sys
import openai
import requests
import base64
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from selenium import webdriver
from selenium.webdriver.common.by import By
import time

import dotenv
import logging
from datetime import datetime
import sys
#print(sys.executable)

dotenv.load_dotenv()
AI_WATERMARK_TEXT=os.environ.get("AI_WATERMARK_TEXT")
AWS_REGION_NAME = os.environ.get("AWS_REGION_NAME")
DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME")
# Get today's date in the format YYYYMMDD
today_date = datetime.now().strftime("%Y%m%d")
# Append today's date to the DDB Table
DYNAMODB_TABLE_NAME = f"{DYNAMODB_TABLE_NAME}-{today_date}"

OPENAI_KEY = os.environ.get("OPENAI_KEY")
IMAGE_STABILITY_AI_API_KEY = os.environ.get("IMAGE_STABILITY_AI_API_KEY")

# Send a message to SQS
AI_IMAGE_CREATED_SQS_URL = os.environ.get("AI_IMAGE_CREATED_SQS_URL")
NEW_IMAGE_SCRAPPED_SQS_URL = os.environ.get("NEW_IMAGE_SCRAPPED_SQS_URL")

# Define the S3 bucket and object key
s3_bucket_name = os.environ.get("IMAGE_STABILITY_AI_GENERATED_S3_Bucket_KEY")

filePath = "/Users/vikas/builderspace/EBITA/files/" + DYNAMODB_TABLE_NAME

# Configure AWS and OpenAI credentials
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION_NAME)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

client = openai.OpenAI(api_key=OPENAI_KEY)

# Function to download image using Selenium
def download_image(url, referrer):
    # Set up Selenium WebDriver (assuming Chrome)
    options = webdriver.ChromeOptions()
    options.headless = True
    driver = webdriver.Chrome(options=options)

    try:
        # Set headers for the request
        headers = {
            'Referer': referrer,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

        # Open the image URL
        driver.get(url)
        time.sleep(2)  # Wait for the page to load

        # Find the image element and get its source URL
        img_element = driver.find_element(By.TAG_NAME, 'img')
        img_url = img_element.get_attribute('src')

        # Download the image
        response = requests.get(img_url, headers=headers, timeout=5)
        if response.status_code == 200:
            print(f"Success downloading image: {response.status_code}")
            return Image.open(BytesIO(response.content))
        else:
            print(f"Error downloading image: {response.status_code}")
            return None
    except Exception as e:
        print(f"Failed to download image: {e}")
        return None
    finally:
        driver.quit()

def check_s3_file_exists(bucketname, key):
    # Initialize S3 client
    s3 = boto3.client('s3')
    fileExists = False

    print("Checking of S3 files exists for key " + key + "in bucket " + bucketname)
    try:
        # Try to get the object from the S3 bucket
        s3.head_object(Bucket=bucketname, Key=key)
        fileExists = True
    except s3.exceptions.NoSuchKey as e:
        fileExists = False
        print(f"No Such Key error: {str(e)}")
    except (NoCredentialsError, PartialCredentialsError) as e:
        fileExists = False
        print(f"Credentials error: {str(e)}")
    except Exception as e:
        fileExists = False
        print(f"Error accessing S3: {str(e)}")
    
    print("File Exists: " + str(fileExists))

    return fileExists

def resize_and_convert_image(input_image_path, size, original_s3_object_key, referrer=""):
    print("The file name is ", input_image_path)
    # Split the file name from the extension
    s3_key_to_be_used, extension = os.path.splitext(original_s3_object_key)

    # Print or return, based on your need
    # print("File name without extension:", s3_key_to_be_used)
    # print("Extension:", extension)

    try:
        # Check if the path is a URL or a local path
        if input_image_path.startswith(('http://', 'https://')):

            # Referrer URL
            headers = {
                'Referer': referrer,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }

            response = requests.get(input_image_path, headers=headers, timeout=5)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            # print("HTTP Status Code:", response.status_code)
            # print("Content-Type:", response.headers['Content-Type'])
            # Only process the image if the content type is correct
            if 'image' in response.headers['Content-Type']:
                image = Image.open(BytesIO(response.content))
                input_file_name = os.path.basename(input_image_path)
        else:
            image = Image.open(input_image_path)
            input_file_name = os.path.basename(input_image_path)

        # Split the file name from the extension
        input_file_name_without_extension, extension = os.path.splitext(input_file_name)

        # print("File name:", input_file_name, input_file_name_without_extension, extension)

        
        # Convert PNG to RGB if necessary (JPEG does not support alpha channel)
        if image.mode in ('RGBA', 'LA'):
            background = Image.new(image.mode[:-1], image.size, (255, 255, 255))
            background.paste(image, image.split()[-1])
            image = background.convert('RGB')

        target_width = size[0]
        target_height = size[1]
        # print("File target width and height:", target_width, target_height)

        # Calculate the target aspect ratio
        target_aspect_ratio = target_width / target_height
        original_width, original_height = image.size
        # print("File original width and height:", original_width, original_height)

        # Calculate cropping box
        if original_width / original_height > target_aspect_ratio:
            new_width = int(original_height * target_aspect_ratio)
            left = (original_width - new_width) // 2
            box = (left, 0, left + new_width, original_height)
        else:
            new_height = int(original_width / target_aspect_ratio)
            top = (original_height - new_height) // 2
            box = (0, top, original_width, top + new_height)

        # Crop the image
        cropped_image = image.crop(box)

        # Resize the image
        resized_image = cropped_image.resize((target_width, target_height), Image.ANTIALIAS)

        # Resize the image using high-quality filter
        #resized_image = image.resize(size, Image.LANCZOS)

        # Construct the output filename using the file_name_without_extension
        output_filename = f"{input_file_name_without_extension}_{size[0]}x{size[1]}.jpg"
            
        # Save the resized image in JPEG format with high quality
        resized_image.save(output_filename, 'JPEG', quality=95)  # High quality setting

        # print("All images have been resized, converted to JPEG, and saved.")

        # Upload the image to S3
        s3_client = boto3.client('s3')
        s3_object_key = f"{s3_key_to_be_used}_{size[0]}x{size[1]}.jpg"
    except requests.exceptions.Timeout:
        # Handle timeouts specifically
        print("Request timed out: Skipping this image.")
        sourceImageTimedOut = True
        return input_image_path
    except requests.exceptions.HTTPError as e:
        # Handle HTTP errors (like 404, 500, etc.)
        print(f"HTTP error occurred: {e}")
    except requests.exceptions.RequestException as e:
        # Handle other possible exceptions
        print(f"Error fetching image: {e}")


    try:
        s3_url = f'https://{s3_bucket_name}.s3.amazonaws.com/{s3_object_key}'

        s3_client.upload_file(output_filename, s3_bucket_name, s3_object_key)
        print(f'Image uploaded to S3 bucket {s3_bucket_name} with key {s3_object_key}')
        
        # After upload, delete the local file to free up space
        try:
            os.remove(output_filename)
            # print(f"Successfully deleted local file: {output_filename}")
        except Exception as e:
            print(f"Failed to delete local file: {e}")

        return s3_url
        
    except FileNotFoundError:
        print('The file was not found')
    except NoCredentialsError:
        print('Credentials not available')
    except Exception as e:
        print(f'An error occurred: {e}')


def watermark_ebit_images(input_image_path, output_image_path, bottom_offset, opacity=128, font_size=36):
    # Open the original image
    original = Image.open(input_image_path)
    original = original.convert("RGBA")  # Convert to RGBA to add transparency to the watermark

    # Make the image editable
    txt = Image.new('RGBA', original.size, (255, 255, 255, 0))

    # Choose a font and size
    font = ImageFont.truetype("Arial.ttf", font_size)  # or any other font and size

    # Initialize ImageDraw
    d = ImageDraw.Draw(txt)

    # Position the text at the bottom-right corner
    textwidth, textheight = d.textsize(AI_WATERMARK_TEXT, font=font)


    x = (original.width - textwidth) / 2  # Calculate x position to center the text
    y = original.height - textheight - bottom_offset  # Calculate y position from the bottom

    # Apply the watermark text
    d.text((x, y), AI_WATERMARK_TEXT, font=font, fill=(255, 255, 255, opacity))

    # Combine the original image with the text image
    watermarked = Image.alpha_composite(original, txt)

    # Convert back to RGB and save the image
    watermarked = watermarked.convert("RGB")
    watermarked.save(output_image_path)


def deprecate_send_sqs_message(queue_url, message, message_group_id):
    try:
        sqs = boto3.client('sqs', region_name='us-east-2')

        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),  # Ensure the message is a JSON formatted string
            MessageGroupId=message_group_id  # Required for FIFO queues
        )
        return response
    except Exception as e:
        print(f"Error sending message to Queue: {str(e)}")

def existing_ai_images_dict(s3_url, s3_key):
    ai_image_dict = {}
    ai_image_dict["original"] = s3_url

    s3_key_original, extension = os.path.splitext(s3_key)

    # Sizes you want to resize your image to
    sizes = [(851, 420), (526, 240), (146, 202), (411, 243), (265, 146)]

    for size in sizes:
        s3_object_key_to_be_used = f"{s3_key_original}_{size[0]}x{size[1]}.jpg"
        s3_url = f'https://{s3_bucket_name}.s3.amazonaws.com/{s3_object_key_to_be_used}'
        key = f"{size[0]}x{size[1]}"
        ai_image_dict[key] = s3_url

    return ai_image_dict


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
    
    s3_object_key = article_id+'_BBS.png'
    #print(f"s3_bucket_name {s3_bucket_name}, amd key {s3_object_key}.")
    #print(f"api_key {api_key}.")
    #print(f"prompt {prompt}.")

    # Generate the S3 URL
    s3_url = f'https://{s3_bucket_name}.s3.amazonaws.com/{s3_object_key}'
    #print(f'S3 URL: {s3_url}')
    
    generatedFileExistsForThisListing = check_s3_file_exists(s3_bucket_name, s3_object_key)
    #print(f'generatedFileExistsForThisListing is: {generatedFileExistsForThisListing}')

    if (generatedFileExistsForThisListing):
        print(f'Found an existing EBITGen image at S3 URL: {s3_url}')
        return existing_ai_images_dict(s3_url, s3_object_key)

    print(f'No existing EBITGen image at S3 URL. Creating a new one: {s3_url}')

    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/generate/core",
        headers={
            "authorization": f"Bearer {IMAGE_STABILITY_AI_API_KEY}",
            "accept": "image/*"
        },
        files={"none": ''},
        data={
            "prompt": prompt,
            "output_format": 'jpeg'
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
        local_watermarked_image_path = 'generated_image_watermarked.png'

        # Watermark AI images before uploading to S3
        watermark_ebit_images(local_image_path, local_watermarked_image_path, 10, 150, 20)
        
        ai_image_dict = {}
        # Sizes you want to resize your image to
        sizes = [(851, 420), (526, 240), (146, 202), (411, 243), (265, 146)]

        for size in sizes:
            resized_s3_url = resize_and_convert_image(local_watermarked_image_path, size, s3_object_key)
            key = f"{size[0]}x{size[1]}"
            ai_image_dict[key] = resized_s3_url

        # Upload the original image to S3
        s3_client = boto3.client('s3')

        try:
            s3_url = f'https://{s3_bucket_name}.s3.amazonaws.com/{s3_object_key}'

            s3_client.upload_file(local_watermarked_image_path, s3_bucket_name, s3_object_key)
            print(f'Image uploaded to S3 bucket {s3_bucket_name} with key {s3_object_key}')

            ai_image_dict["original"] = s3_url

            print("ai_image_dict ios ", ai_image_dict)

            # After upload, delete the local file to free up space
            try:
                os.remove(local_watermarked_image_path)
                #print(f"Successfully deleted local file: {local_watermarked_image_path}")
            except Exception as e:
                print(f"Failed to delete local file: {e}")


            # Now send a SNS message so that the image can be processed
            # Prepare a JSON message with the S3 URL and the file name
            #message = {
            #    "article_id": article_id,
            #    "s3_url": s3_url,
            #}
            # send_sns_message
            #send_sqs_message(AI_IMAGE_CREATED_SQS_URL, message, article_id)

            return ai_image_dict
            
        except FileNotFoundError:
            print('The file was not found')
        except NoCredentialsError:
            print('Credentials not available')
        except Exception as e:
            print(f'An error occurred: {e}')
    else:
        print('Failed to generate image')
        #print('Status code:', response.status_code)
        #print('Response:', response.text)


def generate_readable_description(business_description):
    prompt = (
        f"Convert the following verbose business description into a concise, "
        f"human-readable description in 3 paragraphs:\n\n" + business_description
    )

    #print("prompt os ", prompt)
    # Create a chat completion using the OpenAI API
    chat_completion = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Ensure this model is available or update as necessary
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=200,
    )

    #print(f"Updated readable_description {chat_completion}.")

    readable_description = chat_completion.choices[0].message.content.strip()

    return readable_description


def generate_readable_title_withAI(business_description):

    prompt = (
        f"Convert the following verbose business description into a concise, human-readable and factual headline for what the business/product is with its location, in 6 words or less. "
        f"Exclude any punctuation except when showing city and state. Always show state abbreviated if city is also shown, else show full state name. If no City or State was found, exclude the location details. "
        f"Do not use brackets and placeholder or dummy data for location. "
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

    #print(f"Updated title {chat_completion}.")

    generated_title = chat_completion.choices[0].message.content.strip()

    # Remove quotation marks if present
    generated_title = generated_title.replace('"', "").replace("'", "")

    return generated_title


# Image URL
#input_image_path = 'https://images.bizbuysell.com/shared/listings/205/2058449/eaadd338-567b-444d-b2fe-29c695315f97-W768.jpg'
#referrer = 'https://www.bizbuysell.com/Business-Opportunity/jersey-shore-surf-shop-and-boutique/2058449/'

#resize_and_convert_image(input_image_path, (851, 420), "dssdd.png", "https://www.bizbuysell.com/Business-Opportunity/jersey-shore-surf-shop-and-boutique/2058449/")

# Download the image
#original_image = download_image(input_image_path, referrer)
