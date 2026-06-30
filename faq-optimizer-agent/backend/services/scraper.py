import requests
from bs4 import BeautifulSoup
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class WebScraper:
    """Service for scraping website content"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def scrape_website(self, url: str) -> Optional[str]:
        """
        Scrape text content from a website URL
        
        Args:
            url: Website URL to scrape
            
        Returns:
            Extracted text content or None if scraping fails
        """
        try:
            logger.info(f"Scraping website: {url}")
            
            # Make request to the website
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean up text - remove extra whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = ' '.join(lines)
            
            # Limit text length to avoid token limits (approximately 4000 words)
            words = text.split()
            if len(words) > 4000:
                text = ' '.join(words[:4000])
            
            logger.info(f"Successfully scraped {len(words)} words from {url}")
            return text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping website {url}: {str(e)}")
            raise Exception(f"Failed to scrape website: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {str(e)}")
            raise Exception(f"Error processing website content: {str(e)}")
    
    def extract_domain(self, url: str) -> str:
        """Extract domain name from URL for company identification"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception as e:
            logger.error(f"Error extracting domain from {url}: {str(e)}")
            return url
