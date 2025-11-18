"""
RSS Client for Politico Newsletter Feeds (Simplified - no external dependencies)

This module fetches and processes RSS feeds from Politico using only standard library.
Designed for: National Playbook and Politico Pulse

Output is compatible with the existing email extraction pipeline.
"""

import xml.etree.ElementTree as ET
import requests
import os
import csv
from datetime import datetime
import time
from typing import List, Dict, Optional
import logging
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# RSS Feed Configuration
RSS_FEEDS = {
    'national_playbook': {
        'url': 'http://www.politico.com/rss/playbook.xml',
        'name': 'National Playbook',
        'type': 'national_playbook'
    },
    'politico_pulse': {
        'url': 'http://www.politico.com/rss/politicopulse.xml',
        'name': 'Politico Pulse',
        'type': 'politico_pulse'
    }
}

# Configuration
USER_AGENT = 'PoliticoPlaybookResearch/1.0 (Educational Research; Python/requests)'
REQUEST_TIMEOUT = 30  # seconds
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds


def parse_rfc822_date(date_str: str) -> Optional[datetime]:
    """
    Parse RFC 822 date format used in RSS feeds.

    Args:
        date_str: Date string in RFC 822 format

    Returns:
        datetime object or None if parsing fails
    """
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(date_str)
    except Exception as e:
        logger.warning(f"Could not parse date '{date_str}': {e}")
        return None


def fetch_rss_feed(feed_url: str, user_agent: str = USER_AGENT) -> Optional[str]:
    """
    Fetch RSS feed content.

    Args:
        feed_url: URL of the RSS feed
        user_agent: User agent string for the request

    Returns:
        RSS XML content or None if error
    """
    for attempt in range(RETRY_ATTEMPTS):
        try:
            logger.info(f"Fetching RSS feed: {feed_url} (attempt {attempt + 1}/{RETRY_ATTEMPTS})")

            response = requests.get(
                feed_url,
                headers={'User-Agent': user_agent},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            logger.info(f"Successfully fetched feed: {len(response.content)} bytes")
            return response.text

        except requests.RequestException as e:
            logger.error(f"Request error on attempt {attempt + 1}: {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"Failed to fetch RSS feed after {RETRY_ATTEMPTS} attempts")
                return None


def parse_rss_xml(xml_content: str) -> List[Dict]:
    """
    Parse RSS XML into list of items.

    Args:
        xml_content: RSS XML string

    Returns:
        List of parsed items
    """
    try:
        root = ET.fromstring(xml_content)

        # RSS 2.0 structure: <rss><channel><item>...</item></channel></rss>
        items = []

        for item in root.findall('.//item'):
            title = item.find('title')
            link = item.find('link')
            description = item.find('description')
            pub_date = item.find('pubDate')
            guid = item.find('guid')

            # Extract text content
            item_data = {
                'title': title.text if title is not None else 'No Title',
                'link': link.text if link is not None else '',
                'description': description.text if description is not None else '',
                'pub_date_str': pub_date.text if pub_date is not None else '',
                'guid': guid.text if guid is not None else ''
            }

            # Parse date
            if item_data['pub_date_str']:
                parsed_date = parse_rfc822_date(item_data['pub_date_str'])
                item_data['pub_date'] = parsed_date if parsed_date else datetime.now()
            else:
                item_data['pub_date'] = datetime.now()

            items.append(item_data)

        logger.info(f"Parsed {len(items)} items from RSS feed")
        return items

    except ET.ParseError as e:
        logger.error(f"XML parsing error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error parsing RSS: {e}")
        return []


def fetch_full_article_content(article_url: str) -> Optional[str]:
    """
    Fetch full article HTML from URL if RSS description is incomplete.

    Args:
        article_url: URL of the full article

    Returns:
        HTML content or None if error
    """
    try:
        logger.info(f"Fetching full article: {article_url}")

        response = requests.get(
            article_url,
            headers={'User-Agent': USER_AGENT},
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()

        return response.text

    except requests.RequestException as e:
        logger.error(f"Failed to fetch article content: {e}")
        return None


def save_rss_item(item_data: Dict, feed_type: str, output_dir: str = "data/raw",
                  fetch_full_content: bool = True) -> Optional[str]:
    """
    Save RSS item to file in same format as email extraction.

    Args:
        item_data: Parsed item data dictionary
        feed_type: Type of newsletter (e.g., 'national_playbook')
        output_dir: Directory to save files
        fetch_full_content: Whether to fetch full article if RSS content incomplete

    Returns:
        Filename if saved successfully, None otherwise
    """
    try:
        # Get content from description
        content = item_data['description']

        # Check if content seems complete (heuristic: >1000 characters suggests full content)
        content_complete = len(content) > 1000

        # If content seems incomplete and we have a link, try to fetch full article
        if not content_complete and fetch_full_content and item_data['link']:
            logger.info(f"RSS content incomplete ({len(content)} chars), fetching full article")
            full_content = fetch_full_article_content(item_data['link'])
            if full_content:
                content = full_content
                logger.info(f"Fetched full article: {len(content)} chars")

        # If still no content, skip
        if not content or len(content) < 100:
            logger.warning(f"Insufficient content for item: {item_data['title']}")
            return None

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Create filename in same format as email extraction: YYYY-MM-DD_HHMMSS_rss.html
        date_str = item_data['pub_date'].strftime("%Y-%m-%d")
        time_str = item_data['pub_date'].strftime("%H%M%S")
        filename = f"{date_str}_{time_str}_rss.html"
        filepath = os.path.join(output_dir, filename)

        # Check if file already exists (avoid duplicates)
        if os.path.exists(filepath):
            logger.info(f"File already exists, skipping: {filename}")
            return None

        # Save HTML content
        with open(filepath, 'w', encoding='utf-8') as f:
            # Wrap content in basic HTML structure if it's not already HTML
            if not content.strip().startswith('<'):
                content = f"<html><head><title>{item_data['title']}</title></head><body>{content}</body></html>"
            f.write(content)

        logger.info(f"Saved RSS item to: {filename}")
        return filename

    except Exception as e:
        logger.error(f"Error saving RSS item: {e}")
        return None


def process_feed(feed_key: str, output_dir: str = "data/raw", csv_file: str = "data/playbook_metadata.csv",
                 max_items: int = 10, fetch_full_content: bool = True) -> int:
    """
    Process a single RSS feed and save items.

    Args:
        feed_key: Key in RSS_FEEDS dict (e.g., 'national_playbook')
        output_dir: Directory to save HTML files
        csv_file: CSV file for metadata
        max_items: Maximum number of items to process
        fetch_full_content: Whether to fetch full articles if RSS content incomplete

    Returns:
        Number of items processed successfully
    """
    if feed_key not in RSS_FEEDS:
        logger.error(f"Unknown feed key: {feed_key}")
        return 0

    feed_config = RSS_FEEDS[feed_key]
    logger.info(f"Processing feed: {feed_config['name']}")

    # Fetch feed
    xml_content = fetch_rss_feed(feed_config['url'])
    if not xml_content:
        logger.error(f"Failed to fetch feed: {feed_config['name']}")
        return 0

    # Parse feed
    items = parse_rss_xml(xml_content)
    if not items:
        logger.error(f"No items found in feed: {feed_config['name']}")
        return 0

    # Process items
    processed_count = 0
    csv_exists = os.path.exists(csv_file)

    # Ensure CSV directory exists
    csv_dir = os.path.dirname(csv_file)
    if csv_dir:
        os.makedirs(csv_dir, exist_ok=True)

    with open(csv_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header if new file
        if not csv_exists:
            writer.writerow(["Date", "Subject", "Filename", "Source", "Newsletter_Type"])

        # Process entries (most recent first, limited by max_items)
        for item in items[:max_items]:
            try:
                # Save item
                filename = save_rss_item(item, feed_config['type'], output_dir, fetch_full_content)

                if filename:
                    # Add to CSV metadata
                    date_str = item['pub_date'].strftime("%Y-%m-%d")
                    writer.writerow([
                        date_str,
                        item['title'],
                        filename,
                        'RSS',
                        feed_config['type']
                    ])
                    processed_count += 1

            except Exception as e:
                logger.error(f"Error processing feed entry: {e}")
                continue

    logger.info(f"Processed {processed_count} items from {feed_config['name']}")
    return processed_count


def fetch_all_feeds(output_dir: str = "data/raw", csv_file: str = "data/playbook_metadata.csv",
                    max_items_per_feed: int = 10, fetch_full_content: bool = True) -> Dict[str, int]:
    """
    Fetch all configured RSS feeds.

    Args:
        output_dir: Directory to save HTML files
        csv_file: CSV file for metadata
        max_items_per_feed: Maximum items to fetch per feed
        fetch_full_content: Whether to fetch full articles if RSS content incomplete

    Returns:
        Dictionary mapping feed names to count of items processed
    """
    logger.info("Starting RSS feed collection")
    results = {}

    for feed_key in RSS_FEEDS:
        try:
            count = process_feed(
                feed_key,
                output_dir=output_dir,
                csv_file=csv_file,
                max_items=max_items_per_feed,
                fetch_full_content=fetch_full_content
            )
            results[feed_key] = count
        except Exception as e:
            logger.error(f"Error processing feed {feed_key}: {e}")
            results[feed_key] = 0

    logger.info(f"RSS feed collection complete. Results: {results}")
    return results


def main():
    """Main entry point for RSS client."""
    import argparse

    parser = argparse.ArgumentParser(description='Fetch Politico newsletters via RSS feeds')
    parser.add_argument(
        '--output-dir',
        default='politico_playbook/data/raw',
        help='Directory to save HTML files (default: politico_playbook/data/raw)'
    )
    parser.add_argument(
        '--csv-file',
        default='politico_playbook/data/playbook_metadata.csv',
        help='CSV file for metadata (default: politico_playbook/data/playbook_metadata.csv)'
    )
    parser.add_argument(
        '--max-items',
        type=int,
        default=5,
        help='Maximum items to fetch per feed (default: 5)'
    )
    parser.add_argument(
        '--feed',
        choices=list(RSS_FEEDS.keys()) + ['all'],
        default='all',
        help='Specific feed to fetch, or "all" for all feeds (default: all)'
    )
    parser.add_argument(
        '--no-full-content',
        action='store_true',
        help='Do not fetch full article content if RSS summary is incomplete'
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Politico RSS Feed Fetcher (Simplified)")
    logger.info("=" * 60)
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"CSV metadata file: {args.csv_file}")
    logger.info(f"Max items per feed: {args.max_items}")
    logger.info(f"Fetch full content: {not args.no_full_content}")
    logger.info("=" * 60)

    if args.feed == 'all':
        results = fetch_all_feeds(
            output_dir=args.output_dir,
            csv_file=args.csv_file,
            max_items_per_feed=args.max_items,
            fetch_full_content=not args.no_full_content
        )

        logger.info("\nSummary:")
        logger.info("-" * 60)
        total = 0
        for feed_key, count in results.items():
            feed_name = RSS_FEEDS[feed_key]['name']
            logger.info(f"{feed_name}: {count} items")
            total += count
        logger.info(f"Total: {total} items processed")

    else:
        count = process_feed(
            args.feed,
            output_dir=args.output_dir,
            csv_file=args.csv_file,
            max_items=args.max_items,
            fetch_full_content=not args.no_full_content
        )
        logger.info(f"\nProcessed {count} items from {RSS_FEEDS[args.feed]['name']}")


if __name__ == "__main__":
    main()
