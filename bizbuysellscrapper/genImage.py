import requests
import dotenv
import logging
from datetime import datetime
import os

dotenv.load_dotenv()

IMAGE_STABILITY_AI_API_KEY = os.environ.get("IMAGE_STABILITY_AI_API_KEY")

logging.debug("IMAGE_STABILITY_AI_API_KEY is", IMAGE_STABILITY_AI_API_KEY)


if response.status_code == 200:
    with open("./lighthouse.png", 'wb') as file:
        file.write(response.content)
else:
    raise Exception(str(response.json()))