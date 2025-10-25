from typing import Any

import requests

from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from dify_plugin.interfaces.datasource import DatasourceProvider

__TIMEOUT_SECONDS__ = 60 * 10


class OutlineDatasourceProvider(DatasourceProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """
        Validate the provided credentials by making a test API call to Outline.
        
        Args:
            credentials: Dictionary containing api_key and workspace_url
            
        Raises:
            ToolProviderCredentialValidationError: If credentials are invalid
        """
        api_key = credentials.get("api_key")
        workspace_url = credentials.get("workspace_url", "").rstrip("/")
        
        if not api_key:
            raise ToolProviderCredentialValidationError("API key is required")
        
        if not workspace_url:
            raise ToolProviderCredentialValidationError("Workspace URL is required")
        
        # Validate workspace URL format
        if not workspace_url.startswith(("http://", "https://")):
            raise ToolProviderCredentialValidationError("Workspace URL must start with http:// or https://")
        
        try:
            # Test the API key by making a call to auth.info endpoint
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            
            # Use the API base URL from the workspace URL
            api_base_url = f"{workspace_url}/api"
            
            response = requests.post(
                f"{api_base_url}/auth.info",
                headers=headers,
                json={},
                timeout=__TIMEOUT_SECONDS__,
            )
            
            if response.status_code == 401:
                raise ToolProviderCredentialValidationError("Invalid API key")
            elif response.status_code == 404:
                raise ToolProviderCredentialValidationError("Invalid workspace URL or API not accessible")
            elif response.status_code != 200:
                raise ToolProviderCredentialValidationError(f"API request failed with status {response.status_code}")
            
            response_data = response.json()
            if not response_data.get("ok", False):
                error_message = response_data.get("error", "Unknown error")
                raise ToolProviderCredentialValidationError(f"API error: {error_message}")
                
        except requests.exceptions.ConnectionError:
            raise ToolProviderCredentialValidationError("Cannot connect to workspace URL. Please check the URL is correct.")
        except requests.exceptions.Timeout:
            raise ToolProviderCredentialValidationError("Connection timeout. Please try again.")
        except requests.exceptions.RequestException as e:
            raise ToolProviderCredentialValidationError(f"Network error: {str(e)}")
        except Exception as e:
            raise ToolProviderCredentialValidationError(f"Unexpected error: {str(e)}")