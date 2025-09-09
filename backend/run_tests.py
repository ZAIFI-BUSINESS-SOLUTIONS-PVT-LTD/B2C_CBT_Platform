"""
Test runner script for NEET CBT Platform
Run different test suites and generate coverage reports
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print('='*60)
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    if result.returncode != 0:
        print(f"❌ FAILED: {description}")
        return False
    else:
        print(f"✅ PASSED: {description}")
        return True

def run_unit_tests():
    """Run unit tests with coverage"""
    command = 'pytest -m "unit" --cov=neet_app --cov-report=html --cov-report=term-missing tests/'
    return run_command(command, "Unit Tests with Coverage")

def run_integration_tests():
    """Run integration tests"""
    command = 'pytest -m "integration" tests/'
    return run_command(command, "Integration Tests")

def run_auth_tests():
    """Run authentication tests"""
    command = 'pytest -m "auth" tests/'
    return run_command(command, "Authentication Tests")

def run_chat_tests():
    """Run chatbot tests"""
    command = 'pytest -m "chat" tests/'
    return run_command(command, "Chatbot Tests")

def run_question_selection_tests():
    """Run question selection tests"""
    command = 'pytest -m "question_selection" tests/'
    return run_command(command, "Question Selection Tests")

def run_export_tests():
    """Run export functionality tests"""
    command = 'pytest -m "export" tests/'
    return run_command(command, "Export Tests")

def run_stress_tests():
    """Run stress tests"""
    command = 'pytest -m "stress" --maxfail=3 tests/'
    return run_command(command, "Stress Tests")

def run_all_tests():
    """Run all tests except stress tests"""
    command = 'pytest -m "not stress" --cov=neet_app --cov-report=html --cov-report=term-missing tests/'
    return run_command(command, "All Tests (excluding stress)")

def run_fast_tests():
    """Run fast tests only (exclude slow and stress)"""
    command = 'pytest -m "not slow and not stress" tests/'
    return run_command(command, "Fast Tests Only")

def run_coverage_only():
    """Generate coverage report without running tests"""
    command = 'pytest --cov=neet_app --cov-report=html --cov-report=term-missing --collect-only tests/'
    return run_command(command, "Coverage Report Generation")

def run_specific_test_file(test_file):
    """Run a specific test file"""
    command = f'pytest {test_file} -v'
    return run_command(command, f"Specific Test File: {test_file}")

def main():
    parser = argparse.ArgumentParser(description='NEET CBT Platform Test Runner')
    parser.add_argument('--unit', action='store_true', help='Run unit tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--auth', action='store_true', help='Run authentication tests')
    parser.add_argument('--chat', action='store_true', help='Run chatbot tests')
    parser.add_argument('--questions', action='store_true', help='Run question selection tests')
    parser.add_argument('--export', action='store_true', help='Run export tests')
    parser.add_argument('--stress', action='store_true', help='Run stress tests')
    parser.add_argument('--all', action='store_true', help='Run all tests (excluding stress)')
    parser.add_argument('--fast', action='store_true', help='Run fast tests only')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--file', type=str, help='Run specific test file')
    parser.add_argument('--install-deps', action='store_true', help='Install test dependencies')
    
    args = parser.parse_args()
    
    # Change to backend directory
    os.chdir(backend_dir)
    
    # Install dependencies if requested
    if args.install_deps:
        print("Installing test dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements-dev.txt'])
        return
    
    # Run specific test file
    if args.file:
        success = run_specific_test_file(args.file)
        sys.exit(0 if success else 1)
    
    # Track results
    results = []
    
    # Run selected test suites
    if args.unit:
        results.append(('Unit Tests', run_unit_tests()))
    
    if args.integration:
        results.append(('Integration Tests', run_integration_tests()))
    
    if args.auth:
        results.append(('Auth Tests', run_auth_tests()))
    
    if args.chat:
        results.append(('Chat Tests', run_chat_tests()))
    
    if args.questions:
        results.append(('Question Selection Tests', run_question_selection_tests()))
    
    if args.export:
        results.append(('Export Tests', run_export_tests()))
    
    if args.stress:
        results.append(('Stress Tests', run_stress_tests()))
    
    if args.all:
        results.append(('All Tests', run_all_tests()))
    
    if args.fast:
        results.append(('Fast Tests', run_fast_tests()))
    
    if args.coverage:
        results.append(('Coverage Report', run_coverage_only()))
    
    # If no specific tests requested, run fast tests by default
    if not any([args.unit, args.integration, args.auth, args.chat, args.questions, 
                args.export, args.stress, args.all, args.fast, args.coverage]):
        print("No specific test suite selected. Running fast tests by default.")
        results.append(('Fast Tests (Default)', run_fast_tests()))
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    passed = 0
    failed = 0
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed + failed} test suites")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print(f"\n❌ {failed} test suite(s) failed!")
        sys.exit(1)
    else:
        print(f"\n✅ All {passed} test suite(s) passed!")
        sys.exit(0)

if __name__ == '__main__':
    main()
