import imaplib
import email
from email.header import decode_header
import os
import csv
from datetime import datetime
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

def extract_playbook_emails(mail, output_dir="newsletters", csv_file="playbook_data.csv"):
    """Extract Politico Playbook emails and save content."""
    # Select the inbox
    mail.select("Primary")
    
    # Search for emails from Politico Playbook
    status, messages = mail.search(None, '(FROM "politico.com" SUBJECT "POLITICO Playbook")')
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create or open CSV file for storing metadata
    csv_exists = os.path.exists(csv_file)
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if not csv_exists:
            writer.writerow(["Date", "Subject", "Filename"])
            
        # Process each email
        for num in messages[0].split():
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
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/html":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()
            
            # Save email content to file
            filename = f"{formatted_date}_playbook.html"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(body)
            
            # Save metadata to CSV
            writer.writerow([formatted_date, subject, filename])
            
    return "Email extraction complete."

def main():
    # Replace with your email and password
    email_address = "politicollector@gmail.com"
    password = "tIgwu1-deznit-cozbus"
    mail = connect_to_email(email_address, password)
    result = extract_playbook_emails(mail)
    print(result)
    mail.logout()
    # Close the email connection
    
if __name__ == "__main__":
    main()