#!/usr/bin/env python3
"""
Simple test to verify the Streamlit UI can be imported and basic functions work
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_ui_import():
    """Test that the UI module can be imported without errors"""
    try:
        from apps.ui import streamlit_app
        print("✅ UI module imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import UI module: {e}")
        return False

def test_ui_functions():
    """Test that key UI functions exist"""
    try:
        from apps.ui import streamlit_app
        
        # Check that key functions exist
        functions_to_check = [
            'main',
            'show_health_status_header',
            'show_main_interface',
            'show_bom_tab',
            'show_diff_tab',
            'show_policy_tab',
            'show_actions_tab'
        ]
        
        for func_name in functions_to_check:
            if hasattr(streamlit_app, func_name):
                print(f"✅ Function {func_name} exists")
            else:
                print(f"❌ Function {func_name} missing")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking functions: {e}")
        return False

if __name__ == "__main__":
    print("Testing AI-BOM Autopilot UI...")
    
    success = True
    success &= test_ui_import()
    success &= test_ui_functions()
    
    if success:
        print("\n🎉 All UI tests passed!")
        print("To run the UI: streamlit run apps/ui/streamlit_app.py")
    else:
        print("\n💥 Some UI tests failed!")
        sys.exit(1)