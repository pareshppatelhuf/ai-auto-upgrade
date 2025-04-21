# run.py
import os
import argparse
from dotenv import load_dotenv
from main import AutomatedUpgradeWorkflow

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Automated Dependency Upgrade Tool")
    parser.add_argument("--repo", required=True, help="Path to the repository")
    parser.add_argument("--dependency", help="Specific dependency to upgrade")
    parser.add_argument("--min-severity", default="medium", choices=["low", "medium", "high", "critical"], help="Minimum vulnerability severity to consider")
    parser.add_argument("--use-claude", action="store_true", default=True, help="Use Claude AI (default: True)")
    parser.add_argument("--use-openai", action="store_false", dest="use_claude", help="Use OpenAI instead of Claude")
    
    args = parser.parse_args()
    
    print("🚀 Starting Automated Dependency Upgrade workflow")
    print(f"📂 Repository: {args.repo}")
    print(f"🤖 AI Model: {'Claude' if args.use_claude else 'OpenAI'}")
    
    if args.dependency:
        print(f"📦 Target dependency: {args.dependency}")
    else:
        print(f"📦 Scanning for highest priority dependencies (min severity: {args.min_severity})")
    
    print("\n" + "="*80 + "\n")
    
    workflow = AutomatedUpgradeWorkflow(args.repo, args.use_claude)
    result = workflow.run(args.dependency, args.min_severity)
    
    print("\n" + "="*80 + "\n")
    
    if result["success"]:
        print("\n✅ Upgrade workflow completed successfully!")
        print(f"Dependency: {result['dependency']['name']} upgraded from {result['dependency']['current_version']} to {result['dependency']['latest_version']}")
        print(f"Pull Request: {result['pr_url']}")
    else:
        print(f"\n❌ Upgrade workflow failed: {result['message']}")

if __name__ == "__main__":
    main()
