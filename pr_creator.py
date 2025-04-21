# pr_creator.py
import os
import re
import json
import subprocess
from typing import Dict, List, Optional
from git import Repo
import requests

class PRCreator:
    def __init__(self, repo_path: str):
        """
        Initialize the PR creator
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
        self.github_token = os.getenv("GITHUB_TOKEN")
        
    def update_dependency(self, 
                        dependency_name: str, 
                        current_version: str, 
                        target_version: str) -> bool:
        """
        Update a dependency in the project configuration
        
        Args:
            dependency_name: Name of the dependency
            current_version: Current version
            target_version: Target version
            
        Returns:
            bool: True if the update was successful
        """
        project_type = self._detect_project_type()
        
        if project_type == "npm":
            return self._update_npm_dependency(dependency_name, target_version)
        elif project_type == "pip":
            return self._update_pip_dependency(dependency_name, target_version)
        elif project_type == "maven":
            return self._update_maven_dependency(dependency_name, target_version)
        elif project_type == "gradle":
            return self._update_gradle_dependency(dependency_name, target_version)
        else:
            return False
    
    def _detect_project_type(self) -> str:
        """
        Detect the type of project based on configuration files
        
        Returns:
            str: Project type (npm, maven, pip, etc.)
        """
        if os.path.exists(os.path.join(self.repo_path, "package.json")):
            return "npm"
        elif os.path.exists(os.path.join(self.repo_path, "pom.xml")):
            return "maven"
        elif os.path.exists(os.path.join(self.repo_path, "requirements.txt")) or \
             os.path.exists(os.path.join(self.repo_path, "setup.py")):
            return "pip"
        elif os.path.exists(os.path.join(self.repo_path, "build.gradle")) or \
             os.path.exists(os.path.join(self.repo_path, "build.gradle.kts")):
            return "gradle"
        else:
            return "unknown"
    
    def _update_npm_dependency(self, dependency_name: str, target_version: str) -> bool:
        """
        Update an npm dependency
        
        Args:
            dependency_name: Name of the npm package
            target_version: Target version
            
        Returns:
            bool: True if the update was successful
        """
        try:
            # Use npm to update the dependency
            result = subprocess.run(
                ["npm", "install", f"{dependency_name}@{target_version}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0
        except Exception as e:
            print(f"Error updating npm dependency: {e}")
            return False
    
    def _update_pip_dependency(self, dependency_name: str, target_version: str) -> bool:
        """
        Update a Python dependency in requirements.txt
        
        Args:
            dependency_name: Name of the Python package
            target_version: Target version
            
        Returns:
            bool: True if the update was successful
        """
        requirements_path = os.path.join(self.repo_path, "requirements.txt")
        
        if not os.path.exists(requirements_path):
            return False
            
        try:
            with open(requirements_path, 'r') as f:
                lines = f.readlines()
                
            updated_lines = []
            found = False
            
            for line in lines:
                if line.strip().startswith(f"{dependency_name}=="):
                    updated_lines.append(f"{dependency_name}=={target_version}\n")
                    found = True
                else:
                    updated_lines.append(line)
            
            if not found:
                updated_lines.append(f"{dependency_name}=={target_version}\n")
                
            with open(requirements_path, 'w') as f:
                f.writelines(updated_lines)
                
            return True
        except Exception as e:
            print(f"Error updating pip dependency: {e}")
            return False
    
    def _update_maven_dependency(self, dependency_name: str, target_version: str) -> bool:
        """
        Update a Maven dependency in pom.xml
        
        Args:
            dependency_name: Name of the Maven package (groupId:artifactId)
            target_version: Target version
            
        Returns:
            bool: True if the update was successful
        """
        pom_path = os.path.join(self.repo_path, "pom.xml")
        
        if not os.path.exists(pom_path):
            return False
            
        try:
            # Parse groupId and artifactId
            group_id, artifact_id = dependency_name.split(":")
            
            with open(pom_path, 'r') as f:
                content = f.read()
                
            # Find and replace the version in the dependency section
            pattern = f"<dependency>\\s*<groupId>{group_id}</groupId>\\s*<artifactId>{artifact_id}</artifactId>\\s*<version>[^<]+</version>"
            replacement = f"<dependency>\n        <groupId>{group_id}</groupId>\n        <artifactId>{artifact_id}</artifactId>\n        <version>{target_version}</version>"
            
            updated_content = re.sub(pattern, replacement, content)
            
            with open(pom_path, 'w') as f:
                f.write(updated_content)
                
            return True
        except Exception as e:
            print(f"Error updating Maven dependency: {e}")
            return False
    
    def _update_gradle_dependency(self, dependency_name: str, target_version: str) -> bool:
        """
        Update a Gradle dependency in build.gradle
        
        Args:
            dependency_name: Name of the Gradle package (groupId:artifactId)
            target_version: Target version
            
        Returns:
            bool: True if the update was successful
        """
        gradle_path = os.path.join(self.repo_path, "build.gradle")
        
        if not os.path.exists(gradle_path):
            gradle_path = os.path.join(self.repo_path, "build.gradle.kts")
            if not os.path.exists(gradle_path):
                return False
                
        try:
            # Parse groupId and artifactId
            group_id, artifact_id = dependency_name.split(":")
            
            with open(gradle_path, 'r') as f:
                content = f.read()
                
            # Find and replace the version in the dependency section
            pattern = f"implementation ['\"]({group_id}:{artifact_id}:)[^'\"]+['\"]"
            replacement = f"implementation '$1{target_version}'"
            
            updated_content = re.sub(pattern, replacement, content)
            
            with open(gradle_path, 'w') as f:
                f.write(updated_content)
                
            return True
        except Exception as e:
            print(f"Error updating Gradle dependency: {e}")
            return False
    
    def create_branch(self, dependency_name: str, target_version: str) -> str:
        """
        Create a new branch for the dependency upgrade
        
        Args:
            dependency_name: Name of the dependency
            target_version: Target version
            
        Returns:
            str: Name of the created branch
        """
        try:
            repo = Repo(self.repo_path)
            
            # Create a branch name
            normalized_name = dependency_name.replace('@', '').replace('/', '-').replace(':', '-')
            branch_name = f"upgrade-{normalized_name}-to-{target_version}"
            
            # Check if the branch already exists
            if branch_name in repo.heads:
                # If it exists, check it out
                repo.git.checkout(branch_name)
            else:
                # Create and check out the new branch
                repo.git.checkout('HEAD', b=branch_name)
                
            return branch_name
        except Exception as e:
            print(f"Error creating branch: {e}")
            return ""
    
    def commit_changes(self, dependency_name: str, current_version: str, target_version: str) -> bool:
        """
        Commit the dependency upgrade changes
        
        Args:
            dependency_name: Name of the dependency
            current_version: Current version
            target_version: Target version
            
        Returns:
            bool: True if the commit was successful
        """
        try:
            repo = Repo(self.repo_path)
            
            # Check if there are changes to commit
            if not repo.is_dirty():
                print("No changes to commit")
                return False
                
            # Add all changes
            repo.git.add(A=True)
            
            # Create commit message
            commit_message = f"Upgrade {dependency_name} from {current_version} to {target_version}"
            
            # Commit the changes
            repo.git.commit(m=commit_message)
            
            return True
        except Exception as e:
            print(f"Error committing changes: {e}")
            return False
    
    def push_branch(self, branch_name: str) -> bool:
        """
        Push the branch to the remote repository
        
        Args:
            branch_name: Name of the branch to push
            
        Returns:
            bool: True if the push was successful
        """
        try:
            repo = Repo(self.repo_path)
            
            # Get the remote
            origin = repo.remote('origin')
            
            # Push the branch
            origin.push(branch_name)
            
            return True
        except Exception as e:
            print(f"Error pushing branch: {e}")
            return False
    
    def create_pull_request(self, 
                          branch_name: str, 
                          dependency_name: str, 
                          current_version: str, 
                          target_version: str,
                          pr_description: str) -> Dict:
        """
        Create a pull request for the dependency upgrade
        
        Args:
            branch_name: Name of the branch
            dependency_name: Name of the dependency
            current_version: Current version
            target_version: Target version
            pr_description: Description for the pull request
            
        Returns:
            Dict: Pull request details
        """
        try:
            repo = Repo(self.repo_path)
            
            # Get the remote URL
            remote_url = repo.remote('origin').url
            
            # Extract owner and repo name from the URL
            # Assuming a GitHub URL like https://github.com/owner/repo.git
            # or git@github.com:owner/repo.git
            if remote_url.startswith('https://'):
                match = re.match(r'https://github.com/([^/]+)/([^/\.]+)', remote_url)
                if match:
                    owner, repo_name = match.groups()
                else:
                    return {"success": False, "error": "Could not parse GitHub URL"}
            else:
                match = re.match(r'git@github.com:([^/]+)/([^/\.]+)', remote_url)
                if match:
                    owner, repo_name = match.groups()
                else:
                    return {"success": False, "error": "Could not parse GitHub URL"}
            
            # Create PR title
            pr_title = f"Upgrade {dependency_name} from {current_version} to {target_version}"
            
            # Create PR using GitHub API
            url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "title": pr_title,
                "body": pr_description,
                "head": branch_name,
                "base": "main"  # Assuming the main branch is 'main'
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                pr_data = response.json()
                return {
                    "success": True,
                    "pr_number": pr_data["number"],
                    "pr_url": pr_data["html_url"]
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create PR: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            print(f"Error creating pull request: {e}")
            return {"success": False, "error": str(e)}
