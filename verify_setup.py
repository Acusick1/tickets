#!/usr/bin/env python3
"""Verification script to check project setup."""
import sys
from pathlib import Path


def check_files():
    """Check that all required files exist."""
    print("Checking project files...")
    required_files = [
        "main.py",
        "src/models.py",
        "src/alert_manager.py",
        "src/notifier.py",
        "src/scheduler.py",
        "src/config.py",
        "src/scrapers/base.py",
        "src/scrapers/ticketmaster.py",
        "src/scrapers/stubhub.py",
        "src/scrapers/viagogo.py",
        "src/dashboard/app.py",
        "config/alerts.yaml.example",
        "config/settings.yaml.example",
        "tests/conftest.py",
        "tests/test_models.py",
        "tests/test_scrapers.py",
        "tests/test_alert_manager.py",
        "tests/test_notifier.py",
    ]

    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)
            print(f"  ✗ Missing: {file_path}")
        else:
            print(f"  ✓ {file_path}")

    if missing:
        print(f"\n❌ {len(missing)} files missing!")
        return False
    else:
        print(f"\n✅ All {len(required_files)} required files present!")
        return True


def check_dependencies():
    """Check that dependencies are installed."""
    print("\nChecking dependencies...")
    dependencies = [
        "playwright",
        "sqlalchemy",
        "apscheduler",
        "flask",
        "yaml",
        "pytest",
    ]

    missing = []
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"  ✓ {dep}")
        except ImportError:
            missing.append(dep)
            print(f"  ✗ {dep}")

    if missing:
        print(f"\n❌ {len(missing)} dependencies missing!")
        print("Run: uv sync")
        return False
    else:
        print(f"\n✅ All dependencies installed!")
        return True


def check_config():
    """Check configuration files."""
    print("\nChecking configuration...")

    if not Path("config/settings.yaml").exists():
        print("  ⚠️  config/settings.yaml not found")
        print("     Run: cp config/settings.yaml.example config/settings.yaml")
        print("     Then edit with your email credentials")
        config_ok = False
    else:
        print("  ✓ config/settings.yaml exists")
        config_ok = True

    if not Path("config/alerts.yaml").exists():
        print("  ⚠️  config/alerts.yaml not found")
        print("     Run: cp config/alerts.yaml.example config/alerts.yaml")
        print("     Then add your events to monitor")
        config_ok = False
    else:
        print("  ✓ config/alerts.yaml exists")

    if not config_ok:
        print("\n⚠️  Configuration incomplete!")
        return False
    else:
        print("\n✅ Configuration files present!")
        return True


def check_directories():
    """Check that required directories exist."""
    print("\nChecking directories...")
    directories = ["config", "data", "tests", "src", "src/scrapers", "src/dashboard"]

    for dir_path in directories:
        path = Path(dir_path)
        if not path.exists():
            print(f"  ✗ Missing: {dir_path}")
            path.mkdir(parents=True, exist_ok=True)
            print(f"    Created: {dir_path}")
        else:
            print(f"  ✓ {dir_path}")

    print("\n✅ All directories present!")
    return True


def run_tests():
    """Run the test suite."""
    print("\nRunning tests...")
    import subprocess

    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "-v", "--tb=short"],
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.returncode == 0:
            print("\n✅ All tests passed!")
            return True
        else:
            print("\n❌ Some tests failed!")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("  ⚠️  uv not found - skipping tests")
        print("     Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return None


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Ticket Price Scraper - Setup Verification")
    print("=" * 60)

    checks = []
    checks.append(("Files", check_files()))
    checks.append(("Directories", check_directories()))
    checks.append(("Dependencies", check_dependencies()))
    checks.append(("Configuration", check_config()))

    # Only run tests if basics are OK
    if all(c[1] for c in checks):
        test_result = run_tests()
        if test_result is not None:
            checks.append(("Tests", test_result))

    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)

    for name, result in checks:
        if result is None:
            status = "⚠️  Skipped"
        elif result:
            status = "✅ Passed"
        else:
            status = "❌ Failed"
        print(f"{status} - {name}")

    if all(c[1] for c in checks if c[1] is not None):
        print("\n🎉 Setup verification complete! You're ready to run the scraper.")
        print("\nNext steps:")
        print("  1. Edit config/settings.yaml with your email credentials")
        print("  2. Edit config/alerts.yaml with events to monitor")
        print("  3. Run: uv run python main.py")
        return 0
    else:
        print("\n⚠️  Setup incomplete. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
