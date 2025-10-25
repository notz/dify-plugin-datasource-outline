import re
from typing import Any

from datasources.utils.outline_client import OutlineClient


class OutlineExtractor:
    """
    Extracts and processes content from Outline documents and collections.
    Converts Outline content to a format suitable for use in Dify.
    """

    def __init__(self, api_key: str, workspace_url: str, page_id: str, page_type: str):
        """
        Initialize the extractor.

        Args:
            api_key: Outline API key
            workspace_url: Outline workspace URL
            page_id: ID of the page (document or collection) to extract
            page_type: Type of page ('document' or 'collection')
        """
        self.api_key = api_key
        self.workspace_url = workspace_url
        self.page_id = page_id
        self.page_type = page_type
        self.client = OutlineClient(api_key, workspace_url)

    def extract(self) -> dict[str, Any]:
        """
        Main entry point for extracting content from Outline.

        Returns:
            Dictionary containing extracted content and metadata
        """
        if self.page_type == "document":
            content = self._extract_document_content(self.page_id)
        elif self.page_type == "collection":
            content = self._extract_collection_content(self.page_id)
        else:
            raise ValueError(f"Unsupported page type: {self.page_type}")

        # workspace_info = self.client.get_workspace_info()

        return {
            "content": content,
            "document_id": self.page_id if self.page_type == "document" else "",
            "collection_id": self.page_id if self.page_type == "collection" else "",
        }

    def _extract_document_content(self, document_id: str) -> str:
        """
        Extract content from a single document.

        Args:
            document_id: ID of the document to extract

        Returns:
            Formatted document content as a string
        """
        try:
            doc_info = self.client.get_document_info(document_id)
            doc_data = doc_info.get("data", {})

            title = doc_data.get("title", "Untitled Document")
            text_content = doc_data.get("text", "")
            
            # Basic formatting - Outline returns plain text in the 'text' field
            formatted_content = f"# {title}\n\n"
            
            if text_content:
                # Clean up the text content
                cleaned_content = self._clean_text_content(text_content)
                formatted_content += cleaned_content

            return formatted_content

        except Exception as e:
            return f"Error extracting document content: {str(e)}"

    def _extract_collection_content(self, collection_id: str) -> str:
        """
        Extract content from a collection and its documents.

        Args:
            collection_id: ID of the collection to extract

        Returns:
            Formatted collection content including all documents
        """
        try:
            # Get collection info
            collection_info = self.client.get_collection_info(collection_id)
            collection_data = collection_info.get("data", {})

            collection_name = collection_data.get("name", "Untitled Collection")
            collection_description = collection_data.get("description", "")

            formatted_content = f"# {collection_name}\n\n"
            
            if collection_description:
                formatted_content += f"{collection_description}\n\n"

            formatted_content += "---\n\n"

            # Get all documents in the collection
            try:
                docs_response = self.client.list_documents(limit=100, collection_id=collection_id)
                documents = docs_response.get("data", [])

                if documents:
                    formatted_content += "## Documents in this Collection\n\n"
                    
                    for doc in documents:
                        doc_title = doc.get("title", "Untitled Document")
                        doc_id = doc.get("id", "")
                        
                        formatted_content += f"### {doc_title}\n\n"
                        
                        # Extract document content
                        try:
                            doc_content = self._extract_document_content(doc_id)
                            # Remove the title from the document content since we already added it
                            doc_content_lines = doc_content.split('\n', 2)
                            if len(doc_content_lines) > 2:
                                doc_content = doc_content_lines[2]
                            formatted_content += doc_content + "\n\n"
                        except Exception as e:
                            formatted_content += f"*Error loading document content: {str(e)}*\n\n"
                else:
                    formatted_content += "*No documents found in this collection*\n\n"

            except Exception as e:
                formatted_content += f"*Error loading collection documents: {str(e)}*\n\n"

            return formatted_content

        except Exception as e:
            return f"Error extracting collection content: {str(e)}"

    def _clean_text_content(self, text: str) -> str:
        """
        Clean and format text content from Outline.

        Args:
            text: Raw text content from Outline

        Returns:
            Cleaned and formatted text
        """
        if not text:
            return ""

        # Remove excessive whitespace while preserving paragraph breaks
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        
        # Ensure proper line breaks for readability
        if cleaned:
            # Split into paragraphs and rejoin with consistent spacing
            paragraphs = [p.strip() for p in cleaned.split('\n\n') if p.strip()]
            cleaned = '\n\n'.join(paragraphs)

        return cleaned

    def _format_outline_markdown(self, content: str) -> str:
        """
        Convert Outline's content format to standard markdown if needed.
        
        Args:
            content: Content from Outline
            
        Returns:
            Formatted markdown content
        """
        # Outline might return content in various formats
        # This method can be extended to handle specific formatting needs
        return content