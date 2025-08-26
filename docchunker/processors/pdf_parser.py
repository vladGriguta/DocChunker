"""
PDF parser that extracts structured content from PDF documents.

This parser attempts to detect document structure (headings, lists, tables, paragraphs)
from PDF text and formatting information, returning the same hierarchical format as DocxParser.
"""

from typing import Any, Union, BinaryIO
import re
from pypdf import PdfReader


class PdfParser:
    """Parses PDF documents to a hierarchical structure of elements."""

    def __init__(self):
        self.current_heading_level = 0
        # Font size thresholds for heading detection
        self.heading_font_threshold = 1.2  # Fonts 20% larger than average = headings
        
    def apply(self, file_input: Union[str, BinaryIO]) -> list[dict[str, Any]]:
        """Parse PDF and return a hierarchical list of element dictionaries.
        
        Args:
            file_input: Either a file path (str) or a file-like object (BinaryIO)
        """
        reader = PdfReader(file_input)
        flat_elements = []
        self.current_heading_level = 0
        
        # Extract text with formatting information
        all_text_blocks = []
        for page in reader.pages:
            page_text_blocks = self._extract_text_blocks_with_formatting(page)
            all_text_blocks.extend(page_text_blocks)
        
        # Calculate average font size for heading detection
        font_sizes = [block['font_size'] for block in all_text_blocks if block['font_size']]
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12
        
        # Process text blocks into structured elements
        for block in all_text_blocks:
            text = block['text'].strip()
            if not text:
                continue
                
            element = self._process_text_block(block, avg_font_size)
            if element:
                flat_elements.append(element)
        
        # Reconstruct hierarchy (reuse the logic from DocxParser)
        hierarchical_elements = self._reconstruct_hierarchy(flat_elements)
        return hierarchical_elements
    
    def _extract_text_blocks_with_formatting(self, page) -> list[dict[str, Any]]:
        """Extract text blocks with basic formatting information from a PDF page."""
        text_blocks = []
        
        try:
            # Try to extract with formatting information
            if hasattr(page, 'extract_text'):
                # Basic text extraction - we'll enhance this with font detection
                full_text = page.extract_text()
                
                # Split into paragraphs/blocks based on double newlines
                blocks = re.split(r'\n\s*\n', full_text)
                
                for block in blocks:
                    lines = block.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            # Estimate font size based on text characteristics
                            # This is a heuristic - in practice, you'd want PyMuPDF for real font info
                            font_size = self._estimate_font_size(line)
                            
                            text_blocks.append({
                                'text': line,
                                'font_size': font_size,
                                'x': 0,  # Position info not available with basic PyPDF
                                'y': 0
                            })
                            
        except Exception:
            # Fallback to basic text extraction
            text_blocks.append({
                'text': page.extract_text() or "",
                'font_size': 12,
                'x': 0,
                'y': 0
            })
            
        return text_blocks
    
    def _estimate_font_size(self, text: str) -> float:
        """Heuristic to estimate font size based on text characteristics."""
        # Simple heuristics for heading detection
        
        # All caps text might be headings
        if text.isupper() and len(text) < 100:
            return 16
            
        # Text ending with colons might be headings
        if text.endswith(':') and len(text) < 100:
            return 14
            
        # Short lines might be headings
        if len(text) < 50 and not text.endswith('.'):
            return 13
            
        # Default paragraph size
        return 12
    
    def _process_text_block(self, block: dict[str, Any], avg_font_size: float) -> dict[str, Any] | None:
        """Process a text block into a structured element dictionary."""
        text = block['text'].strip()
        font_size = block.get('font_size', 12)
        
        if not text:
            return None
            
        # Heading detection based on font size
        if font_size > avg_font_size * self.heading_font_threshold:
            heading_level = self._determine_heading_level(font_size, avg_font_size)
            self.current_heading_level = heading_level
            return {
                "type": "heading",
                "level": heading_level,
                "content": text
            }
        
        # List item detection
        list_match = self._detect_list_item(text)
        if list_match:
            return {
                "type": "list_item",
                "level": list_match['level'],
                "content": list_match['content'],
                "num_id": list_match['num_id']
            }
        
        # Table detection (basic - look for multiple columns separated by spaces/tabs)
        if self._is_table_row(text):
            # For now, treat table rows as paragraphs
            # TODO: Implement proper table detection and grouping
            pass
        
        # Default to paragraph
        return {
            "type": "paragraph",
            "level": self.current_heading_level if self.current_heading_level > 0 else 0,
            "content": text
        }
    
    def _determine_heading_level(self, font_size: float, avg_font_size: float) -> int:
        """Determine heading level based on font size."""
        ratio = font_size / avg_font_size
        
        if ratio >= 2.0:
            return 1
        elif ratio >= 1.6:
            return 2
        elif ratio >= 1.4:
            return 3
        elif ratio >= 1.2:
            return 4
        else:
            return 5
    
    def _detect_list_item(self, text: str) -> dict[str, Any] | None:
        """Detect if text is a list item and extract its properties."""
        
        # Bullet list patterns
        bullet_patterns = [
            r'^[\s]*[-•*▪▫][\s]+(.+)$',  # - • * ▪ ▫
            r'^[\s]*[►▶][\s]+(.+)$',    # ► ▶
        ]
        
        for pattern in bullet_patterns:
            match = re.match(pattern, text)
            if match:
                indent_level = len(text) - len(text.lstrip())
                level = indent_level // 4  # Assume 4 spaces per indent level
                return {
                    'level': level,
                    'content': match.group(1).strip(),
                    'num_id': -1  # Bullet list
                }
        
        # Numbered list patterns
        numbered_patterns = [
            r'^[\s]*(\d+)\.[\s]+(.+)$',           # 1. 2. 3.
            r'^[\s]*(\d+)\)[\s]+(.+)$',           # 1) 2) 3)
            r'^[\s]*\((\d+)\)[\s]+(.+)$',         # (1) (2) (3)
            r'^[\s]*([a-z])\.[\s]+(.+)$',         # a. b. c.
            r'^[\s]*([A-Z])\.[\s]+(.+)$',         # A. B. C.
            r'^[\s]*([ivx]+)\.[\s]+(.+)$',        # i. ii. iii. (roman numerals)
        ]
        
        for pattern in numbered_patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                indent_level = len(text) - len(text.lstrip())
                level = indent_level // 4
                return {
                    'level': level,
                    'content': match.group(2).strip(),
                    'num_id': 1  # Numbered list
                }
        
        return None
    
    def _is_table_row(self, text: str) -> bool:
        """Basic detection of table rows (multiple columns)."""
        # Look for multiple columns separated by multiple spaces or tabs
        columns = re.split(r'\s{3,}|\t+', text)
        return len(columns) > 1 and all(col.strip() for col in columns)
    
    def _reconstruct_hierarchy(self, flat_elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Reconstructs a hierarchical structure from a flat list of elements.
        This is identical to the DocxParser logic to ensure consistency.
        """
        root_nodes: list[dict[str, Any]] = []
        parent_stack: list[dict[str, Any]] = []

        for element_data in flat_elements:
            node = {**element_data, 'children': []}

            if node['type'] == 'heading':
                while parent_stack and \
                      ((parent_stack[-1]['type'] == 'heading' and parent_stack[-1]['level'] >= node['level']) or \
                       (parent_stack[-1]['type'] in ['list_container', 'list_item'])):
                    parent_stack.pop()

                if not parent_stack:
                    root_nodes.append(node)
                else:
                    parent_stack[-1]['children'].append(node)
                parent_stack.append(node)

            elif node['type'] == 'list_item':
                li_level = node['level']
                li_num_id = node['num_id']

                while parent_stack:
                    p_on_stack = parent_stack[-1]
                    if p_on_stack['type'] == 'list_container':
                        if p_on_stack['num_id'] == li_num_id:
                            if p_on_stack['level'] == li_level:
                                break
                            elif p_on_stack['level'] < li_level:
                                break
                            else:
                                parent_stack.pop()
                        else:
                            parent_stack.pop()
                    elif p_on_stack['type'] == 'list_item':
                        if p_on_stack['num_id'] == li_num_id and li_level > p_on_stack['level']:
                            break
                        else:
                            parent_stack.pop()
                    elif p_on_stack['type'] == 'heading':
                        break
                    else:
                        parent_stack.pop()

                current_parent_on_stack = parent_stack[-1] if parent_stack else None

                if current_parent_on_stack and \
                   current_parent_on_stack['type'] == 'list_container' and \
                   current_parent_on_stack['num_id'] == li_num_id and \
                   current_parent_on_stack['level'] == li_level:
                    current_parent_on_stack['children'].append(node)
                    parent_stack.append(node)
                else:
                    list_container_node = {
                        'type': 'list_container',
                        'level': li_level,
                        'num_id': li_num_id,
                        'children': [node]
                    }

                    if not current_parent_on_stack:
                        root_nodes.append(list_container_node)
                    else:
                        current_parent_on_stack['children'].append(list_container_node)

                    parent_stack.append(list_container_node)
                    parent_stack.append(node)

            elif node['type'] in ['paragraph', 'table']:
                while parent_stack and parent_stack[-1]['type'] in ['list_item', 'list_container']:
                    parent_stack.pop()
                
                if not parent_stack:
                    root_nodes.append(node)
                else:
                    parent_stack[-1]['children'].append(node)

        return root_nodes