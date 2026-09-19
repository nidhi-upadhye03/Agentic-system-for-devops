"""
Unit tests for auto-response-agent main functionality
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.unit
@pytest.mark.asyncio
class TestAutoResponseAgent:
    """Test AutoResponseAgent main class"""

    async def test_agent_initialization(self, mock_config):
        """Test agent initializes with correct configuration"""
        with patch('app.main.config', mock_config):
            with patch('app.main.ExecutorFactory'):
                with patch('app.main.ApprovalClient'):
                    with patch('app.main.ActionValidator'):
                        with patch('app.main.EventConsumer'):
                            with patch('app.main.EventPublisher'):
                                from app.main import AutoResponseAgent
                                agent = AutoResponseAgent()

                                assert agent.executor is not None
                                assert agent.approval_client is not None
                                assert agent.action_validator is not None
                                assert agent.event_consumer is not None
                                assert agent.event_publisher is not None

    async def test_on_analysis_complete_auto_execute(
        self,
        mock_config,
        sample_analysis_event,
        mock_executor,
        mock_action_validator,
        mock_event_publisher
    ):
        """Test auto-execution of high-confidence recommendations"""
        with patch('app.main.config', mock_config):
            with patch('app.main.ExecutorFactory.create_executor', return_value=mock_executor):
                with patch('app.main.ActionValidator', return_value=mock_action_validator):
                    with patch('app.main.EventPublisher', return_value=mock_event_publisher):
                        with patch('app.main.ApprovalClient'):
                            with patch('app.main.EventConsumer'):
                                from app.main import AutoResponseAgent
                                agent = AutoResponseAgent()
                                agent.event_publisher = mock_event_publisher

                                # Setup validator to allow auto-execution
                                mock_action_validator.should_auto_execute.return_value = True
                                mock_action_validator.validate_action.return_value = {"valid": True}

                                # Execute
                                await agent.on_analysis_complete(sample_analysis_event)

                                # Verify action was executed
                                assert mock_executor.scale_deployment.called

                                # Verify success event was published
                                assert mock_event_publisher.publish.called

    async def test_on_analysis_complete_requires_approval(
        self,
        mock_config,
        sample_low_confidence_event,
        mock_executor,
        mock_action_validator,
        mock_approval_client,
        mock_event_publisher
    ):
        """Test approval workflow for low-confidence recommendations"""
        with patch('app.main.config', mock_config):
            with patch('app.main.ExecutorFactory.create_executor', return_value=mock_executor):
                with patch('app.main.ActionValidator', return_value=mock_action_validator):
                    with patch('app.main.ApprovalClient', return_value=mock_approval_client):
                        with patch('app.main.EventPublisher', return_value=mock_event_publisher):
                            with patch('app.main.EventConsumer'):
                                from app.main import AutoResponseAgent
                                agent = AutoResponseAgent()
                                agent.approval_client = mock_approval_client
                                agent.event_publisher = mock_event_publisher

                                # Setup validator to require approval
                                mock_action_validator.should_auto_execute.return_value = False
                                mock_action_validator.validate_action.return_value = {"valid": True}

                                # Execute
                                await agent.on_analysis_complete(sample_low_confidence_event)

                                # Verify approval was requested
                                assert mock_approval_client.request_approval.called

                                # Verify approval pending event was published
                                assert mock_event_publisher.publish.called

    async def test_execute_action_scale_deployment(
        self,
        mock_config,
        sample_scale_action,
        mock_executor
    ):
        """Test scale deployment action execution"""
        with patch('app.main.config', mock_config):
            with patch('app.main.ExecutorFactory.create_executor', return_value=mock_executor):
                with patch('app.main.ApprovalClient'):
                    with patch('app.main.ActionValidator'):
                        with patch('app.main.EventConsumer'):
                            with patch('app.main.EventPublisher'):
                                from app.main import AutoResponseAgent
                                agent = AutoResponseAgent()

                                # Execute
                                result = await agent.execute_action(
                                    "test-incident-123",
                                    sample_scale_action
                                )

                                # Verify
                                assert result["status"] == "success"
                                assert mock_executor.scale_deployment.called

                                # Check parameters
                                call_args = mock_executor.scale_deployment.call_args
                                assert call_args.kwargs['service_name'] == 'user-service'
                                assert call_args.kwargs['replicas'] == 5

    async def test_execute_action_restart_pods(
        self,
        mock_config,
        sample_restart_action,
        mock_executor
    ):
        """Test restart pods action execution"""
        with patch('app.main.config', mock_config):
            with patch('app.main.ExecutorFactory.create_executor', return_value=mock_executor):
                with patch('app.main.ApprovalClient'):
                    with patch('app.main.ActionValidator'):
                        with patch('app.main.EventConsumer'):
                            with patch('app.main.EventPublisher'):
                                from app.main import AutoResponseAgent
                                agent = AutoResponseAgent()

                                # Execute
                                result = await agent.execute_action(
                                    "test-incident-456",
                                    sample_restart_action
                                )

                                # Verify
                                assert result["status"] == "success"
                                assert mock_executor.restart_pods.called

    async def test_execute_action_rollback(
        self,
        mock_config,
        sample_rollback_action,
        mock_executor
    ):
        """Test rollback deployment action execution"""
        with patch('app.main.config', mock_config):
            with patch('app.main.ExecutorFactory.create_executor', return_value=mock_executor):
                with patch('app.main.ApprovalClient'):
                    with patch('app.main.ActionValidator'):
                        with patch('app.main.EventConsumer'):
                            with patch('app.main.EventPublisher'):
                                from app.main import AutoResponseAgent
                                agent = AutoResponseAgent()

                                # Execute
                                result = await agent.execute_action(
                                    "test-incident-789",
                                    sample_rollback_action
                                )

                                # Verify
                                assert result["status"] == "success"
                                assert mock_executor.rollback_deployment.called

    async def test_execute_action_with_retry(
        self,
        mock_config,
        sample_scale_action,
        mock_executor
    ):
        """Test action execution with retry on failure"""
        with patch('app.main.config', mock_config):
            # First call fails, second succeeds
            mock_executor.scale_deployment = AsyncMock(
                side_effect=[
                    Exception("Temporary failure"),
                    {"status": "success", "replicas": 5}
                ]
            )

            with patch('app.main.ExecutorFactory.create_executor', return_value=mock_executor):
                with patch('app.main.ApprovalClient'):
                    with patch('app.main.ActionValidator'):
                        with patch('app.main.EventConsumer'):
                            with patch('app.main.EventPublisher'):
                                from app.main import AutoResponseAgent
                                agent = AutoResponseAgent()

                                # Execute with retry
                                result = await agent.execute_action_with_retry(
                                    "test-incident-123",
                                    sample_scale_action,
                                    max_retries=2
                                )

                                # Verify succeeded on retry
                                assert result["status"] == "success"
                                assert mock_executor.scale_deployment.call_count == 2


@pytest.mark.unit
class TestActionValidator:
    """Test ActionValidator"""

    def test_should_auto_execute_high_confidence(self):
        """Test auto-execution for high confidence actions"""
        from app.action_validator import ActionValidator

        validator = ActionValidator(
            auto_execute_threshold=95,
            require_approval_actions=[],
            require_approval_criticality=[],
            max_scale_replicas=10,
            min_scale_replicas=1
        )

        action = {
            "type": "scale_deployment",
            "criticality": "medium",
            "confidence": 98
        }

        assert validator.should_auto_execute(action, 98) is True

    def test_should_auto_execute_low_confidence(self):
        """Test requires approval for low confidence"""
        from app.action_validator import ActionValidator

        validator = ActionValidator(
            auto_execute_threshold=95,
            require_approval_actions=[],
            require_approval_criticality=[],
            max_scale_replicas=10,
            min_scale_replicas=1
        )

        action = {
            "type": "scale_deployment",
            "criticality": "medium",
            "confidence": 70
        }

        assert validator.should_auto_execute(action, 70) is False

    def test_should_auto_execute_critical_action(self):
        """Test requires approval for critical actions"""
        from app.action_validator import ActionValidator

        validator = ActionValidator(
            auto_execute_threshold=95,
            require_approval_actions=["rollback"],
            require_approval_criticality=["critical"],
            max_scale_replicas=10,
            min_scale_replicas=1
        )

        action = {
            "type": "rollback_deployment",
            "criticality": "critical",
            "confidence": 98
        }

        assert validator.should_auto_execute(action, 98) is False

    def test_validate_scale_parameters_valid(self):
        """Test scale parameter validation with valid values"""
        from app.action_validator import ActionValidator

        validator = ActionValidator(
            auto_execute_threshold=95,
            require_approval_actions=[],
            require_approval_criticality=[],
            max_scale_replicas=10,
            min_scale_replicas=1
        )

        action = {
            "replicas": 5
        }

        result = validator.validate_scale_parameters(action)
        assert result["valid"] is True
        assert result["replicas"] == 5

    def test_validate_scale_parameters_exceeds_max(self):
        """Test scale parameter validation exceeds maximum"""
        from app.action_validator import ActionValidator

        validator = ActionValidator(
            auto_execute_threshold=95,
            require_approval_actions=[],
            require_approval_criticality=[],
            max_scale_replicas=10,
            min_scale_replicas=1
        )

        action = {
            "replicas": 15  # Exceeds max
        }

        result = validator.validate_scale_parameters(action)
        assert result["valid"] is False or result["replicas"] == 10

    def test_validate_action_missing_target(self):
        """Test action validation with missing target"""
        from app.action_validator import ActionValidator

        validator = ActionValidator(
            auto_execute_threshold=95,
            require_approval_actions=[],
            require_approval_criticality=[],
            max_scale_replicas=10,
            min_scale_replicas=1
        )

        action = {
            "type": "scale_deployment"
            # Missing 'target' field
        }

        result = validator.validate_action(action)
        assert result["valid"] is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestApprovalClient:
    """Test ApprovalClient"""

    @pytest.fixture
    def approval_client(self):
        """Create ApprovalClient instance"""
        from app.approval_client import ApprovalClient
        return ApprovalClient(
            api_url="http://test-api:3000/api",
            timeout=60,
            poll_interval=1
        )

    async def test_request_approval(self, approval_client):
        """Test requesting approval"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"approval_id": "approval-123"}

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            approval_id = await approval_client.request_approval(
                incident_id="test-incident",
                action={"type": "scale_deployment"},
                analysis={"root_cause": "High CPU"}
            )

            assert approval_id == "approval-123"

    async def test_wait_for_approval_approved(self, approval_client):
        """Test waiting for approval that gets approved"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "approved",
                "approver": "admin",
                "comment": "Looks good"
            }

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await approval_client.wait_for_approval("approval-123")

            assert result["approved"] is True
            assert result["approver"] == "admin"

    async def test_wait_for_approval_rejected(self, approval_client):
        """Test waiting for approval that gets rejected"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "rejected",
                "approver": "admin",
                "comment": "Too risky"
            }

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await approval_client.wait_for_approval("approval-123")

            assert result["approved"] is False
            assert result.get("comment") == "Too risky"
