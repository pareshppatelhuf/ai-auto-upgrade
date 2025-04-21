# main.py
import os
import json
import argparse
from typing import Dict, List, Optional
from dotenv import load_dotenv

from agent_core import AIAgent, Message
from dependency_scanner import DependencyScanner
from code_impact_analyzer import CodeImpactAnalyzer
from test_generator import TestGenerator
from pr_creator import PRCreator

# Load environment variables
load_dotenv()

class AutomatedUpgradeWorkflow:
    def __init__(self, repo_path: str, use_claude: bool = True):
        """
        Initialize the automated upgrade workflow
        
        Args:
            repo_path: Path to the repository
            use_claude: If True, use Claude API, otherwise use OpenAI
        """
        self.repo_path = repo_path
        self.use_claude = use_claude
        
        # Initialize components
        self.agent = AIAgent(use_claude=use_claude)
        self.scanner = DependencyScanner(repo_path)
        self.analyzer = CodeImpactAnalyzer(repo_path)
        self.test_generator = TestGenerator(repo_path)
        self.pr_creator = PRCreator(repo_path)
        
    def run(self, dependency_name: Optional[str] = None, min_severity: str = "medium") -> Dict:
        """
        Run the automated upgrade workflow
        
        Args:
            dependency_name: Name of a specific dependency to upgrade (if None, pick highest priority)
            min_severity: Minimum vulnerability severity to consider
            
        Returns:
            Dict: Results of the workflow
        """
        print("🔍 Scanning repository for dependencies...")
        upgrade_candidates = self.scanner.get_upgrade_candidates(min_severity=min_severity)
        
        if not upgrade_candidates:
            return {
                "success": False,
                "message": "No upgrade candidates found"
            }
            
        print(f"📊 Found {len(upgrade_candidates)} upgrade candidates")
        
        # If a specific dependency was requested, find it
        target_dependency = None
        if dependency_name:
            for candidate in upgrade_candidates:
                if candidate["name"] == dependency_name:
                    target_dependency = candidate
                    break
                    
            if not target_dependency:
                return {
                    "success": False,
                    "message": f"Dependency {dependency_name} not found or doesn't need upgrade"
                }
        else:
            # Otherwise, pick the highest priority dependency
            target_dependency = upgrade_candidates[0]
            
        print(f"🎯 Selected dependency: {target_dependency['name']} (current: {target_dependency['current_version']}, target: {target_dependency['latest_version']})")
        
        # Analyze code impact
        print(f"🔍 Analyzing code impact...")
        api_usage = self.analyzer.find_dependency_usage(target_dependency["name"])
        api_examples = self.analyzer.extract_api_usage_examples(target_dependency["name"])
        breaking_changes = self.analyzer.analyze_breaking_changes(
            target_dependency["name"],
            target_dependency["current_version"],
            target_dependency["latest_version"]
        )
        
        # Get upgrade strategy from AI
        print(f"🧠 Getting upgrade strategy from AI...")
        project_info = {
            "name": os.path.basename(os.path.abspath(self.repo_path)),
            "type": self.scanner.detect_project_type()
        }
        
        strategy = self.agent.analyze_upgrade_strategy(
            project_info=project_info,
            dependencies=[target_dependency],
            code_samples=api_examples
        )
        
        print(f"📝 AI Upgrade Strategy:\n{strategy}")
        
        # Get code changes prediction from AI
        print(f"🧠 Predicting necessary code changes...")
        code_changes = self.agent.predict_code_changes(
            dependency_name=target_dependency["name"],
            current_version=target_dependency["current_version"],
            target_version=target_dependency["latest_version"],
            api_usage_examples=api_examples
        )
        
        print(f"📝 Predicted Code Changes:\n{code_changes}")
        
        # Create a branch for the upgrade
        print(f"🌿 Creating branch for upgrade...")
        branch_name = self.pr_creator.create_branch(
            target_dependency["name"],
            target_dependency["latest_version"]
        )
        
        if not branch_name:
            return {
                "success": False,
                "message": "Failed to create branch"
            }
            
        print(f"✅ Created branch: {branch_name}")
        
        # Update the dependency
        print(f"📦 Updating dependency...")
        update_success = self.pr_creator.update_dependency(
            target_dependency["name"],
            target_dependency["current_version"],
            target_dependency["latest_version"]
        )
        
        if not update_success:
            return {
                "success": False,
                "message": "Failed to update dependency"
            }
            
        print(f"✅ Updated dependency")
        
        # Generate tests
        print(f"🧪 Generating tests...")
        changed_apis = [{"name": usage.get("import_path", ""), "context": usage.get("context", "")} for usage in api_usage]
        
        test_cases = self.agent.generate_test_cases(
            dependency_name=target_dependency["name"],
            changed_apis=changed_apis
        )
        
        print(f"📝 Generated Test Cases:\n{test_cases}")
        
        # Write test files
        test_data = self.test_generator.generate_test_cases(
            target_dependency["name"],
            api_usage,
            breaking_changes.get("breaking_changes", [])
        )
        
        # Commit changes
        print(f"💾 Committing changes...")
        commit_success = self.pr_creator.commit_changes(
            target_dependency["name"],
            target_dependency["current_version"],
            target_dependency["latest_version"]
        )
        
        if not commit_success:
            return {
                "success": False,
                "message": "Failed to commit changes"
            }
            
        print(f"✅ Committed changes")
        
        # Run tests
        print(f"🧪 Running tests...")
        test_results = self.test_generator.run_tests()
        
        # Push branch
        print(f"📤 Pushing branch...")
        push_success = self.pr_creator.push_branch(branch_name)
        
        if not push_success:
            return {
                "success": False,
                "message": "Failed to push branch"
            }
            
        print(f"✅ Pushed branch")
        
        # Create PR description
        print(f"📝 Creating PR description...")
        pr_description = self.agent.create_pr_description(
            dependency_updates=[target_dependency],
            code_changes={"summary": code_changes},
            test_results=test_results
        )
        
        print(f"📝 PR Description:\n{pr_description}")
        
        # Create PR
        print(f"🔄 Creating pull request...")
        pr_result = self.pr_creator.create_pull_request(
            branch_name=branch_name,
            dependency_name=target_dependency["name"],
            current_version=target_dependency["current_version"],
            target_version=target_dependency["latest_version"],
            pr_description=pr_description
        )
        
        if not pr_result.get("success", False):
            return {
                "success": False,
                "message": f"Failed to create PR: {pr_result.get('error', 'Unknown error')}"
            }
            
        print(f"✅ Created PR: {pr_result.get('pr_url', '')}")
        
        return {
            "success": True,
            "dependency": target_dependency,
            "branch_name": branch_name,
            "pr_number": pr_result.get("pr_number"),
            "pr_url": pr_result.get("pr_url")
        }

def main():
    parser = argparse.ArgumentParser(description="Automated Dependency Upgrade Tool")
    parser.add_argument("--repo", required=True, help="Path to the repository")
    parser.add_argument("--dependency", help="Specific dependency to upgrade")
    parser.add_argument("--min-severity", default="medium", choices=["low", "medium", "high", "critical"], help="Minimum vulnerability severity to consider")
    parser.add_argument("--use-claude", action="store_true", default=True, help="Use Claude AI (default: True)")
    
    args = parser.parse_args()
    
    workflow = AutomatedUpgradeWorkflow(args.repo, args.use_claude)
    result = workflow.run(args.dependency, args.min_severity)
    
    if result["success"]:
        print("\n✅ Upgrade workflow completed successfully!")
        print(f"Dependency: {result['dependency']['name']} upgraded from {result['dependency']['current_version']} to {result['dependency']['latest_version']}")
        print(f"Pull Request: {result['pr_url']}")
    else:
        print(f"\n❌ Upgrade workflow failed: {result['message']}")

if __name__ == "__main__":
    main()
