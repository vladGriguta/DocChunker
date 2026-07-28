import re
from typing import Any

from docchunker.models.chunk import Chunk


class DocumentChunker:
    """
    Consolidates hierarchical document elements into context-aware text chunks.
    
    This chunker works with hierarchical document structures produced by any parser
    that outputs the standardized format (DOCX, PDF, etc.). It handles sophisticated
    chunking with overlap support for lists, tables, and other complex structures.
    """
    
    SENTENCE_BOUNDARY_REGEX = re.compile(r"(?<=[.!?])\s+")
    PARAGRAPH_SEPARATOR = "\n\n"

    def __init__(self, chunk_size: int = 1000, num_overlapping_elements: int = 0, min_chunk_size: int | None = None):
        self.chunk_size = chunk_size
        self.num_overlapping_elements = num_overlapping_elements
        # Paragraph chunks smaller than this are merged with adjacent paragraphs
        # sharing the same heading context (while staying within chunk_size).
        self.min_chunk_size = min_chunk_size if min_chunk_size is not None else max(1, chunk_size // 4)

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

    def _format_table_row(self, header: list[str], row_data: list[str]) -> str:
        """Formats a single table row with its corresponding header."""
        if not header or len(header) != len(row_data):
            # Fallback if header is missing or mismatched: just join row data
            try:
                return " | ".join(row_data)
            except TypeError:
                raise ValueError("Row data must be a list of strings.")
        return " | ".join([f"{header[i]}: {cell_data}" for i, cell_data in enumerate(row_data)])

    def _process_table_node(self, node: dict[str, Any], current_headings: list[str], chunks: list[Chunk], document_id: str, source_format: str = "docx"):
        """
        Processes a table node, splitting it into multiple chunks by rows if necessary,
        with overlap between chunks. Each chunk includes header context for its rows.
        """
        table_header = node.get('header', [])
        data_rows = node.get('data_rows', [])

        if not data_rows:
            # If there are no data rows, but there's a header, maybe stringify just the header?
            # Or, if table is truly empty, stringify the node as a simple table placeholder.
            # For now, if no data_rows, we can create a simple representation or skip.
            if table_header:
                header_text = "Table Header: " + " | ".join(table_header)
                full_chunk_text = self._create_chunk_text(current_headings, header_text)
                metadata = {
                    "document_id": document_id, "source_type": source_format,
                    "node_type": "table_header_only", "headings": list(current_headings),
                    "num_chars": len(full_chunk_text)
                }
                chunks.append(Chunk(text=full_chunk_text, metadata=metadata))
            return

        current_chunk_row_data_list: list[list[str]] = []
        current_chunk_rows_text_parts: list[str] = []

        headings_prefix_text = self._create_chunk_text(current_headings, "")
        headings_chars = len(headings_prefix_text)
        current_content_chars = 0

        for i, row_data in enumerate(data_rows):
            formatted_row_text = self._format_table_row(table_header, row_data)
            row_chars = len(formatted_row_text)

            if current_chunk_row_data_list and \
               (headings_chars + current_content_chars + row_chars + len("\n")) > self.chunk_size:

                chunk_content_str = "\n".join(current_chunk_rows_text_parts)
                final_chunk_text = self._create_chunk_text(current_headings, chunk_content_str)
                
                # Add overlap metadata - check if this is the first chunk for this specific table
                table_chunks_so_far = len([c for c in chunks if c.metadata.get("node_type") == "table_rows"])
                is_first_table_chunk = table_chunks_so_far == 0
                metadata = {
                    "document_id": document_id, "source_type": source_format,
                    "node_type": "table_rows", "headings": list(current_headings),
                    "num_chars": len(final_chunk_text),
                    "has_overlap": not is_first_table_chunk and self.num_overlapping_elements > 0,
                    "overlap_elements": 0 if is_first_table_chunk else min(self.num_overlapping_elements, len(current_chunk_row_data_list))
                }
                chunks.append(Chunk(text=final_chunk_text, metadata=metadata))

                if self.num_overlapping_elements > 0 and len(current_chunk_row_data_list) >= self.num_overlapping_elements:
                    overlap_row_data = current_chunk_row_data_list[-self.num_overlapping_elements:]
                else:
                    overlap_row_data = []

                current_chunk_row_data_list = list(overlap_row_data)
                current_chunk_rows_text_parts = [self._format_table_row(table_header, r) for r in overlap_row_data]
                current_content_chars = len("\n".join(current_chunk_rows_text_parts))

            current_chunk_row_data_list.append(row_data)
            current_chunk_rows_text_parts.append(formatted_row_text)
            current_content_chars += row_chars + (len("\n") if len(current_chunk_rows_text_parts) > 1 else 0)

        if current_chunk_row_data_list:
            chunk_content_str = "\n".join(current_chunk_rows_text_parts)
            final_chunk_text = self._create_chunk_text(current_headings, chunk_content_str)
            
            # Add overlap metadata for final chunk
            table_chunks_so_far = len([c for c in chunks if c.metadata.get("node_type") == "table_rows"])
            is_first_table_chunk = table_chunks_so_far == 0
            metadata = {
                "document_id": document_id, "source_type": source_format,
                "node_type": "table_rows", "headings": list(current_headings),
                "num_chars": len(final_chunk_text),
                "has_overlap": not is_first_table_chunk and self.num_overlapping_elements > 0,
                "overlap_elements": 0 if is_first_table_chunk else min(self.num_overlapping_elements, len(current_chunk_row_data_list))
            }
            chunks.append(Chunk(text=final_chunk_text, metadata=metadata))


    def _process_list_container(self, node: dict[str, Any], current_headings: list[str], chunks: list[Chunk], document_id: str, source_format: str = "docx"):
        """
        Processes a list_container, splitting it into multiple chunks if necessary,
        with overlap between chunks.
        """
        list_items = node.get('children', [])
        if not list_items:
            return

        current_chunk_item_nodes: list[dict[str, Any]] = []
        current_chunk_items_text_parts: list[str] = []

        headings_prefix_text = self._create_chunk_text(current_headings, "")
        headings_chars = len(headings_prefix_text)
        current_content_chars = 0

        for i, item_node in enumerate(list_items):
            item_text = self._stringify_node_content(item_node, indent_level=0) # Indent relative to list container
            item_chars = len(item_text)
            # Check if adding this item would exceed the chunk size
            # (considering headings + current items + new item)
            if current_chunk_item_nodes and \
               (headings_chars + current_content_chars + item_chars + len("\n")) > self.chunk_size:
                # Finalize the current chunk
                chunk_content_str = "\n".join(current_chunk_items_text_parts)
                final_chunk_text = self._create_chunk_text(current_headings, chunk_content_str)
                
                # Add overlap metadata - check if this is the first chunk for this specific list container
                list_chunks_so_far = len([c for c in chunks if c.metadata.get("node_type") == "list_container"])
                is_first_list_chunk = list_chunks_so_far == 0
                metadata = {
                    "document_id": document_id, 
                    "source_type": source_format,
                    "node_type": "list_container", 
                    "headings": list(current_headings),
                    "num_chars": len(final_chunk_text),
                    "has_overlap": not is_first_list_chunk and self.num_overlapping_elements > 0,
                    "overlap_elements": 0 if is_first_list_chunk else min(self.num_overlapping_elements, len(current_chunk_item_nodes))
                }
                chunks.append(Chunk(text=final_chunk_text, metadata=metadata))

                # TODO: revisit this logic if num_overlapping_elements > 0: only apply it if the previous chunk had significantly more items than the overlap count
                if self.num_overlapping_elements > 0 and len(current_chunk_item_nodes) >= self.num_overlapping_elements:
                    overlap_nodes = current_chunk_item_nodes[-self.num_overlapping_elements:]
                else:
                    overlap_nodes = []

                current_chunk_item_nodes = list(overlap_nodes)
                current_chunk_items_text_parts = [self._stringify_node_content(n, 0) for n in overlap_nodes]
                current_content_chars = len("\n".join(current_chunk_items_text_parts))

            # Add current item to the current chunk (or the new chunk after overlap)
            current_chunk_item_nodes.append(item_node)
            current_chunk_items_text_parts.append(item_text)
            current_content_chars += item_chars + (len("\n") if len(current_chunk_items_text_parts) > 1 else 0)

        # Add the last remaining chunk
        if current_chunk_item_nodes:
            chunk_content_str = "\n".join(current_chunk_items_text_parts)
            final_chunk_text = self._create_chunk_text(current_headings, chunk_content_str)
            
            # Add overlap metadata for final chunk
            list_chunks_so_far = len([c for c in chunks if c.metadata.get("node_type") == "list_container"])
            is_first_list_chunk = list_chunks_so_far == 0
            metadata = {
                "document_id": document_id, 
                "source_type": source_format,
                "node_type": "list_container", 
                "headings": list(current_headings),
                "num_chars": len(final_chunk_text),
                "has_overlap": not is_first_list_chunk and self.num_overlapping_elements > 0,
                "overlap_elements": 0 if is_first_list_chunk else min(self.num_overlapping_elements, len(current_chunk_item_nodes))
            }
            chunks.append(Chunk(text=final_chunk_text, metadata=metadata))

    def _split_text_into_sentences(self, text: str) -> list[str]:
        """Splits text at sentence boundaries using a simple rule-based regex."""
        sentences = [s for s in self.SENTENCE_BOUNDARY_REGEX.split(text) if s.strip()]
        return sentences if sentences else [text]

    def _split_oversized_paragraph(self, content: str, available_chars: int) -> list[str]:
        """
        Splits paragraph content that exceeds the available space into pieces.

        Splitting happens at sentence boundaries; a hard character split is used
        only as a fallback when a single sentence alone exceeds the available space.
        """
        pieces: list[str] = []
        current_parts: list[str] = []
        current_len = 0

        for sentence in self._split_text_into_sentences(content):
            sentence_len = len(sentence)
            separator_len = 1 if current_parts else 0  # sentences are re-joined with " "

            if current_parts and current_len + separator_len + sentence_len > available_chars:
                pieces.append(" ".join(current_parts))
                current_parts = []
                current_len = 0

            if sentence_len > available_chars:
                # Fallback: hard character split for a single overlong sentence.
                for start in range(0, sentence_len, available_chars):
                    piece = sentence[start:start + available_chars]
                    if len(piece) == available_chars:
                        pieces.append(piece)
                    else:
                        current_parts = [piece]
                        current_len = len(piece)
            else:
                current_parts.append(sentence)
                current_len += separator_len + sentence_len

        if current_parts:
            pieces.append(" ".join(current_parts))
        return pieces

    def _emit_paragraph_group(self, paragraph_texts: list[str], current_headings: list[str], chunks: list[Chunk], document_id: str, source_format: str):
        """Emits one chunk for a group of one or more merged paragraphs."""
        if not paragraph_texts:
            return
        content = self.PARAGRAPH_SEPARATOR.join(paragraph_texts)
        chunk_text = self._create_chunk_text(current_headings, content)
        metadata: dict[str, Any] = {
            "document_id": document_id,
            "source_type": source_format,
            "node_type": "paragraph" if len(paragraph_texts) == 1 else "paragraph_group",
            "headings": list(current_headings),
            "num_chars": len(chunk_text),
        }
        if len(paragraph_texts) > 1:
            metadata["num_merged_elements"] = len(paragraph_texts)
        chunks.append(Chunk(text=chunk_text, metadata=metadata))

    def _emit_split_paragraph(self, content: str, current_headings: list[str], chunks: list[Chunk], document_id: str, source_format: str, available_chars: int):
        """Emits multiple chunks for a single paragraph larger than the chunk size."""
        pieces = self._split_oversized_paragraph(content, available_chars)
        split_total = len(pieces)
        for split_index, piece in enumerate(pieces):
            chunk_text = self._create_chunk_text(current_headings, piece)
            metadata = {
                "document_id": document_id,
                "source_type": source_format,
                "node_type": "paragraph",
                "headings": list(current_headings),
                "num_chars": len(chunk_text),
                "is_split": True,
                "split_index": split_index,
                "split_total": split_total,
            }
            chunks.append(Chunk(text=chunk_text, metadata=metadata))

    def _flush_paragraph_buffer(self, paragraph_buffer: list[str], current_headings: list[str], chunks: list[Chunk], document_id: str, source_format: str):
        """
        Flushes buffered consecutive paragraphs (same heading context) as chunks.

        Homogenization rules:
        - A paragraph that would exceed chunk_size on its own is split at
          sentence boundaries into multiple chunks.
        - Consecutive paragraphs are merged while the current group is smaller
          than min_chunk_size and the combined chunk stays within chunk_size.
        """
        if not paragraph_buffer:
            return

        headings_chars = len(self._create_chunk_text(current_headings, ""))
        available_chars = max(self.chunk_size - headings_chars, self.min_chunk_size)

        current_group: list[str] = []
        current_content_chars = 0

        for paragraph_text in paragraph_buffer:
            paragraph_chars = len(paragraph_text)

            if paragraph_chars > available_chars:
                # Oversized paragraph: flush any pending group, then split it.
                self._emit_paragraph_group(current_group, current_headings, chunks, document_id, source_format)
                current_group = []
                current_content_chars = 0
                self._emit_split_paragraph(paragraph_text, current_headings, chunks, document_id, source_format, available_chars)
                continue

            separator_chars = len(self.PARAGRAPH_SEPARATOR) if current_group else 0
            group_is_large_enough = (headings_chars + current_content_chars) >= self.min_chunk_size
            would_overflow = current_content_chars + separator_chars + paragraph_chars > available_chars

            if current_group and (group_is_large_enough or would_overflow):
                self._emit_paragraph_group(current_group, current_headings, chunks, document_id, source_format)
                current_group = []
                current_content_chars = 0
                separator_chars = 0

            current_group.append(paragraph_text)
            current_content_chars += separator_chars + paragraph_chars

        self._emit_paragraph_group(current_group, current_headings, chunks, document_id, source_format)
        paragraph_buffer.clear()

    def _consolidate_recursive(self, nodes: list[dict[str, Any]], current_headings: list[str], chunks: list[Chunk], document_id: str, source_format: str = "docx"):
        paragraph_buffer: list[str] = []

        for node in nodes:
            node_type = node.get('type')

            if node_type == 'paragraph':
                stringified_content = self._stringify_node_content(node, indent_level=0)
                if stringified_content.strip():
                    paragraph_buffer.append(stringified_content)
                continue

            # Any non-paragraph node breaks the run of consecutive paragraphs.
            self._flush_paragraph_buffer(paragraph_buffer, current_headings, chunks, document_id, source_format)

            if node_type == 'heading':
                new_headings = list(current_headings)
                heading_level = node.get('level', 1)

                while len(new_headings) < heading_level:
                    new_headings.append("") 
                new_headings[heading_level - 1] = node.get('content', '')
                new_headings = new_headings[:heading_level]

                if 'children' in node and node['children']:
                    self._consolidate_recursive(node['children'], new_headings, chunks, document_id, source_format)

            elif node_type == 'list_container':
                self._process_list_container(node, current_headings, chunks, document_id, source_format)

            elif node_type == 'table':
                self._process_table_node(node, current_headings, chunks, document_id, source_format)

        self._flush_paragraph_buffer(paragraph_buffer, current_headings, chunks, document_id, source_format)


    def apply(self, elements: list[dict[str, Any]], document_id: str, source_format: str = "docx") -> list[Chunk]:
        """
        Apply chunking logic to hierarchical document elements.
        
        Args:
            elements: Hierarchical document structure from any parser
            document_id: Identifier for the source document
            source_format: Format of the source document (docx, pdf, etc.)
        """
        chunks: list[Chunk] = []
        self._consolidate_recursive(elements, [], chunks, document_id, source_format)
        return chunks