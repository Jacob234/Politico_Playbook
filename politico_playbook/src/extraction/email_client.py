import imaplib
import email
from email.header import decode_header
import os
import csv
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def is_valid_playbook_email(subject, sender_email):
    """
    Validate if an email is a legitimate Politico Playbook newsletter.
    Returns True if it passes all validation checks.
    
    Validation checks:
        - Subject should not be empty.
        - Subject should not contains any excluded keywords.
        - Subject should contain the word "Playbook".
        - Sender email should be from a valid Politico domain.
        
    If all pass, then true
    """
    if not subject:
        return False
    
    subject_lower = subject.lower()
    
    # Exclude welcome/admin emails (be specific to avoid false positives)
    excluded_patterns = [
        'welcome to', 'thank you for subscribing', 'yes! you subscribed',
        'security alert', '2-step verification', 'verification turned on',
        'authenticator app', 'password', 'recovery email', 'sign-in step',
        'unsubscribe', 'preference center', 'subscription confirmed',
        'correction to  ', 'correction to'  # Empty corrections
    ]
    
    if any(pattern in subject_lower for pattern in excluded_patterns):
        return False
    
    # Accept ALL emails EXCEPT those that are clearly admin/welcome/error emails
    # No need to require specific political keywords - let through all legitimate newsletters
    
    # Validate sender
    if sender_email:
        sender_lower = sender_email.lower()
        valid_domains = ['@politico.com', '@email.politico.com']
        if not any(domain in sender_lower for domain in valid_domains):
            return False
    
    return True

def extract_newsletter_metadata(subject, body_text):
    """
    Extract metadata from newsletter content.
    """
    import re
    
    metadata = {
        'sponsor': None,
        'authors': [],
        'playbook_type': 'standard'
    }
    
    if body_text:
        # Extract sponsor information
        sponsor_match = re.search(r'presented by:?\s*([^\n\r]+)', body_text, re.IGNORECASE)
        if sponsor_match:
            metadata['sponsor'] = sponsor_match.group(1).strip()
        
        # Extract authors (common patterns in Playbook)
        author_patterns = [
            r'by\s+([^,\n]+(?:,\s*[^,\n]+)*)',
            r'your playbook team[,:]?\s*([^\n]+)',
            r'with\s+([^,\n]+(?:,\s*[^,\n]+)*)'
        ]
        
        for pattern in author_patterns:
            author_match = re.search(pattern, body_text, re.IGNORECASE)
            if author_match:
                authors_text = author_match.group(1)
                # Split on 'and' or commas
                authors = [name.strip() for name in re.split(r'\s+and\s+|,', authors_text) if name.strip()]
                metadata['authors'] = authors
                break
    
    return metadata

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
        
        # Search for emails from specific date range (2025-08-01 to 2025-08-04)
        import datetime
        start_date = "01-Aug-2025"  # August 1, 2025
        end_date = "04-Aug-2025"    # August 4, 2025
        
        search_criteria = [
            # Broader POLITICO newsletter searches for specific date range
            f'(FROM "politico.com" SINCE "{start_date}" BEFORE "{end_date}")',
            f'(FROM "email.politico.com" SINCE "{start_date}" BEFORE "{end_date}")',
        ]
        
        all_message_ids = set()
        
        for criteria in search_criteria:
            try:
                status, messages = mail.search(None, criteria)
                if status == 'OK' and messages[0]:
                    message_ids = messages[0].split()
                    all_message_ids.update(message_ids)
                    print(f"Found {len(message_ids)} messages with criteria: {criteria}")
            except Exception as e:
                print(f"Search failed for criteria '{criteria}': {e}")
                continue
        
        if not all_message_ids:
            return "No Politico Playbook emails found with any search criteria."
        
        # Convert back to list and get most recent emails (reverse order for newest first)
        message_ids = sorted(list(all_message_ids), reverse=True)
        num_to_fetch = min(max_emails, len(message_ids))
        recent_ids = message_ids[:num_to_fetch]  # Take first N (most recent)
        
        
        
        
        
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
                
                # Extract subject and date with better encoding handling
                subject_header = msg["subject"]
                if subject_header:
                    decoded_parts = decode_header(subject_header)
                    subject_parts = []
                    for part, encoding in decoded_parts:
                        if isinstance(part, bytes):
                            if encoding:
                                subject_parts.append(part.decode(encoding))
                            else:
                                subject_parts.append(part.decode('utf-8', errors='ignore'))
                        else:
                            subject_parts.append(str(part))
                    subject = ''.join(subject_parts)
                else:
                    subject = "No Subject"
                    
                # Extract sender email
                sender_email = msg["from"]
                
                # Validate email before processing
                if not is_valid_playbook_email(subject, sender_email):
                    print(f"Skipping email with subject: {subject} (failed validation)")
                    continue
                    
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