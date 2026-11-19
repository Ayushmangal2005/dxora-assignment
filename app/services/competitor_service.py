"""Competitor benchmarking and intelligence service."""

from typing import List, Dict, Any
from app.schemas import CompetitorItem, CompetitorAnalysis


class CompetitorService:
    """Processes, enriches, and validates competitor analysis data."""

    def format_comparison_table(
        self,
        brand_name: str,
        main_service: str,
        target_market: str,
        brand_strength: str,
        competitors: List[CompetitorItem]
    ) -> List[Dict[str, str]]:
        """
        Build an aligned comparison matrix between your brand and its competitors,
        matching Section 1 requirement.
        """
        matrix = [
            {
                "entity": brand_name,
                "role": "Your Brand",
                "main_service": main_service,
                "target_market": target_market,
                "key_strength": brand_strength,
                "opportunity": "Expand market share & enhance digital presence"
            }
        ]

        for comp in competitors:
            matrix.append({
                "entity": comp.name,
                "role": "Competitor",
                "main_service": comp.main_service,
                "target_market": comp.target_market,
                "key_strength": comp.key_strength,
                "opportunity": comp.opportunity
            })

        return matrix

    def validate_and_enrich_competitors(
        self,
        raw_competitor_data: Dict[str, Any],
        brand_name: str,
        category: str
    ) -> CompetitorAnalysis:
        """Ensure minimum 3 competitors and complete comparison attributes."""
        competitors_list = []
        for item in raw_competitor_data.get("competitors", []):
            if isinstance(item, dict):
                competitors_list.append(
                    CompetitorItem(
                        name=item.get("name", "Industry Competitor"),
                        main_service=item.get("main_service", category),
                        target_market=item.get("target_market", "General Market"),
                        key_strength=item.get("key_strength", "Established market presence"),
                        weakness_or_gap=item.get("weakness_or_gap", "Higher pricing / slower agility"),
                        opportunity=item.get("opportunity", "Differentiate with modern, agile solutions")
                    )
                )

        # Fallback if LLM provided fewer than 3 competitors
        while len(competitors_list) < 3:
            idx = len(competitors_list) + 1
            competitors_list.append(
                CompetitorItem(
                    name=f"Direct {category} Provider #{idx}",
                    main_service=category,
                    target_market="Enterprise & Mid-Market",
                    key_strength="Legacy enterprise client base",
                    weakness_or_gap="Less flexible service tiers",
                    opportunity=f"Capture underserved clients with modern {category} offerings"
                )
            )

        return CompetitorAnalysis(
            brand_overview=raw_competitor_data.get(
                "brand_overview",
                f"{brand_name} operates in the {category} sector delivering tailored solutions."
            ),
            main_business_category=raw_competitor_data.get("main_business_category", category),
            main_products_and_services=raw_competitor_data.get(
                "main_products_and_services",
                [category]
            ),
            competitors=competitors_list,
            strengths=raw_competitor_data.get(
                "strengths",
                ["Specialized expertise", "Customer-centric service", "Competitive agility"]
            ),
            competitive_advantages=raw_competitor_data.get(
                "competitive_advantages",
                [f"Focused specialization in {category}", "Modern technology stack", "Agile delivery"]
            ),
            opportunities=raw_competitor_data.get(
                "opportunities",
                ["Expand digital presence", "Publish authoritative thought leadership", "Target niche verticals"]
            )
        )
