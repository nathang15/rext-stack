import requests
from bs4 import BeautifulSoup
import datetime
from typing import Dict, Optional
import concurrent.futures
import logging
from urllib.parse import urljoin

class HackerNews:
    def __init__(self, username: str, password: str, timeout: int = 10):
        """
        Initialize HackerNews scraper with credentials and optional timeout.
        
        :param username: HackerNews username
        :param password: HackerNews password
        :param timeout: Request timeout in seconds
        """
        self.username = username
        self.password = password
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://news.ycombinator.com"

    def _login(self, session: requests.Session) -> bool:
        """
        Attempt to log in to HackerNews.
        
        :param session: Requests session object
        :return: Boolean indicating successful login
        """
        try:
            login_data = {"acct": self.username, "pw": self.password}
            response = session.post(
                f"{self.base_url}/login?goto=news", 
                data=login_data, 
                timeout=self.timeout
            )
            
            # More robust login check
            login_success = f"user?id={self.username}" in response.text
            if login_success:
                self.logger.info("HackerNews - Login successful")
            else:
                self.logger.error("HackerNews - Login failed")
            
            return login_success
        
        except requests.RequestException as e:
            self.logger.error(f"Login request failed: {e}")
            return False

    def _parse_entry(self, entry: BeautifulSoup) -> Optional[Dict]:
        """
        Parse a single HackerNews entry.
        
        :param entry: BeautifulSoup entry element
        :return: Dictionary of entry details or None
        """
        try:
            record = entry.find("a")
            if not record:
                return None

            attributes = record.attrs
            if not attributes or 'href' not in attributes:
                return None

            if self.username in attributes.get('href', ''):
                return None

            return {
                attributes['href']: {
                    "title": f"Hackernews {entry.text.strip()}",
                    "tags": ["hackernews"],
                    "summary": "",
                    "date": datetime.datetime.today().strftime("%Y-%m-%d"),
                }
            }
        
        except Exception as e:
            self.logger.warning(f"Error parsing entry: {e}")
            return None

    def __call__(self) -> Dict:
        """
        Scrape upvoted threads from HackerNews.
        """
        # Configure logging
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # Use context manager for session
        with requests.Session() as session:
            # Set default headers to mimic browser
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })

            if not self._login(session):
                return {}

            try:
                response = session.get(
                    f"{self.base_url}/upvoted?id={self.username}", 
                    timeout=self.timeout
                )
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                entries = soup.find_all("td", class_="title")

                data = {}
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    results = list(executor.map(self._parse_entry, entries))
                    
                    for result in results:
                        if result:
                            data.update(result)

                return data

            except requests.RequestException as e:
                self.logger.error(f"Failed to fetch upvoted page: {e}")
                return {}