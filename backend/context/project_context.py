"""Fetch high-level project context from GitHub.

Fetches README, package.json, pyproject.toml, and other project metadata
to understand what the project is about — without cloning the entire repo.

This gives the AI and reviewers project-level context:
  - Project name, description, tech stack
  - Key directories (inferred from changed files)
  - README excerpt for project understanding
  - Package info (framework, dependencies count, etc.)
"""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional

from config import Settings, get_settings
from github.client import GitHubClient
from models.context import ProjectContext


# Files to try fetching for project context (in priority order)
_PROJECT_FILES = [
    "README.md",
    "README.md",
    "readme.md",
    "README.rst",
    "README.txt",
    "README",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "requirements.txt",
]

# Key directories that indicate project structure
_KEY_DIR_PATTERNS = [
    "src", "lib", "app", "api", "server", "client", "frontend", "backend",
    "tests", "test", "docs", "config", "scripts", "db", "migrations",
    "components", "pages", "routes", "services", "models", "utils",
]


class ProjectContextFetcher:
    """Fetches project-level context from GitHub."""

    def __init__(
        self,
        client: GitHubClient,
        settings: Optional[Settings] = None,
    ) -> None:
        self.client = client
        self.settings = settings or get_settings()

    def fetch(
        self,
        owner: str,
        repo: str,
        ref: str,
        changed_files: List[str],
    ) -> ProjectContext:
        """Build project context from README + package files + changed file paths."""
        # 1. Fetch README
        readme_content = self._fetch_readme(owner, repo, ref)
        readme_excerpt = readme_content[:2000] if readme_content else ""

        # 2. Fetch package.json / pyproject.toml
        package_info = self._fetch_package_info(owner, repo, ref)

        # 3. Infer tech stack from package info + file extensions
        tech_stack = self._infer_tech_stack(package_info, changed_files)

        # 4. Infer key directories from changed files
        key_directories = self._infer_key_directories(changed_files)

        # 5. Extract name/description
        name = package_info.get("name", repo)
        description = package_info.get("description", "")
        if not description and readme_content:
            description = self._extract_first_paragraph(readme_content)

        # 6. Detect primary language
        language = self._detect_language(package_info, changed_files)

        return ProjectContext(
            name=name,
            description=description[:500],
            language=language,
            tech_stack=tech_stack,
            key_directories=key_directories,
            readme_excerpt=readme_excerpt,
            package_info=package_info,
        )

    def _fetch_readme(self, owner: str, repo: str, ref: str) -> str:
        """Fetch README content (tries multiple filenames)."""
        for filename in _PROJECT_FILES:
            if filename in ("package.json", "pyproject.toml", "setup.py",
                            "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
                            "requirements.txt"):
                continue
            content = self.client.fetch_file_content(owner, repo, filename, ref)
            if content:
                return content
        return ""

    def _fetch_package_info(self, owner: str, repo: str, ref: str) -> Dict[str, str]:
        """Fetch and parse package.json or pyproject.toml for project metadata."""
        info: Dict[str, str] = {}

        # Try package.json (Node/JS/TS projects)
        pkg_content = self.client.fetch_file_content(owner, repo, "package.json", ref)
        if pkg_content:
            try:
                pkg = json.loads(pkg_content)
                if "name" in pkg:
                    info["name"] = pkg["name"]
                if "description" in pkg:
                    info["description"] = pkg["description"]
                if "version" in pkg:
                    info["version"] = str(pkg["version"])
                if "main" in pkg:
                    info["main"] = pkg["main"]
                # Detect framework
                deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
                frameworks = []
                if "next" in deps:
                    frameworks.append("Next.js")
                if "react" in deps:
                    frameworks.append("React")
                if "vue" in deps:
                    frameworks.append("Vue")
                if "express" in deps:
                    frameworks.append("Express")
                if "fastify" in deps:
                    frameworks.append("Fastify")
                if "nestjs" in deps or "@nestjs/core" in deps:
                    frameworks.append("NestJS")
                if "typescript" in deps:
                    frameworks.append("TypeScript")
                if frameworks:
                    info["framework"] = ", ".join(frameworks)
                # Dependency count
                dep_count = len(pkg.get("dependencies") or {})
                if dep_count:
                    info["dependency_count"] = str(dep_count)
            except (json.JSONDecodeError, KeyError):
                pass
            return info

        # Try pyproject.toml (Python projects)
        py_content = self.client.fetch_file_content(owner, repo, "pyproject.toml", ref)
        if py_content:
            info["type"] = "python"
            # Simple extraction (not full TOML parsing)
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', py_content)
            if name_match:
                info["name"] = name_match.group(1)
            desc_match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', py_content)
            if desc_match:
                info["description"] = desc_match.group(1)
            if "fastapi" in py_content.lower():
                info["framework"] = "FastAPI"
            elif "django" in py_content.lower():
                info["framework"] = "Django"
            elif "flask" in py_content.lower():
                info["framework"] = "Flask"
            return info

        # Try requirements.txt (Python, simpler)
        req_content = self.client.fetch_file_content(owner, repo, "requirements.txt", ref)
        if req_content:
            info["type"] = "python"
            deps = [l.strip() for l in req_content.splitlines() if l.strip() and not l.startswith("#")]
            info["dependency_count"] = str(len(deps))
            if any("fastapi" in d.lower() for d in deps):
                info["framework"] = "FastAPI"
            elif any("django" in d.lower() for d in deps):
                info["framework"] = "Django"
            elif any("flask" in d.lower() for d in deps):
                info["framework"] = "Flask"
            return info

        return info

    def _infer_tech_stack(self, package_info: Dict[str, str], changed_files: List[str]) -> List[str]:
        """Infer tech stack from package info + file extensions."""
        stack: List[str] = []

        # From package info
        if "framework" in package_info:
            stack.extend([f.strip() for f in package_info["framework"].split(",")])

        # From file extensions
        extensions = set()
        for f in changed_files:
            _, ext = f.rsplit(".", 1) if "." in f else (f, "")
            if ext:
                extensions.add(ext.lower())

        if ext in ("ts", "tsx") or "ts" in extensions or "tsx" in extensions:
            if "TypeScript" not in stack:
                stack.append("TypeScript")
        if "js" in extensions or "jsx" in extensions:
            if "JavaScript" not in stack:
                stack.append("JavaScript")
        if "py" in extensions:
            if "Python" not in stack:
                stack.append("Python")
        if "go" in extensions:
            if "Go" not in stack:
                stack.append("Go")
        if "rs" in extensions:
            if "Rust" not in stack:
                stack.append("Rust")
        if "java" in extensions:
            if "Java" not in stack:
                stack.append("Java")
        if "sql" in extensions:
            if "SQL" not in stack:
                stack.append("SQL")

        return stack

    def _infer_key_directories(self, changed_files: List[str]) -> List[str]:
        """Infer key project directories from changed file paths."""
        dirs: set[str] = set()
        for f in changed_files:
            parts = f.replace("\\", "/").split("/")
            if len(parts) > 1:
                # Take first 2 directory levels
                top = parts[0]
                if top in _KEY_DIR_PATTERNS:
                    dirs.add(top)
                elif len(parts) > 2 and parts[1] in _KEY_DIR_PATTERNS:
                    dirs.add(f"{top}/{parts[1]}")

        # Sort by name for consistency
        return sorted(dirs)[:10]

    def _extract_first_paragraph(self, readme: str) -> str:
        """Extract the first meaningful paragraph from README."""
        lines = readme.splitlines()
        paragraph: List[str] = []
        in_paragraph = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_paragraph and paragraph:
                    break
                continue
            # Skip headings for description (but keep content after)
            if stripped.startswith("#"):
                continue
            in_paragraph = True
            paragraph.append(stripped)
        return " ".join(paragraph)[:500]

    def _detect_language(self, package_info: Dict[str, str], changed_files: List[str]) -> str:
        """Detect primary language of the project."""
        if "type" in package_info and package_info["type"] == "python":
            return "Python"
        if "framework" in package_info:
            fw = package_info["framework"].lower()
            if "fastapi" in fw or "django" in fw or "flask" in fw:
                return "Python"

        # Count by extension
        ext_counts: Dict[str, int] = {}
        for f in changed_files:
            if "." in f:
                ext = f.rsplit(".", 1)[1].lower()
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

        if not ext_counts:
            return "Unknown"

        # Map extensions to languages
        ext_map = {
            "ts": "TypeScript", "tsx": "TypeScript",
            "js": "JavaScript", "jsx": "JavaScript",
            "py": "Python", "go": "Go", "rs": "Rust",
            "java": "Java", "rb": "Ruby", "php": "PHP",
        }
        best_lang = "Unknown"
        best_count = 0
        for ext, count in ext_counts.items():
            lang = ext_map.get(ext)
            if lang and count > best_count:
                best_lang = lang
                best_count = count

        return best_lang
