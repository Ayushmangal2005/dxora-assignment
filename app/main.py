"""FastAPI application entrypoint for AI-Powered Website Link Analysis API."""

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas import (
    LinkAnalysisRequest,
    LinkAnalysisResponse,
    ErrorResponse,
)
from app.services.analysis_service import AnalysisService
from app.services.website_extractor import WebsiteExtractionError
from app.services.llm_service import LLMServiceError

app = FastAPI(
    title="AI-Powered Website Link Analysis API",
    description=(
        "Production-ready FastAPI service that extracts, analyzes, and understands "
        "website content using LLMs (Google Gemini / OpenAI), delivering structured "
        "competitor insights, SEO intelligence, search queries, service catalogs, "
        "and target audience profiles."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontends and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize analysis service
analysis_service = AnalysisService()


# ---------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------

@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    """Handle URL validation or SSRF protection errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": str(exc),
            "code": "VALIDATION_OR_SSRF_ERROR",
        },
    )


@app.exception_handler(WebsiteExtractionError)
async def extraction_error_handler(request, exc: WebsiteExtractionError):
    """Handle website scraping / unreachable destination errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": str(exc),
            "code": "WEBSITE_EXTRACTION_ERROR",
        },
    )


@app.exception_handler(LLMServiceError)
async def llm_error_handler(request, exc: LLMServiceError):
    """Handle LLM processing or parsing errors."""
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "success": False,
            "error": str(exc),
            "code": "LLM_SERVICE_ERROR",
        },
    )


# ---------------------------------------------------------
# Endpoints
# ---------------------------------------------------------

@app.get("/", tags=["Health"])
async def root():
    """Service status and quick info."""
    return {
        "service": "AI-Powered Website Link Analysis API",
        "status": "healthy",
        "docs": "/docs",
        "endpoint": "POST /link-analysis",
        "recommended_llm": settings.GEMINI_MODEL,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for container and deployment monitors."""
    return {"status": "ok", "provider": settings.LLM_PROVIDER}


@app.post(
    "/link-analysis",
    response_model=LinkAnalysisResponse,
    responses={
        200: {"description": "Successful website analysis", "model": LinkAnalysisResponse},
        400: {"description": "Invalid URL or SSRF attempt blocked", "model": ErrorResponse},
        422: {"description": "Website inaccessible or content extraction failed", "model": ErrorResponse},
        502: {"description": "LLM processing error", "model": ErrorResponse},
    },
    tags=["Analysis"],
)
async def analyze_link(payload: LinkAnalysisRequest):
    """
    Perform deep AI-powered website link analysis.
    
    Accepts a website URL, extracts cleaned content, and generates:
    - Section 1: Competitor vs Your Brand Details (min 3 competitors)
    - Section 2: Top 5 Target Search Queries across Google, Facebook, Instagram, LinkedIn, and X
    - Section 3: SEO Improvements & Keyword Recommendations
    - Section 4: Top 5 Services
    - Section 5: Target Audience Identification
    """
    try:
        result = await analysis_service.run_analysis(payload.url)
        return result
    except (ValueError, WebsiteExtractionError, LLMServiceError):
        # Re-raise to trigger custom exception handlers
        raise
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": f"An unexpected error occurred: {str(e)}",
                "code": "INTERNAL_SERVER_ERROR",
            },
        )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
