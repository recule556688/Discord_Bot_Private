"""Database connection and operations for the Discord bot."""

import json
import logging
import os
from datetime import datetime

import psycopg2


def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
    )
    return conn


def initialize_database():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS logging_channels (
            id SERIAL PRIMARY KEY,
            channel_id BIGINT NOT NULL UNIQUE
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS message_logs (
            id SERIAL PRIMARY KEY,
            encoded_message TEXT NOT NULL
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS birthdays (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            birthdate DATE NOT NULL
        );
        """
    )

    conn.commit()
    cur.close()
    conn.close()


# Birthday operations
def load_birthdays_from_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, birthdate FROM birthdays")
    rows = cur.fetchall()
    birthdays = {row[0]: row[1].strftime("%d-%m-%Y") for row in rows}
    cur.close()
    conn.close()
    return birthdays


def save_birthday_to_db(username, birthdate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        parsed_date = datetime.strptime(birthdate, "%d-%m-%Y").strftime("%Y-%m-%d")
        cur.execute(
            """
            INSERT INTO birthdays (username, birthdate)
            VALUES (%s, %s)
            ON CONFLICT (username) DO UPDATE SET birthdate = EXCLUDED.birthdate
            """,
            (username, parsed_date),
        )
        conn.commit()
    except Exception as e:
        logging.error(f"Error saving birthday to DB: {e}")
    finally:
        cur.close()
        conn.close()


def delete_birthday_from_db(name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM birthdays WHERE username = %s", (name,))
    conn.commit()
    cur.close()
    conn.close()


# Message logging operations
def log_message_to_db(message_data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO message_logs (encoded_message) VALUES (%s)",
        (json.dumps(message_data),),
    )
    conn.commit()
    cur.close()
    conn.close()


def load_excluded_channels():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT channel_id FROM logging_channels")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row[0] for row in rows]


# Logging channels management (used by logging_cog)
def add_logging_channel(channel_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logging_channels (channel_id) VALUES (%s) ON CONFLICT DO NOTHING",
        (channel_id,),
    )
    conn.commit()
    cur.close()
    conn.close()


def remove_logging_channel(channel_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM logging_channels WHERE channel_id = %s", (channel_id,))
    conn.commit()
    cur.close()
    conn.close()
