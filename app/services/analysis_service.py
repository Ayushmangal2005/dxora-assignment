"""Main analysis orchestration service coordinating extraction, LLM, and competitor intelligence."""

from typing import Dict, Any
from app.schemas import (
    LinkAnalysisResponse,
    BrandInfo,
    AnalysisSections,
    CompetitorAnalysis,
    SearchQueryItem,
    SeoImprovements,
    ServiceItem,
    TargetAudience,
)
from app.services.website_extractor import WebsiteExtractor
from app.services.llm_service import LLMService
from app.services.competitor_service import CompetitorService
from app.utils.validators import validate_url


class AnalysisService:
    """End-to-end pipeline orchestrator for website link analysis."""

    def __init__(self):
        self.extractor = WebsiteExtractor()
        self.llm_service = LLMService()
        self.competitor_service = CompetitorService()

    async def run_analysis(self, raw_url: str) -> LinkAnalysisResponse:
        """
        Execute full link analysis workflow:
        1. Validate URL & apply SSRF protection.
        2. Fetch & parse HTML into structured metadata and body text.
        3. Format content and invoke LLM for structured understanding.
        4. Enrich competitor intelligence.
        5. Validate against Pydantic response schemas.
        """
        # Step 1: Validate URL and enforce SSRF defenses
        validated_url = validate_url(raw_url)

        # Step 2: Fetch and extract website content
        raw_html = await self.extractor.fetch_html(validated_url)
        extracted_info = self.extractor.extract_structured_info(validated_url, raw_html)
        formatted_prompt_content = self.extractor.format_for_llm(extracted_info)

        # Step 3: Run LLM analysis
        raw_analysis = await self.llm_service.analyze_content(
            formatted_prompt_content,
            extracted_info
        )

        # Step 4: Extract brand data
        brand_data = raw_analysis.get("brand", {})
        brand_name = brand_data.get("name") or extracted_info.get("site_name") or "Your Brand"
        category = brand_data.get("category") or "General Business"
        summary = brand_data.get("summary") or extracted_info.get("meta_description") or "Business overview."

        brand = BrandInfo(
            name=brand_name,
            category=category,
            summary=summary
        )

        # Step 5: Process the 5 sections
        analysis_data = raw_analysis.get("analysis", {})

        # Section 1: Competitors
        raw_comp = analysis_data.get("competitor_analysis", {})
        competitor_analysis = self.competitor_service.validate_and_enrich_competitors(
            raw_comp,
            brand_name=brand_name,
            category=category
        )

        # Section 2: Search Queries (ensure 5 queries)
        raw_queries = analysis_data.get("target_search_queries", [])
        queries = []
        for q in raw_queries:
            if isinstance(q, dict):
                queries.append(
                    SearchQueryItem(
                        query=q.get("query", "Target query"),
                        platforms=q.get("platforms", ["Google"]),
                        intent=q.get("intent", "Service Discovery"),
                        business_relevance=q.get("business_relevance", "High commercial intent"),
                        target_audience=q.get("target_audience", "Target customer")
                    )
                )
        # Ensure 5 search queries
        platform_presets = [
            ("Google", "Service Search", "High search intent for service provider evaluation"),
            ("LinkedIn", "B2B Search", "B2B networking and vendor selection"),
            ("X", "Industry Discovery", "Thought leadership and trending discussions"),
            ("Facebook", "Community Discovery", "Local business search and recommendations"),
            ("Instagram", "Inspiration", "Visual proof and brand inspiration")
        ]
        while len(queries) < 5:
            idx = len(queries)
            plat, intent, rev = platform_presets[idx % len(platform_presets)]
            queries.append(
                SearchQueryItem(
                    query=f"Best {category.lower()} provider for businesses",
                    platforms=[plat],
                    intent=intent,
                    business_relevance=rev,
                    target_audience="Prospective buyers and business owners"
                )
            )
        queries = queries[:5]

        # Section 3: SEO Improvements
        raw_seo = analysis_data.get("seo_improvements", {})
        seo_improvements = SeoImprovements(
            primary_keyword=raw_seo.get("primary_keyword", f"{category} Services"),
            secondary_keywords=raw_seo.get("secondary_keywords", [f"{category} expert", f"{category} solutions"]),
            long_tail_keywords=raw_seo.get("long_tail_keywords", [f"best {category.lower()} company for growing business"]),
            recommended_title=raw_seo.get("recommended_title", f"{brand_name} | Leading {category} Solutions"),
            meta_description=raw_seo.get("meta_description", f"Explore top-tier {category.lower()} with {brand_name}. Dedicated quality and verified results."),
            supporting_content=raw_seo.get("supporting_content", [
                "Comprehensive Service Breakdown Page",
                "Customer FAQs and Onboarding Guide",
                "Industry Case Studies",
                "Topical Blog Articles"
            ])
        )

        # Section 4: Top 5 Services
        raw_services = analysis_data.get("top_services", [])
        services = []
        for s in raw_services:
            if isinstance(s, dict):
                services.append(
                    ServiceItem(
                        service_name=s.get("service_name", "Core Service"),
                        description=s.get("description", "Comprehensive service offering."),
                        target_industry=s.get("target_industry", category),
                        target_customer=s.get("target_customer", "Target Clients"),
                        main_benefit=s.get("main_benefit", "High efficiency and measurable results"),
                        is_inferred=s.get("is_inferred", False)
                    )
                )
        while len(services) < 5:
            idx = len(services) + 1
            services.append(
                ServiceItem(
                    service_name=f"Consulting Service #{idx}",
                    description=f"Specialized consultation and delivery in {category}.",
                    target_industry=category,
                    target_customer="Enterprise & SMBs",
                    main_benefit="Enhanced operational productivity and competitive edge",
                    is_inferred=True
                )
            )
        services = services[:5]

        # Section 5: Target Audience
        raw_audience = analysis_data.get("target_audience", {})
        target_audience = TargetAudience(
            primary_audience=raw_audience.get("primary_audience", ["Business Owners", "Decision Makers"]),
            secondary_audience=raw_audience.get("secondary_audience", ["Department Heads", "Consultants"]),
            industries=raw_audience.get("industries", [category, "Technology", "Commercial Services"]),
            business_types=raw_audience.get("business_types", ["Startups", "Mid-sized Enterprises", "Corporations"]),
            customer_profiles=raw_audience.get("customer_profiles", ["Founder & CEO", "VP of Operations"]),
            geographical_focus=raw_audience.get("geographical_focus", "Global"),
            customer_needs=raw_audience.get("customer_needs", ["Reliable execution", "Scalable support", "High ROI"]),
            potential_interests=raw_audience.get("potential_interests", ["Productivity", "Innovation", "Cost-efficiency"]),
            recommended_marketing_segments=raw_audience.get("recommended_marketing_segments", [
                "Decision makers on LinkedIn",
                "Intent-based searchers on Google"
            ])
        )

        sections = AnalysisSections(
            competitor_analysis=competitor_analysis,
            target_search_queries=queries,
            seo_improvements=seo_improvements,
            top_services=services,
            target_audience=target_audience
        )

        return LinkAnalysisResponse(
            success=True,
            website=validated_url,
            brand=brand,
            analysis=sections
        )
