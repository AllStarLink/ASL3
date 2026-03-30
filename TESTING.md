# Running Tests for asl-node-auth-check

Quick guide for running and developing tests for the ASL3 project.

## Quick Start

```bash
# Run all stable, passing tests
make test

# Run all Python tests (including those with known issues)
make test-python

# Run specific test file
pytest tests/test_asl_node_auth_check/test_asl_node_auth_check_core.py -v

# Run tests with coverage
pytest tests/ --cov=bin/
```

## Available Makefile Targets

| Target | Purpose |
|--------|---------|
| `make test` | Run all stable, core tests (recommended) |
| `make test-python` | Run all Python tests incl. those with mocking issues |
| `make test-shell` | Run shell script tests (BATS) |
| `make test-all` | Run all tests (Python + Shell) |

## CI/CD Integration

Tests are automatically run in GitHub Actions on:
- Python 3.11 and 3.12
- All pull requests
- Pushes to the develop branch

Workflow file: `.github/workflows/tests.yml`

## Adding New Tests

1. Create test files in `tests/test_<function>/` directory with `test_*.py` naming
2. Use existing test files as templates
3. Run `make test` to verify your tests work
4. Tests are automatically discovered and run in CI/CD

### Test File Template

```python
import unittest
from unittest.mock import patch

class TestMyFeature(unittest.TestCase):
    def test_something(self):
        """Brief description of what is being tested."""
        # Test code here
        pass

if __name__ == "__main__":
    unittest.main()
```

## Configuration Files

- **pytest.ini** - Pytest configuration including test discovery patterns and markers
- **Makefile** - Make targets for running tests
- **.github/workflows/tests.yml** - GitHub Actions CI/CD workflow

## Dependencies

Tests require:
- Python 3.11+
- pytest
- pytest-cov
- sympy
- requests
- unittest.mock (standard library)

Install with:
```bash
pip install pytest sympy requests
```

## Troubleshooting

### Tests not discovered
```bash
# Check what pytest finds
pytest --collect-only tests/

# Ensure test file starts with test_
# and test functions start with test_
```

### Import errors
```bash
# Ensure you're in the project root
cd /path/to/ASL3

# Verify python path includes the scripts
python3 -c "import sys; sys.path.insert(0, '.'); exec(open('tests/test_check_node_status.py').read())"
```

### Mocking issues
Some tests require complex mock setup for subprocess/requests. These are listed in the "In-Development Tests" section. See TEST_COVERAGE.md for details on these tests and workarounds.

## Code Coverage

Generate coverage report:
```bash
pytest tests/test_check_node_status.py tests/test_asl_node_auth_check_core.py \
  --cov=bin/asl-node-auth-check \
  --cov-report=html
```

View report: `htmlcov/index.html`

## For More Information

See `TEST_COVERAGE.md` for detailed test statistics and coverage information.
