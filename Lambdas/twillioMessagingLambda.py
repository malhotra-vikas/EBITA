import json
import os
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Retrieve Twilio configuration from environment variables
ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # You can adjust this to DEBUG if needed

def lambda_handler(event, context):
    # Log the incoming event for debugging purposes
    logger.info(f"Received event: {event}")

    # API Gateway passes the query parameters in the event under 'queryStringParameters'
    query_params = event.get('queryStringParameters', {})
    logger.info(f"Received query_params: {query_params}")

    # Extract parameters with defaults
    buyer_name = query_params.get('buyer_name', 'No Name Provided')
    buyer_email = query_params.get('buyer_email', 'No Email Provided')
    seller_name = query_params.get('seller_name', 'No Seller Name Provided')
    seller_phone_number = query_params.get('seller_phone_number', 'No Phone Number Provided')
    message = query_params.get('message', 'No Message Provided')

    logger.info(f"Received query_params: {buyer_email}, {buyer_name}, {seller_name}, {seller_phone_number} and {message}")
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    logger.info("Twilio client initialized.")

    response = sendMessage(client, buyer_email, buyer_name, seller_name, seller_phone_number, message)
    return response


def sendMessage(client, buyer_email, buyer_name, seller_name, seller_phone_number, message):
    full_message = (f"Message from {buyer_name} ({buyer_email}):\n"
                    f"Hello {seller_name},\n{message}")
    logger.info(f"Full Message to be sent : {full_message}")
    
    try:
        response = client.messages.create(
            body=full_message,
            from_=TWILIO_PHONE_NUMBER,
            to=seller_phone_number
        )
        logger.info(f"Message sent successfully: {response.sid}")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Message sent successfully!', 'twilio_response': response.sid})
        }     
    except TwilioRestException as e:
        logger.error(f"Twilio error: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': f"Twilio error: {str(e)}"})}
    except Exception as e:
        logger.error(f"General error: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': f"General error: {str(e)}"})}
