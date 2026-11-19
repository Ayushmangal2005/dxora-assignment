"""LLM integration service supporting Google Gemini and OpenAI with JSON structured output."""

import json
import re
from typing import Any, Dict
from app.config import settings


class LLMServiceError(Exception):
    """Raised when LLM processing or response parsing fails."""
    pass


class LLMService:
    """Orchestrates structured LLM analysis using Google Gemini or OpenAI."""

    SYSTEM_PROMPT = """
You are an expert AI Business Strategist, Competitor Intelligence Analyst, and Technical SEO Specialist.
Analyze the provided website content and generate an accurate, in-depth, structured business intelligence report.

Return STRICTLY a valid JSON object matching this structure (no additional prose or conversational text):
{
  "brand": {
    "name": "Exact Brand Name or Company Name",
    "category": "Main Business Category or Industry",
    "summary": "Clear, informative 2-3 sentence business summary."
  },
  "analysis": {
    "competitor_analysis": {
      "brand_overview": "Comprehensive overview of the brand's offerings and market stance",
      "main_business_category": "Primary business category",
      "main_products_and_services": ["Service/Product 1", "Service/Product 2", "Service/Product 3"],
      "competitors": [
        {
          "name": "Competitor Name",
          "main_service": "Competitor's core service",
          "target_market": "Target market (e.g. Enterprise / SMBs)",
          "key_strength": "Competitor's major strength",
          "weakness_or_gap": "Competitor's weakness or market gap",
          "opportunity": "Opportunity for your brand against this competitor"
        }
      ],
      "strengths": ["Brand Strength 1", "Brand Strength 2", "Brand Strength 3"],
      "competitive_advantages": ["Competitive Advantage 1", "Competitive Advantage 2"],
      "opportunities": ["Market Opportunity 1", "Market Opportunity 2"]
    },
    "target_search_queries": [
      {
        "query": "Exact high-intent search query phrase",
        "platforms": ["Google", "LinkedIn"],
        "intent": "Service Discovery / B2B Search / Inspiration / Commercial",
        "business_relevance": "Why this query drives qualified leads",
        "target_audience": "Specific persona searching for this"
      }
    ],
    "seo_improvements": {
      "primary_keyword": "Primary target keyword",
      "secondary_keywords": ["Keyword 1", "Keyword 2", "Keyword 3"],
      "long_tail_keywords": ["Long tail phrase 1", "Long tail phrase 2", "Long tail phrase 3"],
      "recommended_title": "Optimized SEO Title Tag (50-60 characters, with brand & keyword)",
      "meta_description": "Engaging meta description (under 160 characters) with primary keyword and call-to-action",
      "supporting_content": [
        "Dedicated landing page for ...",
        "Industry-specific case studies for ...",
        "In-depth FAQ covering ...",
        "Topical blog series on ..."
      ]
    },
    "top_services": [
      {
        "service_name": "Service Name",
        "description": "Short explanation of service capabilities and scope",
        "target_industry": "Primary industry vertical",
        "target_customer": "Ideal client profile",
        "main_benefit": "Key business outcome or ROI for client",
        "is_inferred": false
      }
    ],
    "target_audience": {
      "primary_audience": ["Core Audience 1", "Core Audience 2"],
      "secondary_audience": ["Adjacent Audience 1", "Adjacent Audience 2"],
      "industries": ["Vertical 1", "Vertical 2", "Vertical 3"],
      "business_types": ["Startups", "SMBs", "Enterprise"],
      "customer_profiles": ["Job Title/Role 1", "Job Title/Role 2"],
      "geographical_focus": "Identified location or Global",
      "customer_needs": ["Customer pain point 1", "Customer pain point 2"],
      "potential_interests": ["Interest 1", "Interest 2"],
      "recommended_marketing_segments": ["Segment 1 for ad campaigns", "Segment 2 for outreach"]
    }
  }
}

CRITICAL INSTRUCTIONS:
1. Provide exactly 3 or more realistic competitors based on the business category.
2. Provide exactly 5 distinct target search queries covering Google, Facebook, Instagram, LinkedIn, and X.
3. Provide exactly 5 primary services identified from the content. Mark 'is_inferred': true only if not explicitly named in the website text.
4. Do not fabricate or invent fake search volume numbers.
5. Base the analysis directly on the extracted website content.
""".strip()

    async def analyze_content(self, formatted_content: str, raw_extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze website content and return structured JSON dictionary."""
        provider = settings.LLM_PROVIDER

        if provider == "gemini" and settings.GEMINI_API_KEY:
            return await self._call_gemini(formatted_content)
        elif provider == "openai" and settings.OPENAI_API_KEY:
            return await self._call_openai(formatted_content)
        elif settings.GEMINI_API_KEY:
            return await self._call_gemini(formatted_content)
        elif settings.OPENAI_API_KEY:
            return await self._call_openai(formatted_content)
        else:
            # Fallback mock analyzer for offline testing / development when no API key is set
            return self._generate_fallback_analysis(raw_extracted)

    async def _call_gemini(self, content: str) -> Dict[str, Any]:
        """Call Google Gemini API using google-genai SDK."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            prompt = f"{self.SYSTEM_PROMPT}\n\nHere is the website content to analyze:\n\n{content}"

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )

            response_text = response.text
            return self._clean_and_parse_json(response_text)

        except Exception as e:
            raise LLMServiceError(f"Gemini API call failed: {str(e)}")

    async def _call_openai(self, content: str) -> Dict[str, Any]:
        """Call OpenAI API using official openai SDK."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                response_format={"type": "json_object"},
                temperature=0.2,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this website content:\n\n{content}"},
                ],
            )
            response_text = response.choices[0].message.content
            return self._clean_and_parse_json(response_text)

        except Exception as e:
            raise LLMServiceError(f"OpenAI API call failed: {str(e)}")

    def _clean_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Extract and parse JSON from LLM response string."""
        if not raw_text or not raw_text.strip():
            raise LLMServiceError("LLM returned an empty response.")

        cleaned = raw_text.strip()

        # Remove markdown code block fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Attempt to extract between outermost curly braces
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError as err:
                    raise LLMServiceError(f"Failed to parse extracted JSON block: {err}")
            raise LLMServiceError("LLM response did not contain valid JSON.")

    def _generate_fallback_analysis(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deterministic, realistic fallback analysis for offline evaluation and testing
        when no external API key is provided.
        """
        title = raw.get("title") or "Website"
        site_name = raw.get("site_name") or title.split("|")[0].split("-")[0].strip() or "Brand"
        meta_desc = raw.get("meta_description") or "Comprehensive digital and business solutions provider."
        headings = raw.get("headings", [])
        nav_links = raw.get("nav_links", [])

        category = "Technology & Digital Services"
        if any("law" in h.lower() or "legal" in h.lower() for h in headings):
            category = "Legal Services"
        elif any("health" in h.lower() or "medical" in h.lower() for h in headings):
            category = "Healthcare & Wellness"
        elif any("finance" in h.lower() or "tax" in h.lower() for h in headings):
            category = "Financial Services"
        elif any("ecommerce" in h.lower() or "shop" in h.lower() for h in headings):
            category = "E-Commerce & Retail"

        services = []
        if nav_links:
            for link in nav_links[:5]:
                services.append({
                    "service_name": link.title(),
                    "description": f"Professional {link.lower()} tailored to client requirements.",
                    "target_industry": category,
                    "target_customer": "Growing Businesses & Organizations",
                    "main_benefit": f"High quality, efficient {link.lower()} outcomes",
                    "is_inferred": False
                })

        while len(services) < 5:
            idx = len(services) + 1
            default_names = ["Custom Consulting", "Digital Implementation", "Managed Support", "Strategy & Planning", "Enterprise Solutions"]
            name = default_names[idx - 1]
            services.append({
                "service_name": name,
                "description": f"{name} delivering measurable business impact.",
                "target_industry": category,
                "target_customer": "Mid-market & Enterprise Clients",
                "main_benefit": "Operational excellence and strategic growth",
                "is_inferred": True
            })

        return {
            "brand": {
                "name": site_name,
                "category": category,
                "summary": meta_desc[:250] if meta_desc else f"{site_name} delivers industry-leading {category} solutions."
            },
            "analysis": {
                "competitor_analysis": {
                    "brand_overview": f"{site_name} is an established provider specializing in {category}.",
                    "main_business_category": category,
                    "main_products_and_services": [s["service_name"] for s in services[:3]],
                    "competitors": [
                        {
                            "name": f"Apex {category.split()[0]} Global",
                            "main_service": f"Enterprise {category}",
                            "target_market": "Fortune 500 & Large Corporations",
                            "key_strength": "Global scale and brand recognition",
                            "weakness_or_gap": "High overhead, slower turnaround time",
                            "opportunity": f"Deliver agile, modern {category} solutions with faster time-to-value"
                        },
                        {
                            "name": f"NextGen {category.split()[0]} Solutions",
                            "main_service": f"Bespoke {category}",
                            "target_market": "High-growth Startups",
                            "key_strength": "Modern tech stack and aggressive pricing",
                            "weakness_or_gap": "Limited cross-domain capabilities",
                            "opportunity": "Offer end-to-end consulting and dedicated account support"
                        },
                        {
                            "name": f"Vanguard {category.split()[0]} Group",
                            "main_service": f"Full-Suite {category}",
                            "target_market": "Mid-Market Businesses",
                            "key_strength": "Long-standing regional client relationships",
                            "weakness_or_gap": "Less transparent pricing structure",
                            "opportunity": "Showcase transparent deliverables, superior customer support, and digital agility"
                        }
                    ],
                    "strengths": [
                        "Tailored client engagements",
                        f"Specialized expertise in {category}",
                        "Fast turnaround and dedicated attention"
                    ],
                    "competitive_advantages": [
                        "Agile delivery model compared to legacy firms",
                        "Transparent, predictable engagement model"
                    ],
                    "opportunities": [
                        "Enhance search visibility for high-intent long-tail keywords",
                        "Produce industry-focused case studies and whitepapers",
                        "Leverage social proof and verified client testimonials"
                    ]
                },
                "target_search_queries": [
                    {
                        "query": f"Best {category.lower()} provider",
                        "platforms": ["Google"],
                        "intent": "Service Discovery",
                        "business_relevance": "Direct intent to evaluate and hire service providers",
                        "target_audience": "Decision-makers and business owners"
                    },
                    {
                        "query": f"{category.lower()} case studies and solutions",
                        "platforms": ["LinkedIn"],
                        "intent": "B2B Search",
                        "business_relevance": "Evaluates credibility and proof of work in professional networks",
                        "target_audience": "Corporate Directors and VPs"
                    },
                    {
                        "query": f"Top modern {category.lower()} tips",
                        "platforms": ["X"],
                        "intent": "Industry Trends",
                        "business_relevance": "Establishes topical authority and thought leadership",
                        "target_audience": "Tech-savvy founders and professionals"
                    },
                    {
                        "query": f"{category.lower()} recommendations for businesses",
                        "platforms": ["Facebook"],
                        "intent": "Community Discovery",
                        "business_relevance": "Peer recommendations in business groups",
                        "target_audience": "Small business owners and local operators"
                    },
                    {
                        "query": f"Modern {category.lower()} design ideas",
                        "platforms": ["Instagram"],
                        "intent": "Inspiration",
                        "business_relevance": "Visual appeal and portfolio showcase",
                        "target_audience": "Creative directors and marketing leads"
                    }
                ],
                "seo_improvements": {
                    "primary_keyword": f"{category} solutions",
                    "secondary_keywords": [
                        f"{category.lower()} agency",
                        f"professional {category.lower()}",
                        f"{category.lower()} consulting"
                    ],
                    "long_tail_keywords": [
                        f"best {category.lower()} company for growing businesses",
                        f"affordable and reliable {category.lower()} services",
                        f"how to choose a {category.lower()} partner"
                    ],
                    "recommended_title": f"{site_name} | Leading {category} & Solutions",
                    "meta_description": f"Discover top-tier {category.lower()} with {site_name}. Empowering organizations with proven expertise, modern tools, and exceptional outcomes.",
                    "supporting_content": [
                        f"Comprehensive {category} Service Hub Page",
                        "Frequently Asked Questions (FAQ) regarding engagement and onboarding",
                        "Industry-specific Landing Pages targeting key client verticals",
                        "Thought leadership blog articles on emerging trends and benchmarks"
                    ]
                },
                "top_services": services,
                "target_audience": {
                    "primary_audience": ["Business Owners", "C-Level Executives", "Operations Directors"],
                    "secondary_audience": ["Department Managers", "Procurement Officers", "Tech Consultants"],
                    "industries": [category, "Technology", "Corporate Services", "E-Commerce"],
                    "business_types": ["Growing Startups", "Mid-Sized Enterprises", "Established Businesses"],
                    "customer_profiles": ["Founder & CEO", "VP of Operations", "Head of Digital Transformation"],
                    "geographical_focus": "Global / North America & International",
                    "customer_needs": [
                        "Need for reliable, scalable solutions",
                        "Desire to reduce operational friction and costs",
                        "Requirement for specialized domain expertise"
                    ],
                    "potential_interests": ["Operational Efficiency", "Digital Modernization", "High ROI Solutions"],
                    "recommended_marketing_segments": [
                        "B2B Tech Leaders on LinkedIn",
                        "High-growth startup founders searching on Google",
                        "Regional business associations"
                    ]
                }
            }
        }
