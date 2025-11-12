#!/usr/bin/env python3
"""Check if all essential packages are installed."""

import sys

essential_packages = [
    ("fastapi", "FastAPI web framework"),
    ("uvicorn", "Uvicorn ASGI server"),
    ("pandas", "Pandas data processing"),
    ("numpy", "NumPy numerical computing"),
    ("requests", "Requests HTTP library"),
    ("yfinance", "Yahoo Finance API"),
    ("openai", "OpenAI API client"),
    ("pydantic", "Pydantic data validation"),
]

optional_packages = [
    ("dotenv", "Python dotenv (has fallback)", "python-dotenv"),
    ("plotly", "Plotly visualization", None),
    ("matplotlib", "Matplotlib plotting", None),
    ("sklearn", "Scikit-learn ML", "scikit-learn"),
    ("pmdarima", "Pmdarima time series", None),
    ("statsmodels", "Statsmodels statistics", None),
]

def check_package(import_name: str, description: str, install_name: str = None) -> bool:
    """Check if a package is installed."""
    display_name = install_name if install_name else import_name
    try:
        __import__(import_name.replace("-", "_"))
        print(f"✅ {display_name:20s} - {description}")
        return True
    except ImportError:
        print(f"❌ {display_name:20s} - {description} (MISSING)")
        return False

def main():
    """Check all packages."""
    print("=" * 60)
    print("Package Installation Check")
    print("=" * 60)
    print()
    
    print("Essential Packages:")
    print("-" * 60)
    essential_missing = []
    for package, description in essential_packages:
        if not check_package(package, description):
            essential_missing.append(package)
    
    print()
    print("Optional Packages:")
    print("-" * 60)
    optional_missing = []
    for package_info in optional_packages:
        if len(package_info) == 3:
            package, description, install_name = package_info
        else:
            package, description = package_info
            install_name = None
        if not check_package(package, description, install_name):
            optional_missing.append(install_name if install_name else package)
    
    print()
    print("=" * 60)
    if essential_missing:
        print(f"❌ {len(essential_missing)} essential package(s) missing:")
        for pkg in essential_missing:
            print(f"   - {pkg}")
        print()
        print("Install missing packages with:")
        print(f"   pip install {' '.join(essential_missing)}")
        print()
        print("Or install all packages with:")
        print("   pip install -r requirements.txt")
        return 1
    else:
        print("✅ All essential packages are installed!")
        if optional_missing:
            print(f"ℹ️  {len(optional_missing)} optional package(s) missing (not required)")
        return 0

if __name__ == "__main__":
    sys.exit(main())

