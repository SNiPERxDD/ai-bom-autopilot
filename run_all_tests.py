#!/usr/bin/env python3
"""
Comprehensive test runner for AI-BOM Autopilot
Runs all tests and provides a complete system validation
"""

import sys
import os
import subprocess
import time
from datetime import datetime

def run_test_script(script_name, description):
    """Run a test script and return results"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        success = result.returncode == 0
        
        print(f"\n⏱️  Duration: {duration:.2f} seconds")
        print(f"🎯 Result: {'✅ PASSED' if success else '❌ FAILED'}")
        
        return success, duration
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out after 5 minutes")
        return False, 300
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False, 0

def main():
    """Run all tests"""
    print("🚀 AI-BOM Autopilot - Comprehensive Test Suite")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Test suite configuration
    tests = [
        ("tests/test_setup.py", "Dependency Installation & Basic Setup"),
        ("core/graph/selftest.py", "System Self-Test & Capabilities"),
        ("tests/test_sql_syntax.py", "SQL Syntax & API Structure Validation"),
        ("tests/test_e2e_mock.py", "End-to-End Mock Workflow Testing"),
    ]
    
    results = []
    total_duration = 0
    
    # Run all tests
    for script, description in tests:
        success, duration = run_test_script(script, description)
        results.append((description, success, duration))
        total_duration += duration
        
        if not success:
            print(f"\n⚠️  Test failed: {description}")
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"📈 Overall Results: {passed}/{total} tests passed")
    print(f"⏱️  Total Duration: {total_duration:.2f} seconds")
    print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n📋 Detailed Results:")
    for description, success, duration in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {description} ({duration:.2f}s)")
    
    # Final verdict
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
        print("✅ AI-BOM Autopilot is ready for deployment")
        print("\n📝 Next Steps:")
        print("  1. Configure your .env file with real credentials")
        print("  2. Set up TiDB Serverless database")
        print("  3. Run: ./run.sh")
        print("  4. Create demo project: python seed/create_demo_project.py")
        return True
    else:
        print(f"\n❌ {total - passed} TESTS FAILED")
        print("🔧 Please fix the failing tests before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)