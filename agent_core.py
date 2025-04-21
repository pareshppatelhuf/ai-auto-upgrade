# agent_core.py
import os
from typing import Dict, List, Optional, Union
from dotenv import load_dotenv
import anthropic
import openai
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

class Message(BaseModel):
    role: str
    content: str

class AIAgent:
    def __init__(self, use_claude: bool = True):
        """
        Initialize the AI Agent with either Claude or OpenAI
        
        Args:
            use_claude (bool): If True, use Claude API, otherwise use OpenAI
        """
        self.use_claude = use_claude
        
        if use_claude:
            self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = "claude-3-opus-20240229"
        else:
            self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = "gpt-4-turbo"
            
        self.system_prompt = """
        You are an AI assistant specialized in automated software dependency upgrades.
        Your task is to help developers identify, implement, and validate dependency updates
        while minimizing security risks and developer intervention.
        
        You analyze dependency networks, predict code impacts, automate test creation,
        and help create pull requests to maintain modern, secure, and compliant software systems.
        
        Be precise, technical, and focus on providing actionable insights.
        """
        
    def send_message(self, messages: List[Message], temperature: float = 0.7) -> str:
        """
        Send a message to the AI model and get a response
        
        Args:
            messages: List of messages in the conversation
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            
        Returns:
            str: The model's response
        """
        if self.use_claude:
            formatted_messages = [
                {"role": msg.role, "content": msg.content} for msg in messages
            ]
            
            response = self.client.messages.create(
                model=self.model,
                system=self.system_prompt,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=4000
            )
            return response.content[0].text
        else:
            # Format messages for OpenAI
            formatted_messages = [{"role": "system", "content": self.system_prompt}]
            formatted_messages.extend([{"role": msg.role, "content": msg.content} for msg in messages])
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=4000
            )
            return response.choices[0].message.content

    def analyze_upgrade_strategy(self, 
                               project_info: Dict,
                               dependencies: List[Dict],
                               code_samples: Optional[List[str]] = None) -> str:
        """
        Analyze dependencies and suggest an upgrade strategy
        
        Args:
            project_info: Information about the project
            dependencies: List of dependencies with current and available versions
            code_samples: Representative code samples using the dependencies
            
        Returns:
            str: Upgrade strategy recommendations
        """
        prompt = f"""
        Please analyze the following project and its dependencies to suggest an upgrade strategy:
        
        Project Information:
        {project_info}
        
        Dependencies:
        {dependencies}
        
        """
        
        if code_samples:
            prompt += f"""
            Code Samples:
            {code_samples}
            """
            
        prompt += """
        For each dependency, please provide:
        1. Risk assessment (High/Medium/Low)
        2. Recommended version to upgrade to
        3. Potential breaking changes to be aware of
        4. Suggested testing approach
        5. Implementation strategy
        
        Prioritize security-critical updates and minimize breaking changes.
        """
        
        messages = [Message(role="user", content=prompt)]
        return self.send_message(messages)
    
    def predict_code_changes(self, 
                           dependency_name: str,
                           current_version: str,
                           target_version: str,
                           api_usage_examples: List[str]) -> str:
        """
        Predict necessary code changes for a dependency upgrade
        
        Args:
            dependency_name: Name of the dependency
            current_version: Current version
            target_version: Target version for upgrade
            api_usage_examples: Examples of how the API is currently used
            
        Returns:
            str: Predicted code changes
        """
        prompt = f"""
        Please predict the necessary code changes to upgrade {dependency_name} from version {current_version} to {target_version}.
        
        Here are examples of how the dependency is currently used in the codebase:
        
        ```
        {api_usage_examples}
        ```
        
        Please provide:
        1. Specific code modifications needed
        2. Any API changes between versions
        3. Deprecated methods or classes to be aware of
        4. Suggested replacement patterns
        """
        
        messages = [Message(role="user", content=prompt)]
        return self.send_message(messages)
    
    def generate_test_cases(self,
                          dependency_name: str,
                          changed_apis: List[Dict],
                          existing_test_examples: Optional[List[str]] = None) -> str:
        """
        Generate test cases for validating a dependency upgrade
        
        Args:
            dependency_name: Name of the dependency
            changed_apis: List of APIs that changed in the upgrade
            existing_test_examples: Examples of existing tests
            
        Returns:
            str: Generated test cases
        """
        prompt = f"""
        Please generate test cases to validate the upgrade of {dependency_name}.
        
        The following APIs have changed or need special attention:
        {changed_apis}
        """
        
        if existing_test_examples:
            prompt += f"""
            Here are examples of existing tests:
            
            ```
            {existing_test_examples}
            ```
            """
            
        prompt += """
        Please provide:
        1. Unit tests for critical functionality
        2. Integration tests for component interactions
        3. Edge cases that should be tested
        4. Test assertions to verify correct behavior
        
        Format the tests as executable code that can be directly added to the test suite.
        """
        
        messages = [Message(role="user", content=prompt)]
        return self.send_message(messages, temperature=0.2)  # Lower temperature for more precise code
    
    def create_pr_description(self,
                            dependency_updates: List[Dict],
                            code_changes: Dict,
                            test_results: Dict) -> str:
        """
        Generate a pull request description for dependency upgrades
        
        Args:
            dependency_updates: List of dependencies being updated
            code_changes: Summary of code changes made
            test_results: Results of validation tests
            
        Returns:
            str: Formatted pull request description
        """
        prompt = f"""
        Please create a comprehensive pull request description for the following dependency upgrades:
        
        Dependencies being updated:
        {dependency_updates}
        
        Code changes implemented:
        {code_changes}
        
        Test results:
        {test_results}
        
        The PR description should include:
        1. A clear summary of the changes
        2. Motivation for the upgrades (security, features, etc.)
        3. Potential risks and mitigations
        4. Testing performed
        5. Any manual verification steps needed
        
        Format the description in Markdown for GitHub.
        """
        
        messages = [Message(role="user", content=prompt)]
        return self.send_message(messages)
