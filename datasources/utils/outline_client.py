"""
Outline API Client for Dify plugins
This module provides a unified interface for interacting with the Outline API
"""

import time
from typing import Any

import requests

from dify_plugin.entities.datasource import OnlineDocumentPage

__TIMEOUT_SECONDS__ = 60 * 10


class OutlineClient:
    """
    A client for interacting with the Outline API.
    Abstracts the API calls and provides a unified interface for all Outline operations.
    """

    def __init__(self, api_key: str, workspace_url: str):
        """
        Initialize the Outline client with an API key and workspace URL.

        Args:
            api_key: The Outline API key for authentication
            workspace_url: The workspace URL (e.g., https://your-team.getoutline.com)
        """
        self.api_key = api_key
        self.workspace_url = workspace_url.rstrip("/")
        self.api_base_url = f"{self.workspace_url}/api"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _make_request(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ) -> dict[str, Any]:
        """
        Make a POST request to the Outline API with retry logic.

        Args:
            endpoint: The API endpoint (e.g., 'documents.list')
            data: JSON data to send in the request body
            max_retries: Maximum number of retries
            backoff_factor: Backoff factor for exponential backoff

        Returns:
            The JSON response from the API

        Raises:
            requests.exceptions.RequestException: If the request fails after all retries
            ValueError: If the API returns an error response
        """
        url = f"{self.api_base_url}/{endpoint}"
        request_data = data or {}

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=request_data,
                    timeout=__TIMEOUT_SECONDS__,
                )

                if response.status_code == 429:  # Rate limited
                    if attempt < max_retries:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        time.sleep(min(retry_after, 300))  # Cap at 5 minutes
                        continue
                    else:
                        raise requests.exceptions.RequestException("Rate limit exceeded")

                response.raise_for_status()
                response_json = response.json()

                if not response_json.get("ok", False):
                    error_message = response_json.get("error", "Unknown API error")
                    raise ValueError(f"Outline API error: {error_message}")

                return response_json

            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    wait_time = backoff_factor * (2**attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    raise e

        # This should never be reached, but just in case
        raise requests.exceptions.RequestException("Max retries exceeded")

    def get_auth_info(self) -> dict[str, Any]:
        """
        Get authentication information and user details.

        Returns:
            Dictionary containing user and team information
        """
        return self._make_request("auth.info")

    def list_documents(self, limit: int = 25, offset: int = 0, collection_id: str | None = None) -> dict[str, Any]:
        """
        List documents in the workspace.

        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            collection_id: Optional collection ID to filter by

        Returns:
            Dictionary containing document list and pagination info
        """
        data = {
            "limit": limit,
            "offset": offset,
        }
        
        if collection_id:
            data["collectionId"] = collection_id

        return self._make_request("documents.list", data)

    def get_document_info(self, document_id: str) -> dict[str, Any]:
        """
        Get detailed information about a specific document.

        Args:
            document_id: The ID of the document to retrieve

        Returns:
            Dictionary containing document information
        """
        return self._make_request("documents.info", {"id": document_id})

    def list_collections(self, limit: int = 25, offset: int = 0) -> dict[str, Any]:
        """
        List collections in the workspace.

        Args:
            limit: Maximum number of collections to return
            offset: Number of collections to skip

        Returns:
            Dictionary containing collection list and pagination info
        """
        data = {
            "limit": limit,
            "offset": offset,
        }

        return self._make_request("collections.list", data)

    def get_collection_info(self, collection_id: str) -> dict[str, Any]:
        """
        Get detailed information about a specific collection.

        Args:
            collection_id: The ID of the collection to retrieve

        Returns:
            Dictionary containing collection information
        """
        return self._make_request("collections.info", {"id": collection_id})

    def search_documents(self, query: str, limit: int = 25, offset: int = 0) -> dict[str, Any]:
        """
        Search for documents in the workspace.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            Dictionary containing search results and pagination info
        """
        data = {
            "query": query,
            "limit": limit,
            "offset": offset,
        }

        return self._make_request("documents.search", data)

    def get_authorized_pages(self) -> list[OnlineDocumentPage]:
        """
        Get all authorized pages (documents and collections) that can be accessed.

        Returns:
            List of OnlineDocumentPage objects representing accessible documents
        """
        pages = []

        try:
            # Get all collections first
            collections_response = self.list_collections(limit=100)  # Get more collections at once
            collections = collections_response.get("data", [])

            for collection in collections:
                # Add collection as a page
                pages.append(
                    OnlineDocumentPage(
                        page_id=collection["id"],
                        page_name=collection["name"],
                        page_icon={"type": "emoji", "emoji": collection.get("emoji", "🔹")},
                        type="collection",
                        url=f"{self.workspace_url}/collection/{collection['id']}",
                        last_edited_time=collection["updatedAt"],
                    )
                )

            # Get all documents
            offset = 0
            limit = 100
            while True:
                docs_response = self.list_documents(limit=limit, offset=offset)
                documents = docs_response.get("data", [])
                if not documents:
                    break

                for doc in documents:
                    pages.append(
                        OnlineDocumentPage(
                            page_id=doc["id"],
                            page_name=doc["title"],
                            page_icon={"type": "emoji", "emoji": doc["emoji"]} if doc.get("emoji") else None,
                            parent_id=doc.get("parentDocumentId") if doc.get("parentDocumentId") else doc.get("collectionId"),
                            type="document",
                            url=doc.get("url", f"{self.workspace_url}/doc/{doc['urlId']}"),
                            last_edited_time=doc["updatedAt"],
                        )
                    )
                # If less than limit, we've reached the last page
                if len(documents) < limit:
                    break
                offset += limit
      
        except Exception as e:
            raise ValueError(f"Error fetching authorized pages: {str(e)}")

        return pages

    def get_workspace_info(self) -> dict[str, str]:
        """
        Get workspace information including name and ID.

        Returns:
            Dictionary containing workspace_name, workspace_id and workspace_url
        """
        try:
            auth_info = self.get_auth_info()
            user_data = auth_info.get("data", {})
            team_data = user_data.get("team", {})

            return {
                "workspace_name": team_data.get("name", "Outline Workspace"),
                "workspace_id": team_data.get("id", ""),
                "workspace_url": self.workspace_url,
            }
        except Exception as e:
            return {
                "workspace_name": "Outline Workspace",
                "workspace_id": "",
                "workspace_url": self.workspace_url,
            }