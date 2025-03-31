## This tool uses duckduckgo-search-python to search the web for a specific song and return the results.

from duckduckgo_search import DDGS
from typing import List, Dict
import asyncio
import logging
from duckduckgo_search.exceptions import DuckDuckGoSearchException
import time
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logger = logging.getLogger(__name__)

class RateLimitedDDGS:
    def __init__(self):
        self.ddgs = DDGS()
        self.last_request_time = 0
        self.min_delay = 1.0  # Minimum 1 second between requests

    def _wait_for_rate_limit(self):
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_delay:
            time.sleep(self.min_delay - time_since_last)
        self.last_request_time = time.time()

    @retry(
        retry=retry_if_exception_type(DuckDuckGoSearchException),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3)
    )
    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        self._wait_for_rate_limit()
        results = []
        try:
            for r in self.ddgs.text(f"{query} lyrics", max_results=max_results):
                logger.debug(f"Found raw result: {r}")
                processed = {
                    'title': r.get('title', ''),
                    'link': r.get('href', ''),
                    'snippet': r.get('body', r.get('snippet', ''))
                }
                logger.debug(f"Processed result: {processed}")
                results.append(processed)
        except DuckDuckGoSearchException as e:
            logger.warning(f"Search attempt failed: {e}")
            raise
        return results

# Create a singleton instance
ddgs_client = RateLimitedDDGS()

async def search_web(query: str) -> List[Dict]:
    """
    Search the web for song lyrics
    """
    logger.debug(f"Searching for: {query}")
    try:
        results = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: ddgs_client.search(query)
        )
        logger.debug(f"Search returned {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise
