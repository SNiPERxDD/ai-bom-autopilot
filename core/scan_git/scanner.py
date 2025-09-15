import os
import git
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from core.schemas.models import Project, ScanState
import logging
import fnmatch

logger = logging.getLogger(__name__)

@dataclass
class FileCandidate:
    """Represents a candidate file found during Git repository scan"""
    file_path: str
    content_hash: str
    commit_sha: str
    file_size: int
    
class GitScanner:
    """Scans Git repositories for ML artifacts, respecting .gitignore"""
    
    def __init__(self):
        # Target file extensions for ML artifacts as specified in requirements
        self.target_extensions = {'.py', '.ipynb', '.yaml', '.yml', '.json', '.md', '.prompt'}
        
        # Built-in ignore patterns (in addition to .gitignore)
        self.builtin_ignore_patterns = [
            '.git/',
            '__pycache__/',
            '*.pyc',
            '.DS_Store',
            'Thumbs.db'
        ]
    
    def scan_repository(self, repo_path: str, branch: str = "main") -> List[FileCandidate]:
        """
        Scan a Git repository for ML artifact candidates.
        
        Args:
            repo_path: Path to the local Git repository
            branch: Git branch to scan (default: main)
            
        Returns:
            List of FileCandidate objects with file paths, content hashes, and commit SHAs
        """
        candidates = []
        
        try:
            # Open the Git repository
            repo = git.Repo(repo_path)
            
            # Get current commit SHA
            commit_sha = repo.head.commit.hexsha
            logger.info(f"Scanning repository at commit {commit_sha[:8]} on branch {branch}")
            
            # Load .gitignore patterns
            gitignore_patterns = self._load_gitignore_patterns(repo_path)
            
            # Walk the repository directory
            repo_root = Path(repo_path)
            for file_path in self._walk_repository(repo_root, gitignore_patterns):
                # Check if file has target extension
                if file_path.suffix.lower() in self.target_extensions:
                    try:
                        # Read file content and calculate hash
                        with open(file_path, 'rb') as f:
                            content = f.read()
                        
                        content_hash = hashlib.sha256(content).hexdigest()
                        relative_path = str(file_path.relative_to(repo_root))
                        file_size = len(content)
                        
                        candidate = FileCandidate(
                            file_path=relative_path,
                            content_hash=content_hash,
                            commit_sha=commit_sha,
                            file_size=file_size
                        )
                        candidates.append(candidate)
                        
                    except (OSError, IOError) as e:
                        logger.warning(f"Could not read file {file_path}: {e}")
                        continue
            
            logger.info(f"Found {len(candidates)} candidate artifacts")
            return candidates
            
        except git.exc.InvalidGitRepositoryError:
            logger.error(f"Invalid Git repository at {repo_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to scan repository: {e}")
            raise
    
    def _load_gitignore_patterns(self, repo_path: str) -> List[str]:
        """
        Load .gitignore patterns from the repository.
        
        Args:
            repo_path: Path to the Git repository
            
        Returns:
            List of gitignore patterns
        """
        patterns = self.builtin_ignore_patterns.copy()
        
        gitignore_path = Path(repo_path) / '.gitignore'
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith('#'):
                            patterns.append(line)
                logger.debug(f"Loaded {len(patterns) - len(self.builtin_ignore_patterns)} patterns from .gitignore")
            except (OSError, IOError) as e:
                logger.warning(f"Could not read .gitignore: {e}")
        
        return patterns
    
    def _walk_repository(self, repo_root: Path, gitignore_patterns: List[str]) -> List[Path]:
        """
        Walk the repository directory, respecting .gitignore patterns.
        
        Args:
            repo_root: Root path of the repository
            gitignore_patterns: List of gitignore patterns to respect
            
        Returns:
            List of file paths that are not ignored
        """
        valid_files = []
        
        for root, dirs, files in os.walk(repo_root):
            root_path = Path(root)
            
            # Filter directories based on gitignore patterns
            dirs[:] = [d for d in dirs if not self._is_ignored(
                str((root_path / d).relative_to(repo_root)) + '/', gitignore_patterns
            )]
            
            # Process files
            for file in files:
                file_path = root_path / file
                relative_path = str(file_path.relative_to(repo_root))
                
                # Check if file should be ignored
                if not self._is_ignored(relative_path, gitignore_patterns):
                    valid_files.append(file_path)
        
        return valid_files
    
    def _is_ignored(self, file_path: str, gitignore_patterns: List[str]) -> bool:
        """
        Check if a file path should be ignored based on gitignore patterns.
        
        Args:
            file_path: Relative file path to check
            gitignore_patterns: List of gitignore patterns
            
        Returns:
            True if the file should be ignored, False otherwise
        """
        for pattern in gitignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith('/'):
                if file_path.startswith(pattern) or ('/' + pattern) in ('/' + file_path):
                    return True
            # Handle file patterns
            elif fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(os.path.basename(file_path), pattern):
                return True
            # Handle patterns with path separators
            elif '/' in pattern and fnmatch.fnmatch(file_path, pattern):
                return True
        
        return False
    
    def get_file_content(self, repo_path: str, file_path: str) -> Optional[str]:
        """
        Get content of a specific file as text.
        
        Args:
            repo_path: Path to the repository root
            file_path: Relative path to the file within the repository
            
        Returns:
            File content as string, or None if file cannot be read
        """
        full_path = Path(repo_path) / file_path
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except (OSError, IOError) as e:
            logger.warning(f"Failed to read {full_path}: {e}")
            return None
    
    def get_file_hash(self, content: bytes) -> str:
        """
        Get SHA256 hash of file content.
        
        Args:
            content: File content as bytes
            
        Returns:
            SHA256 hash as hexadecimal string
        """
        return hashlib.sha256(content).hexdigest()
    
    def clone_or_update_repository(self, repo_url: str, local_path: str, branch: str = "main") -> str:
        """
        Clone a repository or update existing clone.
        
        Args:
            repo_url: URL of the Git repository
            local_path: Local path where repository should be cloned
            branch: Git branch to checkout (default: main)
            
        Returns:
            Path to the local repository
        """
        # Fix common URL errors
        if repo_url.startswith("https:/github.com"):
            logger.warning("Fixing malformed GitHub URL (missing slash after https:)")
            repo_url = repo_url.replace("https:/github.com", "https://github.com")
            
        local_path = Path(local_path)
        
        if local_path.exists() and (local_path / '.git').exists():
            # Repository already exists, update it
            try:
                repo = git.Repo(local_path)
                origin = repo.remotes.origin
                origin.fetch()
                
                # Checkout the specified branch
                if branch in [ref.name.split('/')[-1] for ref in repo.remotes.origin.refs]:
                    repo.git.checkout(branch)
                    origin.pull()
                    logger.info(f"Updated repository at {local_path}")
                else:
                    logger.warning(f"Branch {branch} not found, using current branch")
                    
            except Exception as e:
                logger.error(f"Failed to update repository: {e}")
                raise
        else:
            # Clone the repository
            try:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                repo = git.Repo.clone_from(repo_url, local_path, branch=branch)
                logger.info(f"Cloned repository to {local_path}")
            except Exception as e:
                logger.error(f"Failed to clone repository: {e}")
                raise
        
        return str(local_path)
    
    def scan_project_repository(self, project: Project) -> ScanState:
        """
        Scan a Git repository for ML artifacts based on project information.
        
        Args:
            project: Project object with repository information
            
        Returns:
            Updated ScanState with file candidates
        """
        try:
            # Create a scan state from the project
            state = ScanState(project=project)
            
            # Initialize required collections to avoid attribute errors
            state.models = []
            state.datasets = []
            state.prompts = []
            state.tools = []
            state.evidence_chunks = []
            state.policy_events = []
            state.actions = []
            state.error = None
            
            # Create repos directory if it doesn't exist
            repos_dir = os.path.join(os.getcwd(), "repos")
            os.makedirs(repos_dir, exist_ok=True)
            
            # Generate a unique local path for the repository
            repo_dir = f"id={project.id}_{project.name.replace(' ', '_')}"
            local_path = os.path.join(repos_dir, repo_dir)
            
            # Clone or update the repository
            logger.info(f"Cloning/updating repository: {project.repo_url}")
            repo_path = self.clone_or_update_repository(
                project.repo_url, 
                local_path, 
                branch=project.default_branch
            )
            
            # Scan the repository for ML artifact candidates
            candidates = self.scan_repository(repo_path, branch=project.default_branch)
            
            # Add results to scan state
            state.file_candidates = candidates
            state.meta['commit_sha'] = candidates[0].commit_sha if candidates else None
            state.meta['counters'] = {'files_scanned': len(candidates)}
            
            # Set commit_sha on state object for compatibility
            state.commit_sha = candidates[0].commit_sha if candidates else None
            
            return state
            
        except Exception as e:
            logger.error(f"Failed to scan repository: {project}")
            state = ScanState(project=project)
            # Initialize required collections to avoid attribute errors
            state.models = []
            state.datasets = []
            state.prompts = []
            state.tools = []
            state.evidence_chunks = []
            state.policy_events = []
            state.actions = []
            state.error = str(e)
            return state