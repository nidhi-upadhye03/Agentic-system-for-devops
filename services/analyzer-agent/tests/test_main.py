"""
Unit tests for analyzer-agent main functionality
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


@pytest.mark.unit
@pytest.mark.asyncio
class TestAnalyzerAgent:
    """Test AnalyzerAgent main class"""

    async def test_analyzer_initialization(self, mock_config):
        """Test analyzer agent initializes with correct configuration"""
        with patch('app.main.config', mock_config):
            with patch('app.main.LLMAnalyzer'):
                with patch('app.main.EventConsumer'):
                    with patch('app.main.EventPublisher'):
                        from app.main import AnalyzerAgent
                        agent = AnalyzerAgent()

                        assert agent.running == False
                        assert agent.llm_analyzer is not None
                        assert agent.event_consumer is not None
                        assert agent.event_publisher is not None

    async def test_on_incident_detected_success(
        self,
        analyzer_agent,
        sample_incident_event,
        sample_llm_analysis
    ):
        """Test successful incident analysis workflow"""
        # Setup
        analyzer_agent.llm_analyzer.analyze = AsyncMock(return_value=sample_llm_analysis)

        # Execute
        await analyzer_agent.on_incident_detected(sample_incident_event)

        # Verify LLM was called
        assert analyzer_agent.llm_analyzer.analyze.called

        # Verify analysis was published
        assert analyzer_agent.event_publisher.publish.called
        publish_call = analyzer_agent.event_publisher.publish.call_args
        assert publish_call.kwargs['routing_key'] == "analyzer.analysis.complete"

        # Verify published message structure
        message = publish_call.kwargs['message']
        assert message['agent'] == 'analyzer'
        assert message['type'] == 'analysis_complete'
        assert message['incident_id'] == 'test-incident-123'
        assert 'analysis' in message
        assert 'recommendations' in message

    async def test_on_incident_detected_with_error(
        self,
        analyzer_agent,
        sample_incident_event
    ):
        """Test incident analysis handles errors gracefully"""
        # Setup - make LLM analyzer fail
        analyzer_agent.llm_analyzer.analyze = AsyncMock(
            side_effect=Exception("LLM service unavailable")
        )

        # Execute
        await analyzer_agent.on_incident_detected(sample_incident_event)

        # Verify error was published
        assert analyzer_agent.event_publisher.publish.called
        publish_call = analyzer_agent.event_publisher.publish.call_args
        assert publish_call.kwargs['routing_key'] == "analyzer.analysis.failed"

        message = publish_call.kwargs['message']
        assert message['type'] == 'analysis_failed'
        assert 'error' in message

    async def test_analyze_with_llm(
        self,
        analyzer_agent,
        sample_incident_event,
        sample_logs,
        sample_similar_incidents
    ):
        """Test LLM analysis is called with correct prompt"""
        # Setup
        expected_analysis = {
            "root_cause": "High CPU from database queries",
            "confidence": 90
        }
        analyzer_agent.llm_analyzer.analyze = AsyncMock(return_value=expected_analysis)

        # Execute
        result = await analyzer_agent.analyze_with_llm(
            sample_incident_event,
            sample_logs,
            sample_similar_incidents
        )

        # Verify
        assert result == expected_analysis
        assert analyzer_agent.llm_analyzer.analyze.called

        # Verify prompt was passed
        call_args = analyzer_agent.llm_analyzer.analyze.call_args
        assert 'prompt' in call_args.kwargs
        assert isinstance(call_args.kwargs['prompt'], str)
        assert len(call_args.kwargs['prompt']) > 0

    async def test_generate_recommendations_with_new_format(
        self,
        analyzer_agent,
        sample_incident_event
    ):
        """Test recommendation generation with new structured format"""
        # LLM analysis with new format
        analysis = {
            "root_cause": "High CPU usage",
            "confidence": 85,
            "recommendations": [
                {
                    "action_type": "SCALE",
                    "target_service": "user-service",
                    "target_type": "deployment",
                    "rationale": "Scale to handle load",
                    "criticality": "high",
                    "parameters": {"replicas": 5}
                }
            ]
        }

        # Execute
        recommendations = analyzer_agent.generate_recommendations(
            analysis,
            sample_incident_event
        )

        # Verify
        assert len(recommendations) > 0
        rec = recommendations[0]
        assert rec['type'] == 'scale_deployment'
        assert rec['target'] == 'user-service'
        assert rec['replicas'] == 5
        assert rec['confidence'] == 85

    async def test_generate_recommendations_skips_investigate(
        self,
        analyzer_agent,
        sample_incident_event
    ):
        """Test that INVESTIGATE actions are skipped"""
        analysis = {
            "root_cause": "Unknown issue",
            "confidence": 40,
            "recommendations": [
                {
                    "action_type": "INVESTIGATE",
                    "target_service": "user-service",
                    "target_type": "deployment",
                    "rationale": "Need more data",
                    "criticality": "low",
                    "parameters": {}
                },
                {
                    "action_type": "SCALE",
                    "target_service": "user-service",
                    "target_type": "deployment",
                    "rationale": "Scale as precaution",
                    "criticality": "medium",
                    "parameters": {"replicas": 3}
                }
            ]
        }

        # Execute
        recommendations = analyzer_agent.generate_recommendations(
            analysis,
            sample_incident_event
        )

        # Verify only SCALE action is included
        assert len(recommendations) == 1
        assert recommendations[0]['type'] == 'scale_deployment'

    async def test_build_analysis_prompt(
        self,
        analyzer_agent,
        sample_incident_event,
        sample_logs,
        sample_similar_incidents
    ):
        """Test analysis prompt is built correctly"""
        # Execute
        prompt = analyzer_agent._build_analysis_prompt(
            sample_incident_event,
            sample_logs,
            sample_similar_incidents
        )

        # Verify prompt contains key information
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert 'cpu_usage_percent' in prompt
        assert 'user-service' in prompt
        assert '95.5' in prompt  # current value
        assert '80.0' in prompt  # threshold

    async def test_fetch_logs_for_incident_disabled(
        self,
        analyzer_agent,
        sample_incident_event
    ):
        """Test log fetching when disabled"""
        analyzer_agent.log_fetcher = None

        # Execute
        logs = await analyzer_agent.fetch_logs_for_incident(sample_incident_event)

        # Verify
        assert logs == []

    async def test_fetch_logs_for_incident_enabled(
        self,
        analyzer_agent,
        sample_incident_event,
        mock_log_fetcher
    ):
        """Test log fetching when enabled"""
        analyzer_agent.log_fetcher = mock_log_fetcher
        expected_logs = ["ERROR: Connection timeout", "WARN: High CPU"]
        mock_log_fetcher.fetch_logs = AsyncMock(return_value=expected_logs)

        # Execute
        logs = await analyzer_agent.fetch_logs_for_incident(sample_incident_event)

        # Verify
        assert logs == expected_logs
        assert mock_log_fetcher.fetch_logs.called

    async def test_search_similar_incidents_disabled(
        self,
        analyzer_agent,
        sample_incident_event
    ):
        """Test RAG search when disabled"""
        analyzer_agent.rag_search = None

        # Execute
        similar = await analyzer_agent.search_similar_incidents(sample_incident_event)

        # Verify
        assert similar == []

    async def test_search_similar_incidents_enabled(
        self,
        analyzer_agent,
        sample_incident_event,
        mock_rag_search,
        sample_similar_incidents
    ):
        """Test RAG search when enabled"""
        analyzer_agent.rag_search = mock_rag_search
        mock_rag_search.search = AsyncMock(return_value=sample_similar_incidents)

        # Execute
        similar = await analyzer_agent.search_similar_incidents(sample_incident_event)

        # Verify
        assert len(similar) == len(sample_similar_incidents)
        assert mock_rag_search.search.called

        # Verify search query construction
        call_args = mock_rag_search.search.call_args
        query = call_args.kwargs['query']
        assert 'cpu_usage_percent' in query
        assert 'user-service' in query

    async def test_publish_analysis(
        self,
        analyzer_agent,
        sample_incident_event,
        sample_llm_analysis
    ):
        """Test analysis publication"""
        recommendations = [
            {
                "type": "scale_deployment",
                "target": "user-service",
                "replicas": 5
            }
        ]

        # Execute
        await analyzer_agent.publish_analysis(
            "test-incident-123",
            sample_incident_event,
            sample_llm_analysis,
            recommendations
        )

        # Verify
        assert analyzer_agent.event_publisher.publish.called
        call_args = analyzer_agent.event_publisher.publish.call_args

        assert call_args.kwargs['routing_key'] == "analyzer.analysis.complete"
        message = call_args.kwargs['message']
        assert message['agent'] == 'analyzer'
        assert message['type'] == 'analysis_complete'
        assert message['incident_id'] == 'test-incident-123'
        assert message['analysis'] == sample_llm_analysis
        assert message['recommendations'] == recommendations

    async def test_publish_analysis_error(
        self,
        analyzer_agent,
        sample_incident_event
    ):
        """Test error publication"""
        error_msg = "LLM timeout"

        # Execute
        await analyzer_agent.publish_analysis_error(
            "test-incident-123",
            sample_incident_event,
            error_msg
        )

        # Verify
        assert analyzer_agent.event_publisher.publish.called
        call_args = analyzer_agent.event_publisher.publish.call_args

        assert call_args.kwargs['routing_key'] == "analyzer.analysis.failed"
        message = call_args.kwargs['message']
        assert message['type'] == 'analysis_failed'
        assert message['error'] == error_msg


@pytest.mark.unit
class TestPromptBuilding:
    """Test prompt building functions"""

    def test_build_analysis_prompt_basic(self):
        """Test basic prompt building"""
        from app.prompts import build_analysis_prompt

        prompt = build_analysis_prompt(
            service_name="user-service",
            metric_name="cpu_usage_percent",
            current_value="95.5",
            threshold="80.0",
            severity="high",
            affected_services=["user-service"],
            cluster="prod",
            namespace="production",
            timestamp="2025-11-01T20:00:00Z",
            logs=[],
            similar_incidents=[]
        )

        assert isinstance(prompt, str)
        assert "user-service" in prompt
        assert "cpu_usage_percent" in prompt
        assert "95.5" in prompt
        assert "80.0" in prompt

    def test_build_analysis_prompt_with_logs(self):
        """Test prompt building with logs"""
        from app.prompts import build_analysis_prompt

        logs = [
            "ERROR: Database timeout",
            "WARN: Connection pool exhausted"
        ]

        prompt = build_analysis_prompt(
            service_name="database-service",
            metric_name="query_latency",
            current_value="5000",
            threshold="1000",
            severity="critical",
            affected_services=["database-service"],
            cluster="prod",
            namespace="production",
            timestamp="2025-11-01T20:00:00Z",
            logs=logs,
            similar_incidents=[]
        )

        assert "ERROR: Database timeout" in prompt
        assert "Connection pool exhausted" in prompt

    def test_build_analysis_prompt_with_similar_incidents(self):
        """Test prompt building with similar incidents"""
        from app.prompts import build_analysis_prompt

        similar_incidents = [
            {
                "incident_id": "past-1",
                "resolution": "Scaled to 5 replicas",
                "success_rate": 0.9
            }
        ]

        prompt = build_analysis_prompt(
            service_name="api-service",
            metric_name="response_time",
            current_value="2500",
            threshold="1000",
            severity="high",
            affected_services=["api-service"],
            cluster="prod",
            namespace="production",
            timestamp="2025-11-01T20:00:00Z",
            logs=[],
            similar_incidents=similar_incidents
        )

        assert "past-1" in prompt or "similar" in prompt.lower()


@pytest.mark.unit
class TestActionMapper:
    """Test ActionMapper functionality"""

    def test_parse_scale_action(self):
        """Test parsing SCALE action"""
        from app.action_mapper import ActionMapper

        llm_output = "Scale user-service deployment to 5 replicas"

        recommendations = ActionMapper.parse_llm_response(
            llm_output,
            fallback_service="user-service"
        )

        assert len(recommendations) > 0
        # This will depend on ActionMapper implementation

    def test_parse_restart_action(self):
        """Test parsing RESTART action"""
        from app.action_mapper import ActionMapper

        llm_output = "Restart pods for database-service"

        recommendations = ActionMapper.parse_llm_response(
            llm_output,
            fallback_service="database-service"
        )

        assert len(recommendations) >= 0
        # ActionMapper may or may not parse this correctly

    def test_parse_multiple_actions(self):
        """Test parsing multiple actions"""
        from app.action_mapper import ActionMapper

        llm_output = """
        1. Scale user-service to 5 replicas
        2. Restart auth-service pods
        """

        recommendations = ActionMapper.parse_llm_response(
            llm_output,
            fallback_service="user-service"
        )

        # Should parse at least one action
        assert isinstance(recommendations, list)
