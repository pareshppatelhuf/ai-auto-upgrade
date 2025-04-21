# dependency_scanner.py
import os
import json
import requests
from typing import Dict, List, Optional, Tuple
import subprocess
import re
from packaging import version
import semver

class DependencyScanner:
    def __init__(self, repo_path: str):
        """
        Initialize the dependency scanner
        
        Args:
            repo_path: Path to the repository to scan
        """
        self.repo_path = repo_path
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.nvd_api_key = os.getenv("NVD_API_KEY")
        
    def detect_project_type(self) -> str:
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
            
    def scan_dependencies(self) -> List[Dict]:
        """
        Scan the repository for dependencies
        
        Returns:
            List[Dict]: List of dependencies with their details
        """
        project_type = self.detect_project_type()
        
        if project_type == "npm":
            return self._scan_npm_dependencies()
        elif project_type == "pip":
            return self._scan_pip_dependencies()
        elif project_type == "maven":
            return self._scan_maven_dependencies()
        elif project_type == "gradle":
            return self._scan_gradle_dependencies()
        else:
            raise ValueError(f"Unsupported project type: {project_type}")
            
    def _scan_npm_dependencies(self) -> List[Dict]:
        """
        Scan npm dependencies from package.json
        
        Returns:
            List[Dict]: List of npm dependencies
        """
        package_json_path = os.path.join(self.repo_path, "package.json")
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)
            
        dependencies = []
        
        # Process regular dependencies
        if "dependencies" in package_data:
            for name, version_str in package_data["dependencies"].items():
                version_str = version_str.replace('^', '').replace('~', '')
                dependencies.append({
                    "name": name,
                    "current_version": version_str,
                    "type": "production"
                })
                
        # Process dev dependencies
        if "devDependencies" in package_data:
            for name, version_str in package_data["devDependencies"].items():
                version_str = version_str.replace('^', '').replace('~', '')
                dependencies.append({
                    "name": name,
                    "current_version": version_str,
                    "type": "development"
                })
                
        # Get latest versions and vulnerabilities
        for dep in dependencies:
            latest_version = self._get_npm_latest_version(dep["name"])
            dep["latest_version"] = latest_version
            
            # Check if update is available
            if latest_version != dep["current_version"]:
                try:
                    current_semver = semver.VersionInfo.parse(dep["current_version"])
                    latest_semver = semver.VersionInfo.parse(latest_version)
                    
                    if latest_semver.major > current_semver.major:
                        dep["update_type"] = "major"
                    elif latest_semver.minor > current_semver.minor:
                        dep["update_type"] = "minor"
                    else:
                        dep["update_type"] = "patch"
                except:
                    dep["update_type"] = "unknown"
            else:
                dep["update_type"] = "none"
                
            # Get vulnerability information
            vulnerabilities = self._check_vulnerabilities(dep["name"], dep["current_version"])
            dep["vulnerabilities"] = vulnerabilities
            
        return dependencies
    
    def _scan_pip_dependencies(self) -> List[Dict]:
        """
        Scan Python dependencies from requirements.txt
        
        Returns:
            List[Dict]: List of Python dependencies
        """
        requirements_path = os.path.join(self.repo_path, "requirements.txt")
        if not os.path.exists(requirements_path):
            return []
            
        dependencies = []
        
        with open(requirements_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                # Parse package name and version
                if '==' in line:
                    name, current_version = line.split('==', 1)
                    name = name.strip()
                    current_version = current_version.strip()
                    
                    dependencies.append({
                        "name": name,
                        "current_version": current_version,
                        "type": "production"
                    })
        
        # Get latest versions and vulnerabilities
        for dep in dependencies:
            latest_version = self._get_pypi_latest_version(dep["name"])
            dep["latest_version"] = latest_version
            
            # Check if update is available
            if latest_version != dep["current_version"]:
                try:
                    current_ver = version.parse(dep["current_version"])
                    latest_ver = version.parse(latest_version)
                    
                    if latest_ver.major > current_ver.major:
                        dep["update_type"] = "major"
                    elif latest_ver.minor > current_ver.minor:
                        dep["update_type"] = "minor"
                    else:
                        dep["update_type"] = "patch"
                except:
                    dep["update_type"] = "unknown"
            else:
                dep["update_type"] = "none"
                
            # Get vulnerability information
            vulnerabilities = self._check_vulnerabilities(dep["name"], dep["current_version"])
            dep["vulnerabilities"] = vulnerabilities
            
        return dependencies
    
    def _scan_maven_dependencies(self) -> List[Dict]:
        """
        Scan Maven dependencies from pom.xml
        
        Returns:
            List[Dict]: List of Maven dependencies
        """
        # This is a simplified implementation
        # A real implementation would parse the XML properly
        pom_path = os.path.join(self.repo_path, "pom.xml")
        if not os.path.exists(pom_path):
            return []
            
        dependencies = []
        
        with open(pom_path, 'r') as f:
            content = f.read()
            
        # Very simple regex-based extraction
        dep_pattern = r'<dependency>.*?<groupId>(.*?)</groupId>.*?<artifactId>(.*?)</artifactId>.*?<version>(.*?)</version>.*?</dependency>'
        for match in re.finditer(dep_pattern, content, re.DOTALL):
            group_id, artifact_id, current_version = match.groups()
            name = f"{group_id}:{artifact_id}"
            
            dependencies.append({
                "name": name,
                "current_version": current_version,
                "type": "production"
            })
        
        # Get latest versions and vulnerabilities
        for dep in dependencies:
            latest_version = self._get_maven_latest_version(dep["name"])
            dep["latest_version"] = latest_version
            
            # Check if update is available
            if latest_version != dep["current_version"]:
                try:
                    current_ver = version.parse(dep["current_version"])
                    latest_ver = version.parse(latest_version)
                    
                    if latest_ver.major > current_ver.major:
                        dep["update_type"] = "major"
                    elif latest_ver.minor > current_ver.minor:
                        dep["update_type"] = "minor"
                    else:
                        dep["update_type"] = "patch"
                except:
                    dep["update_type"] = "unknown"
            else:
                dep["update_type"] = "none"
                
            # Get vulnerability information
            vulnerabilities = self._check_vulnerabilities(dep["name"], dep["current_version"])
            dep["vulnerabilities"] = vulnerabilities
            
        return dependencies
    
    def _scan_gradle_dependencies(self) -> List[Dict]:
        """
        Scan Gradle dependencies from build.gradle
        
        Returns:
            List[Dict]: List of Gradle dependencies
        """
        # This is a simplified implementation
        gradle_path = os.path.join(self.repo_path, "build.gradle")
        if not os.path.exists(gradle_path):
            gradle_path = os.path.join(self.repo_path, "build.gradle.kts")
            if not os.path.exists(gradle_path):
                return []
                
        dependencies = []
        
        with open(gradle_path, 'r') as f:
            content = f.read()
            
        # Simple regex for Gradle dependencies
        # This is a simplification and won't catch all formats
        dep_pattern = r'implementation [\'"]([^:]+):([^:]+):([^\'"]+)[\'"]'
        for match in re.finditer(dep_pattern, content):
            group_id, artifact_id, current_version = match.groups()
            name = f"{group_id}:{artifact_id}"
            
            dependencies.append({
                "name": name,
                "current_version": current_version,
                "type": "production"
            })
        
        # Get latest versions and vulnerabilities
        for dep in dependencies:
            latest_version = self._get_maven_latest_version(dep["name"])  # Maven Central is used for Gradle too
            dep["latest_version"] = latest_version
            
            # Check if update is available
            if latest_version != dep["current_version"]:
                try:
                    current_ver = version.parse(dep["current_version"])
                    latest_ver = version.parse(latest_version)
                    
                    if latest_ver.major > current_ver.major:
                        dep["update_type"] = "major"
                    elif latest_ver.minor > current_ver.minor:
                        dep["update_type"] = "minor"
                    else:
                        dep["update_type"] = "patch"
                except:
                    dep["update_type"] = "unknown"
            else:
                dep["update_type"] = "none"
                
            # Get vulnerability information
            vulnerabilities = self._check_vulnerabilities(dep["name"], dep["current_version"])
            dep["vulnerabilities"] = vulnerabilities
            
        return dependencies
    
    def _get_npm_latest_version(self, package_name: str) -> str:
        """
        Get the latest version of an npm package
        
        Args:
            package_name: Name of the npm package
            
        Returns:
            str: Latest version
        """
        try:
            url = f"https://registry.npmjs.org/{package_name}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("dist-tags", {}).get("latest", "unknown")
            return "unknown"
        except Exception as e:
            print(f"Error getting npm version: {e}")
            return "unknown"
    
    def _get_pypi_latest_version(self, package_name: str) -> str:
        """
        Get the latest version of a PyPI package
        
        Args:
            package_name: Name of the PyPI package
            
        Returns:
            str: Latest version
        """
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("info", {}).get("version", "unknown")
            return "unknown"
        except Exception as e:
            print(f"Error getting PyPI version: {e}")
            return "unknown"
    
    def _get_maven_latest_version(self, package_name: str) -> str:
        """
        Get the latest version of a Maven package
        
        Args:
            package_name: Name of the Maven package (groupId:artifactId)
            
        Returns:
            str: Latest version
        """
        try:
            group_id, artifact_id = package_name.split(":")
            group_path = group_id.replace(".", "/")
            url = f"https://search.maven.org/solrsearch/select?q=g:{group_id}+AND+a:{artifact_id}&rows=1&wt=json"
            
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data["response"]["numFound"] > 0:
                    return data["response"]["docs"][0]["latestVersion"]
            return "unknown"
        except Exception as e:
            print(f"Error getting Maven version: {e}")
            return "unknown"
    
    def _check_vulnerabilities(self, package_name: str, version: str) -> List[Dict]:
        """
        Check for known vulnerabilities in a package
        
        Args:
            package_name: Name of the package
            version: Version of the package
            
        Returns:
            List[Dict]: List of vulnerabilities
        """
        # This is a simplified implementation
        # A real implementation would query NVD or other vulnerability databases
        try:
            # For npm packages, we can use the npm audit API
            if os.path.exists(os.path.join(self.repo_path, "package.json")):
                temp_dir = os.path.join(os.getcwd(), "temp_audit")
                os.makedirs(temp_dir, exist_ok=True)
                
                with open(os.path.join(temp_dir, "package.json"), "w") as f:
                    json.dump({
                        "name": "temp-audit",
                        "version": "1.0.0",
                        "dependencies": {
                            package_name: version
                        }
                    }, f)
                
                try:
                    result = subprocess.run(
                        ["npm", "audit", "--json"],
                        cwd=temp_dir,
                        capture_output=True,
                        text=True
                    )
                    
                    # Clean up
                    import shutil
                    shutil.rmtree(temp_dir)
                    
                    if result.returncode == 0:
                        return []  # No vulnerabilities
                        
                    try:
                        audit_data = json.loads(result.stdout)
                        vulnerabilities = []
                        
                        if "vulnerabilities" in audit_data:
                            for vuln_name, vuln_data in audit_data["vulnerabilities"].items():
                                if vuln_name == package_name:
                                    vulnerabilities.append({
                                        "severity": vuln_data.get("severity", "unknown"),
                                        "description": vuln_data.get("title", "No description available"),
                                        "fixed_in": vuln_data.get("fixAvailable", {}).get("version", "unknown")
                                    })
                        
                        return vulnerabilities
                    except json.JSONDecodeError:
                        return []
                except:
                    # Clean up in case of error
                    import shutil
                    shutil.rmtree(temp_dir)
                    return []
            
            # For other package types, we would query vulnerability databases
            # This is a placeholder for demonstration
            return []
            
        except Exception as e:
            print(f"Error checking vulnerabilities: {e}")
            return []
    
    def get_upgrade_candidates(self, min_severity: str = "medium") -> List[Dict]:
        """
        Get a list of dependencies that are candidates for upgrade
        
        Args:
            min_severity: Minimum vulnerability severity to consider (low, medium, high, critical)
            
        Returns:
            List[Dict]: List of upgrade candidates with details
        """
        all_dependencies = self.scan_dependencies()
        
        # Filter dependencies that need upgrade
        upgrade_candidates = []
        
        for dep in all_dependencies:
            # Check if there's a newer version
            if dep["latest_version"] != "unknown" and dep["latest_version"] != dep["current_version"]:
                # Check if there are vulnerabilities
                has_vulnerabilities = False
                for vuln in dep.get("vulnerabilities", []):
                    severity = vuln.get("severity", "").lower()
                    if severity in ["critical", "high"] or (severity == "medium" and min_severity in ["medium", "low"]) or (severity == "low" and min_severity == "low"):
                        has_vulnerabilities = True
                        break
                
                upgrade_priority = "low"
                if has_vulnerabilities:
                    upgrade_priority = "high"
                elif dep["update_type"] == "patch":
                    upgrade_priority = "medium"
                
                upgrade_candidates.append({
                    "name": dep["name"],
                    "current_version": dep["current_version"],
                    "latest_version": dep["latest_version"],
                    "update_type": dep["update_type"],
                    "vulnerabilities": dep.get("vulnerabilities", []),
                    "priority": upgrade_priority
                })
        
        # Sort by priority (high first)
        upgrade_candidates.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["priority"]])
        
        return upgrade_candidates
