"""Website content extraction and HTML processing service."""

import json
import re
from typing import Dict, List, Optional
import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.utils.validators import validate_url


class WebsiteExtractionError(Exception):
    """Raised when website fetching or parsing fails."""
    pass


class WebsiteExtractor:
    """Fetches, cleans, and extracts structured semantic content from web pages."""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    async def fetch_html(self, url: str) -> str:
        """Fetch raw HTML content with timeout and error handling."""
        # Re-validate URL before fetching to ensure safety
        validated_url = validate_url(url)

        async with httpx.AsyncClient(
            timeout=settings.SCRAPE_TIMEOUT_SECONDS,
            headers=self.DEFAULT_HEADERS,
            follow_redirects=True,
            verify=False,  # Avoid failing on common enterprise self-signed certs
        ) as client:
            try:
                response = await client.get(validated_url)
                
                # Check final URL after redirects for SSRF
                if str(response.url) != validated_url:
                    validate_url(str(response.url))

                response.raise_for_status()
                return response.text

            except httpx.TimeoutException:
                raise WebsiteExtractionError(
                    f"Connection to '{url}' timed out after {settings.SCRAPE_TIMEOUT_SECONDS} seconds."
                )
            except httpx.HTTPStatusError as e:
                raise WebsiteExtractionError(
                    f"Website returned HTTP error status {e.response.status_code} ({e.response.reason_phrase})."
                )
            except httpx.RequestError as e:
                raise WebsiteExtractionError(
                    f"Failed to connect to website '{url}': {str(e)}"
                )

    def extract_structured_info(self, url: str, html: str) -> Dict[str, any]:
        """Parse HTML and extract metadata, headings, navigation links, and cleaned body content."""
        if not html or not html.strip():
            raise WebsiteExtractionError("Fetched webpage content is empty.")

        soup = BeautifulSoup(html, "html.parser")

        # 1. Page Title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("meta", property="og:title"):
            title = soup.find("meta", property="og:title").get("content", "").strip()

        # 2. Meta Description
        meta_desc = ""
        meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if meta_desc_tag:
            meta_desc = meta_desc_tag.get("content", "").strip()
        elif soup.find("meta", property="og:description"):
            meta_desc = soup.find("meta", property="og:description").get("content", "").strip()

        # 3. Brand / Site Name
        site_name = ""
        site_name_tag = soup.find("meta", property="og:site_name")
        if site_name_tag:
            site_name = site_name_tag.get("content", "").strip()

        # 4. JSON-LD Structured Data
        json_ld_data: List[Dict] = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                if script.string:
                    parsed = json.loads(script.string.strip())
                    if isinstance(parsed, dict):
                        json_ld_data.append(parsed)
                    elif isinstance(parsed, list):
                        json_ld_data.extend([item for item in parsed if isinstance(item, dict)])
            except Exception:
                continue

        # 5. Extract Key Navigation & Service Links
        nav_links: List[str] = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"].lower()
            if text and len(text) < 40:
                if any(k in href for k in ["service", "product", "solution", "about", "pricing", "feature"]):
                    if text not in nav_links:
                        nav_links.append(text)
        nav_links = nav_links[:15]  # Top 15 relevant navigation items

        # 6. Headings (H1, H2, H3)
        headings: List[str] = []
        for tag in soup.find_all(["h1", "h2", "h3"]):
            text = tag.get_text(separator=" ", strip=True)
            if text and len(text) > 3:
                headings.append(f"[{tag.name.upper()}] {text}")
        headings = headings[:25]  # Cap top 25 headings

        # 7. Strip unwanted tags for clean body text
        for element in soup(["script", "style", "noscript", "svg", "iframe", "head"]):
            element.decompose()

        # Remove header and footer after preserving navigation links
        for element in soup(["header", "footer"]):
            element.decompose()

        # Extract main text
        raw_text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        # Deduplicate consecutive or repeating lines
        cleaned_lines: List[str] = []
        seen = set()
        for line in lines:
            if len(line) < 3:
                continue
            line_lower = line.lower()
            if line_lower not in seen:
                seen.add(line_lower)
                cleaned_lines.append(line)

        cleaned_body = "\n".join(cleaned_lines)

        # Budget length limit for LLM prompt
        if len(cleaned_body) > settings.MAX_EXTRACTED_CHARACTERS:
            cleaned_body = cleaned_body[: settings.MAX_EXTRACTED_CHARACTERS] + "\n...[truncated for token optimization]"

        return {
            "url": url,
            "title": title,
            "meta_description": meta_desc,
            "site_name": site_name,
            "json_ld": json_ld_data[:3],
            "nav_links": nav_links,
            "headings": headings,
            "body_text": cleaned_body,
        }

    def format_for_llm(self, data: Dict[str, any]) -> str:
        """Format the extracted content into a clean markdown document for the LLM."""
        sections = [
            f"# WEBSITE CONTENT ANALYSIS FOR: {data['url']}",
            f"**Page Title:** {data.get('title') or 'N/A'}",
            f"**Meta Description:** {data.get('meta_description') or 'N/A'}",
            f"**Site Name:** {data.get('site_name') or 'N/A'}",
        ]

        if data.get("headings"):
            sections.append("\n### Key Headings:")
            sections.extend([f"- {h}" for h in data["headings"]])

        if data.get("nav_links"):
            sections.append("\n### Services & Solutions Navigation Items:")
            sections.extend([f"- {n}" for n in data["nav_links"]])

        if data.get("json_ld"):
            sections.append("\n### Structured Metadata (JSON-LD):")
            sections.append(json.dumps(data["json_ld"], indent=2))

        sections.append("\n### Extracted Body Content:")
        sections.append(data.get("body_text", ""))

        return "\n".join(sections)
