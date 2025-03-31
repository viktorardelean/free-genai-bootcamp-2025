## This tool takes web page content and parses into to extract out the target content.

import aiohttp
from bs4 import BeautifulSoup

async def get_page_content(url: str) -> str:
    """Get content from a webpage"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove scripts, styles, etc.
            for tag in soup(['script', 'style', 'meta', 'link']):
                tag.decompose()
                
            return soup.get_text(strip=True)

