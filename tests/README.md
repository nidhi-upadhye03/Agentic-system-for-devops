# Testing Strategy - DevOps Agent Platform

## Overview

This document outlines the comprehensive testing strategy for the DevOps Agent Platform. The platform consists of 12 microservices that require thorough testing at multiple levels.

## Testing Levels

### 1. Unit Tests
- **Target**: Individual functions, classes, and modules
- **Coverage Goal**: 80% minimum
- **Location**: `services/<service-name>/tests/`
- **Run Command**: `pytest services/<service-name>/tests/ -m unit`

### 2. Integration Tests
- **Target**: Interactions between services and external dependencies
- **Location**: `tests/integration/`
- **Dependencies**: RabbitMQ, Redis, PostgreSQL, Qdrant
- **Run Command**: `pytest tests/integration/ -m integration`

### 3. End-to-End Tests
- **Target**: Complete workflows across multiple services
- **Location**: `tests/e2e/`
- **Dependencies**: Full stack (all services running)
- **Run Command**: `pytest tests/e2e/ -m e2e`

## Service Coverage Status

### ✅ Services with Tests (25%)
1. **llm-service** - 4 test files, 1,012 lines
   - test_llm_client.py
   - test_rag_pipeline.py
   - conftest.py

2. **worker-service** - 3 test files, 842 lines
   - test_consumers.py
   - test_tasks.py
   - conftest.py

3. **monitoring-agent** - 1 test file, 123 lines
   - test_imports.py

### ❌ Services WITHOUT Tests (75%)
4. **analyzer-agent** - PRIORITY HIGH
5. **auto-response-agent** - PRIORITY HIGH
6. **memory-agent** - PRIORITY HIGH
7. **notifier-agent** - PRIORITY MEDIUM
8. **approval-dashboard/backend** - PRIORITY MEDIUM
9. **approval-dashboard/frontend** - PRIORITY MEDIUM
10. **ops-dashboard/backend** - PRIORITY LOW
11. **ops-dashboard/frontend** - PRIORITY LOW
12. **test-app** - PRIORITY LOW

## Testing Infrastructure

### Python (Services)
- **Framework**: pytest 7.4+
- **Async Support**: pytest-asyncio
- **Mocking**: pytest-mock, unittest.mock
- **Coverage**: pytest-cov
- **HTTP Client**: httpx (for FastAPI testing)
- **Database**: SQLAlchemy with in-memory SQLite for tests

### JavaScript/TypeScript (Dashboards)
- **Framework**: Jest
- **React Testing**: @testing-library/react
- **Coverage**: jest --coverage

## Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_function():
    pass

@pytest.mark.integration
@pytest.mark.requires_rabbitmq
async def test_message_queue():
    pass

@pytest.mark.e2e
@pytest.mark.slow
async def test_full_workflow():
    pass
```

## Running Tests

### All Tests
```bash
pytest
```

### By Level
```bash
pytest -m unit                  # Unit tests only
pytest -m integration          # Integration tests only
pytest -m e2e                  # E2E tests only
```

### By Service
```bash
pytest services/analyzer-agent/tests/
pytest services/memory-agent/tests/
```

### With Coverage
```bash
pytest --cov=services --cov-report=html
# Open coverage_html_report/index.html
```

### Skip Slow Tests
```bash
pytest -m "not slow"
```

### Skip Tests Requiring External Services
```bash
pytest -m "not requires_k8s and not requires_db"
```

## CI/CD Integration

Tests run automatically in GitHub Actions on:
- Pull requests
- Pushes to main branch
- Nightly scheduled runs

### Workflow Files
- `.github/workflows/test-llm-service.yml`
- `.github/workflows/test-worker-service.yml`
- `.github/workflows/test-monitoring-agent.yml`
- `.github/workflows/test-analyzer-agent.yml` (to be created)
- `.github/workflows/test-integration.yml` (to be created)

## Test Data Management

### Fixtures
- **Shared fixtures**: `tests/conftest.py`
- **Service-specific fixtures**: `services/<service>/tests/conftest.py`

### Mock Data
- **Mock responses**: `tests/fixtures/`
- **Sample metrics**: `tests/fixtures/metrics/`
- **Sample logs**: `tests/fixtures/logs/`

## Performance Testing

### Load Testing
- **Tool**: Locust
- **Location**: `tests/performance/`
- **Scenarios**: API endpoints, WebSocket connections, message queue throughput

### Stress Testing
- Test agent behavior under:
  - High incident volume
  - Database connection limits
  - Message queue backpressure

## Security Testing

### Static Analysis
- **Tool**: bandit (Python), npm audit (Node.js)
- **Run**: `bandit -r services/`

### Dependency Scanning
- **Tool**: safety (Python), Snyk (Node.js)
- **Run**: `safety check`

## Documentation Testing

### Docstring Tests
```bash
pytest --doctest-modules services/
```

## Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
   - ✅ `test_analyzer_detects_high_cpu_incident`
   - ❌ `test_1`

2. **Arrange-Act-Assert**: Structure tests clearly
   ```python
   def test_function():
       # Arrange
       input_data = {"key": "value"}

       # Act
       result = function_to_test(input_data)

       # Assert
       assert result == expected_value
   ```

3. **Mock External Dependencies**: Don't make real API calls or database queries in unit tests
   ```python
   @pytest.mark.unit
   def test_llm_call(mock_openai):
       mock_openai.return_value = "mocked response"
       result = call_llm("test prompt")
       assert result == "mocked response"
   ```

4. **Test Edge Cases**: Test normal flow, error cases, and edge cases
   - Empty inputs
   - Null values
   - Very large inputs
   - Concurrent access

5. **Keep Tests Fast**: Unit tests should run in milliseconds
   - Use in-memory databases
   - Mock network calls
   - Avoid sleep() - use async/await

## Coverage Goals

| Service | Current | Target | Priority |
|---------|---------|--------|----------|
| llm-service | 75% | 85% | Medium |
| worker-service | 70% | 85% | Medium |
| monitoring-agent | 20% | 80% | High |
| analyzer-agent | 0% | 80% | **Critical** |
| auto-response-agent | 0% | 80% | **Critical** |
| memory-agent | 0% | 80% | **Critical** |
| notifier-agent | 0% | 75% | High |
| approval-dashboard | 0% | 70% | Medium |
| ops-dashboard | 0% | 60% | Low |

## Implementation Roadmap

### Phase 1: Critical Agents (Week 1)
- [ ] analyzer-agent unit tests (80% coverage)
- [ ] auto-response-agent unit tests (80% coverage)
- [ ] memory-agent unit tests (80% coverage)

### Phase 2: Integration Tests (Week 2)
- [ ] RabbitMQ message flow tests
- [ ] Database integration tests
- [ ] Qdrant vector store tests
- [ ] Redis caching tests

### Phase 3: Dashboard Tests (Week 3)
- [ ] approval-dashboard backend API tests
- [ ] approval-dashboard frontend component tests
- [ ] ops-dashboard WebSocket tests

### Phase 4: E2E Tests (Week 4)
- [ ] Full incident workflow (monitoring → analysis → action → notification)
- [ ] Approval workflow tests
- [ ] Memory learning workflow tests

## Troubleshooting

### Common Issues

1. **Tests hang**: Check for missing `await` in async tests
2. **Port conflicts**: Use random ports or ensure services are mocked
3. **Database errors**: Ensure test database is created and migrations run
4. **Import errors**: Check PYTHONPATH includes service directories

### Debug Mode
```bash
pytest -vv --log-cli-level=DEBUG services/<service>/tests/
```

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
