import os
import requests
from bs4 import BeautifulSoup
import datetime
from typing import Dict, Optional
import concurrent.futures
import logging
import nltk
from urllib.parse import urljoin
import re
import math
from nltk.stem import WordNetLemmatizer

class HackerNews:
    def __init__(self, username: str, password: str, timeout: int = 10):
        self.username = username
        self.password = password
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://news.ycombinator.com"
        
        self._setup_nltk_resources()

    def _login(self, session: requests.Session) -> bool:
        try:
            login_data = {"acct": self.username, "pw": self.password}
            response = session.post(
                f"{self.base_url}/login?goto=news", 
                data=login_data, 
                timeout=self.timeout
            )
            
            login_success = f"user?id={self.username}" in response.text
            if login_success:
                self.logger.info("HackerNews - Login successful")
            else:
                self.logger.error("HackerNews - Login failed")
            
            return login_success
        
        except requests.RequestException as e:
            self.logger.error(f"Login request failed: {e}")
            return False

            

    def _setup_nltk_resources(self):
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            try:
                nltk.download('punkt', quiet=True)
            except Exception as e:
                self.logger.warning(f"Failed to download punkt: {e}")

    def _generate_summary(self, text: str, max_length: int = 300) -> str:
        try:
            import math

            def sentence_split(text):
                return re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
            
            def tokenize(text):
                words = re.findall(r'\b\w+\b', text.lower())
                return [word for word in words if len(word) > 1]
            
            stop_words = {}
            current_dir = os.path.dirname(__file__)
            stop_words_file = os.path.join(current_dir, 'stop_words.txt')

            with open(stop_words_file, 'r', encoding='utf-8') as file:
                stop_words = {line.strip().lower() for line in file}
            try:
                sentences = nltk.sent_tokenize(text)
                words = nltk.word_tokenize(text.lower())
            except Exception:
                sentences = sentence_split(text)
                words = tokenize(text)
            
            filtered_words = [
                word for word in words 
                if word not in stop_words 
                and len(word) > 2 
                and len(word) < 20
            ]
            
            word_freq = {}
            for word in filtered_words:
                word_freq[word] = word_freq.get(word, 0) + 1 / math.log(filtered_words.count(word) + 2)
            
            sentence_scores = {}
            for sentence in sentences:
                normalized_length = len(sentence.split()) / 15.0
                
                score = sum(
                    word_freq.get(word.lower(), 0) 
                    for word in tokenize(sentence)
                ) / normalized_length
                
                sentence_scores[sentence] = score
            
            sorted_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)
            
            summary_sentences = sorted_sentences[:3]
            summary = " ".join(summary_sentences)
            
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(' ', 1)[0] + "..."
            
            return summary.strip()
        
        except Exception as e:
            self.logger.warning(f"Summary generation failed: {e}")
            return text[:max_length] + "..."
        
    # TODO: Mapreduce implementation later
    def _extract_tags(self, text: str) -> list:
        try:
            # Load stop words
            stop_words = {}
            current_dir = os.path.dirname(__file__)
            stop_words_file = os.path.join(current_dir, 'stop_words.txt')

            with open(stop_words_file, 'r', encoding='utf-8') as file:
                stop_words = {line.strip().lower() for line in file}

            # Simplified allowed parts of speech
            allowed_pos = {
                'NN',   # Noun, singular
                'NNS',  # Noun, plural
                'NNP',  # Proper noun, singular
                'NNPS', # Proper noun, plural
                'JJ',   # Adjective
                'VB',   # Verb, base form
                'VBD',  # Verb, past tense
                'VBG',  # Verb, gerund
                'VBN',  # Verb, past participle
                'VBP',  # Verb, non-3rd person singular present
                'VBZ',  # Verb, 3rd person singular present
            }

            try:
                import nltk
                words = nltk.word_tokenize(text.lower())
                pos_tags = nltk.pos_tag(words)
            except Exception:
                words = re.findall(r'\b\w+\b', text.lower())
                pos_tags = [(word, 'NN') for word in words]

                filtered_words = [
                    word for word, pos in pos_tags
                    if (
                        word not in stop_words
                        and len(word) > 2
                        and not word.isdigit()
                        and (pos in allowed_pos)
                    )
                ]

                word_freq = {}
                for word in filtered_words:
                    word_freq[word] = word_freq.get(word, 0) + 1 / math.log(filtered_words.count(word) + 1)

                tags = sorted(
                set(filtered_words),
                key=lambda x: word_freq.get(x, 0),
                reverse=True
                )[:3]

                return tags

        except Exception as e:
            self.logger.warning(f"tag extraction failed: {e}")
            return []

    def _fetch_page_content(self, url: str) -> Optional[str]:
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            content_tags = ['article', 'main', 'div', 'p']
            content_text = []
            
            for tag in content_tags:
                elements = soup.find_all(tag, class_=lambda x: x and ('content' in x.lower() or 'article' in x.lower()))
                content_text.extend([elem.get_text(strip=True) for elem in elements])
            
            if not content_text:
                content_text = [soup.body.get_text(strip=True)] if soup.body else []
            
            return " ".join(content_text)
        
        except requests.RequestException as e:
            self.logger.warning(f"Failed to fetch content for {url}: {e}")
            return None

    def _parse_entry(self, entry: BeautifulSoup) -> Optional[Dict]:
        try:
            record = entry.find("a")
            if not record:
                return None

            attributes = record.attrs
            if not attributes or 'href' not in attributes:
                return None

            if self.username in attributes.get('href', ''):
                return None

            url = attributes['href']
            if not url.startswith(('http://', 'https://')):
                url = urljoin(self.base_url, url)

            content = self._fetch_page_content(url)
            
            tags = ["hackernews"]
            summary = ""
            
            if content:
                tags.extend(self._extract_tags(content))
                summary = self._generate_summary(content)

            return {
                url: {
                    "title": f"HackerNews: {record.text.strip()}",
                    "tags": list(set(tags)),
                    "summary": summary,
                    "date": datetime.datetime.today().strftime("%Y-%m-%d"),
                }
            }
        
        except Exception as e:
            self.logger.warning(f"Error parsing entry: {e}")
            return None

    def __call__(self) -> Dict:
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        with requests.Session() as session:
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