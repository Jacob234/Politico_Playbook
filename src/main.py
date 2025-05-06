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
from email_extractor import connect_to_email, extract_playbook_emails
from html_formatter import extract_text_from_html

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
    directories = ['data', 'logs', 'newsletters']
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

def process_email_newsletters():
    """Process newsletters from email inbox."""
    load_dotenv()
    email_address = os.getenv('EMAIL_ADDRESS', 'politicollector@gmail.com')
    password = os.getenv('EMAIL_PASSWORD', 'tIgwu1-deznit-cozbus')
    
    logger.info("Connecting to email...")
    mail_connection = connect_to_email(email_address, password)
    
    if mail_connection:
        try:
            logger.info("Extracting Politico Playbook emails...")
            result = extract_playbook_emails(
                mail_connection, 
                output_dir="data/newsletters", 
                csv_file="data/playbook_metadata.csv"
            )
            logger.info(result)
            
            # Process extracted HTML files
            process_extracted_newsletters()
            
        except Exception as e:
            logger.error(f"Error during email extraction: {e}")
        finally:
            mail_connection.logout()
            logger.info("Email connection closed")
    else:
        logger.error("Failed to establish email connection")

def process_extracted_newsletters():
    """Process the extracted newsletter HTML files."""
    newsletter_dir = "data/newsletters"
    if not os.path.exists(newsletter_dir):
        logger.warning(f"Directory {newsletter_dir} does not exist")
        return
    
    for filename in os.listdir(newsletter_dir):
        if filename.endswith(".html"):
            file_path = os.path.join(newsletter_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Extract text from HTML
                text_content = extract_text_from_html(html_content)
                
                # Save extracted text
                text_file = os.path.join("data", filename.replace(".html", ".txt"))
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                
                logger.info(f"Processed {filename}")
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")

def main():
    """Main function to orchestrate the newsletter collection process."""
    logger.info("Starting Politico Playbook collection")
    
    setup_directories()
    
    # Method 1: Extract from email
    process_email_newsletters()
    
    # Method 2: Fetch from website (as fallback)
    url = get_playbook_url()
    html_content = fetch_newsletter(url)
    if html_content:
        parsed_content = parse_newsletter(html_content)
        save_newsletter(parsed_content, datetime.now())
    
    logger.info("Completed Politico Playbook collection")

if __name__ == "__main__":
    main()