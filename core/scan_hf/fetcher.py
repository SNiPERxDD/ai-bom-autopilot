import requests
import yaml
import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class HFCard:
    """HuggingFace model/dataset card"""
    slug: str
    type: str  # 'model' or 'dataset'
    license: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    datasets: List[str] = field(default_factory=list)
    model_type: Optional[str] = None
    pipeline_tag: Optional[str] = None
    library_name: Optional[str] = None
    raw_card: Dict[str, Any] = field(default_factory=dict)
    version: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)

@dataclass
class CacheEntry:
    """Cache entry with TTL support"""
    data: HFCard
    expires_at: datetime
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

class HuggingFaceFetcher:
    """Fetches model and dataset cards from HuggingFace with TTL-based caching"""
    
    def __init__(self, cache_ttl_hours: int = None):
        self.base_url = "https://huggingface.co"
        self.api_url = "https://huggingface.co/api"
        self.session = requests.Session()
        
        # Configure TTL from environment or default to 24 hours
        self.cache_ttl_hours = cache_ttl_hours or int(os.getenv('HF_CACHE_TTL_HOURS', '24'))
        self.cache: Dict[str, CacheEntry] = {}  # TTL-based cache
        
        # Set up session headers
        hf_token = os.getenv('HUGGINGFACE_TOKEN')
        if hf_token:
            self.session.headers.update({'Authorization': f'Bearer {hf_token}'})
        
    def fetch_card(self, slug: str, version: Optional[str] = None) -> Optional[HFCard]:
        """Fetch model or dataset card from HuggingFace with caching"""
        cache_key = f"{slug}:{version}" if version else slug
        
        # Check cache first
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if not entry.is_expired():
                logger.debug(f"Cache hit for {cache_key}")
                return entry.data
            else:
                # Remove expired entry
                del self.cache[cache_key]
                logger.debug(f"Cache expired for {cache_key}")
        
        try:
            # Try model first
            card = self._fetch_model_card(slug, version)
            if card:
                self._cache_card(cache_key, card)
                return card
            
            # Try dataset
            card = self._fetch_dataset_card(slug, version)
            if card:
                self._cache_card(cache_key, card)
                return card
                
        except Exception as e:
            logger.error(f"Failed to fetch card for {slug}: {e}")
        
        return None
    
    def _cache_card(self, cache_key: str, card: HFCard) -> None:
        """Cache a card with TTL"""
        expires_at = datetime.now() + timedelta(hours=self.cache_ttl_hours)
        self.cache[cache_key] = CacheEntry(data=card, expires_at=expires_at)
        logger.debug(f"Cached {cache_key} until {expires_at}")
    
    def clear_expired_cache(self) -> int:
        """Remove expired entries from cache and return count removed"""
        expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"Cleared {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self.cache)
        expired_entries = sum(1 for entry in self.cache.values() if entry.is_expired())
        
        return {
            'total_entries': total_entries,
            'active_entries': total_entries - expired_entries,
            'expired_entries': expired_entries,
            'cache_ttl_hours': self.cache_ttl_hours
        }
    
    def _fetch_model_card(self, slug: str, version: Optional[str] = None) -> Optional[HFCard]:
        """Fetch model card with optional version/revision"""
        try:
            # Get model info from API
            api_url = f"{self.api_url}/models/{slug}"
            if version:
                api_url += f"?revision={version}"
            
            response = self._make_request(api_url)
            
            if response.status_code != 200:
                logger.debug(f"Model API returned {response.status_code} for {slug}")
                return None
            
            model_info = response.json()
            
            # Get README content (try version-specific first, then main)
            revision = version or "main"
            readme_url = f"{self.base_url}/{slug}/raw/{revision}/README.md"
            readme_response = self._make_request(readme_url)
            
            # If version-specific README fails, try main
            if readme_response.status_code != 200 and version:
                readme_url = f"{self.base_url}/{slug}/raw/main/README.md"
                readme_response = self._make_request(readme_url)
            
            card_data = {}
            if readme_response.status_code == 200:
                card_data = self._parse_card_yaml(readme_response.text)
            
            # Extract version info
            card_version = version or model_info.get('sha', model_info.get('id', 'main'))
            
            return HFCard(
                slug=slug,
                type="model",
                version=card_version,
                license=card_data.get('license') or model_info.get('license'),
                tags=model_info.get('tags', []),
                datasets=card_data.get('datasets', []),
                model_type=self._extract_model_type(model_info, card_data),
                pipeline_tag=model_info.get('pipeline_tag'),
                library_name=model_info.get('library_name'),
                raw_card=model_info
            )
            
        except Exception as e:
            logger.warning(f"Failed to fetch model card for {slug}: {e}")
            return None
    
    def _fetch_dataset_card(self, slug: str, version: Optional[str] = None) -> Optional[HFCard]:
        """Fetch dataset card with optional version/revision"""
        try:
            # Get dataset info from API
            api_url = f"{self.api_url}/datasets/{slug}"
            if version:
                api_url += f"?revision={version}"
            
            response = self._make_request(api_url)
            
            if response.status_code != 200:
                logger.debug(f"Dataset API returned {response.status_code} for {slug}")
                return None
            
            dataset_info = response.json()
            
            # Get README content (try version-specific first, then main)
            revision = version or "main"
            readme_url = f"{self.base_url}/datasets/{slug}/raw/{revision}/README.md"
            readme_response = self._make_request(readme_url)
            
            # If version-specific README fails, try main
            if readme_response.status_code != 200 and version:
                readme_url = f"{self.base_url}/datasets/{slug}/raw/main/README.md"
                readme_response = self._make_request(readme_url)
            
            card_data = {}
            if readme_response.status_code == 200:
                card_data = self._parse_card_yaml(readme_response.text)
            
            # Extract version info
            card_version = version or dataset_info.get('sha', dataset_info.get('id', 'main'))
            
            return HFCard(
                slug=slug,
                type="dataset",
                version=card_version,
                license=card_data.get('license') or dataset_info.get('license'),
                tags=dataset_info.get('tags', []),
                datasets=card_data.get('datasets', []),
                raw_card=dataset_info
            )
            
        except Exception as e:
            logger.warning(f"Failed to fetch dataset card for {slug}: {e}")
            return None
    
    def _extract_model_type(self, model_info: Dict[str, Any], card_data: Dict[str, Any]) -> Optional[str]:
        """Extract model type from API response and card data"""
        # Try card data first
        if 'model_type' in card_data:
            return card_data['model_type']
        
        # Try model-index from API
        if model_info.get('model-index'):
            model_index = model_info['model-index']
            if isinstance(model_index, list) and len(model_index) > 0:
                return model_index[0].get('name')
        
        # Try pipeline_tag as fallback
        return model_info.get('pipeline_tag')
    
    def _parse_card_yaml(self, readme_content: str) -> Dict[str, Any]:
        """Parse YAML front-matter from README with improved error handling"""
        try:
            if not readme_content or not readme_content.strip().startswith('---'):
                return {}
            
            # Find the end of YAML front-matter
            lines = readme_content.split('\n')
            yaml_end = -1
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    yaml_end = i
                    break
            
            if yaml_end == -1:
                logger.debug("No closing --- found in YAML front-matter")
                return {}
            
            yaml_content = '\n'.join(lines[1:yaml_end])
            if not yaml_content.strip():
                return {}
            
            parsed = yaml.safe_load(yaml_content)
            return parsed if isinstance(parsed, dict) else {}
            
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML front-matter: {e}")
            return {}
        except Exception as e:
            logger.warning(f"Unexpected error parsing YAML front-matter: {e}")
            return {}
    
    def _make_request(self, url: str, max_retries: int = 3) -> requests.Response:
        """Make HTTP request with retries and rate limiting"""
        for attempt in range(max_retries):
            try:
                # Add small delay to respect rate limits
                if attempt > 0:
                    time.sleep(min(2 ** attempt, 10))  # Exponential backoff, max 10s
                
                response = self.session.get(url, timeout=30)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited, waiting {retry_after}s before retry")
                    time.sleep(retry_after)
                    continue
                
                return response
                
            except requests.Timeout as e:
                logger.warning(f"Request timeout (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
        
        raise requests.RequestException("Max retries exceeded")
    
    def batch_fetch_cards(self, slugs: List[str], versions: Optional[List[str]] = None) -> Dict[str, HFCard]:
        """Fetch multiple cards with rate limiting and progress logging"""
        cards = {}
        total = len(slugs)
        
        # Ensure versions list matches slugs length if provided
        if versions and len(versions) != len(slugs):
            raise ValueError("versions list must match slugs list length")
        
        logger.info(f"Fetching {total} HuggingFace cards...")
        
        for i, slug in enumerate(slugs):
            # Rate limiting: pause every 10 requests
            if i > 0 and i % 10 == 0:
                logger.debug(f"Rate limiting pause after {i} requests")
                time.sleep(1)
            
            # Progress logging
            if i > 0 and i % 50 == 0:
                logger.info(f"Progress: {i}/{total} cards fetched")
            
            version = versions[i] if versions else None
            card = self.fetch_card(slug, version)
            if card:
                cards[slug] = card
            else:
                logger.debug(f"Failed to fetch card for {slug}")
        
        logger.info(f"Successfully fetched {len(cards)}/{total} cards")
        return cards
    
    def validate_slug(self, slug: str) -> bool:
        """Validate HuggingFace slug format"""
        if not slug or '/' not in slug:
            return False
        
        parts = slug.split('/')
        if len(parts) != 2:
            return False
        
        # Basic validation: no empty parts, reasonable characters
        username, repo = parts
        if not username or not repo:
            return False
        
        # Allow alphanumeric, hyphens, underscores, dots
        import re
        pattern = r'^[a-zA-Z0-9._-]+$'
        return bool(re.match(pattern, username) and re.match(pattern, repo))