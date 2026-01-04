"""Session management for the dispatcher."""

from pathlib import Path
from typing import TYPE_CHECKING

from veridical.api.models import (
    AutomationMode,
    CreateSessionRequest,
    GitHubRepoContext,
    SessionResponse,
    SourceContext,
)
from veridical.dispatcher.prompt import PromptBuilder
from veridical.synchronizer.git import GitWrapper

if TYPE_CHECKING:
    from veridical.api.client import JulesClient
    from veridical.config.schema import VeridicalConfig


class Dispatcher:
    """Manages prompt construction and session dispatch.

    The Dispatcher is responsible for:
    1. Building prompts using the sandwich strategy
    2. Creating Jules sessions via the API
    3. Injecting dynamic constraints based on iteration context
    """

    def __init__(
        self,
        config: "VeridicalConfig",
        api_client: "JulesClient",
        repo_path: Path,
        *,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        """Initialize the dispatcher.

        Args:
            config: Veridical configuration
            api_client: Jules API client
            repo_path: Path to the repository root
            prompt_builder: Optional custom prompt builder
        """
        self.config = config
        self.api_client = api_client
        self.repo_path = repo_path
        self.git = GitWrapper(repo_path)
        self.prompt_builder = prompt_builder or PromptBuilder()

    def build_prompt(
        self,
        task: str,
        error_context: str | None = None,
    ) -> str:
        """Build a complete prompt for Jules.

        Args:
            task: User's task description
            error_context: Error context from previous iteration

        Returns:
            Complete sandwich-structured prompt
        """
        return self.prompt_builder.build_prompt(
            task=task,
            error_context=error_context,
        )

    async def create_session(
        self,
        prompt: str,
        *,
        source: str | None = None,
        branch: str | None = None,
    ) -> SessionResponse:
        """Create a new Jules session.

        Args:
            prompt: Complete prompt to send
            source: Source identifier (e.g., 'sources/github/owner/repo')
            branch: Git branch to work from. If None, uses config default or auto-detected.

        Returns:
            Created session information
        """
        target_branch = branch or self.config.git.base_branch

        if source:
            source_context = SourceContext(
                source=source,
                github_repo_context=GitHubRepoContext(
                    starting_branch=target_branch,
                ),
            )
        else:
            # Auto-detect from local git config
            remote_url = self.git.get_remote_url()
            source_context = SourceContext.from_remote_url(remote_url, target_branch)

        request = CreateSessionRequest(
            prompt=prompt,
            source_context=source_context,
            automation_mode=AutomationMode.AUTO_CREATE_PR,
            require_plan_approval=not self.config.jules.auto_approve_plans,
        )

        return await self.api_client.create_session(request)
