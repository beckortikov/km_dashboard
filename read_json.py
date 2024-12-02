import requests
import os
from dotenv import load_dotenv
load_dotenv()

LINK = os.environ.get("LINK")


def response_json():

    headers = {
        'Content-Type': 'application/json'
        }
    response = requests.get(LINK, headers=headers)
    return response.json()