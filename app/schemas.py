"""Pydantic schemas for request, response, and structured analysis."""

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# Request Models
# ---------------------------------------------------------

class LinkAnalysisRequest(BaseModel):
    """Request payload for website link analysis."""
    url: str = Field(
        ...,
        description="The full URL of the website to analyze (e.g. https://example.com)",
        json_schema_extra={"example": "https://example.com"}
    )


# ---------------------------------------------------------
# Section 1: Competitor vs Your Brand Details
# ---------------------------------------------------------

class CompetitorItem(BaseModel):
    """Detailed competitor comparison entry."""
    name: str = Field(..., description="Competitor brand name")
    main_service: str = Field(..., description="Competitor's primary product or service")
    target_market: str = Field(..., description="Target market or customer segment (e.g., Enterprise, SMBs)")
    key_strength: str = Field(..., description="Key competitive strength")
    weakness_or_gap: str = Field(..., description="Weakness, vulnerability, or market gap")
    opportunity: str = Field(..., description="Opportunity for your brand against this competitor")


class CompetitorAnalysis(BaseModel):
    """Section 1: Competitor vs Your Brand analysis."""
    brand_overview: str = Field(..., description="Comprehensive overview of your brand")
    main_business_category: str = Field(..., description="Primary industry or business category")
    main_products_and_services: List[str] = Field(default_factory=list, description="List of primary products and services")
    competitors: List[CompetitorItem] = Field(
        default_factory=list,
        description="List of minimum 3 identified industry competitors"
    )
    strengths: List[str] = Field(default_factory=list, description="Your brand's core strengths and competitive advantages")
    competitive_advantages: List[str] = Field(default_factory=list, description="Specific differentiators vs competitors")
    opportunities: List[str] = Field(default_factory=list, description="Actionable opportunities to improve market positioning")


# ---------------------------------------------------------
# Section 2: Top 5 Target Search Queries
# ---------------------------------------------------------

class SearchQueryItem(BaseModel):
    """Section 2: Search query across search engines and social platforms."""
    query: str = Field(..., description="Target search query or phrase")
    platforms: List[str] = Field(
        ...,
        description="Relevant platforms (e.g., Google, Facebook, Instagram, LinkedIn, X)"
    )
    intent: str = Field(..., description="Search intent (e.g., Service Discovery, B2B Search, Inspiration, Commercial)")
    business_relevance: str = Field(..., description="Why this query is critical to the business")
    target_audience: str = Field(..., description="Audience demographic or persona executing this search")


# ---------------------------------------------------------
# Section 3: SEO Improvement
# ---------------------------------------------------------

class SeoImprovements(BaseModel):
    """Section 3: Comprehensive SEO recommendations and keyword intelligence."""
    primary_keyword: str = Field(..., description="Single most impactful target keyword for the brand")
    secondary_keywords: List[str] = Field(default_factory=list, description="Relevant secondary search keywords")
    long_tail_keywords: List[str] = Field(default_factory=list, description="High-intent long-tail keyword phrases")
    recommended_title: str = Field(..., description="Optimized, high-CTR SEO title tag")
    meta_description: str = Field(..., description="Human-friendly meta description under 160 characters")
    supporting_content: List[str] = Field(
        default_factory=list,
        description="Recommended supporting pages, blog topics, FAQs, and industry landing pages"
    )


# ---------------------------------------------------------
# Section 4: Top 5 Services
# ---------------------------------------------------------

class ServiceItem(BaseModel):
    """Section 4: Service details identified from the website."""
    service_name: str = Field(..., description="Name of the service")
    description: str = Field(..., description="Short explanation of what the service offers")
    target_industry: str = Field(..., description="Relevant business vertical or industry")
    target_customer: str = Field(..., description="Ideal customer persona or company type")
    main_benefit: str = Field(..., description="Primary value proposition or customer outcome")
    is_inferred: bool = Field(
        default=False,
        description="True if inferred by AI; False if explicitly extracted from website text"
    )


# ---------------------------------------------------------
# Section 5: Target Audience Identification
# ---------------------------------------------------------

class TargetAudience(BaseModel):
    """Section 5: Target audience segmentation and profile."""
    primary_audience: List[str] = Field(default_factory=list, description="Core target audience groups")
    secondary_audience: List[str] = Field(default_factory=list, description="Secondary or adjacent audience groups")
    industries: List[str] = Field(default_factory=list, description="Target industry verticals")
    business_types: List[str] = Field(default_factory=list, description="Business structures (e.g. Startups, SMBs, Enterprise)")
    customer_profiles: List[str] = Field(default_factory=list, description="Buyer personas or decision-maker titles")
    geographical_focus: str = Field(default="Global", description="Target geography or regional scope")
    customer_needs: List[str] = Field(default_factory=list, description="Pain points, requirements, and challenges solved")
    potential_interests: List[str] = Field(default_factory=list, description="Key interests, topics, and values")
    recommended_marketing_segments: List[str] = Field(
        default_factory=list,
        description="Recommended actionable segments for ad targeting and outreach"
    )


# ---------------------------------------------------------
# Aggregated Analysis & Response
# ---------------------------------------------------------

class BrandInfo(BaseModel):
    """Extracted high-level brand details."""
    name: str = Field(..., description="Identified brand or business name")
    category: str = Field(..., description="Main business category")
    summary: str = Field(..., description="High-level business summary")


class AnalysisSections(BaseModel):
    """The 5 structured analysis sections."""
    competitor_analysis: CompetitorAnalysis
    target_search_queries: List[SearchQueryItem]
    seo_improvements: SeoImprovements
    top_services: List[ServiceItem]
    target_audience: TargetAudience


class LinkAnalysisResponse(BaseModel):
    """Final API response matching specification."""
    success: bool = True
    website: str
    brand: BrandInfo
    analysis: AnalysisSections


class ErrorResponse(BaseModel):
    """Standard error response format."""
    success: bool = False
    error: str
    code: Optional[str] = None
    detail: Optional[str] = None
