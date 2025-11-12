"""
PostHog Agent Executor for E2B Sandbox Integration

Manages E2B sandbox lifecycle and executes PostHog driver scripts
in isolated cloud environments.
"""

from e2b import Sandbox
from typing import Dict, Optional, List
import json


class PostHogAgentExecutor:
    """
    Manages execution of PostHog driver scripts in E2B sandboxes.

    Handles:
    - Sandbox creation and cleanup
    - Driver file uploads
    - Dependency installation
    - Script execution with proper environment
    - Error handling and output parsing
    """

    def __init__(
        self,
        e2b_api_key: str,
        posthog_api_key: str,
        posthog_project_id: str,
        posthog_project_api_key: Optional[str] = None,
        posthog_api_url: str = "https://us.posthog.com"
    ):
        """
        Initialize executor with API credentials.

        Args:
            e2b_api_key: E2B API key for sandbox creation
            posthog_api_key: PostHog Personal API key
            posthog_project_id: PostHog project ID
            posthog_project_api_key: PostHog Project API key (for event capture)
            posthog_api_url: PostHog API base URL (US/EU/self-hosted)
        """
        self.e2b_api_key = e2b_api_key
        self.posthog_api_key = posthog_api_key
        self.posthog_project_id = posthog_project_id
        self.posthog_project_api_key = posthog_project_api_key
        self.posthog_api_url = posthog_api_url
        self.sandbox = None

    def __enter__(self):
        """Context manager entry - create and setup sandbox."""
        # Create E2B sandbox
        self.sandbox = Sandbox(api_key=self.e2b_api_key)

        # Upload driver files
        self._upload_driver()

        # Install dependencies
        self._install_dependencies()

        return self

    def _upload_driver(self):
        """Upload PostHog driver files to sandbox."""
        import os
        from pathlib import Path

        # Get driver directory
        driver_dir = Path(__file__).parent / 'posthog_driver'

        # Files to upload
        files_to_upload = {
            '__init__.py': driver_dir / '__init__.py',
            'client.py': driver_dir / 'client.py',
            'exceptions.py': driver_dir / 'exceptions.py'
        }

        # Upload each file
        for filename, filepath in files_to_upload.items():
            if filepath.exists():
                with open(filepath, 'r') as f:
                    content = f.read()
                    self.sandbox.files.write(
                        f'/home/user/posthog_driver/{filename}',
                        content
                    )

    def _install_dependencies(self):
        """Install required Python packages in sandbox."""
        # Install requests and python-dotenv
        result = self.sandbox.commands.run('pip install requests python-dotenv')
        if result.exit_code != 0:
            raise RuntimeError(f"Failed to install dependencies: {result.stderr}")

    def execute_script(
        self,
        script: str,
        description: str = "",
        timeout: int = 60
    ) -> Dict:
        """
        Execute a Python script in the sandbox.

        Args:
            script: Python script code
            description: Human-readable description of what script does
            timeout: Execution timeout in seconds

        Returns:
            Dictionary with:
                - success: bool
                - output: stdout content
                - error: error message if failed
                - description: script description
        """
        # Replace API key placeholders
        script = script.replace('<api_key_placeholder>', self.posthog_api_key)
        script = script.replace('<project_id_placeholder>', self.posthog_project_id)
        script = script.replace('<project_api_key_placeholder>',
                               self.posthog_project_api_key or '')
        script = script.replace('<api_url_placeholder>', self.posthog_api_url)

        # Execute script with environment variables
        result = self.sandbox.run_code(
            code=script,
            envs={
                'PYTHONPATH': '/home/user',
                'POSTHOG_PERSONAL_API_KEY': self.posthog_api_key,
                'POSTHOG_PROJECT_ID': self.posthog_project_id,
                'POSTHOG_PROJECT_API_KEY': self.posthog_project_api_key or '',
                'POSTHOG_API_URL': self.posthog_api_url
            }
        )

        return {
            'success': not result.error,
            'output': result.logs.stdout if not result.error else '',
            'error': str(result.error) if result.error else None,
            'description': description
        }

    def execute_template(
        self,
        template_name: str,
        template_vars: Dict[str, str],
        templates: Dict[str, str]
    ) -> Dict:
        """
        Execute a script template with variable substitution.

        Args:
            template_name: Name of template to execute
            template_vars: Variables to substitute in template
            templates: Dictionary of available templates

        Returns:
            Execution result dictionary
        """
        if template_name not in templates:
            return {
                'success': False,
                'output': '',
                'error': f"Unknown template: {template_name}",
                'description': ''
            }

        # Get template
        script = templates[template_name]

        # Substitute variables
        for var_name, var_value in template_vars.items():
            placeholder = f'{{{var_name}}}'
            script = script.replace(placeholder, var_value)

        # Execute
        return self.execute_script(
            script,
            description=f"Executing template: {template_name}"
        )

    def batch_execute(
        self,
        scripts: List[Dict[str, str]]
    ) -> List[Dict]:
        """
        Execute multiple scripts in sequence.

        Args:
            scripts: List of dicts with 'code' and 'description' keys

        Returns:
            List of execution results
        """
        results = []
        for script_info in scripts:
            result = self.execute_script(
                script_info['code'],
                description=script_info.get('description', '')
            )
            results.append(result)

            # Stop on first error if desired
            if not result['success']:
                break

        return results

    def __exit__(self, *args):
        """Context manager exit - cleanup sandbox."""
        if self.sandbox:
            self.sandbox.kill()

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"PostHogAgentExecutor(project_id={self.posthog_project_id}, "
            f"api_url={self.posthog_api_url})"
        )
