# NEET CBT Platform - Testing Guide

This document provides comprehensive information about the testing infrastructure implemented for the NEET CBT Platform.

## Overview

The testing suite covers all core functionality of the platform including:
- Authentication (JWT & Google OAuth)
- Chatbot functionality 
- Question selection and test creation
- Time tracking and metadata capture
- Export functionality (PDF, PNG, JPG)
- Performance and stress testing

## Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements-dev.txt
```

### 2. Run Tests

#### Run all fast tests (recommended for development)
```bash
python run_tests.py --fast
```

#### Run specific test categories
```bash
python run_tests.py --unit          # Unit tests with coverage
python run_tests.py --integration   # Integration tests
python run_tests.py --auth          # Authentication tests
python run_tests.py --chat          # Chatbot tests
python run_tests.py --questions     # Question selection tests
python run_tests.py --export        # Export functionality tests
```

### 3. View Coverage Report
After running tests with coverage, open `htmlcov/index.html` in your browser.

## Test Categories

### By Functionality
- `auth` - Authentication and authorization tests
- `chat` - Chatbot functionality tests
- `question_selection` - Question selection and test creation tests
- `export` - Export functionality (PDF, PNG, JPG) tests

### By Type
- `unit` - Fast, isolated unit tests
- `integration` - End-to-end workflow tests
- `stress` - High-volume and performance tests
- `slow` - Tests that take longer to run

## Test Structure

```
backend/tests/
├── conftest.py                           # Test configuration and fixtures
├── test_app.py                          # Main integration tests
├── test_authentication_comprehensive.py # Authentication tests
├── test_chatbot_comprehensive.py        # Chatbot functionality tests
├── test_question_selection_comprehensive.py # Question selection tests
├── test_timing_metadata_comprehensive.py # Timing and metadata tests
├── test_export_regression.py            # Export functionality tests
└── test_stress_comprehensive.py         # Stress and performance tests
```

## Test Categories

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests for individual functions
- `@pytest.mark.integration` - Integration tests for complete workflows
- `@pytest.mark.auth` - Authentication-related tests
- `@pytest.mark.chat` - Chatbot functionality tests
- `@pytest.mark.question_selection` - Question selection tests
- `@pytest.mark.export` - Export functionality tests
- `@pytest.mark.stress` - High-load and performance tests
- `@pytest.mark.slow` - Tests that take longer to run

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements-dev.txt
```

### 2. Run Tests

```bash
# Run all fast tests (default)
python run_tests.py

# Run specific test categories
python run_tests.py --unit          # Unit tests with coverage
python run_tests.py --integration   # Integration tests
python run_tests.py --auth          # Authentication tests
python run_tests.py --chat          # Chatbot tests
python run_tests.py --questions     # Question selection tests
python run_tests.py --export        # Export tests
python run_tests.py --stress        # Stress tests (slow)

# Run all tests except stress tests
python run_tests.py --all

# Run fast tests only
python run_tests.py --fast

# Generate coverage report
python run_tests.py --coverage
```

### 3. Using pytest directly

```bash
# Run all tests with coverage
pytest --cov=neet_app --cov-report=html tests/

# Run specific test file
pytest tests/test_authentication_comprehensive.py -v

# Run tests by marker
pytest -m "auth" tests/
pytest -m "unit and not slow" tests/

# Run with specific output format
pytest tests/ --tb=short --verbose
```

## Test Coverage

Target coverage: **80% minimum**

Generate coverage reports:
```bash
pytest --cov=neet_app --cov-report=html --cov-report=term-missing tests/
```

View HTML coverage report:
```bash
# Coverage report will be in htmlcov/index.html
```

## Test Data and Fixtures

### Key Fixtures (from conftest.py)

- `sample_student_profile` - Creates a test student with proper credentials
- `authenticated_client` - API client with JWT authentication
- `sample_topic` - Sample topic for testing
- `sample_questions` - Set of sample questions
- `sample_chat_session` - Chat session for testing
- `sample_platform_test` - Platform test configuration
- `mock_llm_response` - Mocked chatbot service response

### Using Fixtures in Tests

```python
@pytest.mark.django_db
def test_example(authenticated_client, sample_topic):
    response = authenticated_client.get('/api/topics/')
    assert response.status_code == 200
```

## Writing New Tests

### 1. Follow the AAA Pattern

```python
def test_example_function():
    # Arrange - Set up test data
    user = create_test_user()
    
    # Act - Execute the function being tested
    result = function_under_test(user)
    
    # Assert - Verify the results
    assert result.success == True
```

### 2. Use Descriptive Test Names

```python
def test_send_message_updates_session_title_on_first_message():
    """Test that sending the first message updates the session title"""
    # Implementation...
```

### 3. Test Both Valid and Invalid Inputs

```python
def test_create_session_with_valid_data():
    # Test success case
    
def test_create_session_with_invalid_topic():
    # Test failure case
    
def test_create_session_with_missing_required_fields():
    # Test validation
```

### 4. Mock External Dependencies

```python
@patch('neet_app.services.chatbot_service.NeetChatbotService.generate_response')
def test_chat_functionality(mock_service):
    mock_service.return_value = {'success': True, 'response': 'Test response'}
    # Test implementation...
```

## Test Environment Setup

### Database

Tests use Django's test database which is automatically created and destroyed.

### Environment Variables

Test-specific settings can be configured in `test_settings.py` or via environment variables:

```bash
export DJANGO_SETTINGS_MODULE=neet_backend.test_settings
export DB_NAME=test_db
export DEBUG=True
```

### Mocking External Services

External services (LLM APIs, file systems, etc.) are mocked to ensure:
- Tests run consistently
- No external dependencies
- Fast execution
- No side effects

## Performance Testing

### Stress Tests

Stress tests are marked with `@pytest.mark.stress` and test:
- High-volume concurrent requests
- Large data handling
- Memory usage under load
- Database performance

Run stress tests separately:
```bash
python run_tests.py --stress
```

### Performance Benchmarks

Key performance targets:
- Session creation: < 0.5s each
- Message sending: < 1s each
- Question selection: < 5s for large datasets
- Export generation: < 10s for large images

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements-dev.txt
      - name: Run tests
        run: |
          cd backend
          python run_tests.py --all
      - name: Check coverage
        run: |
          cd backend
          pytest --cov=neet_app --cov-fail-under=80 tests/
```

## Troubleshooting

### Common Issues

1. **Database errors**: Ensure PostgreSQL is running and test database permissions are correct
2. **Import errors**: Check PYTHONPATH includes the backend directory
3. **Mock failures**: Verify mock patches match the actual import paths
4. **Timeout errors**: Increase timeout values for slow tests or mark them as `@pytest.mark.slow`

### Debug Mode

Run tests with more verbose output:
```bash
pytest tests/ -v --tb=long --capture=no
```

### Isolating Failing Tests

```bash
# Run single test
pytest tests/test_authentication_comprehensive.py::TestStudentLogin::test_valid_student_login -v

# Run with pdb debugger
pytest tests/test_file.py --pdb
```

## Best Practices

1. **Test Independence**: Each test should be independent and not rely on other tests
2. **Data Cleanup**: Use fixtures and Django's test database for automatic cleanup
3. **Mock External Services**: Always mock external APIs, file systems, etc.
4. **Clear Assertions**: Use descriptive assertion messages
5. **Test Edge Cases**: Test boundary conditions, error cases, and edge scenarios
6. **Performance Awareness**: Mark slow tests appropriately
7. **Documentation**: Document complex test scenarios and fixtures

## Maintenance

### Regular Tasks

1. **Update test data** when models change
2. **Review coverage reports** and add tests for uncovered code
3. **Update mocks** when external APIs change
4. **Performance benchmarking** to catch regressions
5. **Test data cleanup** to prevent test database bloat

### Adding New Features

When adding new features:
1. Write tests first (TDD approach)
2. Include unit tests for individual functions
3. Add integration tests for complete workflows
4. Update fixtures if new models are involved
5. Add performance tests for high-load scenarios

---

For questions or issues with the testing infrastructure, please refer to the development team or create an issue in the project repository.
