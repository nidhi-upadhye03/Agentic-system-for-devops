"""
LLM Analyzer - Performs root cause analysis using LLM

This module integrates with the LLM service to perform intelligent
root cause analysis of infrastructure incidents.
"""
import logging
import json
import os
import aiohttp
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class LLMAnalyzerError(Exception):
    """Custom exception for LLM analyzer errors"""
    pass


class LLMAnalyzer:
    """LLM-powered incident analyzer"""

    def __init__(
        self,
        service_url: str = None,
        provider: str = "openai",
        model: str = "gpt-4",
        temperature: float = 0.2
    ):
        """
        Initialize LLM Analyzer

        Args:
            service_url: URL of the LLM service
            provider: LLM provider (openai, anthropic)
            model: Model name
            temperature: Temperature for generation (0-1)
        """
        # Read from environment variable if not provided
        if service_url is None:
            service_url = os.getenv("LLM_SERVICE_URL", "http://llm-service:8000")

        self.service_url = service_url.rstrip('/')
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"LLM Analyzer initialized: {provider}/{model} at {self.service_url}")

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def analyze(self, prompt: str, timeout: int = 600) -> Dict[str, Any]:
        """
        Perform root cause analysis using LLM

        Args:
            prompt: Analysis prompt with incident context
            timeout: Request timeout in seconds

        Returns:
            Analysis result dictionary

        Raises:
            LLMAnalyzerError: If analysis fails
        """
        await self._ensure_session()

        url = f"{self.service_url}/api/v1/chat"
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert DevOps engineer analyzing production incidents. Provide detailed, actionable root cause analysis in JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": 2000
        }

        try:
            async with self.session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LLMAnalyzerError(
                        f"LLM service returned status {response.status}: {error_text}"
                    )

                data = await response.json()

                # Extract analysis from response
                content = data.get("response", "")
                if not content:
                    raise LLMAnalyzerError("Empty response from LLM service")

                # Parse JSON response
                analysis = self._parse_analysis_response(content)

                logger.debug(f"Analysis complete: confidence={analysis.get('confidence', 0)}%")
                return analysis

        except aiohttp.ClientError as e:
            raise LLMAnalyzerError(f"Network error calling LLM service: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise LLMAnalyzerError(f"Failed to parse LLM response as JSON: {str(e)}") from e
        except Exception as e:
            raise LLMAnalyzerError(f"Unexpected error during analysis: {str(e)}") from e

    def _parse_analysis_response(self, content: str) -> Dict[str, Any]:
        """
        Parse and validate LLM analysis response

        Args:
            content: Raw LLM response content

        Returns:
            Validated analysis dictionary

        Raises:
            LLMAnalyzerError: If response is invalid
        """
        try:
            # Try to parse as JSON
            analysis = json.loads(content)

            # Validate required fields
            required_fields = ["root_cause", "explanation", "confidence", "immediate_actions"]
            missing_fields = [field for field in required_fields if field not in analysis]

            if missing_fields:
                logger.warning(f"Missing fields in analysis: {missing_fields}")
                # Fill in defaults
                if "root_cause" not in analysis:
                    analysis["root_cause"] = "Unable to determine root cause"
                if "explanation" not in analysis:
                    analysis["explanation"] = "Insufficient data for detailed analysis"
                if "confidence" not in analysis:
                    analysis["confidence"] = 50
                if "immediate_actions" not in analysis:
                    analysis["immediate_actions"] = ["Manual investigation required"]

            # Ensure confidence is a number
            if not isinstance(analysis["confidence"], (int, float)):
                analysis["confidence"] = 50

            # Clamp confidence to 0-100 range
            analysis["confidence"] = max(0, min(100, analysis["confidence"]))

            # Ensure immediate_actions is a list
            if not isinstance(analysis["immediate_actions"], list):
                analysis["immediate_actions"] = [str(analysis["immediate_actions"])]

            # Add defaults for optional fields
            if "contributing_factors" not in analysis:
                analysis["contributing_factors"] = []
            if "long_term_recommendations" not in analysis:
                analysis["long_term_recommendations"] = []

            return analysis

        except json.JSONDecodeError:
            # If not valid JSON, try to extract from text
            logger.warning("LLM response is not valid JSON, attempting to extract")
            return self._extract_analysis_from_text(content)

    def _extract_analysis_from_text(self, content: str) -> Dict[str, Any]:
        """
        Extract analysis from non-JSON text response

        Args:
            content: Raw text content

        Returns:
            Best-effort analysis dictionary
        """
        # This is a fallback for when LLM doesn't return proper JSON
        # Extract what we can from the text

        analysis = {
            "root_cause": "Analysis extraction failed",
            "explanation": content[:500],  # First 500 chars
            "confidence": 30,  # Low confidence for non-JSON response
            "contributing_factors": [],
            "immediate_actions": ["Manual review required"],
            "long_term_recommendations": []
        }

        # Try to find confidence percentage
        import re
        confidence_match = re.search(r'confidence[:\s]+(\d+)%?', content, re.IGNORECASE)
        if confidence_match:
            analysis["confidence"] = int(confidence_match.group(1))

        # Try to find root cause
        root_cause_match = re.search(r'root\s+cause[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE)
        if root_cause_match:
            analysis["root_cause"] = root_cause_match.group(1).strip()

        return analysis

    async def health_check(self) -> bool:
        """
        Check if LLM service is accessible

        Returns:
            True if healthy, False otherwise
        """
        await self._ensure_session()

        try:
            url = f"{self.service_url}/health"
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                is_healthy = response.status == 200
                logger.debug(f"LLM service health check: {'OK' if is_healthy else 'FAILED'}")
                return is_healthy
        except Exception as e:
            logger.error(f"LLM service health check failed: {e}")
            return False

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
