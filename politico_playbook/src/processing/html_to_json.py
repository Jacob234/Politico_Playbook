"""
HTML to JSON Newsletter Converter

Converts Politico newsletter HTML files to structured JSON format
following the schema defined in src/models/schemas.py
"""

import re
import json
import os
import csv
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path


def extract_sponsor_info(soup):
    """Extract sponsor information from newsletter HTML."""
    sponsor = None
    
    # Look for "Presented by" text
    presented_by_patterns = [
        r'presented by\s*([^:]+)',
        r'presented by:\s*([^\n\r]+)',
    ]
    
    # Check preview text first
    preview_div = soup.find('div', style=lambda x: x and 'display:none' in x)
    if preview_div:
        preview_text = preview_div.get_text()
        for pattern in presented_by_patterns:
            match = re.search(pattern, preview_text, re.IGNORECASE)
            if match:
                sponsor = match.group(1).strip()
                break
    
    # If not found in preview, check main content
    if not sponsor:
        text_content = soup.get_text()
        for pattern in presented_by_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                sponsor = match.group(1).strip()
                break
    
    return sponsor


def extract_authors(soup):
    """Extract author information from newsletter HTML with improved accuracy."""
    authors = []
    
    # Find the author byline area (usually near the top after the header)
    text_content = soup.get_text()
    lines = text_content.split('\n')
    
    # Look for email links first (most reliable method)
    email_links = soup.find_all('a', href=lambda x: x and 'mailto:' in x)
    for link in email_links:
        href = link.get('href', '')
        if '@politico.com' in href:
            # Extract email address
            email_match = re.search(r'mailto:([^@]+)@', href)
            if email_match:
                email_username = email_match.group(1)
                
                # Try to find the display name associated with this email
                link_text = link.get_text(strip=True)
                if link_text and len(link_text) < 50 and ' ' in link_text:
                    # This looks like a real name
                    if link_text not in authors:
                        authors.append(link_text)
                elif email_username:
                    # Convert email username to likely name format
                    name_from_email = email_username.replace('.', ' ').replace('_', ' ').title()
                    if name_from_email not in authors and len(name_from_email) > 3:
                        authors.append(name_from_email)
    
    # Look for "By [Name]" patterns in the first 20 lines (header area)
    header_text = '\n'.join(lines[:20])
    by_patterns = [
        r'By\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # "By FirstName LastName"
        r'^\s*([A-Z][a-z]+\s+[A-Z][a-z]+)\s*$'     # Standalone "FirstName LastName"
    ]
    
    for pattern in by_patterns:
        matches = re.finditer(pattern, header_text, re.MULTILINE)
        for match in matches:
            potential_author = match.group(1).strip()
            # Validate it looks like a real name
            if (len(potential_author.split()) >= 2 and 
                len(potential_author) < 30 and 
                not any(keyword in potential_author.lower() for keyword in 
                       ['presented', 'association', 'politico', 'guide', 'unofficial']) and
                potential_author not in authors):
                authors.append(potential_author)
    
    # Look for "With help from [Names]" pattern
    help_pattern = r'With help from\s+([^.\n]+)'
    help_matches = re.finditer(help_pattern, text_content, re.IGNORECASE)
    for match in help_matches:
        help_text = match.group(1).strip()
        # Split on common separators
        helper_names = re.split(r',\s*|\s+and\s+', help_text)
        for name in helper_names:
            name = name.strip()
            # Validate it's a reasonable name
            if (2 <= len(name.split()) <= 3 and 
                len(name) < 30 and
                re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*$', name) and
                name not in authors):
                authors.append(name)
    
    # Remove duplicates while preserving order and clean up
    cleaned_authors = []
    for author in authors:
        author = author.strip()
        if author and author not in cleaned_authors and len(author) > 2:
            # Final validation - should look like a real name
            words = author.split()
            if (2 <= len(words) <= 3 and 
                all(word[0].isupper() and word[1:].islower() for word in words if word)):
                cleaned_authors.append(author)
    
    return cleaned_authors[:5]  # Limit to maximum 5 authors to prevent false positives


def clean_newsletter_text(soup):
    """Extract and clean the main newsletter text content."""
    
    # Remove unwanted elements
    for element in soup.find_all(['script', 'style', 'meta', 'link', 'title']):
        element.decompose()
    
    # Remove hidden preview text
    for div in soup.find_all('div', style=lambda x: x and 'display:none' in x):
        div.decompose()
    
    # Remove unsubscribe footers and similar
    footer_keywords = ['unsubscribe', 'privacy policy', 'terms', 'copyright', '1000 wilson blvd']
    for element in soup.find_all(string=True):  # Use 'string' instead of 'text'
        if element and any(keyword in element.lower() for keyword in footer_keywords):
            try:
                parent = element.parent
                if parent and parent.name:  # Make sure parent exists and is a tag
                    parent.decompose()
            except AttributeError:
                continue
    
    # Get clean text
    text = soup.get_text()
    
    # Clean up whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Normalize line breaks
    text = re.sub(r'[ \t]+', ' ', text)      # Normalize spaces
    text = text.strip()
    
    return text


def determine_newsletter_type(soup, text, subject):
    """Determine the type of newsletter based on email addresses, images, and content."""
    text_lower = text.lower()
    subject_lower = subject.lower() if subject else ""
    
    # Email address to playbook type mapping
    email_to_type = {
        'playbook@politico.com': 'national_playbook',
        'awren@politico.com': 'national_playbook',  # Adam Wren 
        'zstanton@politico.com': 'national_playbook',  # Zack Stanton
        'cmahtesian@politico.com': 'national_playbook',  # Charlie Mahtesian
        'jcoltin@politico.com': 'new_york_playbook',  # Jeff Coltin
        'nreisman@politico.com': 'new_york_playbook',  # Nick Reisman
        'engo@politico.com': 'new_york_playbook',  # Emily Ngo
        'jbeeferman@politico.com': 'new_york_playbook',  # Joe Beeferman
        'ecordover@politico.com': 'transgender_sports_newsletter',  # Erin Cordover - specialized
        'klong@politico.com': 'womens_rule',  # Katherine Long
        'massachusettsplaybook@email.politico.com': 'massachusetts_playbook'
        # Add more mappings as we identify them
    }
    
    # Check email addresses first (most reliable)
    email_links = soup.find_all('a', href=lambda x: x and 'mailto:' in x)
    for link in email_links:
        href = link.get('href', '')
        if 'mailto:' in href:
            email_match = re.search(r'mailto:([^@]+@[^?&\s]+)', href)
            if email_match:
                email_address = email_match.group(1).lower()
                if email_address in email_to_type:
                    return email_to_type[email_address]
    
    # Check image headers for newsletter type
    img_tags = soup.find_all('img')
    for img in img_tags:
        src = img.get('src', '').lower()
        alt = img.get('alt', '').lower()
        title = img.get('title', '').lower()
        
        if 'new-york-playbook' in src:
            if 'pm' in src:
                return 'new_york_playbook_pm'
            else:
                return 'new_york_playbook'
        elif 'california-playbook' in src:
            return 'california_playbook'
        elif 'florida-playbook' in src:
            return 'florida_playbook'
        elif 'playbook.jpg' in src or 'playbook' in title.lower():
            return 'national_playbook'
        elif 'pulse' in src:
            return 'politico_pulse'
        elif 'nightly' in src:
            return 'politico_nightly'
    
    # Check preview text (hidden div)
    preview_div = soup.find('div', style=lambda x: x and 'display:none' in x)
    if preview_div:
        preview_text = preview_div.get_text().lower()
        
        if 'new yorkers' in preview_text and 'afternoon' in preview_text:
            return 'new_york_playbook_pm'
        elif 'new yorkers' in preview_text:
            return 'new_york_playbook'
        elif 'california' in preview_text:
            return 'california_playbook'
        elif 'florida' in preview_text:
            return 'florida_playbook'
        elif 'unofficial guide to official washington' in preview_text:
            return 'national_playbook'
    
    # Fallback to content analysis
    if 'new york' in text_lower and 'playbook' in text_lower:
        if 'afternoon' in text_lower or 'pm' in subject_lower:
            return 'new_york_playbook_pm'
        else:
            return 'new_york_playbook'
    elif 'california' in text_lower and 'playbook' in text_lower:
        return 'california_playbook'
    elif 'florida' in text_lower and 'playbook' in text_lower:
        return 'florida_playbook'
    elif 'playbook' in text_lower or 'playbook' in subject_lower:
        return 'national_playbook'
    elif 'pulse' in text_lower or 'pulse' in subject_lower:
        return 'politico_pulse'
    elif 'nightly' in text_lower or 'nightly' in subject_lower:
        return 'politico_nightly'
    else:
        return 'politico_newsletter'


def html_to_json(html_file_path, subject=None, date=None):
    """
    Convert a single HTML newsletter file to JSON format.
    
    Args:
        html_file_path: Path to the HTML newsletter file
        subject: Newsletter subject line (optional)
        date: Newsletter date (optional)
    
    Returns:
        Dictionary with structured newsletter data
    """
    
    # Read HTML file
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract metadata
    sponsor = extract_sponsor_info(soup)
    authors = extract_authors(soup)
    clean_text = clean_newsletter_text(soup)
    
    # Get file info
    file_name = os.path.basename(html_file_path)
    
    # Extract date from filename if not provided
    if not date:
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_name)
        if date_match:
            date = date_match.group(1)
    
    # Determine newsletter type
    newsletter_type = determine_newsletter_type(soup, clean_text, subject)
    
    # Build JSON structure according to schema
    newsletter_data = {
        "file_name": file_name,
        "date": date,
        "subject_line": subject or "Unknown Subject",
        "playbook_type": newsletter_type,
        "authors": authors,
        "sponsor": sponsor,
        "text": clean_text
    }
    
    return newsletter_data


def process_newsletter_batch(csv_file_path, raw_html_dir, output_dir):
    """
    Process a batch of newsletters from CSV metadata file.
    
    Args:
        csv_file_path: Path to CSV file with newsletter metadata
        raw_html_dir: Directory containing raw HTML files
        output_dir: Directory to save JSON files
    """
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    processed_count = 0
    errors = []
    
    # Read newsletter metadata
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                date = row.get('Date')
                subject = row.get('Subject')
                filename = row.get('Filename')
                
                # Build paths
                html_file_path = os.path.join(raw_html_dir, filename)
                
                if not os.path.exists(html_file_path):
                    print(f"Warning: HTML file not found: {html_file_path}")
                    continue
                
                # Convert to JSON
                newsletter_json = html_to_json(html_file_path, subject, date)
                
                # Save JSON file
                json_filename = filename.replace('.html', '.json')
                json_file_path = os.path.join(output_dir, json_filename)
                
                with open(json_file_path, 'w', encoding='utf-8') as json_file:
                    json.dump(newsletter_json, json_file, indent=2, ensure_ascii=False)
                
                processed_count += 1
                print(f"✓ Processed: {subject[:50]}... -> {json_filename}")
                
            except Exception as e:
                error_msg = f"Error processing {row.get('Filename', 'unknown')}: {e}"
                errors.append(error_msg)
                print(f"✗ {error_msg}")
    
    print(f"\n=== Processing Complete ===")
    print(f"Successfully processed: {processed_count} newsletters")
    if errors:
        print(f"Errors: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
    
    return processed_count, errors


def main():
    """Main function for testing the converter."""
    
    # Define paths
    base_dir = Path(__file__).parent.parent.parent
    csv_file = base_dir / "data" / "all_august_2025.csv"
    raw_html_dir = base_dir / "data" / "raw"
    output_dir = base_dir / "data" / "structured"
    
    print("=== HTML to JSON Newsletter Converter ===")
    print(f"CSV file: {csv_file}")
    print(f"HTML directory: {raw_html_dir}")
    print(f"Output directory: {output_dir}")
    print()
    
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_file}")
        return
    
    # Process the batch
    processed_count, errors = process_newsletter_batch(csv_file, raw_html_dir, output_dir)
    
    if processed_count > 0:
        print(f"\n✓ Successfully converted {processed_count} newsletters to JSON format!")
        print(f"JSON files saved in: {output_dir}")


if __name__ == "__main__":
    main()