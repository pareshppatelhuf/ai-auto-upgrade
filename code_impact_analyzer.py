# CodeImpactAnalyzer.py
import os
import subprocess
import zipfile
from pathlib import Path
import tempfile

class CodeImpactAnalyzer:
    @staticmethod
    def download_jar(artifact: str, tmp_path: Path) -> Path:
        """Download the JAR file using Maven and return its path."""
        group_id, artifact_id, version = artifact.split(":")
        jar_name = f"{artifact_id}-{version}.jar"
        output_path = tmp_path / jar_name

        print(f"⏳ Downloading {artifact} to {output_path}")
        os.system(f"mvn org.apache.maven.plugins:maven-dependency-plugin:3.1.2:get -Dartifact={artifact}")

        os.system(f"mvn org.apache.maven.plugins:maven-dependency-plugin:3.1.2:copy -Dartifact={artifact} -DoutputDirectory={tmp_path}")

        if not output_path.exists():
            raise FileNotFoundError(f"JAR not found at: {output_path}")

        return output_path

    @staticmethod
    def extract_package_names_from_jar(jar_path: Path):
        """Extract all package names from a JAR file."""
        print(f"📦 Extracting packages from {jar_path}")
        packages = set()
        with zipfile.ZipFile(jar_path, 'r') as jar:
            for file in jar.namelist():
                if file.endswith(".class") and not file.startswith("META-INF"):
                    pkg = '/'.join(file.split('/')[:-1])
                    if pkg:
                        packages.add(pkg.replace('/', '.'))
        return sorted(packages)

    @staticmethod
    def find_java_usages_by_package(project_dir: Path, package_prefixes):
        """Scan the project directory for usages of classes from the given packages."""
        print(f"🔍 Scanning Java files in {project_dir}")
        matches = []
        unique_files = set()
        for root, _, files in os.walk(project_dir):
            for file in files:
                if file.endswith(".java"):
                    file_path = os.path.join(root, file)
                    with open(file_path, encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            for prefix in package_prefixes:
                                if prefix in line:
                                    matches.append({
                                        'file': file_path,
                                        'line': line_num,
                                        'content': line.strip(),
                                        'prefix': prefix
                                    })
                                    unique_files.add(file_path)
        print(f"🔍 Found {len(matches)} usages in {len(unique_files)} unique files.")
        return unique_files

    @staticmethod
    def analyze_dependency_impact(artifact: str, project_dir: str):
        """A single method to analyze the impact of the artifact update in the project."""
        # Create a temporary directory for downloading the JAR
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            try:
                # Step 1: Download the JAR
                jar_path = CodeImpactAnalyzer.download_jar(artifact, tmp_path)

                # Step 2: Extract package names from the JAR
                packages = CodeImpactAnalyzer.extract_package_names_from_jar(jar_path)
                if not packages:
                    print("❌ No packages found in JAR.")
                    return

                print(f"📦 Found packages: {packages[:5]}{'...' if len(packages) > 5 else ''}")

                # Step 3: Find Java usages by package
                results = CodeImpactAnalyzer.find_java_usages_by_package(Path(project_dir), packages)
                return results
            except subprocess.CalledProcessError:
                print(f"❌ Failed to download artifact: {artifact}")
