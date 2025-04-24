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
