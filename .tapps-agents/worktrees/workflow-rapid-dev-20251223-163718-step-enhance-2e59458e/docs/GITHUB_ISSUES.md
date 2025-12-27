# GitHub Issues for HomeIQ Test Coverage Improvement

**Created:** November 15, 2025
**Purpose:** Track remaining test implementation work (P0/P1/P2)
**Context:** Shared library tests completed (~2,700 lines), now expand to services

---

## Issue #1: [P0] Add AI Automation UI Test Suite (Vitest + React Testing Library)

**Priority:** 🔴 P0 - Critical
**Effort:** 8-12 hours
**Dependencies:** None

### Description

Implement comprehensive test suite for the AI Automation UI (Port 3001) using modern 2025 frontend testing patterns with Vitest (4× faster than Jest) and React Testing Library.

**Current Status:** 0% test coverage (47 TypeScript/React files untested)

**Risk:** Primary user interface for AI automation has no automated tests. Regressions could break critical user workflows.

### Modern 2025 Patterns

✅ **Vitest** (replaces Jest) - Native ESM, 4× faster
✅ **Playwright Component Testing** - Component-level isolation
✅ **MSW 2.0** - Modern API mocking
✅ **Testing Library** - User-centric testing

### Acceptance Criteria

- [ ] Vitest configuration setup (`vitest.config.ts`)
- [ ] Test coverage >70% for components
- [ ] Test coverage >80% for hooks
- [ ] Test coverage >60% for stores/state management
- [ ] MSW 2.0 API mocking configured
- [ ] All tests pass in CI/CD pipeline
- [ ] Test execution time <30 seconds

### File Structure

```
services/ai-automation-ui/
├── vitest.config.ts (new)
├── src/
│   ├── test/
│   │   └── setup.ts (new)
│   ├── __tests__/
│   │   ├── components/
│   │   │   ├── AutomationApproval.test.tsx
│   │   │   ├── PatternAnalysis.test.tsx
│   │   │   ├── ConversationFlow.test.tsx
│   │   │   └── SettingsPanel.test.tsx
│   │   ├── hooks/
│   │   │   ├── useAutomationState.test.ts
│   │   │   ├── usePatternDetection.test.ts
│   │   │   ├── useWebSocket.test.ts
│   │   │   └── useDeviceIntelligence.test.ts
│   │   ├── store/
│   │   │   ├── automationSlice.test.ts
│   │   │   └── conversationSlice.test.ts
│   │   └── integration/
│   │       ├── automationWorkflow.test.tsx
│   │       └── patternToApproval.test.tsx
│   └── mocks/
│       └── handlers.ts (MSW 2.0)
```

### Code Templates

**vitest.config.ts:**
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['**/*.test.{ts,tsx}', '**/test/**'],
      thresholds: {
        statements: 70,
        branches: 60,
        functions: 70,
        lines: 70
      }
    },
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false
      }
    }
  }
});
```

**Component Test Example:**
```typescript
// src/__tests__/components/AutomationApproval.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AutomationApproval } from '../../components/AutomationApproval';

describe('AutomationApproval', () => {
  it('should approve automation when button clicked', async () => {
    const user = userEvent.setup();
    const onApprove = vi.fn();

    render(
      <AutomationApproval
        automation={{ id: 1, name: 'Test Automation' }}
        onApprove={onApprove}
      />
    );

    const approveButton = screen.getByRole('button', { name: /approve/i });
    await user.click(approveButton);

    expect(onApprove).toHaveBeenCalledWith(1);
  });
});
```

**Hook Test Example:**
```typescript
// src/__tests__/hooks/useAutomationState.test.ts
import { describe, it, expect, beforeAll, afterEach, afterAll } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { useAutomationState } from '../../hooks/useAutomationState';

const server = setupServer(
  http.get('/api/patterns', () => {
    return HttpResponse.json({
      patterns: [{ id: 1, type: 'time-of-day', confidence: 0.95 }]
    });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('useAutomationState', () => {
  it('should fetch and update patterns', async () => {
    const { result } = renderHook(() => useAutomationState());

    await waitFor(() => {
      expect(result.current.patterns).toHaveLength(1);
      expect(result.current.patterns[0].confidence).toBe(0.95);
    });
  });
});
```

### Dependencies

```json
{
  "devDependencies": {
    "vitest": "^2.0.0",
    "@vitest/ui": "^2.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@testing-library/jest-dom": "^6.1.0",
    "jsdom": "^23.0.0",
    "msw": "^2.4.0",
    "@playwright/experimental-ct-react": "^1.47.0"
  }
}
```

### Success Metrics

- ✅ All components have unit tests
- ✅ All hooks have unit tests
- ✅ Integration tests cover main user flows
- ✅ Coverage thresholds met (70/60/70/70)
- ✅ Tests run in <30 seconds
- ✅ No flaky tests

### References

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [MSW 2.0 Documentation](https://mswjs.io/)
- [HomeIQ CLAUDE.md Testing Standards](/CLAUDE.md)

---

## Issue #2: [P0] Add OpenVINO Service ML Tests (Embedding & NER Validation)

**Priority:** 🔴 P0 - Critical
**Effort:** 6-8 hours
**Dependencies:** None

### Description

Implement comprehensive tests for OpenVINO Service (Port 8026→8019) including embedding quality validation, NER accuracy testing, and re-ranking correctness using modern AI/LLM testing frameworks.

**Current Status:** 1 test file (165 lines) vs 571 lines of source code (~29% coverage)

**Risk:** Core AI inference service lacks validation of ML model quality and accuracy.

### Modern 2025 Patterns

✅ **DeepEval** - LLM testing framework
✅ **Property-based testing** - Validate embedding properties
✅ **Semantic similarity testing** - Ensure embeddings capture meaning
✅ **Benchmark datasets** - Standard NER evaluation sets

### Acceptance Criteria

- [ ] Embedding dimension validation tests
- [ ] Embedding normalization tests
- [ ] Semantic similarity tests (cosine similarity)
- [ ] NER accuracy tests with benchmark datasets
- [ ] Re-ranking correctness tests
- [ ] Model loading and fallback tests
- [ ] Performance tests (<100ms per embedding)
- [ ] Coverage >85% for openvino service

### File Structure

```
services/openvino-service/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_embeddings.py (new)
│   ├── test_ner.py (new)
│   ├── test_reranking.py (new)
│   ├── test_model_loading.py (new)
│   ├── test_performance.py (new)
│   └── fixtures/
│       ├── embedding_test_data.json
│       └── ner_benchmark.json
```

### Code Templates

**test_embeddings.py:**
```python
import pytest
import numpy as np
from hypothesis import given, strategies as st, settings

@pytest.mark.asyncio
async def test_embedding_dimensions():
    """Test embeddings have correct dimensions (384 for BGE-small)"""
    embedding = await openvino.embed("Test sentence")

    assert len(embedding) == 384
    assert isinstance(embedding, np.ndarray)

@pytest.mark.asyncio
async def test_embedding_normalization():
    """Test embeddings are normalized"""
    embedding = await openvino.embed("Normalized test")

    norm = np.linalg.norm(embedding)
    assert 0.99 <= norm <= 1.01  # Allow floating point tolerance

@pytest.mark.asyncio
async def test_semantic_similarity():
    """Test similar sentences have high cosine similarity"""
    embedding1 = await openvino.embed("The cat sat on the mat")
    embedding2 = await openvino.embed("A feline rested on the rug")

    similarity = cosine_similarity(embedding1, embedding2)

    # Similar semantics should have >0.75 similarity
    assert similarity > 0.75

@pytest.mark.asyncio
async def test_semantic_dissimilarity():
    """Test dissimilar sentences have low similarity"""
    embedding1 = await openvino.embed("The weather is sunny today")
    embedding2 = await openvino.embed("Quantum physics is fascinating")

    similarity = cosine_similarity(embedding1, embedding2)

    # Unrelated content should have <0.3 similarity
    assert similarity < 0.3

# Property-based test for embeddings
@given(text=st.text(min_size=5, max_size=500))
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_embedding_properties(text):
    """Property: All valid text should produce valid embeddings"""
    embedding = await openvino.embed(text)

    # Property 1: Correct dimensions
    assert len(embedding) == 384

    # Property 2: No NaN or Inf
    assert not np.isnan(embedding).any()
    assert not np.isinf(embedding).any()

    # Property 3: Normalized
    norm = np.linalg.norm(embedding)
    assert 0.99 <= norm <= 1.01
```

**test_ner.py:**
```python
import pytest
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

@pytest.mark.asyncio
async def test_ner_entity_extraction():
    """Test NER extracts correct entities"""
    text = "Apple Inc. CEO Tim Cook announced the new iPhone in Cupertino."
    entities = await openvino.extract_entities(text)

    # Verify organizations
    orgs = [e for e in entities if e['type'] == 'ORG']
    assert any(e['text'] == 'Apple Inc.' for e in orgs)

    # Verify people
    people = [e for e in entities if e['type'] == 'PER']
    assert any(e['text'] == 'Tim Cook' for e in people)

    # Verify locations
    locations = [e for e in entities if e['type'] == 'LOC']
    assert any(e['text'] == 'Cupertino' for e in locations)

@pytest.mark.asyncio
async def test_ner_with_llm_judge():
    """Use LLM-as-judge to validate NER quality"""
    text = "Microsoft CEO Satya Nadella spoke at Build 2025 in Seattle."
    entities = await openvino.extract_entities(text)

    test_case = LLMTestCase(
        input=text,
        actual_output=str(entities),
        expected_output="Organizations: Microsoft; People: Satya Nadella; Events: Build 2025; Locations: Seattle"
    )

    metric = AnswerRelevancyMetric(threshold=0.8)
    assert_test(test_case, [metric])
```

**test_performance.py:**
```python
import pytest
import time

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_embedding_latency():
    """Test embedding generation meets <100ms target"""
    text = "Performance test sentence"

    start = time.perf_counter()
    embedding = await openvino.embed(text)
    duration_ms = (time.perf_counter() - start) * 1000

    # Target: <100ms from CLAUDE.md
    assert duration_ms < 100
    assert embedding is not None

@pytest.mark.asyncio
async def test_batch_embedding_throughput():
    """Test batch processing efficiency"""
    texts = ["Sentence " + str(i) for i in range(100)]

    start = time.perf_counter()
    embeddings = await openvino.embed_batch(texts)
    duration_ms = (time.perf_counter() - start) * 1000

    # Should process 100 embeddings faster than 100x single
    assert duration_ms < 5000  # <5s for 100 embeddings
    assert len(embeddings) == 100
```

### Success Metrics

- ✅ Embedding tests verify dimensions, normalization, similarity
- ✅ NER tests validate entity extraction accuracy
- ✅ Performance tests ensure <100ms latency
- ✅ Property-based tests cover edge cases
- ✅ Coverage >85%

### References

- [DeepEval Documentation](https://docs.confident-ai.com/)
- [BGE-small Model Documentation](https://huggingface.co/BAAI/bge-small-en-v1.5)
- [NER Benchmarks](https://paperswithcode.com/task/named-entity-recognition-ner)

---

## Issue #3: [P0] Add ML Service Algorithm Tests (Clustering & Anomaly Detection)

**Priority:** 🔴 P0 - Critical
**Effort:** 6-8 hours
**Dependencies:** None

### Description

Implement comprehensive tests for ML Service (Port 8025→8020) covering clustering algorithms (DBSCAN, K-means), anomaly detection, and pattern recognition with known datasets.

**Current Status:** 1 test file (217 lines) vs 417 lines of source code (~52% coverage)

**Risk:** Machine learning algorithms lack validation, could produce incorrect results.

### Modern 2025 Patterns

✅ **Synthetic datasets** - Controlled test data with known properties
✅ **Property-based testing** - Validate algorithm properties
✅ **Benchmark datasets** - Standard ML evaluation sets
✅ **Statistical validation** - Chi-square, silhouette scores

### Acceptance Criteria

- [ ] Clustering algorithm correctness tests
- [ ] Anomaly detection accuracy tests
- [ ] Pattern recognition validation tests
- [ ] Algorithm property tests (convergence, consistency)
- [ ] Performance tests (<1s for 1000 points)
- [ ] Coverage >85%

### Code Templates

```python
# tests/test_clustering.py
import pytest
import numpy as np
from sklearn.datasets import make_blobs

@pytest.mark.asyncio
async def test_dbscan_identifies_clusters():
    """Test DBSCAN correctly identifies distinct clusters"""
    # Generate synthetic data with 3 clusters
    X, y_true = make_blobs(n_samples=300, centers=3, random_state=42)

    clusters = await ml_service.cluster_dbscan(X, eps=0.5, min_samples=5)

    # Should find 3 clusters (plus potential noise)
    unique_clusters = set(clusters) - {-1}  # Exclude noise
    assert len(unique_clusters) == 3

@pytest.mark.asyncio
async def test_kmeans_convergence():
    """Test K-means converges to stable clusters"""
    X, _ = make_blobs(n_samples=300, centers=4, random_state=42)

    # Run twice with same data
    clusters1 = await ml_service.cluster_kmeans(X, k=4, random_state=42)
    clusters2 = await ml_service.cluster_kmeans(X, k=4, random_state=42)

    # Should produce identical results with same random state
    assert np.array_equal(clusters1, clusters2)

@pytest.mark.asyncio
async def test_anomaly_detection_accuracy():
    """Test anomaly detection identifies outliers"""
    # Normal data
    normal = np.random.normal(0, 1, (100, 2))

    # Outliers
    outliers = np.array([[10, 10], [-10, -10], [10, -10]])

    X = np.vstack([normal, outliers])

    anomalies = await ml_service.detect_anomalies(X)

    # Should detect the 3 outliers
    assert len(anomalies) >= 3
    assert any(idx >= 100 for idx in anomalies)  # Outliers are at end
```

---

## Issue #4: [P0] Add AI Core Service Orchestration Tests

**Priority:** 🔴 P0 - Critical
**Effort:** 4-6 hours
**Dependencies:** None

### Description

Test AI Core Service (Port 8018) orchestration logic, service coordination, and failure handling.

**Current Status:** 1 test file (208 lines), orchestration logic untested

### Acceptance Criteria

- [ ] Service coordination tests
- [ ] Failure handling and fallback tests
- [ ] Load balancing tests
- [ ] Request routing tests
- [ ] Coverage >80%

---

## Issue #5: [P0] Add AI Code Executor Security Tests

**Priority:** 🔴 P0 - Critical Security
**Effort:** 6-8 hours
**Dependencies:** None

### Description

Implement comprehensive security testing for AI Code Executor sandbox including filesystem isolation, network isolation, resource limits, and escape attempt prevention.

**Current Status:** No tests (9 Python files, ~603 lines untested)

**Risk:** 🚨 **CRITICAL SECURITY RISK** - Sandboxed code execution without security validation

### Acceptance Criteria

- [ ] Filesystem isolation tests
- [ ] Network isolation tests
- [ ] Resource limit enforcement tests
- [ ] Privilege escalation prevention tests
- [ ] Timeout enforcement tests
- [ ] Module import restriction tests
- [ ] Coverage >90% (security critical)

### Code Templates

```python
# tests/security/test_sandbox_isolation.py
import pytest

@pytest.mark.security
@pytest.mark.asyncio
async def test_filesystem_access_restricted():
    """Test code cannot access filesystem outside sandbox"""
    malicious_code = """
import os
os.listdir('/')  # Should fail
    """

    with pytest.raises(SecurityException):
        await executor.execute(malicious_code)

@pytest.mark.security
@pytest.mark.asyncio
async def test_network_access_blocked():
    """Test code cannot make network requests"""
    malicious_code = """
import urllib.request
urllib.request.urlopen('https://evil.com')  # Should fail
    """

    with pytest.raises(SecurityException):
        await executor.execute(malicious_code)

@pytest.mark.security
@pytest.mark.asyncio
async def test_resource_limits_enforced():
    """Test CPU/memory limits are enforced"""
    memory_bomb = """
data = 'x' * (10 * 1024 * 1024 * 1024)  # 10GB
    """

    with pytest.raises(ResourceLimitExceeded):
        await executor.execute(memory_bomb)
```

---

## Issue #6: [P1] Add Integration Test Suite with Testcontainers

**Priority:** 🟡 P1 - High
**Effort:** 8-12 hours
**Dependencies:** None

### Description

Implement integration tests using Testcontainers to test with real InfluxDB, MQTT broker, and other dependencies instead of mocks.

### Modern 2025 Patterns

✅ **Testcontainers** - Real dependencies in Docker
✅ **Test isolation** - Each test gets fresh containers
✅ **End-to-end flows** - Complete data pipeline testing

### Acceptance Criteria

- [ ] InfluxDB container integration
- [ ] MQTT broker container integration
- [ ] End-to-end data flow tests
- [ ] Cross-service integration tests
- [ ] Performance tests with real infrastructure

### Code Template

```python
# tests/integration/test_data_pipeline_with_containers.py
import pytest
from testcontainers.influxdb import InfluxDbContainer
from testcontainers.core.container import DockerContainer

@pytest.fixture(scope="session")
def influxdb_container():
    """Real InfluxDB for integration tests"""
    with InfluxDbContainer("influxdb:2.7") as influx:
        yield influx

@pytest.fixture(scope="session")
def mqtt_container():
    """Real MQTT broker for integration tests"""
    with DockerContainer("eclipse-mosquitto:2.0") \
        .with_exposed_ports(1883) as mqtt:
        yield mqtt

@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_data_flow(influxdb_container, mqtt_container):
    """Test complete data flow: MQTT → Ingestion → InfluxDB"""
    influx_url = influxdb_container.get_connection_url()
    mqtt_url = f"mqtt://localhost:{mqtt_container.get_exposed_port(1883)}"

    # Publish MQTT message
    await publish_test_event(mqtt_url, "sensor.temperature", 22.5)

    # Wait for ingestion
    await asyncio.sleep(2)

    # Query InfluxDB
    client = InfluxDBClient(url=influx_url)
    result = client.query('SELECT * FROM "state_changed" WHERE entity_id="sensor.temperature"')

    assert len(result) > 0
    assert result[0]["value"] == 22.5
```

---

## Issue #7: [P1] Add Performance Test Suite (pytest-benchmark)

**Priority:** 🟡 P1 - High
**Effort:** 4-6 hours
**Dependencies:** None

### Description

Implement comprehensive performance regression tests using pytest-benchmark to ensure system meets CLAUDE.md performance targets.

### CLAUDE.md Performance Targets

| Operation | Target | Acceptable | Investigation |
|-----------|--------|------------|---------------|
| Health checks | <10ms | <50ms | >100ms |
| Device queries | <10ms | <50ms | >100ms |
| Event queries | <100ms | <200ms | >500ms |
| InfluxDB batch write | <100ms | <200ms | >500ms |

### Acceptance Criteria

- [ ] Benchmark all critical operations
- [ ] Verify targets from CLAUDE.md
- [ ] Performance regression detection
- [ ] Generate benchmark reports
- [ ] Track metrics over time

### Code Template

```python
# tests/performance/test_batch_processing.py
import pytest

def test_influxdb_batch_write_performance(benchmark):
    """Verify batch writes meet <100ms target"""
    events = generate_test_events(1000)

    result = benchmark(batch_processor.write_batch, events)

    # Target: <100ms for 1000 events
    assert result.stats.mean < 0.100
    assert result.stats.stddev < 0.020  # Consistent performance

@pytest.mark.asyncio
async def test_device_query_latency(benchmark):
    """Verify device queries meet <10ms target"""
    async def query():
        return await data_api.get_devices()

    result = benchmark.pedantic(query, iterations=100, rounds=10)

    # Property: 95th percentile <10ms
    assert result.stats.quantiles[3] < 0.010
```

---

## Issue #8: [P1] Add Database Migration Tests

**Priority:** 🟡 P1 - High
**Effort:** 4-6 hours
**Dependencies:** None

### Description

Test Alembic database migrations for data integrity, idempotency, and upgrade/downgrade cycles.

### Acceptance Criteria

- [ ] Migration upgrade/downgrade cycle tests
- [ ] Data integrity after migration tests
- [ ] Migration idempotency tests
- [ ] Rollback functionality tests
- [ ] Coverage for all migrations

### Code Template

```python
# tests/migrations/test_alembic_migrations.py
import pytest
from alembic import command
from alembic.config import Config

@pytest.fixture
def alembic_config():
    """Alembic configuration for testing"""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", "sqlite:///test.db")
    return config

def test_upgrade_downgrade_cycle(alembic_config):
    """Test migration can upgrade and downgrade"""
    # Upgrade to latest
    command.upgrade(alembic_config, "head")

    # Downgrade one version
    command.downgrade(alembic_config, "-1")

    # Upgrade again
    command.upgrade(alembic_config, "head")

def test_migration_idempotency(alembic_config):
    """Test running migration twice doesn't cause errors"""
    command.upgrade(alembic_config, "head")
    command.upgrade(alembic_config, "head")  # Should be safe
```

---

## Issue #9: [P1] Add Health Dashboard Frontend Tests

**Priority:** 🟡 P1 - High
**Effort:** 4-6 hours
**Dependencies:** None

### Description

Expand existing Health Dashboard tests (Port 3000) to cover all components, hooks, and integration flows.

**Current Status:** 8 test files exist, expand coverage

### Acceptance Criteria

- [ ] Component test coverage >70%
- [ ] Hook test coverage >80%
- [ ] Integration test coverage >60%
- [ ] E2E tests for critical user flows
- [ ] Visual regression tests

---

## Issue #10: [P2] Add Log Aggregator Tests

**Priority:** 🟢 P2 - Medium
**Effort:** 3-4 hours
**Dependencies:** None

### Description

Test Log Aggregator (Port 8015) for Docker log collection, parsing accuracy, and retention policy enforcement.

### Acceptance Criteria

- [ ] Docker log streaming tests
- [ ] Log parsing accuracy tests
- [ ] Buffer overflow handling tests
- [ ] InfluxDB log storage tests
- [ ] Retention policy enforcement tests

---

## Issue #11: [P2] Add Disaster Recovery Tests

**Priority:** 🟢 P2 - Medium
**Effort:** 6-8 hours
**Dependencies:** None

### Description

Test disaster recovery procedures including database backup/restore, service failover, and data consistency.

### Acceptance Criteria

- [ ] Database backup/restore tests
- [ ] Service failover tests
- [ ] Data consistency verification tests
- [ ] Recovery time objective (RTO) tests
- [ ] Recovery point objective (RPO) tests

### Code Template

```python
# tests/disaster_recovery/test_backup_restore.py
import pytest

@pytest.mark.disaster_recovery
@pytest.mark.asyncio
async def test_influxdb_backup_restore():
    """Test InfluxDB backup and restore procedure"""
    # Write test data
    await write_test_data()

    # Create backup
    backup_path = await backup_influxdb()

    # Simulate disaster (clear database)
    await clear_influxdb()

    # Restore from backup
    await restore_influxdb(backup_path)

    # Verify data restored
    data = await query_test_data()
    assert len(data) > 0
```

---

## Issue #12: [P2] Setup CI/CD Test Pipeline

**Priority:** 🟢 P2 - Medium
**Effort:** 4-6 hours
**Dependencies:** Issues #1-9

### Description

Configure GitHub Actions workflow to run all tests automatically on every push and pull request with coverage reporting.

### Acceptance Criteria

- [ ] GitHub Actions workflow configured
- [ ] Tests run on every push
- [ ] Tests run on every PR
- [ ] Coverage reports posted to PR
- [ ] Coverage threshold enforcement
- [ ] Parallel test execution
- [ ] Test results artifacts

### Code Template

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test-python:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements-test.txt

      - name: Run tests with coverage
        run: |
          pytest tests/shared \
            --cov=shared \
            --cov-branch \
            --cov-report=xml \
            --cov-report=term \
            -n auto

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

      - name: Coverage threshold check
        run: |
          coverage report --fail-under=80

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run Vitest
        run: npm run test:coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v4

  test-e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Playwright
        run: npx playwright install --with-deps

      - name: Run E2E tests
        run: npx playwright test

      - name: Upload Playwright Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/
```

---

## Issue #13: [P2] Add Mutation Testing Baseline

**Priority:** 🟢 P2 - Medium
**Effort:** 2-3 hours
**Dependencies:** Issues #1-9

### Description

Establish mutation testing baseline using mutmut to identify weak tests that don't catch bugs.

### Acceptance Criteria

- [ ] Mutmut configured for project
- [ ] Baseline mutation score established
- [ ] Weak tests identified and documented
- [ ] Target mutation score set (>85%)
- [ ] CI/CD integration (weekly runs)

### Commands

```bash
# Run mutation testing
mutmut run --paths-to-mutate=shared/

# View results
mutmut results

# Show surviving mutants (weak tests)
mutmut show

# Target: >85% mutation score
```

---

## Summary

### P0 - Critical (Immediate Next Sprint)
1. ✅ **AI Automation UI Test Suite** - Primary user interface (0% coverage)
2. ✅ **OpenVINO Service ML Tests** - Core AI inference (29% coverage)
3. ✅ **ML Service Algorithm Tests** - ML algorithms (52% coverage)
4. ✅ **AI Core Service Tests** - Orchestration logic untested
5. ✅ **AI Code Executor Security Tests** - 🚨 Critical security risk

**Estimated Effort:** 30-42 hours total

### P1 - High Priority
6. ✅ **Integration Tests with Testcontainers** - Real dependencies
7. ✅ **Performance Test Suite** - Regression prevention
8. ✅ **Database Migration Tests** - Data integrity
9. ✅ **Health Dashboard Tests** - Expand existing coverage

**Estimated Effort:** 20-30 hours total

### P2 - Medium Priority
10. ✅ **Log Aggregator Tests** - Observability
11. ✅ **Disaster Recovery Tests** - Business continuity
12. ✅ **CI/CD Pipeline** - Automation
13. ✅ **Mutation Testing** - Test quality

**Estimated Effort:** 15-21 hours total

### Total Estimated Effort
**65-93 hours** (~2-3 sprint cycles for full implementation)

---

## Next Steps

1. **Create GitHub Issues** - Copy each issue section to GitHub
2. **Prioritize P0 Issues** - Start with AI Automation UI and Security
3. **Assign to Sprint** - Allocate based on team capacity
4. **Track Progress** - Update issue status as work completes

---

**Created:** November 15, 2025
**Maintainer:** HomeIQ Development Team
**Status:** Ready for GitHub issue creation
