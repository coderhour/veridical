"""Prompt construction using the sandwich strategy."""

from jinja2 import Template

# Default role layer template
DEFAULT_ROLE_TEMPLATE = """\
You are a Senior Principal Engineer with expertise in code quality, testing, \
and software architecture. You are meticulous about SOLID principles, \
type safety, and comprehensive test coverage. You follow best practices \
and avoid introducing technical debt.
"""

# Default constraint layer template
DEFAULT_CONSTRAINT_TEMPLATE = """\
Before submitting your work, verify that:
1. All existing tests pass
2. New code is covered by appropriate tests
3. No linter warnings are introduced
4. Type annotations are complete and correct
5. The solution is minimal and focused on the task

{% if error_context %}
IMPORTANT: The previous attempt failed with the following errors:
{{ error_context }}

You MUST address these specific issues in your solution.
{% endif %}
"""


class PromptBuilder:
    """Builder for creating sandwich-structured prompts.

    The sandwich prompt structure:
    1. Role layer (top) - Persona and expertise definition
    2. Intent layer (middle) - User's task description
    3. Constraint layer (bottom) - Quality rules and error context
    """

    def __init__(
        self,
        role_template: str = DEFAULT_ROLE_TEMPLATE,
        constraint_template: str = DEFAULT_CONSTRAINT_TEMPLATE,
    ) -> None:
        """Initialize the prompt builder.

        Args:
            role_template: Jinja2 template for role layer
            constraint_template: Jinja2 template for constraint layer
        """
        self.role_template = Template(role_template)
        self.constraint_template = Template(constraint_template)

    def build_prompt(
        self,
        task: str,
        error_context: str | None = None,
        *,
        extra_constraints: list[str] | None = None,
    ) -> str:
        """Build a complete sandwich prompt.

        Args:
            task: User's task description (intent layer)
            error_context: Error context from previous iteration
            extra_constraints: Additional constraints to include

        Returns:
            Complete prompt string
        """
        # Render role layer
        role = self.role_template.render()

        # Render constraint layer
        constraint = self.constraint_template.render(
            error_context=error_context,
        )

        # Add extra constraints if provided
        if extra_constraints:
            constraint += "\n\nAdditional constraints:\n"
            for i, c in enumerate(extra_constraints, 1):
                constraint += f"{i}. {c}\n"

        # Assemble sandwich
        return f"{role}\n\n## Task\n\n{task}\n\n## Constraints\n\n{constraint}"
