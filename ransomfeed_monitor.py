#!/usr/bin/env python3
import time
import datetime
import json
import os
import re
import subprocess
import logging
import requests
import xml.etree.ElementTree as ET
import configparser
from logging.handlers import RotatingFileHandler

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Constants from config
STATE_FILE = config['main']['state_file']
RSS_URL = config['main']['rss_url']
KEYWORD = config['main']['keyword']
LOG_FILE = config['main']['log_file']
POLL_INTERVAL = int(config['main']['poll_interval'])
RECORD_RETENTION_DAYS = int(config['main']['record_retention_days'])
RETENTION_SECONDS = RECORD_RETENTION_DAYS * 86400

FROM_EMAIL = config['email']['from']
RECIPIENT_EMAIL = config['email']['to']
EMAILS_PER_MINUTE_LIMIT = int(config['email']['emails_per_minute'])
EMAILS_PER_DAY_LIMIT = int(config['email']['emails_per_day'])

# Logging configuration
handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=2)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logging.basicConfig(handlers=[handler], level=logging.INFO)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error reading state file: {e}. Starting with empty state.")
    return { "processed": {}, "emails": [] }

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logging.error(f"Error saving state file: {e}")

def purge_state(state):
    now = time.time()
    state["processed"] = {k: v for k, v in state.get("processed", {}).items() if now - v <= RETENTION_SECONDS}
    state["emails"] = [ts for ts in state.get("emails", []) if now - ts <= RETENTION_SECONDS]

def extract_email_fields(item):
    title = item.find('title').text if item.find('title') is not None else ""
    link = item.find('link').text if item.find('link') is not None else ""
    pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
    description = item.find('description').text if item.find('description') is not None else ""

    bold_matches = re.findall(r'<b>(.*?)</b>', description)
    ransom_name = bold_matches[0] if len(bold_matches) > 0 else ""
    victim = bold_matches[1] if len(bold_matches) > 1 else title

    cleaned_desc = re.sub(r'<[^>]+>', '', description)
    match = re.search(r'(Target victim website:\s*.*)', cleaned_desc)
    if match:
        cleaned_desc = match.group(1).strip()

    subject = f"New event with keyword '{KEYWORD}': {title}"
    return subject, victim, ransom_name, pub_date, link, cleaned_desc

def send_email_via_postfix(subject, victim, ransom_name, pub_date, link, cleaned_desc):
    try:
        with open("email_template_with_placeholders.html", "r", encoding="utf-8") as f:
            html_template = f.read()

        html_body = html_template \
            .replace("{keyword}", KEYWORD) \
            .replace("{victim}", victim) \
            .replace("{ransom_name}", ransom_name) \
            .replace("{pub_date}", pub_date) \
            .replace("{link}", link) \
            .replace("{cleaned_desc}", cleaned_desc)

        email_content = f"""From: {FROM_EMAIL}
To: {RECIPIENT_EMAIL}
Subject: {subject}
MIME-Version: 1.0
Content-Type: text/html; charset=UTF-8

{html_body}"""

        subprocess.run(["sendmail", "-t"], input=email_content.encode('utf-8'), check=True)
        logging.info(f"Email sent: {subject}")
        return True

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to send email: {e}")
        return False
    except Exception as e:
        logging.error(f"Error generating email content: {e}")
        return False

def can_send_email(state):
    now = time.time()
    if len([ts for ts in state["emails"] if now - ts < 60]) >= EMAILS_PER_MINUTE_LIMIT:
        return False, "Per-minute limit reached"
    if len([ts for ts in state["emails"] if datetime.date.fromtimestamp(ts) == datetime.date.today()]) >= EMAILS_PER_DAY_LIMIT:
        return False, "Daily limit reached"
    return True, ""

def bootstrap_state(state):
    if not state.get("processed"):
        try:
            response = requests.get(RSS_URL, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                channel = root.find('channel')
                if channel is not None:
                    now = time.time()
                    for item in channel.findall('item'):
                        item_id = item.find('id').text if item.find('id') is not None else None
                        if item_id:
                            state["processed"][item_id] = now
                    save_state(state)
                    logging.info(f"Bootstrap completed: {len(state['processed'])} entries marked as processed.")
        except Exception as e:
            logging.error(f"Error during bootstrap: {e}")

def main():
    state = load_state()
    bootstrap_state(state)
    pending_items = []

    while True:
        purge_state(state)
        save_state(state)

        try:
            response = requests.get(RSS_URL, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                channel = root.find('channel')

                if channel is not None:
                    for item in channel.findall('item'):
                        item_id = item.find('id').text if item.find('id') is not None else None
                        if item_id and item_id not in state["processed"]:
                            description = item.find('description').text if item.find('description') is not None else ""
                            if KEYWORD in description:
                                pending_items.append(item)

                    while pending_items:
                        can_send, reason = can_send_email(state)
                        if not can_send:
                            logging.info(f"Email sending limit: {reason}. Remaining entries will be processed later.")
                            break

                        item = pending_items.pop(0)
                        subject, victim, ransom_name, pub_date, link, cleaned_desc = extract_email_fields(item)
                        if send_email_via_postfix(subject, victim, ransom_name, pub_date, link, cleaned_desc):
                            state["emails"].append(time.time())
                            state["processed"][item.find('id').text] = time.time()
                            save_state(state)

        except Exception as e:
            logging.error(f"Error while fetching RSS feed: {e}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
