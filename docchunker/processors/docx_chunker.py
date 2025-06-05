import re
from typing import Any

from docchunker.models.chunk import Chunk
from docchunker.utils.text_utils import count_tokens_in_text


class DocxChunker:
    """
    Consolidates hierarchical document elements into context-aware text chunks.
    Milestone 1: Recursive consolidation, stringification, basic chunk creation.
    """
    
    def __init__(self, chunk_size: int = 200, num_overlapping_elements: int = 1): # Added num_overlapping_elements for future use
        self.chunk_size = chunk_size
        self.num_overlapping_elements = num_overlapping_elements # Will be used in Milestone 2

    def _stringify_node_content(self, node: dict[str, Any], current_headings: list[str], indent_level: int = 0) -> str:
        """
        Recursively stringifies a node and its children, prepending current headings.
        """
        parts = []
        indent = "  " * indent_level

        # Add node's own content based on type
        if node['type'] == 'paragraph':
            parts.append(indent + node['content'])
        elif node['type'] == 'list_item':
            # Basic list marker, could be improved with actual numbering/bullet style
            marker = "- " if node.get('num_id', -1) == -1 or node['level'] % 2 == 0 else f"{node['level'] + 1}. " # Simple alternating marker
            parts.append(indent + marker + node['content'])
        elif node['type'] == 'table':
            # For tables, the 'content' is already a pre-processed string of cell texts
            parts.append(indent + "Table:\n" + indent + node['content'].replace("\n", "\n" + indent))
        elif node['type'] == 'heading':
            # Headings are handled by the context, but if stringifying a heading node directly (e.g. if it had no children)
            parts.append(indent + f"H{node['level']}: {node['content']}")
        elif node['type'] == 'list_container':
            # List containers themselves don't have direct content, their children do.
            # The stringification of children will handle their content.
            pass # Content comes from children

        # Recursively stringify children
        if 'children' in node and node['children']:
            for child_node in node['children']:
                # For list items, their children (nested list_containers) should be indented further
                child_indent_level = indent_level + 1 if node['type'] == 'list_item' or node['type'] == 'list_container' else indent_level
                parts.append(self._stringify_node_content(child_node, [], child_indent_level)) # Headings already part of parent context

        return "\n".join(parts)

    def _create_chunk_text(self, headings: list[str], content_text: str) -> str:
        """Helper to format the chunk text with headings."""
        heading_prefix = ""
        if headings:
            heading_prefix = "\n".join([f"H{i+1}: {h}" for i, h in enumerate(headings)]) + "\n---\n"
        return heading_prefix + content_text

    def _consolidate_recursive(self, nodes: list[dict[str, Any]], current_headings: list[str], chunks: list[Chunk], document_id: str):
        """
        Recursively processes nodes, accumulates context, and creates chunks.
        """
        for node in nodes:
            node_type = node['type']

            if node_type == 'heading':
                # Update heading context for children
                # Headings are H1, H2, etc. Their level is 1-indexed.
                # current_headings should store only the content, indexed by (level - 1)
                new_headings = list(current_headings) # Make a copy
                heading_level = node['level'] # 1-indexed
                
                # Ensure new_headings list is long enough
                while len(new_headings) < heading_level:
                    new_headings.append("") 
                
                new_headings[heading_level - 1] = node['content'] # Store content
                # Trim any deeper headings from previous branches
                new_headings = new_headings[:heading_level]

                # Recursively process children of this heading with the new context
                if 'children' in node and node['children']:
                    self._consolidate_recursive(node['children'], new_headings, chunks, document_id)

            elif node_type in ['paragraph', 'list_container', 'table']:
                # These are our primary "chunkable" units for Milestone 1
                
                # Stringify the entire node (including its children like list items within a list_container)
                # We pass an empty list for headings here because _create_chunk_text will add them
                stringified_content = self._stringify_node_content(node, [], indent_level=0)
                
                # Create the full text for the potential chunk, including current heading context
                chunk_text = self._create_chunk_text(current_headings, stringified_content)
                
                # Milestone 1: If it's a paragraph, list, or table, try to make a chunk.
                # For now, we don't split these further if they are too large.
                # We also don't handle overlap yet.
                
                # Basic check: if the stringified content is not empty
                if stringified_content.strip():
                    # For Milestone 1, we're not strictly enforcing chunk_size for list_container/table yet.
                    # We'll create one chunk per such element.
                    # Paragraphs are assumed to be small enough.
                    # A more robust size check and splitting logic will be in Milestone 2.
                    
                    # Rough size check for logging or future use
                    # current_size = len(chunk_text)
                    # if current_size > self.chunk_size:
                    #     print(f"Warning: Oversized chunk created for {node_type} (Size: {current_size})")

                    metadata = {
                        "document_id": document_id,
                        "source_type": "docx",
                        "node_type": node_type, # Add type of main node
                        "headings": list(current_headings), # Store context
                        "num_tokens": count_tokens_in_text(chunk_text)
                    }
                    chunks.append(Chunk(text=chunk_text, metadata=metadata))

            # list_item nodes are processed as part of their list_container by _stringify_node_content,
            # so they don't typically trigger direct chunk creation at this top recursive level.

    def apply(self, elements: list[dict[str, Any]], document_id: str) -> list[Chunk]:
        """
        Receive parsed hierarchical elements and convert them to chunks.
        Consolidates as many artifacts as possible into a single chunk.
        """
        chunks: list[Chunk] = []
        self._consolidate_recursive(elements, [], chunks, document_id)
        return chunks
