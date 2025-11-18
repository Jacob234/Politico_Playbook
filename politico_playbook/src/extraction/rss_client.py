"""
RSS Client for Politico Newsletter Feeds

This module fetches and processes RSS feeds from Politico, particularly for:
- National Playbook
- Politico Pulse

Output is compatible with the existing email extraction pipeline.
"""

import feedparser
import requests
from bs4 import BeautifulSoup
import os
import csv
from datetime import datetime
from dateutil import parser as date_parser
import time
from typing import List, Dict, Optional
import logging

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
USER_AGENT = 'PoliticoPlaybookResearch/1.0 (Educational Research; Python/feedparser)'
REQUEST_TIMEOUT = 30  # seconds
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds


def fetch_rss_feed(feed_url: str, user_agent: str = USER_AGENT) -> Optional[feedparser.FeedParserDict]:
    """
    Fetch and parse an RSS feed.

    Args:
        feed_url: URL of the RSS feed
        user_agent: User agent string for the request

    Returns:
        Parsed feed object or None if error
    """
    for attempt in range(RETRY_ATTEMPTS):
        try:
            logger.info(f"Fetching RSS feed: {feed_url} (attempt {attempt + 1}/{RETRY_ATTEMPTS})")

            # Set custom user agent
            response = requests.get(
                feed_url,
                headers={'User-Agent': user_agent},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            # Parse feed
            feed = feedparser.parse(response.content)

            if feed.bozo:
                logger.warning(f"Feed has parsing issues: {feed.bozo_exception}")

            logger.info(f"Successfully fetched feed with {len(feed.entries)} entries")
            return feed

        except requests.RequestException as e:
            logger.error(f"Request error on attempt {attempt + 1}: {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"Failed to fetch RSS feed after {RETRY_ATTEMPTS} attempts")
                return None
        except Exception as e:
            logger.error(f"Unexpected error fetching feed: {e}")
            return None


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


def parse_feed_item(item: feedparser.FeedParserDict, feed_type: str) -> Dict:
    """
    Parse a single feed item into standardized format.

    Args:
        item: Feed entry from feedparser
        feed_type: Type of newsletter (e.g., 'national_playbook')

    Returns:
        Dictionary with parsed item data
    """
    # Extract basic fields
    title = item.get('title', 'No Title')
    link = item.get('link', '')

    # Parse publication date
    pub_date = None
    if hasattr(item, 'published_parsed') and item.published_parsed:
        pub_date = datetime(*item.published_parsed[:6])
    elif hasattr(item, 'published') and item.published:
        try:
            pub_date = date_parser.parse(item.published)
        except Exception as e:
            logger.warning(f"Could not parse date '{item.published}': {e}")

    if not pub_date:
        pub_date = datetime.now()
        logger.warning(f"No valid date found, using current time for: {title}")

    # Extract content (try multiple fields)
    content = ''
    if hasattr(item, 'content') and item.content:
        # Some feeds put full content here
        content = item.content[0].value if isinstance(item.content, list) else item.content
    elif hasattr(item, 'summary') and item.summary:
        # Others use summary
        content = item.summary
    elif hasattr(item, 'description') and item.description:
        # Fallback to description
        content = item.description

    # Check if content seems complete (heuristic: >1000 characters suggests full content)
    content_complete = len(content) > 1000

    return {
        'title': title,
        'link': link,
        'pub_date': pub_date,
        'content': content,
        'content_complete': content_complete,
        'feed_type': feed_type,
        'guid': item.get('id', link)  # Unique identifier for deduplication
    }


def save_rss_item(item_data: Dict, output_dir: str = "data/raw", fetch_full_content: bool = True) -> Optional[str]:
    """
    Save RSS item to file in same format as email extraction.

    Args:
        item_data: Parsed item data dictionary
        output_dir: Directory to save files
        fetch_full_content: Whether to fetch full article if RSS content incomplete

    Returns:
        Filename if saved successfully, None otherwise
    """
    try:
        # Get or fetch content
        content = item_data['content']

        # If content seems incomplete and we have a link, try to fetch full article
        if not item_data['content_complete'] and fetch_full_content and item_data['link']:
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

        # Create filename in same format as email extraction: YYYY-MM-DD_HHMMSS_email.html
        # (keeping "email" in name for compatibility with existing pipeline)
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
    feed = fetch_rss_feed(feed_config['url'])
    if not feed or not feed.entries:
        logger.error(f"No entries found in feed: {feed_config['name']}")
        return 0

    # Process items
    processed_count = 0
    csv_exists = os.path.exists(csv_file)

    # Ensure CSV directory exists
    os.makedirs(os.path.dirname(csv_file) if os.path.dirname(csv_file) else ".", exist_ok=True)

    with open(csv_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header if new file
        if not csv_exists:
            writer.writerow(["Date", "Subject", "Filename", "Source", "Newsletter_Type"])

        # Process entries (most recent first, limited by max_items)
        for entry in feed.entries[:max_items]:
            try:
                # Parse item
                item_data = parse_feed_item(entry, feed_config['type'])

                # Save item
                filename = save_rss_item(item_data, output_dir, fetch_full_content)

                if filename:
                    # Add to CSV metadata
                    date_str = item_data['pub_date'].strftime("%Y-%m-%d")
                    writer.writerow([
                        date_str,
                        item_data['title'],
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
        default=10,
        help='Maximum items to fetch per feed (default: 10)'
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
    logger.info("Politico RSS Feed Fetcher")
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
