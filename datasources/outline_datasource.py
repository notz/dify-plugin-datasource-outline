from collections.abc import Generator
from typing import Any

from datasources.utils.outline_client import OutlineClient
from datasources.utils.outline_extractor import OutlineExtractor

from dify_plugin.entities.datasource import (
    DatasourceGetPagesResponse,
    DatasourceMessage,
    GetOnlineDocumentPageContentRequest,
    OnlineDocumentInfo,
)
from dify_plugin.interfaces.datasource.online_document import OnlineDocumentDatasource


class OutlineDataSource(OnlineDocumentDatasource):
    """
    Outline datasource implementation for Dify.
    Provides access to documents and collections from Outline workspaces.
    """

    def _get_pages(self, datasource_parameters: dict[str, Any]) -> DatasourceGetPagesResponse:
        """
        Get all accessible pages (documents and collections) from the Outline workspace.

        Args:
            datasource_parameters: Parameters for the datasource (unused for Outline)

        Returns:
            DatasourceGetPagesResponse containing all accessible pages
        """
        # Get credentials from runtime
        api_key = self.runtime.credentials.get("api_key")
        workspace_url = self.runtime.credentials.get("workspace_url")
        
        if not api_key:
            raise ValueError("API key not found in credentials")
        
        if not workspace_url:
            raise ValueError("Workspace URL not found in credentials")

        # Initialize client and get workspace info
        outline_client = OutlineClient(api_key, workspace_url)
        workspace_info = outline_client.get_workspace_info()
        
        # Get all accessible pages
        pages = outline_client.get_authorized_pages()
        
        # Create online document info
        online_document_info = OnlineDocumentInfo(
            workspace_name=workspace_info.get("workspace_name", "Outline Workspace"),
            workspace_icon="",  # Outline doesn't provide workspace icons via API
            workspace_id=workspace_info.get("workspace_id", ""),
            pages=pages,
            total=len(pages),
        )
        
        return DatasourceGetPagesResponse(
            result=[online_document_info],
        )

    def _get_content(self, page: GetOnlineDocumentPageContentRequest) -> Generator[DatasourceMessage, None, None]:
        """
        Get content from a specific page (document or collection).

        Args:
            page: Request containing page information

        Yields:
            DatasourceMessage objects containing the extracted content and metadata
        """
        # Get credentials from runtime
        api_key = self.runtime.credentials.get("api_key")
        workspace_url = self.runtime.credentials.get("workspace_url")
        
        if not api_key:
            raise ValueError("API key not found in credentials")
        
        if not workspace_url:
            raise ValueError("Workspace URL not found in credentials")

        try:
            # Initialize extractor
            extractor = OutlineExtractor(
                api_key=api_key,
                workspace_url=workspace_url,
                page_id=page.page_id,
                page_type=page.type
            )
            
            # Extract content
            extracted_data = extractor.extract()
            
            # Yield content and metadata as separate messages
            yield self.create_variable_message("content", extracted_data["content"])
            yield self.create_variable_message("document_id", extracted_data["document_id"])
            yield self.create_variable_message("collection_id", extracted_data["collection_id"])
            
        except Exception as e:
            raise ValueError(f"Error extracting content from Outline: {str(e)}") from e