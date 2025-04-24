# main.py
import os
import json
import argparse
import anthropic
from utility import read_file_content
from prompt import create_prompt, get_updated_file_content
from typing import Dict, List, Optional
from dotenv import load_dotenv
from code_impact_analyzer import CodeImpactAnalyzer
from agent_core import AIAgent, Message

# Load environment variables
load_dotenv()

ai = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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
        
    def run(self, dependency_name: Optional[str] = None, min_severity: str = "medium") -> Dict:
        """
        Run the automated upgrade workflow
        
        Args:
            dependency_name: Name of a specific dependency to upgrade (if None, pick highest priority)
            min_severity: Minimum vulnerability severity to consider
            
        Returns:
            Dict: Results of the workflow
        """
        
        dependency_to_be_updated = {
            "group": "org.springframework.security",
            "artifact": "spring-security-oauth2-authorization-server",
            "current_version": "1.0.4",
            "latest_version": "1.0.5",
            "update_type": "minor",
            "vulnerabilities": [
                {"severity": "high", "description": "Critical vulnerability detected"}
            ],
            "priority": "high"
        }

        # Analyze code impact
        print(f"🔍 Analyzing code impact...")
        unique_file_set = CodeImpactAnalyzer.analyze_dependency_impact(dependency_to_be_updated["group"]+":"+dependency_to_be_updated["artifact"]+":"+dependency_to_be_updated["current_version"], self.repo_path)
        
        for unique_file in unique_file_set:
            print(f"Found usage in {unique_file}")
            file_content = read_file_content(unique_file)
            prompt_data = create_prompt(file_content, unique_file, dependency_to_be_updated["current_version"], dependency_to_be_updated["latest_version"], dependency_to_be_updated)
            get_updated_file_content(unique_file, prompt_data, ai)
             
        # Code update by AI
        print(f"🧠 Code updated by AI....!!")

def main():
    parser = argparse.ArgumentParser(description="Automated Dependency Upgrade Tool")
    parser.add_argument("--repo", required=True, help="Path to the repository")
    parser.add_argument("--dependency", help="Specific dependency to upgrade")
    parser.add_argument("--min-severity", default="medium", choices=["low", "medium", "high", "critical"], help="Minimum vulnerability severity to consider")
    parser.add_argument("--use-claude", action="store_true", default=True, help="Use Claude AI (default: True)")
    2
    args = parser.parse_args()
    
    workflow = AutomatedUpgradeWorkflow(args.repo, args.use_claude)
    result = workflow.run(args.dependency, args.min_severity)

if __name__ == "__main__":
    main()
