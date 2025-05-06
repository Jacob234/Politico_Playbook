#!/usr/bin/env python3
"""
Politico Playbook Extraction Tool
Main script for collecting and processing Politico Playbook newsletters from email.
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv
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
    directories = ['data', 'logs', 'data/newsletters', 'data/text']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def process_email_newsletters():
    """Process newsletters from email inbox."""
    load_dotenv()
    email_address = os.getenv('EMAIL_ADDRESS', 'politicollector@gmail.com')
    password = os.getenv('EMAIL_PASSWORD', 'ckaczaggrgagpimb')
    
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
                
                # Save extracted text to dedicated text directory
                text_file = os.path.join("data/text", filename.replace(".html", ".txt"))
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                
                logger.info(f"Processed {filename}")
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")

def main():
    """Main function to orchestrate the newsletter collection process."""
    logger.info("Starting Politico Playbook collection")
    
    setup_directories()
    
    # Extract newsletters from email
    process_email_newsletters()
    
    logger.info("Completed Politico Playbook collection")

if __name__ == "__main__":
    main()