#!/usr/bin/env python
"""
Market Structure Platform - Final Deployment Verification Checklist
市場結構平台 - 最終部署驗證清單
"""

import os
import sys
from pathlib import Path


class DeploymentChecklist:
    """Complete deployment verification checklist"""
    
    def __init__(self):
        self.checks = []
        self.passed = 0
        self.failed = 0
    
    def add_check(self, category, name, status, message=""):
        """Add a check result"""
        self.checks.append({
            'category': category,
            'name': name,
            'status': status,
            'message': message
        })
        if status:
            self.passed += 1
        else:
            self.failed += 1
    
    def print_report(self):
        """Print verification report"""
        print("\n" + "="*80)
        print("MARKET STRUCTURE PLATFORM - DEPLOYMENT VERIFICATION REPORT")
        print("市場結構平台 - 部署驗證報告")
        print("="*80 + "\n")
        
        current_category = None
        for check in self.checks:
            if check['category'] != current_category:
                print(f"\n📋 {check['category']}")
                print("-" * 80)
                current_category = check['category']
            
            status_icon = "✅" if check['status'] else "❌"
            print(f"{status_icon} {check['name']}")
            if check['message']:
                print(f"   └─ {check['message']}")
        
        print("\n" + "="*80)
        print(f"Results: {self.passed} passed, {self.failed} failed")
        print("="*80 + "\n")
        
        return self.failed == 0


def check_directory_structure():
    """Check if all required directories exist"""
    checklist = DeploymentChecklist()
    
    dirs = [
        'market_structure',
        'data_provider',
        'notification',
        'alpha_engine',
        'bubble_detection',
        'core',
        'dashboard',
        'deep_value',
        'smart_money',
        'theme_rotation',
        '.github/workflows',
    ]
    
    for dir_path in dirs:
        exists = Path(dir_path).exists()
        checklist.add_check(
            "Directory Structure",
            f"Directory: {dir_path}",
            exists,
            "" if exists else "Missing directory"
        )
    
    return checklist


def check_core_files():
    """Check if all core implementation files exist"""
    checklist = DeploymentChecklist()
    
    files = {
        'market_structure/engine.py': 'Market regime detector',
        'market_structure/analysis_scheduler.py': 'Analysis orchestrator',
        'data_provider/base.py': 'Multi-source data provider',
        'notification/manager.py': 'Multi-channel notification system',
        '.github/workflows/daily-analysis.yml': 'GitHub Actions workflow',
        '.env.example': 'Configuration template',
        'requirements.txt': 'Python dependencies',
    }
    
    for file_path, description in files.items():
        exists = Path(file_path).exists()
        checklist.add_check(
            "Core Files",
            f"{file_path}",
            exists,
            description if exists else "Missing file"
        )
    
    return checklist


def check_configuration():
    """Check environment configuration"""
    checklist = DeploymentChecklist()
    
    env_exists = Path('.env').exists()
    checklist.add_check(
        "Configuration",
        ".env file exists",
        env_exists,
        "Note: Copy from .env.example if missing"
    )
    
    env_example_exists = Path('.env.example').exists()
    checklist.add_check(
        "Configuration",
        ".env.example template",
        env_example_exists,
        "Configuration reference"
    )
    
    if env_exists:
        with open('.env', 'r') as f:
            content = f.read()
            
        checks = {
            'STOCK_LIST': 'Stock list configured',
            'LOG_LEVEL': 'Log level configured',
        }
        
        for key, description in checks.items():
            has_key = key in content and f"{key}=" in content
            checklist.add_check(
                "Configuration",
                description,
                has_key,
                f"Add {key} to .env" if not has_key else ""
            )
    
    return checklist


def check_dependencies():
    """Check if required Python packages are installed"""
    checklist = DeploymentChecklist()
    
    packages = {
        'pandas': 'Data manipulation',
        'numpy': 'Numerical computing',
        'scikit-learn': 'Machine learning',
        'hmmlearn': 'Hidden Markov Models',
        'yfinance': 'Yahoo Finance data',
    }
    
    for package, description in packages.items():
        try:
            __import__(package)
            installed = True
        except ImportError:
            installed = False
        
        checklist.add_check(
            "Dependencies",
            f"{package}",
            installed,
            description if installed else "Install: pip install -r requirements.txt"
        )
    
    return checklist


def check_documentation():
    """Check if all documentation files exist"""
    checklist = DeploymentChecklist()
    
    docs = {
        'README.md': 'Main documentation',
        'INTEGRATION_GUIDE.py': 'Deployment guide',
        'INTEGRATION_COMPLETE.md': 'Complete system documentation',
        'MARKET_DETECTOR_DOCS.md': 'Market detector documentation',
    }
    
    for doc, description in docs.items():
        exists = Path(doc).exists()
        checklist.add_check(
            "Documentation",
            f"{doc}",
            exists,
            description
        )
    
    return checklist


def check_initialization():
    """Check if platform has been initialized"""
    checklist = DeploymentChecklist()
    
    dirs = ['logs', 'data', 'cache', 'results']
    
    for dir_path in dirs:
        exists = Path(dir_path).exists()
        checklist.add_check(
            "Initialization",
            f"Directory: {dir_path}/",
            exists,
            "Run: python init.py" if not exists else ""
        )
    
    return checklist


def print_deployment_guide():
    """Print the deployment guide"""
    guide = """
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║              MARKET STRUCTURE PLATFORM - DEPLOYMENT GUIDE                 ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

📋 DEPLOYMENT STEPS:

1️⃣  SETUP & INITIALIZATION
   ✓ Ensure all directories exist
   ✓ Run: python init.py
   ✓ Verify logs/, data/, cache/, results/ created

2️⃣  CONFIGURATION
   ✓ Copy: cp .env.example .env
   ✓ Edit .env with your API keys
   ✓ Set STOCK_LIST (required)
   ✓ Configure at least one notification channel (recommended)

3️⃣  LOCAL TESTING
   ✓ Test analysis: python market_structure/analysis_scheduler.py
   ✓ Check logs in logs/analysis.log
   ✓ Verify indicators calculated
   ✓ Test notifications if configured

4️⃣  GITHUB DEPLOYMENT
   ✓ Create GitHub repository
   ✓ Push code: git add . && git commit && git push
   ✓ Add Secrets in Settings > Secrets and variables > Actions
   ✓ Enable workflows in Actions tab
   ✓ Run workflow manually to test: workflow_dispatch

5️⃣  VERIFICATION
   ✓ Check workflow execution logs
   ✓ Verify notifications received
   ✓ Monitor for 24-48 hours
   ✓ Adjust configuration as needed

6️⃣  ONGOING MAINTENANCE
   ✓ Monitor logs for errors
   ✓ Review analysis results
   ✓ Update stock list as needed
   ✓ Check for API key expiration

════════════════════════════════════════════════════════════════════════════════

🔧 KEY COMMANDS:

# Initialize platform
python init.py

# Run analysis locally
python market_structure/analysis_scheduler.py --stocks "AAPL,600519" --notify

# Check system status
python -c "from notification.manager import NotificationManager; print(NotificationManager().get_status())"

# View logs
tail -f logs/analysis.log

# Test data provider
python -c "from data_provider.base import DataProviderManager; DataProviderManager().fetch_stock_data('AAPL')"

════════════════════════════════════════════════════════════════════════════════

🚨 TROUBLESHOOTING:

Issue: Import errors
→ Solution: pip install --upgrade -r requirements.txt

Issue: GitHub Actions fails
→ Solution: Check all Secrets are configured in GitHub Settings

Issue: No notifications sent
→ Solution: Verify webhook URLs and API keys in .env

Issue: Stock data not available
→ Solution: Check internet connection and data provider status

════════════════════════════════════════════════════════════════════════════════

📚 DOCUMENTATION:

• README.md - Main documentation and overview
• INTEGRATION_GUIDE.py - Detailed deployment steps
• INTEGRATION_COMPLETE.md - Complete system reference
• MARKET_DETECTOR_DOCS.md - Technical details
• .env.example - All configuration options

════════════════════════════════════════════════════════════════════════════════

✅ DEPLOYMENT CHECKLIST:

Before going live:
 □ All directories created
 □ All core files present
 □ Dependencies installed
 □ Configuration file (.env) created and filled
 □ Local testing successful
 □ Notifications tested
 □ GitHub repository created
 □ Secrets added to GitHub
 □ Workflow enabled
 □ Manual workflow test passed
 □ Documentation reviewed

════════════════════════════════════════════════════════════════════════════════

🎯 NEXT STEPS:

1. Run verification checklist: python DEPLOYMENT_CHECKLIST.py
2. Follow deployment steps above
3. Test locally before GitHub deployment
4. Monitor logs for first 24 hours
5. Adjust configuration as needed

════════════════════════════════════════════════════════════════════════════════

💡 TIPS:

• Start with one stock for testing
• Use Discord for easy webhook testing
• Monitor logs/analysis.log for debugging
• Check GitHub Actions logs for automation issues
• Keep API keys secure in .env
• Review analysis results daily initially

════════════════════════════════════════════════════════════════════════════════
"""
    print(guide)


def main():
    """Run all verification checks"""
    
    print("\n" + "="*80)
    print("MARKET STRUCTURE PLATFORM - DEPLOYMENT VERIFICATION")
    print("="*80 + "\n")
    
    all_checklists = []
    
    # Run all checks
    print("🔍 Checking directory structure...")
    checklist = check_directory_structure()
    all_checklists.append(checklist)
    
    print("🔍 Checking core files...")
    checklist = check_core_files()
    all_checklists.append(checklist)
    
    print("🔍 Checking configuration...")
    checklist = check_configuration()
    all_checklists.append(checklist)
    
    print("🔍 Checking dependencies...")
    checklist = check_dependencies()
    all_checklists.append(checklist)
    
    print("🔍 Checking documentation...")
    checklist = check_documentation()
    all_checklists.append(checklist)
    
    print("🔍 Checking initialization...")
    checklist = check_initialization()
    all_checklists.append(checklist)
    
    # Combine results
    total_passed = sum(c.passed for c in all_checklists)
    total_failed = sum(c.failed for c in all_checklists)
    
    # Print summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    print("="*80 + "\n")
    
    if total_failed == 0:
        print("🎉 All checks passed! Platform ready for deployment.\n")
    else:
        print(f"⚠️  {total_failed} checks failed. Please review and fix issues.\n")
    
    # Print deployment guide
    print_deployment_guide()
    
    # Exit status
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
