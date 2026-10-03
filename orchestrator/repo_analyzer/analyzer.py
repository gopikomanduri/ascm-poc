"""Repository analyzer: Scan and understand existing codebases."""
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import re


class RepositoryAnalyzer:
    """Analyze existing repositories to understand structure and purpose."""

    def __init__(self, repo_paths: List[str]):
        self.repo_paths = repo_paths
        self.analysis_results: Dict[str, Any] = {}

        # File patterns for different types
        self.code_extensions = {
            '.py', '.go', '.ts', '.tsx', '.js', '.jsx',
            '.java', '.cpp', '.c', '.rs', '.rb', '.php'
        }

        self.config_files = {
            'package.json', 'requirements.txt', 'go.mod', 'pom.xml',
            'Dockerfile', 'docker-compose.yml', '.github/workflows', 'Makefile'
        }

        self.doc_extensions = {'.md', '.rst', '.txt'}

    def analyze_all(self) -> Dict[str, Any]:
        """Analyze all repositories."""
        results = {}
        for repo_path in self.repo_paths:
            results[repo_path] = self.analyze_repo(repo_path)
        self.analysis_results = results
        return results

    def analyze_repo(self, repo_path: str) -> Dict[str, Any]:
        """Analyze a single repository."""
        print(f"\n🔍 Analyzing repository: {repo_path}")

        repo_name = os.path.basename(repo_path)

        analysis = {
            "repo_name": repo_name,
            "repo_path": repo_path,
            "structure": self._analyze_structure(repo_path),
            "languages": self._detect_languages(repo_path),
            "dependencies": self._extract_dependencies(repo_path),
            "architecture": self._detect_architecture(repo_path),
            "key_files": self._identify_key_files(repo_path),
            "purposes": self._infer_purpose(repo_path),
            "technologies": self._detect_technologies(repo_path),
        }

        print(f"✅ Analysis complete: {repo_name}")
        return analysis

    def _analyze_structure(self, repo_path: str) -> Dict[str, Any]:
        """Analyze repository structure."""
        structure = {
            "directories": [],
            "file_count": 0,
            "total_lines": 0,
        }

        for root, dirs, files in os.walk(repo_path):
            # Skip hidden and cache directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            rel_path = os.path.relpath(root, repo_path)
            if rel_path != '.':
                structure["directories"].append(rel_path)

            structure["file_count"] += len(files)

            # Count lines in code files
            for file in files:
                if any(file.endswith(ext) for ext in self.code_extensions):
                    try:
                        filepath = os.path.join(root, file)
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            structure["total_lines"] += len(f.readlines())
                    except:
                        pass

        return structure

    def _detect_languages(self, repo_path: str) -> Dict[str, int]:
        """Detect programming languages used."""
        languages = {}

        lang_map = {
            '.py': 'Python',
            '.go': 'Go',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript (React)',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript (React)',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
        }

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                _, ext = os.path.splitext(file)
                if ext in lang_map:
                    lang = lang_map[ext]
                    languages[lang] = languages.get(lang, 0) + 1

        return dict(sorted(languages.items(), key=lambda x: x[1], reverse=True))

    def _extract_dependencies(self, repo_path: str) -> Dict[str, List[str]]:
        """Extract project dependencies."""
        dependencies = {}

        # Check for package.json
        package_json = os.path.join(repo_path, 'package.json')
        if os.path.exists(package_json):
            try:
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    dependencies['npm'] = list((data.get('dependencies', {}) or {}).keys())
            except:
                pass

        # Check for requirements.txt
        requirements = os.path.join(repo_path, 'requirements.txt')
        if os.path.exists(requirements):
            try:
                with open(requirements, 'r') as f:
                    dependencies['pip'] = [line.split('==')[0].split('>=')[0] for line in f if line.strip()]
            except:
                pass

        # Check for go.mod
        go_mod = os.path.join(repo_path, 'go.mod')
        if os.path.exists(go_mod):
            try:
                with open(go_mod, 'r') as f:
                    lines = f.readlines()
                    in_require = False
                    deps = []
                    for line in lines:
                        if 'require' in line:
                            in_require = True
                            continue
                        if in_require and line.strip() and not line.startswith('\t'):
                            in_require = False
                        if in_require and line.strip():
                            deps.append(line.split()[0])
                    dependencies['go'] = deps
            except:
                pass

        return dependencies

    def _detect_architecture(self, repo_path: str) -> Dict[str, Any]:
        """Detect high-level architecture."""
        architecture = {
            "type": "unknown",
            "pattern": "unknown",
            "layers": [],
        }

        # Check for common architecture patterns
        dirs = set(os.listdir(repo_path))

        # Microservices
        if any(d in dirs for d in ['services', 'cmd', 'apps']):
            architecture["type"] = "microservices"
            architecture["pattern"] = "Distributed services"

        # Monolithic
        elif any(d in dirs for d in ['src', 'lib', 'app']):
            architecture["type"] = "monolithic"
            architecture["pattern"] = "Centralized application"

        # Check for layering
        if os.path.exists(os.path.join(repo_path, 'api')):
            architecture["layers"].append("API Layer")
        if os.path.exists(os.path.join(repo_path, 'database')):
            architecture["layers"].append("Data Layer")
        if os.path.exists(os.path.join(repo_path, 'services')):
            architecture["layers"].append("Business Logic")
        if os.path.exists(os.path.join(repo_path, 'ui')):
            architecture["layers"].append("Presentation Layer")

        return architecture

    def _identify_key_files(self, repo_path: str) -> Dict[str, str]:
        """Identify key configuration and documentation files."""
        key_files = {}

        important_files = [
            'README.md', 'ARCHITECTURE.md', 'API.md',
            'Dockerfile', 'docker-compose.yml',
            'Makefile', '.github/workflows/ci.yml',
            'package.json', 'requirements.txt', 'go.mod',
            'app.py', 'main.go', 'index.js', 'server.py'
        ]

        for file in important_files:
            full_path = os.path.join(repo_path, file)
            if os.path.exists(full_path):
                key_files[file] = full_path

        return key_files

    def _infer_purpose(self, repo_path: str) -> List[str]:
        """Infer the purpose/domain of the repository."""
        purposes = []

        # Check README for clues
        readme_path = os.path.join(repo_path, 'README.md')
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r') as f:
                    content = f.read().lower()

                    # Domain detection
                    if any(word in content for word in ['payment', 'stripe', 'checkout', 'billing']):
                        purposes.append('Payment Processing')
                    if any(word in content for word in ['database', 'sql', 'nosql', 'cache']):
                        purposes.append('Data Management')
                    if any(word in content for word in ['api', 'rest', 'graphql', 'gateway']):
                        purposes.append('API/Gateway')
                    if any(word in content for word in ['auth', 'oauth', 'jwt', 'security']):
                        purposes.append('Authentication/Authorization')
                    if any(word in content for word in ['monitoring', 'logs', 'metrics', 'observability']):
                        purposes.append('Observability')
                    if any(word in content for word in ['web', 'frontend', 'ui', 'react', 'vue']):
                        purposes.append('Web Application')
                    if any(word in content for word in ['machine learning', 'ml', 'ai', 'model']):
                        purposes.append('Machine Learning')
            except:
                pass

        # Check for API indicators
        if self._has_files_matching(repo_path, r'.*controller.*\.py|.*handler.*\.go|.*route.*\.js'):
            purposes.append('API/Web Service')

        # Check for data processing
        if self._has_files_matching(repo_path, r'.*processor.*|.*pipeline.*|.*worker.*'):
            purposes.append('Data Processing')

        return purposes if purposes else ['General Purpose']

    def _detect_technologies(self, repo_path: str) -> Dict[str, List[str]]:
        """Detect technologies and frameworks used."""
        technologies = {
            'frontend': [],
            'backend': [],
            'database': [],
            'infrastructure': [],
        }

        # Check files for framework hints
        all_files = []
        for root, dirs, files in os.walk(repo_path):
            all_files.extend([f.lower() for f in files])

        content_sample = ' '.join(all_files)

        # Frontend
        if any(word in content_sample for word in ['react', 'vue', 'angular']):
            if 'react' in content_sample:
                technologies['frontend'].append('React')
            if 'vue' in content_sample:
                technologies['frontend'].append('Vue.js')

        # Backend
        if 'fastapi' in content_sample or 'flask' in content_sample:
            technologies['backend'].append('Python Web')
        if any(word in content_sample for word in ['gin', 'echo', 'go.mod']):
            technologies['backend'].append('Go')
        if 'package.json' in content_sample:
            technologies['backend'].append('Node.js')

        # Database
        if any(word in content_sample for word in ['postgres', 'mysql', 'sql']):
            technologies['database'].append('SQL')
        if any(word in content_sample for word in ['mongo', 'dynamodb']):
            technologies['database'].append('NoSQL')
        if 'redis' in content_sample:
            technologies['database'].append('Redis')

        # Infrastructure
        if 'dockerfile' in content_sample:
            technologies['infrastructure'].append('Docker')
        if 'docker-compose' in content_sample:
            technologies['infrastructure'].append('Docker Compose')
        if 'kubernetes' in content_sample or 'k8s' in content_sample:
            technologies['infrastructure'].append('Kubernetes')

        return technologies

    def _has_files_matching(self, repo_path: str, pattern: str) -> bool:
        """Check if repository has files matching a pattern."""
        regex = re.compile(pattern, re.IGNORECASE)

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if regex.match(file):
                    return True

        return False
