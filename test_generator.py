# test_generator.py
import os
import re
import json
import subprocess
from typing import Dict, List, Optional, Tuple
import pytest

class TestGenerator:
    def __init__(self, repo_path: str):
        """
        Initialize the test generator
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
        
    def detect_test_framework(self) -> str:
        """
        Detect the testing framework used in the project
        
        Returns:
            str: Test framework (jest, pytest, junit, etc.)
        """
        # Check for Jest (JavaScript/TypeScript)
        package_json_path = os.path.join(self.repo_path, "package.json")
        if os.path.exists(package_json_path):
            with open(package_json_path, 'r') as f:
                try:
                    data = json.load(f)
                    
                    # Check dependencies and devDependencies
                    deps = data.get("dependencies", {})
                    dev_deps = data.get("devDependencies", {})
                    
                    if "jest" in dev_deps or "jest" in deps:
                        return "jest"
                    elif "mocha" in dev_deps or "mocha" in deps:
                        return "mocha"
                except:
                    pass
        
        # Check for pytest (Python)
        requirements_path = os.path.join(self.repo_path, "requirements.txt")
        if os.path.exists(requirements_path):
            with open(requirements_path, 'r') as f:
                content = f.read()
                if "pytest" in content:
                    return "pytest"
        
        # Check for JUnit (Java)
        pom_path = os.path.join(self.repo_path, "pom.xml")
        if os.path.exists(pom_path):
            with open(pom_path, 'r') as f:
                content = f.read()
                if "junit" in content.lower():
                    return "junit"
        
        # Default to generic
        return "generic"
    
    def find_existing_tests(self, dependency_name: str) -> List[Dict]:
        """
        Find existing tests that might be related to a dependency
        
        Args:
            dependency_name: Name of the dependency
            
        Returns:
            List[Dict]: List of existing tests
        """
        test_framework = self.detect_test_framework()
        
        # Normalize dependency name
        normalized_name = dependency_name.lower().replace('-', '_')
        
        results = []
        
        # Define test directories based on common conventions
        test_dirs = ["test", "tests", "src/test", "__tests__", "spec"]
        
        for test_dir in test_dirs:
            test_path = os.path.join(self.repo_path, test_dir)
            
            if not os.path.exists(test_path) or not os.path.isdir(test_path):
                continue
                
            for root, _, files in os.walk(test_path):
                for file in files:
                    # Skip non-test files
                    if not self._is_test_file(file, test_framework):
                        continue
                        
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.repo_path)
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        try:
                            content = f.read()
                            
                            # Check if the file contains references to the dependency
                            if normalized_name in content.lower():
                                # Extract test cases
                                test_cases = self._extract_test_cases(content, test_framework)
                                
                                if test_cases:
                                    results.append({
                                        "file": relative_path,
                                        "test_cases": test_cases
                                    })
                        except:
                            # Skip files that can't be read
                            pass
        
        return results
    
    def _is_test_file(self, filename: str, framework: str) -> bool:
        """
        Check if a file is a test file based on naming conventions
        
        Args:
            filename: Name of the file
            framework: Test framework
            
        Returns:
            bool: True if the file is a test file
        """
        if framework == "jest":
            return filename.endswith((".test.js", ".test.ts", ".spec.js", ".spec.ts"))
        elif framework == "mocha":
            return filename.endswith((".test.js", ".spec.js"))
        elif framework == "pytest":
            return filename.startswith("test_") and filename.endswith(".py")
        elif framework == "junit":
            return filename.endswith("Test.java")
        else:
            # Generic test file detection
            return "test" in filename.lower() or "spec" in filename.lower()
    
    def _extract_test_cases(self, content: str, framework: str) -> List[Dict]:
        """
        Extract test cases from a file
        
        Args:
            content: Content of the file
            framework: Test framework
            
        Returns:
            List[Dict]: List of test cases
        """
        test_cases = []
        
        if framework == "jest" or framework == "mocha":
            # Extract Jest/Mocha test cases
            # Look for patterns like describe('...', () => { ... }) and it('...', () => { ... })
            describe_pattern = r"describe\(['\"]([^'\"]+)['\"]"
            it_pattern = r"it\(['\"]([^'\"]+)['\"]"
            
            # Find describe blocks
            for match in re.finditer(describe_pattern, content):
                describe_name = match.group(1)
                
                # Find it blocks (individual tests)
                for it_match in re.finditer(it_pattern, content):
                    test_name = it_match.group(1)
                    
                    test_cases.append({
                        "name": f"{describe_name} - {test_name}",
                        "type": "unit"
                    })
                    
        elif framework == "pytest":
            # Extract pytest test cases
            # Look for functions starting with test_
            test_pattern = r"def\s+(test_[a-zA-Z0-9_]+)\s*\("
            
            for match in re.finditer(test_pattern, content):
                test_name = match.group(1)
                
                test_cases.append({
                    "name": test_name,
                    "type": "unit"
                })
                
        elif framework == "junit":
            # Extract JUnit test cases
            # Look for methods annotated with @Test
            test_pattern = r"@Test\s+[public\s]+void\s+([a-zA-Z0-9_]+)\s*\("
            
            for match in re.finditer(test_pattern, content):
                test_name = match.group(1)
                
                test_cases.append({
                    "name": test_name,
                    "type": "unit"
                })
        
        return test_cases
    
    def generate_test_cases(self, 
                          dependency_name: str, 
                          api_usage: List[Dict],
                          breaking_changes: List[Dict]) -> Dict:
        """
        Generate test cases for a dependency upgrade
        
        Args:
            dependency_name: Name of the dependency
            api_usage: List of API usage examples
            breaking_changes: List of breaking changes
            
        Returns:
            Dict: Generated test cases
        """
        test_framework = self.detect_test_framework()
        
        # Find existing tests
        existing_tests = self.find_existing_tests(dependency_name)
        
        # Generate new tests based on API usage and breaking changes
        generated_tests = []
        
        if test_framework == "jest":
            generated_tests = self._generate_jest_tests(dependency_name, api_usage, breaking_changes)
        elif test_framework == "pytest":
            generated_tests = self._generate_pytest_tests(dependency_name, api_usage, breaking_changes)
        elif test_framework == "junit":
            generated_tests = self._generate_junit_tests(dependency_name, api_usage, breaking_changes)
        else:
            # Generic test generation
            generated_tests = self._generate_generic_tests(dependency_name, api_usage, breaking_changes)
        
        return {
            "existing_tests": existing_tests,
            "generated_tests": generated_tests,
            "framework": test_framework
        }
    
    def _generate_jest_tests(self, 
                           dependency_name: str, 
                           api_usage: List[Dict],
                           breaking_changes: List[Dict]) -> List[Dict]:
        """
        Generate Jest tests for a dependency upgrade
        
        Args:
            dependency_name: Name of the dependency
            api_usage: List of API usage examples
            breaking_changes: List of breaking changes
            
        Returns:
            List[Dict]: Generated Jest tests
        """
        tests = []
        
        # Normalize dependency name for use in variable names
        normalized_name = dependency_name.replace('-', '').replace('@', '').replace('/', '')
        
        # Create a basic test file
        test_content = f"""
import {normalized_name} from '{dependency_name}';

describe('{dependency_name} upgrade validation', () => {{
    test('should import the dependency correctly', () => {{
        expect({normalized_name}).toBeDefined();
    }});
        """
        
        # Add tests for each API usage
        for i, usage in enumerate(api_usage):
            # Extract the function or method being used
            context = usage.get("context", "")
            
            # Simple heuristic to extract function names
            function_match = re.search(r'\.([a-zA-Z0-9_]+)\(', context)
            
            if function_match:
                function_name = function_match.group(1)
                
                test_content += f"""
    test('{function_name} function should be available', () => {{
        expect({normalized_name}.{function_name}).toBeDefined();
        // Add more specific assertions based on expected behavior
    }});
                """
                
                tests.append({
                    "name": f"validate_{function_name}_availability",
                    "content": test_content,
                    "file": f"{normalized_name}.test.js"
                })
        
        # Add tests for breaking changes
        for i, change in enumerate(breaking_changes):
            change_description = change.get("description", "")
            
            test_content += f"""
    test('should handle breaking change: {change_description}', () => {{
        // Add assertions to verify the breaking change is handled correctly
    }});
            """
        
        test_content += "\n});"
        
        tests.append({
            "name": f"validate_{normalized_name}_upgrade",
            "content": test_content,
            "file": f"{normalized_name}.test.js"
        })
        
        return tests
    
    def _generate_pytest_tests(self, 
                             dependency_name: str, 
                             api_usage: List[Dict],
                             breaking_changes: List[Dict]) -> List[Dict]:
        """
        Generate pytest tests for a dependency upgrade
        
        Args:
            dependency_name: Name of the dependency
            api_usage: List of API usage examples
            breaking_changes: List of breaking changes
            
        Returns:
            List[Dict]: Generated pytest tests
        """
        tests = []
        
        # Normalize dependency name for use in variable names
        normalized_name = dependency_name.replace('-', '_').replace('.', '_').lower()
        
        # Create a basic test file
        test_content = f"""
import pytest
import {normalized_name}

def test_{normalized_name}_import():
    \"\"\"Test that the dependency can be imported correctly.\"\"\"
    assert {normalized_name} is not None
        """
        
        # Add tests for each API usage
        for i, usage in enumerate(api_usage):
            # Extract the function or method being used
            context = usage.get("context", "")
            
            # Simple heuristic to extract function names
            function_match = re.search(r'\.([a-zA-Z0-9_]+)\(', context)
            
            if function_match:
                function_name = function_match.group(1)
                
                test_content += f"""

def test_{normalized_name}_{function_name}_availability():
    \"\"\"Test that the {function_name} function is available.\"\"\"
    assert hasattr({normalized_name}, '{function_name}')
    # Add more specific assertions based on expected behavior
                """
                
                tests.append({
                    "name": f"test_{normalized_name}_{function_name}_availability",
                    "content": test_content,
                    "file": f"test_{normalized_name}.py"
                })
        
        # Add tests for breaking changes
        for i, change in enumerate(breaking_changes):
            change_description = change.get("description", "")
            
            test_content += f"""

def test_{normalized_name}_breaking_change_{i}():
    \"\"\"Test that breaking change is handled: {change_description}\"\"\"
    # Add assertions to verify the breaking change is handled correctly
    pass
            """
        
        tests.append({
            "name": f"test_{normalized_name}_upgrade",
            "content": test_content,
            "file": f"test_{normalized_name}.py"
        })
        
        return tests
    
    def _generate_junit_tests(self, 
                            dependency_name: str, 
                            api_usage: List[Dict],
                            breaking_changes: List[Dict]) -> List[Dict]:
        """
        Generate JUnit tests for a dependency upgrade
        
        Args:
            dependency_name: Name of the dependency
            api_usage: List of API usage examples
            breaking_changes: List of breaking changes
            
        Returns:
            List[Dict]: Generated JUnit tests
        """
        tests = []
        
        # Convert dependency name to Java class name
        class_name = "".join(word.capitalize() for word in re.findall(r'[a-zA-Z0-9]+', dependency_name))
        
        # Create a basic test file
        test_content = f"""
import org.junit.Test;
import static org.junit.Assert.*;

public class {class_name}UpgradeTest {{
    
    @Test
    public void testDependencyAvailability() {{
        // Test that the dependency can be used
        // Add assertions based on expected behavior
    }}
        """
        
        # Add tests for each API usage
        for i, usage in enumerate(api_usage):
            # Extract the function or method being used
            context = usage.get("context", "")
            
            # Simple heuristic to extract method names
            method_match = re.search(r'\.([a-zA-Z0-9_]+)\(', context)
            
            if method_match:
                method_name = method_match.group(1)
                
                test_content += f"""
    
    @Test
    public void test{method_name.capitalize()}Method() {{
        // Test that the {method_name} method works correctly
        // Add assertions based on expected behavior
    }}
                """
                
                tests.append({
                    "name": f"test{method_name.capitalize()}Method",
                    "content": test_content,
                    "file": f"{class_name}UpgradeTest.java"
                })
        
        # Add tests for breaking changes
        for i, change in enumerate(breaking_changes):
            change_description = change.get("description", "")
            
            test_content += f"""
    
    @Test
    public void testBreakingChange{i}() {{
        // Test that breaking change is handled: {change_description}
        // Add assertions to verify the breaking change is handled correctly
    }}
            """
        
        test_content += "\n}"
        
        tests.append({
            "name": f"test{class_name}Upgrade",
            "content": test_content,
            "file": f"{class_name}UpgradeTest.java"
        })
        
        return tests
    
    def _generate_generic_tests(self, 
                              dependency_name: str, 
                              api_usage: List[Dict],
                              breaking_changes: List[Dict]) -> List[Dict]:
        """
        Generate generic tests for a dependency upgrade
        
        Args:
            dependency_name: Name of the dependency
            api_usage: List of API usage examples
            breaking_changes: List of breaking changes
            
        Returns:
            List[Dict]: Generated generic tests
        """
        # Default to pytest format for generic tests
        return self._generate_pytest_tests(dependency_name, api_usage, breaking_changes)
    
    def write_test_files(self, generated_tests: List[Dict]) -> List[str]:
        """
        Write generated test files to disk
        
        Args:
            generated_tests: List of generated tests
            
        Returns:
            List[str]: List of written test file paths
        """
        test_framework = self.detect_test_framework()
        
        # Determine the test directory
        test_dir = None
        
        if test_framework == "jest":
            test_dirs = ["__tests__", "test", "tests"]
        elif test_framework == "pytest":
            test_dirs = ["tests", "test"]
        elif test_framework == "junit":
            test_dirs = ["src/test/java", "test"]
        else:
            test_dirs = ["tests", "test"]
            
        # Find the first existing test directory
        for dir_name in test_dirs:
            dir_path = os.path.join(self.repo_path, dir_name)
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                test_dir = dir_path
                break
                
        # If no test directory exists, create one
        if test_dir is None:
            test_dir = os.path.join(self.repo_path, test_dirs[0])
            os.makedirs(test_dir, exist_ok=True)
            
        # Write test files
        written_files = []
        
        for test in generated_tests:
            file_path = os.path.join(test_dir, test["file"])
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w') as f:
                f.write(test["content"])
                
            written_files.append(file_path)
            
        return written_files
    
    def run_tests(self, test_files: List[str] = None) -> Dict:
        """
        Run tests to validate the dependency upgrade
        
        Args:
            test_files: List of test files to run (if None, run all tests)
            
        Returns:
            Dict: Test results
        """
        test_framework = self.detect_test_framework()
        
        try:
            if test_framework == "jest":
                return self._run_jest_tests(test_files)
            elif test_framework == "pytest":
                return self._run_pytest_tests(test_files)
            elif test_framework == "junit":
                return self._run_junit_tests(test_files)
            else:
                # Default to generic test runner
                return self._run_generic_tests(test_files)
        except Exception as e:
            return {
                "success": False,
                "framework": test_framework,
                "error": str(e),
                "results": []
            }
    
    def _run_jest_tests(self, test_files: List[str] = None) -> Dict:
        """
        Run Jest tests
        
        Args:
            test_files: List of test files to run
            
        Returns:
            Dict: Test results
        """
        command = ["npm", "test"]
        
        if test_files:
            # Jest can run specific test files
            command.extend(test_files)
            
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            return {
                "success": result.returncode == 0,
                "framework": "jest",
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {
                "success": False,
                "framework": "jest",
                "error": str(e)
            }
    
    def _run_pytest_tests(self, test_files: List[str] = None) -> Dict:
        """
        Run pytest tests
        
        Args:
            test_files: List of test files to run
            
        Returns:
            Dict: Test results
        """
        command = ["pytest", "-v"]
        
        if test_files:
            command.extend(test_files)
            
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            return {
                "success": result.returncode == 0,
                "framework": "pytest",
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {
                "success": False,
                "framework": "pytest",
                "error": str(e)
            }
    
    def _run_junit_tests(self, test_files: List[str] = None) -> Dict:
        """
        Run JUnit tests
        
        Args:
            test_files: List of test files to run
            
        Returns:
            Dict: Test results
        """
        # For Maven projects
        if os.path.exists(os.path.join(self.repo_path, "pom.xml")):
            command = ["mvn", "test"]
            
            if test_files:
                # Maven can run specific test classes
                test_classes = []
                for file_path in test_files:
                    # Extract class name from file path
                    file_name = os.path.basename(file_path)
                    if file_name.endswith(".java"):
                        class_name = file_name[:-5]  # Remove .java extension
                        test_classes.append(class_name)
                
                if test_classes:
                    test_pattern = ",".join(test_classes)
                    command.extend(["-Dtest=" + test_pattern])
        else:
            # For Gradle projects
            command = ["./gradlew", "test"]
            
            if test_files:
                # Gradle can run specific test classes
                test_classes = []
                for file_path in test_files:
                    # Extract class name from file path
                    file_name = os.path.basename(file_path)
                    if file_name.endswith(".java"):
                        class_name = file_name[:-5]  # Remove .java extension
                        test_classes.append(class_name)
                
                if test_classes:
                    test_pattern = ",".join(test_classes)
                    command.extend(["--tests", test_pattern])
            
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            return {
                "success": result.returncode == 0,
                "framework": "junit",
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {
                "success": False,
                "framework": "junit",
                "error": str(e)
            }
    
    def _run_generic_tests(self, test_files: List[str] = None) -> Dict:
        """
        Run generic tests
        
        Args:
            test_files: List of test files to run
            
        Returns:
            Dict: Test results
        """
        # Default to pytest for generic tests
        return self._run_pytest_tests(test_files)
