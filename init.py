#!/usr/bin/env python
"""
Initialization Script - Setup Market Structure Platform with daily_stock_analysis
初始化腳本 - 設置市場結構平台並整合日常股票分析
"""

import os
import sys
import shutil
from pathlib import Path


def create_directories():
    """創建必要的目錄結構"""
    directories = [
        "logs",
        "data",
        "cache",
        "results",
        "data_provider",
        "notification",
        ".github/workflows",
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created {dir_path}/")


def create_init_files():
    """創建 __init__.py 文件"""
    init_paths = [
        "data_provider/__init__.py",
        "notification/__init__.py",
    ]
    
    for path in init_paths:
        Path(path).touch(exist_ok=True)
        print(f"✓ Created {path}")


def create_env_file():
    """創建 .env 文件"""
    env_path = Path(".env")
    
    if env_path.exists():
        print("⚠ .env already exists, skipping")
        return
    
    # 複製 .env.example
    if Path(".env.example").exists():
        shutil.copy(".env.example", ".env")
        print("✓ Created .env from .env.example")
    else:
        # 創建基礎 .env
        with open(".env", "w") as f:
            f.write("""# Market Structure Platform Configuration
STOCK_LIST=600519,AAPL
LOG_LEVEL=INFO
DEBUG=false
""")
        print("✓ Created basic .env")


def validate_installation():
    """驗證安裝"""
    print("\n" + "="*80)
    print("Validating Installation...")
    print("="*80)
    
    required_packages = [
        "pandas",
        "numpy",
        "scikit-learn",
        "hmmlearn",
        "yfinance",
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (missing)")
            missing.append(package)
    
    if missing:
        print(f"\n⚠ Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("\n✓ All required packages installed")
    return True


def print_next_steps():
    """打印後續步驟"""
    print("\n" + "="*80)
    print("🎯 NEXT STEPS")
    print("="*80)
    
    steps = """
1. Configure Environment
   ├─ Edit .env with your API keys
   ├─ Set STOCK_LIST (required)
   └─ Configure notification channels (optional)

2. Test Locally
   ├─ python market_structure/analysis_scheduler.py --stocks "AAPL,600519"
   └─ Check logs/analysis.log for results

3. Deploy to GitHub Actions
   ├─ Push code to GitHub
   ├─ Add Secrets in Settings > Secrets and variables
   └─ Enable workflows in Actions tab

4. Verify Notifications
   ├─ Test Discord: Use your webhook
   ├─ Test Telegram: Send message to bot
   └─ Test Email: Check inbox

5. Monitor Execution
   ├─ GitHub Actions automatically runs daily at 18:00 (Beijing Time)
   ├─ Check logs for any issues
   └─ Verify notifications are received

Configuration Guide:
  📖 See INTEGRATION_GUIDE.py for detailed instructions
  📖 See .env.example for all available options
  
Getting Help:
  - Check logs/ directory for detailed error logs
  - Test components individually
  - Review error messages carefully
  - Validate API keys and credentials
"""
    
    print(steps)
    
    print("\n" + "="*80)
    print("✅ INITIALIZATION COMPLETE")
    print("="*80)


def main():
    """主程式"""
    
    print("\n" + "="*80)
    print("Market Structure Platform - Initialization")
    print("初始化市場結構平台")
    print("="*80 + "\n")
    
    try:
        # 1. 創建目錄
        print("Creating directory structure...")
        create_directories()
        
        # 2. 創建 __init__ 文件
        print("\nCreating module files...")
        create_init_files()
        
        # 3. 創建 .env
        print("\nSetting up configuration...")
        create_env_file()
        
        # 4. 驗證安裝
        print("\nValidating installation...")
        if not validate_installation():
            print("\n⚠ Some packages are missing")
            print("Run: pip install -r requirements.txt")
            sys.exit(1)
        
        # 5. 打印後續步驟
        print_next_steps()
        
        print("\n📚 Documentation:")
        print("  - Integration Guide: python INTEGRATION_GUIDE.py")
        print("  - Platform Docs: README_ZH_TW.md")
        print("  - Market Detector: MARKET_DETECTOR_DOCS.md")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n✗ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
