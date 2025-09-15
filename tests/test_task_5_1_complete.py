#!/usr/bin/env python3
"""
Comprehensive test suite for Task 5.1: BOM, Diff, and Policy Engines
This script validates all sub-tasks are working correctly:
- 5.2: BOM validation step post-generation
- 5.3: DiffPrev service for structural comparison
- 5.4: PolicyCheck service with starter policies and dedupe logic
"""

import sys
import os
import subprocess

def run_test(test_name, test_script):
    """Run a test script and return success status"""
    print(f"\n{'='*60}")
    print(f"🧪 Running {test_name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, test_script], 
                              capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            print(f"✅ {test_name}: PASSED")
            # Print last few lines of output for summary
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines[-3:]:
                if line.strip():
                    print(f"   {line}")
            return True
        else:
            print(f"❌ {test_name}: FAILED")
            print("STDOUT:")
            print(result.stdout)
            print("STDERR:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"💥 {test_name}: ERROR - {e}")
        return False

def main():
    """Run all Task 5.1 tests"""
    print("🚀 ML-BOM Autopilot - Task 5.1 Complete Test Suite")
    print("Testing BOM Generation, Diff Analysis, and Policy Evaluation")
    
    tests = [
        ("BOM Generator Tests", "test_bom_generator.py"),
        ("Diff Engine Tests", "test_diff_engine.py"),
        ("Policy Engine Tests", "test_policy_engine.py"),
        ("Integration Tests", "test_bom_diff_policy_integration.py")
    ]
    
    results = []
    
    for test_name, test_script in tests:
        success = run_test(test_name, test_script)
        results.append((test_name, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nTask 5.1 Implementation Complete:")
        print("✅ 5.2: BOM validation with cyclonedx-python-lib")
        print("✅ 5.3: Structural BOM diff with stable component IDs")
        print("✅ 5.4: Policy engine with 5 starter policies and dedupe logic")
        print("\nFeatures implemented:")
        print("• CycloneDX v1.5 ML-BOM generation")
        print("• SHA256 hash calculation and logging")
        print("• Tool-based BOM validation with PASS/FAIL status")
        print("• Structural diff ignoring non-semantic fields")
        print("• Policy evaluation with dedupe_key logic")
        print("• Support for policy overrides with expiration")
        print("• Comprehensive error handling and logging")
        return 0
    else:
        print(f"\n❌ {total - passed} TESTS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())