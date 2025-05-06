#!/usr/bin/env python3
"""
Politico Playbook Extraction Tool
Main script for collecting and processing Politico Playbook newsletters.
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/playbook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_directories():
    """Create necessary directories if they don't exist."""
    directories = ['data', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def get_playbook_url():
    """Get the Politico Playbook URL from environment variables."""
    load_dotenv()
    return os.getenv('PLAYBOOK_URL', 'https://www.politico.com/newsletters/playbook')

def fetch_newsletter(url):
    """Fetch the newsletter content from the given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error fetching newsletter: {e}")
        return None

def parse_newsletter(html_content):
    """Parse the newsletter HTML content."""
    if not html_content:
        return None
    
    soup = BeautifulSoup(html_content, 'lxml')
    # TODO: Implement specific parsing logic based on Politico's HTML structure
    return soup

def save_newsletter(content, date):
    """Save the newsletter content to a file."""
    if not content:
        return
    
    filename = f"data/playbook_{date.strftime('%Y%m%d')}.html"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(str(content))
        logger.info(f"Saved newsletter to {filename}")
    except IOError as e:
        logger.error(f"Error saving newsletter: {e}")

def main():
    """Main function to orchestrate the newsletter collection process."""
    logger.info("Starting Politico Playbook collection")
    
    setup_directories()
    url = get_playbook_url()
    
    html_content = fetch_newsletter(url)
    if html_content:
        parsed_content = parse_newsletter(html_content)
        save_newsletter(parsed_content, datetime.now())
    
    logger.info("Completed Politico Playbook collection")

if __name__ == "__main__":
    main() 