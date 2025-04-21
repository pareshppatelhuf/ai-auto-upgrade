# code_impact_analyzer.py
import os
import re
import ast
import json
from typing import Dict, List, Optional, Set, Tuple
import subprocess
from git import Repo

class CodeImpactAnalyzer:
    def __init__(self, repo_path: str):
        """
        Initialize the code impact analyzer
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
        
    def find_dependency_usage(self, dependency_name: str) -> List[Dict]:
        """
        Find where a dependency is used in the codebase
        
        Args:
            dependency_name: Name of the dependency
            
        Returns:
            List[Dict]: List of files and lines where the dependency is used
        """
        project_type = self._detect_project_type()
        
        if project_type == "npm":
            return self._find_js_dependency_usage(dependency_name)
        elif project_type == "pip":
            return self._find_python_dependency_usage(dependency_name)
        elif project_type in ["maven", "gradle"]:
            return self._find_java_dependency_usage(dependency_name)
        else:
            return []
    
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
    
    def _find_js_dependency_usage(self, dependency_name: str) -> List[Dict]:
        """
        Find where a JavaScript/npm dependency is used in the codebase
        
        Args:
            dependency_name: Name of the npm package
            
        Returns:
            List[Dict]: List of files and lines where the dependency is used
        """
        usage_patterns = [
            f"require\\(['\"]({dependency_name}|{dependency_name}/[^'\"]+)['\"]\\)",
            f"from ['\"]({dependency_name}|{dependency_name}/[^'\"]+)['\"]",
            f"import .+ from ['\"]({dependency_name}|{dependency_name}/[^'\"]+)['\"]"
        ]
        
        results = []
        
        for root, _, files in os.walk(self.repo_path):
            # Skip node_modules and other non-source directories
            if "node_modules" in root or ".git" in root:
                continue
                
            for file in files:
                if file.endswith((".js", ".jsx", ".ts", ".tsx")):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.repo_path)
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        try:
                            content = f.read()
                            
                            for pattern in usage_patterns:
                                for match in re.finditer(pattern, content):
                                    # Get line number
                                    line_num = content[:match.start()].count('\n') + 1
                                    
                                    # Extract context (the line of code)
                                    lines = content.split('\n')
                                    context = lines[line_num - 1] if line_num <= len(lines) else ""
                                    
                                    results.append({
                                        "file": relative_path,
                                        "line": line_num,
                                        "context": context.strip(),
                                        "import_path": match.group(1)
                                    })
                        except:
                            # Skip files that can't be read
                            pass
        
        return results
    
    def _find_python_dependency_usage(self, dependency_name: str) -> List[Dict]:
        """
        Find where a Python dependency is used in the codebase
        
        Args:
            dependency_name: Name of the Python package
            
        Returns:
            List[Dict]: List of files and lines where the dependency is used
        """
        # Normalize dependency name
        normalized_name = dependency_name.lower().replace('-', '_')
        
        usage_patterns = [
            f"import {normalized_name}",
            f"from {normalized_name} import",
            f"import {normalized_name} as"
        ]
        
        results = []
        
        for root, _, files in os.walk(self.repo_path):
            # Skip virtual environments and other non-source directories
            if "venv" in root or ".git" in root or "__pycache__" in root:
                continue
                
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.repo_path)
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        try:
                            content = f.read()
                            
                            for pattern in usage_patterns:
                                for match in re.finditer(pattern, content):
                                    # Get line number
                                    line_num = content[:match.start()].count('\n') + 1
                                    
                                    # Extract context (the line of code)
                                    lines = content.split('\n')
                                    context = lines[line_num - 1] if line_num <= len(lines) else ""
                                    
                                    results.append({
                                        "file": relative_path,
                                        "line": line_num,
                                        "context": context.strip(),
                                        "import_path": pattern.replace(normalized_name, normalized_name)
                                    })
                                    
                            # Also try to find usage of the package's functions/classes
                            try:
                                tree = ast.parse(content)
                                for node in ast.walk(tree):
                                    if isinstance(node, ast.Name) and node.id == normalized_name:
                                        line_num = node.lineno
                                        
                                        # Extract context
                                        lines = content.split('\n')
                                        context = lines[line_num - 1] if line_num <= len(lines) else ""
                                        
                                        results.append({
                                            "file": relative_path,
                                            "line": line_num,
                                            "context": context.strip(),
                                            "usage_type": "direct_reference"
                                        })
                            except:
                                # Skip AST parsing errors
                                pass
                        except:
                            # Skip files that can't be read
                            pass
        
        return results
    
    def _find_java_dependency_usage(self, dependency_name: str) -> List[Dict]:
        """
        Find where a Java dependency is used in the codebase
        
        Args:
            dependency_name: Name of the Maven/Gradle package (groupId:artifactId)
            
        Returns:
            List[Dict]: List of files and lines where the dependency is used
        """
        # Extract artifactId from the dependency name
        try:
            group_id, artifact_id = dependency_name.split(":")
        except:
            artifact_id = dependency_name
            
        # Convert artifact_id to potential package names
        # This is a heuristic and might not work for all cases
        package_name_candidates = []
        
        # Convert from kebab-case to different formats
        if "-" in artifact_id:
            # Original
            package_name_candidates.append(artifact_id)
            
            # Camel case
            parts = artifact_id.split("-")
            camel_case = parts[0] + "".join(p.capitalize() for p in parts[1:])
            package_name_candidates.append(camel_case)
            
            # Pascal case
            pascal_case = "".join(p.capitalize() for p in parts)
            package_name_candidates.append(pascal_case)
        else:
            package_name_candidates.append(artifact_id)
        
        results = []
        
        for root, _, files in os.walk(self.repo_path):
            # Skip build directories and other non-source directories
            if "build" in root or "target" in root or ".git" in root:
                continue
                
            for file in files:
                if file.endswith((".java", ".kt", ".scala")):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.repo_path)
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        try:
                            content = f.read()
                            
                            # Look for import statements
                            import_pattern = r"import\s+([^;]+);"
                            for match in re.finditer(import_pattern, content):
                                import_stmt = match.group(1).strip()
                                
                                # Check if any candidate is in the import statement
                                for candidate in package_name_candidates:
                                    if candidate.lower() in import_stmt.lower():
                                        # Get line number
                                        line_num = content[:match.start()].count('\n') + 1
                                        
                                        # Extract context (the line of code)
                                        lines = content.split('\n')
                                        context = lines[line_num - 1] if line_num <= len(lines) else ""
                                        
                                        results.append({
                                            "file": relative_path,
                                            "line": line_num,
                                            "context": context.strip(),
                                            "import_path": import_stmt
                                        })
                                        break
                        except:
                            # Skip files that can't be read
                            pass
        
        return results
    
    def extract_api_usage_examples(self, dependency_name: str, max_examples: int = 10) -> List[str]:
        """
        Extract code examples showing how the dependency's API is used
        
        Args:
            dependency_name: Name of the dependency
            max_examples: Maximum number of examples to extract
            
        Returns:
            List[str]: Code examples showing API usage
        """
        usage_locations = self.find_dependency_usage(dependency_name)
        
        if not usage_locations:
            return []
            
        examples = []
        processed_files = set()
        
        for usage in usage_locations:
            file_path = os.path.join(self.repo_path, usage["file"])
            
            # Skip if we already processed this file
            if file_path in processed_files:
                continue
                
            processed_files.add(file_path)
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Extract a code snippet around the usage
                    lines = content.split('\n')
                    line_index = usage["line"] - 1
                    
                    # Get a window of lines around the usage
                    start = max(0, line_index - 5)
                    end = min(len(lines), line_index + 15)
                    
                    snippet = "\n".join(lines[start:end])
                    examples.append(f"File: {usage['file']}\n```\n{snippet}\n```")
                    
                    if len(examples) >= max_examples:
                        break
            except:
                continue
        
        return examples
    
    def analyze_breaking_changes(self, 
                               dependency_name: str, 
                               current_version: str, 
                               target_version: str) -> Dict:
        """
        Analyze potential breaking changes when upgrading a dependency
        
        Args:
            dependency_name: Name of the dependency
            current_version: Current version
            target_version: Target version for upgrade
            
        Returns:
            Dict: Analysis of potential breaking changes
        """
        # This would ideally query package documentation, release notes, etc.
        # For this example, we'll use a simplified approach
        
        project_type = self._detect_project_type()
        
        # Get usage examples
        usage_examples = self.extract_api_usage_examples(dependency_name)
        
        # Get repository history to see if this dependency was upgraded before
        repo_history = self._get_dependency_upgrade_history(dependency_name)
        
        # For npm packages, we can use the npm view command to get information
        if project_type == "npm":
            try:
                result = subprocess.run(
                    ["npm", "view", dependency_name, "versions", "--json"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    versions = json.loads(result.stdout)
                    
                    # Find versions between current and target
                    try:
                        from packaging import version
                        current_ver = version.parse(current_version)
                        target_ver = version.parse(target_version)
                        
                        intermediate_versions = [
                            v for v in versions
                            if current_ver < version.parse(v) <= target_ver
                        ]
                    except:
                        intermediate_versions = []
                        
                    return {
                        "dependency": dependency_name,
                        "current_version": current_version,
                        "target_version": target_version,
                        "usage_examples": usage_examples,
                        "previous_upgrades": repo_history,
                        "intermediate_versions": intermediate_versions,
                        "risk_assessment": self._assess_upgrade_risk(dependency_name, current_version, target_version)
                    }
            except Exception as e:
                print(f"Error analyzing npm breaking changes: {e}")
        
        # Generic analysis for other package types
        return {
            "dependency": dependency_name,
            "current_version": current_version,
            "target_version": target_version,
            "usage_examples": usage_examples,
            "previous_upgrades": repo_history,
            "risk_assessment": self._assess_upgrade_risk(dependency_name, current_version, target_version)
        }
    
    def _get_dependency_upgrade_history(self, dependency_name: str) -> List[Dict]:
        """
        Get history of previous upgrades for a dependency
        
        Args:
            dependency_name: Name of the dependency
            
        Returns:
            List[Dict]: History of previous upgrades
        """
        try:
            repo = Repo(self.repo_path)
            
            # This is a simplified approach - in a real implementation,
            # we would search commit messages and diff content more thoroughly
            history = []
            
            # Look for package.json changes for npm
            if os.path.exists(os.path.join(self.repo_path, "package.json")):
                for commit in repo.iter_commits(paths="package.json"):
                    if dependency_name.lower() in commit.message.lower():
                        history.append({
                            "commit": commit.hexsha,
                            "date": commit.committed_datetime.isoformat(),
                            "message": commit.message
                        })
            
            # Look for requirements.txt changes for Python
            elif os.path.exists(os.path.join(self.repo_path, "requirements.txt")):
                for commit in repo.iter_commits(paths="requirements.txt"):
                    if dependency_name.lower() in commit.message.lower():
                        history.append({
                            "commit": commit.hexsha,
                            "date": commit.committed_datetime.isoformat(),
                            "message": commit.message
                        })
            
            # Look for pom.xml changes for Maven
            elif os.path.exists(os.path.join(self.repo_path, "pom.xml")):
                for commit in repo.iter_commits(paths="pom.xml"):
                    if dependency_name.lower() in commit.message.lower():
                        history.append({
                            "commit": commit.hexsha,
                            "date": commit.committed_datetime.isoformat(),
                            "message": commit.message
                        })
            
            return history[:5]  # Return the 5 most recent upgrades
            
        except Exception as e:
            print(f"Error getting dependency upgrade history: {e}")
            return []
    
    def _assess_upgrade_risk(self, dependency_name: str, current_version: str, target_version: str) -> str:
        """
        Assess the risk level of a dependency upgrade
        
        Args:
            dependency_name: Name of the dependency
            current_version: Current version
            target_version: Target version for upgrade
            
        Returns:
            str: Risk level (low, medium, high)
        """
        try:
            from packaging import version
            
            current_ver = version.parse(current_version)
            target_ver = version.parse(target_version)
            
            # Major version bump is high risk
            if target_ver.major > current_ver.major:
                return "high"
            
            # Minor version bump is medium risk
            elif target_ver.minor > current_ver.minor:
                return "medium"
            
            # Patch version bump is low risk
            else:
                return "low"
                
        except Exception as e:
            print(f"Error assessing upgrade risk: {e}")
            
            # Default to medium if we can't parse versions
            return "medium"
    
    def get_affected_files(self, dependency_name: str) -> List[str]:
        """
        Get a list of files that might be affected by upgrading a dependency
        
        Args:
            dependency_name: Name of the dependency
            
        Returns:
            List[str]: List of potentially affected files
        """
        usage_locations = self.find_dependency_usage(dependency_name)
        return list(set(usage["file"] for usage in usage_locations))
