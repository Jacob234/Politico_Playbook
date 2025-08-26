import imaplib
import email
from email.header import decode_header
import os
import csv
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
def clean(text):
    # Clean text for creating a folder
    return "".join(c if c.isalnum() or c in [' ', '.', '_'] else '_' for c in text)

def save_to_csv(date, subject, body, filename="politico_playbook.csv"):
    file_exists = os.path.isfile(filename)
    
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['date', 'subject', 'body']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            'date': date,
            'subject': subject,
            'body': body
        })
        
def connect_to_email(email_address, password):
    """Connect to Gmail using IMAP."""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_address, password)
        return mail
    except Exception as e:
        print(f"Failed to connect to email: {e}")
        return None

def extract_playbook_emails(mail, output_dir="newsletters", csv_file="playbook_data.csv", max_emails=10):
    """Extract Politico Playbook emails and save content."""
    # Select the inbox
    try:
        status, messages = mail.select("INBOX")
        
        if status != 'OK':
            return f"Failed to select mailbox: {messages}"
        
        # Search for emails from Politico Playbook
        status, total_messages = mail.search(None, 'All')
        if status != 'OK':
            return f"Failed to search mailbox: {total_messages}"
        
        message_ids = total_messages[0].split()
        
        num_to_fetch = min(max_emails, len(message_ids))
        recent_ids = message_ids[-num_to_fetch:]
        
        
        
        
        
    except Exception as e:
        return f"Error in extract_playbook_emails: {e}"
        
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create or open CSV file for storing metadata
    csv_exists = os.path.exists(csv_file)
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if not csv_exists:
            writer.writerow(["Date", "Subject", "Filename"])
            
        # Process each email
        processed_count = 0
        for num in recent_ids:
            try:
                status, data = mail.fetch(num, '(RFC822)')
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Extract subject and date
                subject = decode_header(msg["subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                    
                date_str = msg["date"]
                date_obj = email.utils.parsedate_to_datetime(date_str)
                formatted_date = date_obj.strftime("%Y-%m-%d")
                
                # Extract email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/html":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()
                
                # Only process if there's a body to save
                if body:
                    # Save email content to file with a unique identifier
                    timestamp = date_obj.strftime("%H%M%S")
                    filename = f"{formatted_date}_{timestamp}_email.html"
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(body)
                    
                    # Save metadata to CSV
                    writer.writerow([formatted_date, subject, filename])
                    processed_count += 1
                    
            except Exception as e:
                print(f"Error processing email {num}: {e}")
                continue
            
    return f"Email extraction complete. Processed {processed_count} emails."

def main():
    # Get credentials from environment variables
    email_address = os.getenv('GMAIL_ADDRESS')
    password = os.getenv('GMAIL_APP_PASSWORD')
    
    if not email_address or not password:
        print("Error: Gmail credentials not found in environment variables.")
        print("Please set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in your .env file.")
        return
    
    mail = connect_to_email(email_address, password)
    if mail:
        result = extract_playbook_emails(mail)
        print(result)
        mail.logout()
    else:
        print("Failed to connect to Gmail.")
    
if __name__ == "__main__":
    main()