"""Crafty API authentication."""

import logging
import os

import aiohttp

from config import ENV_PATH, set_crafty_api_token, get_crafty_api_token


def update_env_file(new_token):
    if not os.path.exists(ENV_PATH):
        return
    with open(ENV_PATH, "r") as file:
        lines = file.readlines()
    with open(ENV_PATH, "w") as file:
        for line in lines:
            if line.startswith("CRAFTY_API_TOKEN"):
                file.write(f'CRAFTY_API_TOKEN="{new_token}"\n')
            else:
                file.write(line)


async def authenticate():
    crafty_login = os.getenv("CRAFTY_LOGIN")
    crafty_password = os.getenv("CRAFTY_PASSWORD")
    if not crafty_login or not crafty_password:
        logging.error(
            "CRAFTY_LOGIN or CRAFTY_PASSWORD environment variables are not set."
        )
        return

    url = "https://crafty.tessdev.fr/api/v2/auth/login"
    payload = {"username": crafty_login, "password": crafty_password}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            logging.info(f"Authentication response status: {response.status}")
            if response.status == 200:
                token = data["data"]["token"]
                set_crafty_api_token(token)
                logging.info("Successfully authenticated, new token obtained")
                update_env_file(token)
            else:
                logging.error("Failed to authenticate")
                logging.error(data)
