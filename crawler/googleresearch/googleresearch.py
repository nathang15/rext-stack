import requests
from bs4 import BeautifulSoup
import datetime
from typing import Dict, Optional, List
import logging
import nltk
from urllib.parse import urljoin
import concurrent.futures
from dataclasses import dataclass
from time import sleep
import re
import os
import math

@dataclass
class Publication:
    title: str
    abstract: str
    url: str
    date: str
    tags: list[str]
    research_areas: list[str]

class GoogleResearch:
    def __init__(self, timeout: int = 10, max_pages: int = 5, category: Optional[str] = None):
        self.timeout = timeout
        self.max_pages = max_pages
        self.categories = self._parse_categories(category) if category else []
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://research.google/pubs/"
        self._setup_nltk()

    def _setup_nltk(self):
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('averaged_perceptron_tagger')
        except LookupError:
            nltk.download('punkt', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)

    def _extract_tags(self, text: str) -> list:
        try:
            stop_words = {}
            current_dir = os.path.dirname(__file__)
            parent_dir = os.path.dirname(current_dir)
            stop_words_file = os.path.join(parent_dir, 'common', 'stop_words.txt')

            with open(stop_words_file, 'r', encoding='utf-8') as file:
                stop_words = {line.strip().lower() for line in file}

            allowed_pos = {
                'NN', 'NNS', 'NNP', 'NNPS', 'JJ'
            }

            try:
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

            return list(set(tags))

        except Exception as e:
            self.logger.warning(f"Tag extraction failed: {e}")
            return []

    def _fetch_page(self, url: str) -> Optional[str]:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None

    def _get_publication_links(self, soup: BeautifulSoup) -> List[str]:
        links = []
        for heading in soup.select('a.row-card__heading'):
            if 'href' in heading.attrs:
                url = urljoin(self.base_url, heading['href'])
                links.append(url)
        return links
    
    def _parse_categories(self, category_string: str) -> list[str]:
        """Parse multiple categories from URL parameter string."""
        parts = category_string.split('&category=')
        
        # Clean up categories
        categories = []
        for part in parts:
            if 'category=' in part:
                part = part.split('category=')[1]
            
            if part:
                categories.append(self._normalize_category(part))
        
        return categories

    def _normalize_category(self, category: str) -> list[str]:
        """Normalize a single category name into a tag."""
        if '-and-' in category:
            return category
        
        category = category.replace('%20', '-')
        
        category = category.lower().strip()
        category = re.sub(r'[^a-z0-9-]', '', category)
        
        return category

    def _normalize_research_area(self, area: str) -> str:
        """Convert research area to normalized tag format"""
        area = re.sub(r'\s*\([^)]*\)', '', area)
        area = re.sub(r'[^a-zA-Z0-9\s]', '', area.lower())
        area = re.sub(r'\s+', '-', area.strip())
        return area

    def _clean_tags(self, tags: list[str]) -> list[str]:
        """Clean and normalize tags list."""
        compound_terms = {
            ('distributed', 'systems'): 'distributed-systems',
            ('parallel', 'computing'): 'parallel-computing',
            ('machine', 'learning'): 'machine-learning',
            ('machine', 'intelligence'): 'machine-intelligence',
            ('distributed', 'tracing'): 'distributed-tracing',
            ('file', 'system'): 'file-system',
            ('deep', 'learning'): 'deep-learning',
            ('neural', 'network'): 'neural-network',
            ('code', 'generation'): 'code-generation'
        }
        
        unique_tags = set()
        singular_forms_seen = set()
        for tag in tags:
            if '-and-' in tag:
                continue
                
            if not tag.endswith('s'):
                singular_forms_seen.add(tag)
            
            unique_tags.add(tag)
        
        final_tags = set()
        for tag in unique_tags:
            if tag.endswith('s'):
                singular = tag[:-1]
                if singular not in singular_forms_seen:
                    final_tags.add(tag)
            else:
                final_tags.add(tag)
        for term_pair, compound_term in compound_terms.items():
            if all(term in final_tags for term in term_pair):
                for term in term_pair:
                    final_tags.remove(term)
                final_tags.add(compound_term)
        
        return sorted(list(final_tags))

    def _parse_publication_page(self, url: str) -> Optional[Publication]:
        try:
            html_content = self._fetch_page(url)
            if not html_content:
                return None

            soup = BeautifulSoup(html_content, 'html.parser')
            
            title_elem = soup.select_one('h1')
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)
            
            date = str(datetime.datetime.today().strftime("%Y-%m-%d"))
            
            abstract = ""
            abstract_section = soup.find('h3', string='Abstract')
            if abstract_section:
                abstract_div = abstract_section.find_parent('section').select_one('.glue-grid__col--span-9-lg')
                if abstract_div:
                    abstract = abstract_div.get_text(strip=True)
            
            research_areas = []
            area_tags = []
            areas_section = soup.find('h3', string='Research Areas')
            if areas_section:
                areas_div = areas_section.find_parent('section').select_one('.glue-grid__col--span-9-lg')
                if areas_div:
                    area_links = areas_div.select('.glue-headline.body')
                    for area in area_links:
                        area_text = area.get_text(strip=True)
                        research_areas.append(area_text)
                        area_tags.append(self._normalize_research_area(area_text))
            
            # Extract tags from both title and abstract
            title_tags = self._extract_tags(title) if title else []
            abstract_tags = self._extract_tags(abstract) if abstract else []
            
            all_tags = []
            if self.categories:
                for category in self.categories:
                    if '-and-' in category:
                        category_parts = category.split('-and-')
                        all_tags.extend(category_parts)
                    else:
                        all_tags.append(category)
            all_tags.extend(area_tags)
            all_tags.extend(title_tags)
            all_tags.extend(abstract_tags)
            all_tags.append("google-research")
            
            final_tags = self._clean_tags(all_tags)
            
            return Publication(
                title=title,
                abstract=abstract,
                url=url,
                date=date,
                tags=final_tags,
                research_areas=research_areas
            )
            
        except Exception as e:
            self.logger.warning(f"Error parsing publication page {url}: {e}")
            return None

    def _get_next_page_url(self, page_number: int) -> str:
        url = f"{self.base_url}?page={page_number}"
        if self.categories:
            url += ''.join(f"&category={cat}" for cat in self.categories)
        return url

    def __call__(self) -> Dict:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        publications_data = {}
        
        for page in range(1, self.max_pages + 1):
            current_url = self._get_next_page_url(page)
            self.logger.info(f"Crawling page {page}: {current_url}")
            
            html_content = self._fetch_page(current_url)
            if not html_content:
                break
                
            soup = BeautifulSoup(html_content, 'html.parser')
            publication_links = self._get_publication_links(soup)
            
            if not publication_links:
                self.logger.info("No more publications found")
                break
                
            self.logger.info(f"Found {len(publication_links)} publications on page {page}")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                publications = list(executor.map(self._parse_publication_page, publication_links))
            
            for pub in publications:
                if pub:
                    publications_data[pub.url] = {
                        "title": pub.title,
                        "abstract": pub.abstract,
                        "date": pub.date,
                        "tags": pub.tags,
                        "research_areas": pub.research_areas
                    }
            
            sleep(1)
            
        self.logger.info(f"Crawling completed. Processed {len(publications_data)} publications")
        return publications_data