"""Comprehensive test suite for AI-Powered Website Link Analysis API."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.utils.validators import validate_url, is_private_or_restricted_ip
from app.services.website_extractor import WebsiteExtractor, WebsiteExtractionError
from app.services.competitor_service import CompetitorService
from app.services.llm_service import LLMService

client = TestClient(app)

SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Acme Software - Enterprise Cloud Solutions</title>
    <meta name="description" content="Acme Software delivers mission-critical cloud migration and AI engineering.">
    <meta property="og:site_name" content="Acme Software">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Acme Software",
        "description": "Enterprise cloud services"
    }
    </script>
</head>
<body>
    <header>
        <nav>
            <a href="/services/cloud-migration">Cloud Migration</a>
            <a href="/services/ai-consulting">AI Consulting</a>
            <a href="/services/devops">DevOps Automation</a>
            <a href="/services/cybersecurity">Cybersecurity</a>
            <a href="/services/data-analytics">Data Analytics</a>
        </nav>
    </header>
    <main>
        <h1>Next-Generation Enterprise Cloud Platforms</h1>
        <h2>Accelerate Your Digital Transformation</h2>
        <p>Acme Software empowers Fortune 500 enterprises to modernize legacy infrastructure with secure, scalable cloud architectures.</p>
        <p>Our dedicated architects guarantee 99.99% uptime and accelerated time-to-market.</p>
    </main>
    <footer>
        <p>&copy; 2026 Acme Software Inc.</p>
    </footer>
</body>
</html>
"""


# ---------------------------------------------------------
# 1. URL Validation & SSRF Protection Tests
# ---------------------------------------------------------

class TestURLValidationAndSSRF:
    @patch("socket.getaddrinfo")
    def test_valid_urls_pass(self, mock_getaddrinfo):
        # Mock public IP resolution for example.com
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        assert validate_url("https://example.com") == "https://example.com"
        assert validate_url("http://example.com") == "http://example.com"
        assert validate_url("example.com") == "https://example.com"

    def test_localhost_and_loopback_blocked(self):
        with pytest.raises(ValueError, match="SSRF"):
            validate_url("http://localhost:8000")
        with pytest.raises(ValueError, match="SSRF"):
            validate_url("http://127.0.0.1:4000")
        with pytest.raises(ValueError, match="SSRF"):
            validate_url("http://0.0.0.0")

    def test_private_ips_blocked(self):
        with pytest.raises(ValueError, match="SSRF"):
            validate_url("http://192.168.1.1/admin")
        with pytest.raises(ValueError, match="SSRF"):
            validate_url("http://10.0.0.5")
        with pytest.raises(ValueError, match="SSRF"):
            validate_url("http://172.16.0.1")

    def test_cloud_metadata_blocked(self):
        with pytest.raises(ValueError, match="SSRF"):
            validate_url("http://169.254.169.254/latest/meta-data")
        with pytest.raises(ValueError, match="SSRF"):
            validate_url("http://metadata.google.internal")

    @patch("socket.getaddrinfo")
    def test_domain_resolving_to_private_ip_blocked(self, mock_getaddrinfo):
        # Simulate DNS rebinding or internal domain resolving to private IP
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("192.168.1.50", 0))]
        with pytest.raises(ValueError, match="restricted internal IP"):
            validate_url("https://internal-portal.corp")

    def test_invalid_scheme_rejected(self):
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            validate_url("ftp://ftp.example.com")
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            validate_url("javascript:alert(1)")

    def test_empty_or_non_string_url_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            validate_url("")
        with pytest.raises(ValueError, match="non-empty string"):
            validate_url(None)


# ---------------------------------------------------------
# 2. Website Extractor Unit Tests
# ---------------------------------------------------------

class TestWebsiteExtractor:
    def test_extract_structured_info(self):
        extractor = WebsiteExtractor()
        data = extractor.extract_structured_info("https://acmesoftware.com", SAMPLE_HTML)

        assert data["title"] == "Acme Software - Enterprise Cloud Solutions"
        assert "cloud migration" in data["meta_description"].lower()
        assert data["site_name"] == "Acme Software"
        assert len(data["headings"]) >= 2
        assert any("Cloud Migration" in link for link in data["nav_links"])
        assert "Acme Software empowers" in data["body_text"]

    def test_empty_html_raises_error(self):
        extractor = WebsiteExtractor()
        with pytest.raises(WebsiteExtractionError, match="empty"):
            extractor.extract_structured_info("https://example.com", "   ")

    def test_format_for_llm(self):
        extractor = WebsiteExtractor()
        data = extractor.extract_structured_info("https://acmesoftware.com", SAMPLE_HTML)
        formatted = extractor.format_for_llm(data)

        assert "# WEBSITE CONTENT ANALYSIS FOR:" in formatted
        assert "Acme Software" in formatted
        assert "Key Headings:" in formatted


# ---------------------------------------------------------
# 3. Competitor Service Unit Tests
# ---------------------------------------------------------

class TestCompetitorService:
    def test_validate_and_enrich_competitors_minimum_count(self):
        service = CompetitorService()
        raw_data = {"competitors": [{"name": "Comp1", "main_service": "Cloud", "target_market": "SMB", "key_strength": "Price", "weakness_or_gap": "Scale", "opportunity": "Enterprise"}]}
        result = service.validate_and_enrich_competitors(raw_data, "MyBrand", "Cloud Computing")

        # Minimum 3 competitors must be present
        assert len(result.competitors) >= 3
        assert result.brand_overview is not None
        assert len(result.strengths) > 0
        assert len(result.opportunities) > 0

    def test_comparison_table_formatting(self):
        service = CompetitorService()
        raw_data = {"competitors": []}
        result = service.validate_and_enrich_competitors(raw_data, "MyBrand", "Cloud Computing")
        matrix = service.format_comparison_table(
            "MyBrand", "Cloud Computing", "Enterprise", "Reliability", result.competitors
        )
        assert len(matrix) >= 4  # 1 brand + min 3 competitors
        assert matrix[0]["role"] == "Your Brand"
        assert matrix[1]["role"] == "Competitor"


# ---------------------------------------------------------
# 4. LLM Service Unit Tests
# ---------------------------------------------------------

class TestLLMService:
    def test_json_cleaner(self):
        service = LLMService()
        # Test clean JSON
        assert service._clean_and_parse_json('{"key": "value"}') == {"key": "value"}

        # Test markdown fenced JSON
        fenced = "```json\n{\"test\": 123}\n```"
        assert service._clean_and_parse_json(fenced) == {"test": 123}

        # Test fenced without json label
        fenced_plain = "```\n{\"status\": \"ok\"}\n```"
        assert service._clean_and_parse_json(fenced_plain) == {"status": "ok"}

    def test_fallback_analysis_structure(self):
        service = LLMService()
        raw_info = {
            "title": "Alpha Cloud | Enterprise Cloud Solutions",
            "site_name": "Alpha Cloud",
            "meta_description": "Premier enterprise cloud architecture.",
            "headings": ["[H1] Scalable Cloud Infrastructure"],
            "nav_links": ["Cloud Migration", "Managed Kubernetes", "DevOps"],
        }
        res = service._generate_fallback_analysis(raw_info)
        assert "brand" in res
        assert "analysis" in res
        analysis = res["analysis"]
        assert "competitor_analysis" in analysis
        assert len(analysis["competitor_analysis"]["competitors"]) >= 3
        assert len(analysis["target_search_queries"]) == 5
        assert "seo_improvements" in analysis
        assert len(analysis["top_services"]) == 5
        assert "target_audience" in analysis


# ---------------------------------------------------------
# 5. End-to-End API Route Tests
# ---------------------------------------------------------

class TestAPIRoutes:
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["docs"] == "/docs"

    def test_health_endpoint(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_ssrf_blocked_at_api_endpoint(self):
        response = client.post("/link-analysis", json={"url": "http://127.0.0.1:4000"})
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["code"] == "VALIDATION_OR_SSRF_ERROR"
        assert "SSRF" in data["error"]

    def test_invalid_url_rejected_at_api_endpoint(self):
        response = client.post("/link-analysis", json={"url": "ftp://files.example.com"})
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["code"] == "VALIDATION_OR_SSRF_ERROR"

    @patch("socket.getaddrinfo")
    @patch("app.services.website_extractor.WebsiteExtractor.fetch_html", new_callable=AsyncMock)
    def test_successful_analysis_flow(self, mock_fetch, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        mock_fetch.return_value = SAMPLE_HTML

        response = client.post("/link-analysis", json={"url": "https://acmesoftware.com"})
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["website"] == "https://acmesoftware.com"

        # Brand Check
        assert "brand" in data
        assert "name" in data["brand"]
        assert "category" in data["brand"]
        assert "summary" in data["brand"]

        analysis = data["analysis"]

        # Section 1: Competitors
        comp = analysis["competitor_analysis"]
        assert "brand_overview" in comp
        assert len(comp["competitors"]) >= 3
        assert len(comp["strengths"]) > 0
        assert len(comp["opportunities"]) > 0

        # Section 2: Top 5 Target Search Queries
        queries = analysis["target_search_queries"]
        assert len(queries) == 5
        for q in queries:
            assert "query" in q
            assert len(q["platforms"]) >= 1
            assert "intent" in q
            assert "business_relevance" in q
            assert "target_audience" in q

        # Section 3: SEO Improvements
        seo = analysis["seo_improvements"]
        assert "primary_keyword" in seo
        assert len(seo["secondary_keywords"]) > 0
        assert "recommended_title" in seo
        assert "meta_description" in seo
        assert len(seo["supporting_content"]) > 0

        # Section 4: Top 5 Services
        services = analysis["top_services"]
        assert len(services) == 5
        for s in services:
            assert "service_name" in s
            assert "description" in s
            assert "target_industry" in s
            assert "target_customer" in s
            assert "main_benefit" in s
            assert "is_inferred" in s

        # Section 5: Target Audience
        aud = analysis["target_audience"]
        assert len(aud["primary_audience"]) > 0
        assert len(aud["industries"]) > 0
        assert len(aud["business_types"]) > 0
        assert len(aud["customer_profiles"]) > 0
        assert len(aud["customer_needs"]) > 0
