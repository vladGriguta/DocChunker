import re
from typing import Any

from docchunker.models.chunk import Chunk
from docchunker.utils.text_utils import count_tokens_in_text


class DocxChunker:
    """
    Consolidates hierarchical document elements into context-aware text chunks.
    Milestone 2: Refined list_container processing with splitting and overlap.
    """
    
    def __init__(self, chunk_size: int = 200, num_overlapping_elements: int = 0):
        self.chunk_size = chunk_size
        self.num_overlapping_elements = num_overlapping_elements
        if self.num_overlapping_elements > 0:
            raise NotImplementedError("Overlapping chunks are not yet supported.")

    def _stringify_node_content(self, node: dict[str, Any], indent_level: int = 0) -> str:
        """
        Recursively stringifies a node and its children.
        No heading context prepended here; that's handled by _create_chunk_text.
        """
        parts = []
        indent = "  " * indent_level

        node_type = node.get('type', 'unknown')

        if node_type == 'paragraph':
            parts.append(indent + node.get('content', ''))
        elif node_type == 'list_item':
            marker_level = node.get('level', 0) # 0-indexed ilvl
            # Basic list marker, could be improved with actual numbering/bullet style
            # Using a simple alternating marker for demonstration
            marker = "- " if node.get('num_id', -1) == -1 or marker_level % 2 == 0 else f"{marker_level + 1}. "
            parts.append(indent + marker + node.get('content', ''))
        elif node_type == 'table':
            parts.append(indent + "Table:\n" + indent + node.get('content', '').replace("\n", "\n" + indent))
        elif node_type == 'heading':
            parts.append(indent + f"H{node.get('level', 0)}: {node.get('content', '')}")
        elif node_type == 'list_container':
            # Content comes from children, handled in recursion below
            pass

        if 'children' in node and node['children']:
            for child_node in node['children']:
                child_indent_level = indent_level + 1 if node_type in ['list_item', 'list_container'] else indent_level
                parts.append(self._stringify_node_content(child_node, child_indent_level))
        
        return "\n".join(filter(None, parts)) # Filter out empty strings that might result from empty nodes

    def _create_chunk_text(self, headings: list[str], content_text: str) -> str:
        """Helper to format the chunk text with headings."""
        heading_prefix = ""
        if headings:
            # Filter out empty heading strings before joining
            formatted_headings = [f"H{i+1}: {h_content}" for i, h_content in enumerate(headings) if h_content.strip()]
            if formatted_headings:
                heading_prefix = "\n".join(formatted_headings) + "\n---\n"
        return heading_prefix + content_text

    def _process_list_container(self, node: dict[str, Any], current_headings: list[str], chunks: list[Chunk], document_id: str):
        """
        Processes a list_container, splitting it into multiple chunks if necessary,
        with overlap between chunks.
        """
        list_items = node.get('children', [])
        if not list_items:
            return

        current_chunk_item_nodes: list[dict[str, Any]] = []
        current_chunk_items_text_parts: list[str] = []

        # Calculate tokens for the heading prefix once
        headings_prefix_text = self._create_chunk_text(current_headings, "") # Text of headings only
        headings_tokens = count_tokens_in_text(headings_prefix_text)
        current_content_tokens = 0

        for i, item_node in enumerate(list_items):
            item_text = self._stringify_node_content(item_node, indent_level=0) # Indent relative to list container
            item_tokens = count_tokens_in_text(item_text)
            
            # Check if adding this item would exceed the chunk size
            # (considering headings + current items + new item)
            if current_chunk_item_nodes and \
               (headings_tokens + current_content_tokens + item_tokens + count_tokens_in_text("\n")) > self.chunk_size:
                # Finalize the current chunk
                chunk_content_str = "\n".join(current_chunk_items_text_parts)
                final_chunk_text = self._create_chunk_text(current_headings, chunk_content_str)
                metadata = {
                    "document_id": document_id, 
                    "source_type": "docx",
                    "node_type": "list_container", 
                    "headings": list(current_headings),
                    "num_tokens": count_tokens_in_text(final_chunk_text)
                }
                chunks.append(Chunk(text=final_chunk_text, metadata=metadata))

                # TODO: revisit this logic if num_overlapping_elements > 0: only apply it if the previous chunk had significantly more items than the overlap count
                if self.num_overlapping_elements > 0 and len(current_chunk_item_nodes) >= self.num_overlapping_elements:
                    overlap_nodes = current_chunk_item_nodes[-self.num_overlapping_elements:]
                else:
                    overlap_nodes = []

                current_chunk_item_nodes = list(overlap_nodes)
                current_chunk_items_text_parts = [self._stringify_node_content(n, 0) for n in overlap_nodes]
                current_content_tokens = count_tokens_in_text("\n".join(current_chunk_items_text_parts))
            
            # Add current item to the current chunk (or the new chunk after overlap)
            current_chunk_item_nodes.append(item_node)
            current_chunk_items_text_parts.append(item_text)
            current_content_tokens += item_tokens + (count_tokens_in_text("\n") if len(current_chunk_items_text_parts) > 1 else 0)

        # Add the last remaining chunk
        if current_chunk_item_nodes:
            chunk_content_str = "\n".join(current_chunk_items_text_parts)
            final_chunk_text = self._create_chunk_text(current_headings, chunk_content_str)
            metadata = {
                "document_id": document_id, 
                "source_type": "docx",
                "node_type": "list_container", 
                "headings": list(current_headings),
                "num_tokens": count_tokens_in_text(final_chunk_text)
            }
            chunks.append(Chunk(text=final_chunk_text, metadata=metadata))

    def _consolidate_recursive(self, nodes: list[dict[str, Any]], current_headings: list[str], chunks: list[Chunk], document_id: str):
        for node in nodes:
            node_type = node.get('type')

            if node_type == 'heading':
                new_headings = list(current_headings)
                heading_level = node.get('level', 1)
                
                while len(new_headings) < heading_level:
                    new_headings.append("") 
                new_headings[heading_level - 1] = node.get('content', '')
                new_headings = new_headings[:heading_level]

                if 'children' in node and node['children']:
                    self._consolidate_recursive(node['children'], new_headings, chunks, document_id)

            elif node_type == 'list_container':
                # Delegate to the specialized list container processing method
                self._process_list_container(node, current_headings, chunks, document_id)

            elif node_type in ['paragraph', 'table']:
                stringified_content = self._stringify_node_content(node, indent_level=0)
                if stringified_content.strip():
                    chunk_text = self._create_chunk_text(current_headings, stringified_content)
                    # For paragraphs and tables (in M2, tables are still one chunk)
                    # We assume a paragraph fits. Tables are one chunk.
                    # If a single paragraph/table + headings is too large, it will be oversized.
                    metadata = {
                        "document_id": document_id,
                        "source_type": "docx",
                        "node_type": node_type,
                        "headings": list(current_headings),
                        "num_tokens": count_tokens_in_text(chunk_text)
                    }
                    chunks.append(Chunk(text=chunk_text, metadata=metadata))
            

    def apply(self, elements: list[dict[str, Any]], document_id: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        self._consolidate_recursive(elements, [], chunks, document_id)
        return chunks
