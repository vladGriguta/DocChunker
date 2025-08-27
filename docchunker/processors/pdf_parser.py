"""
PDF parser that extracts structured content from PDF documents.

This parser attempts to detect document structure (headings, lists, tables, paragraphs)
from PDF text and formatting information, returning the same hierarchical format as DocxParser.
Uses PyMuPDF (fitz) for rich formatting extraction with fallback to PyPDF.
"""

from typing import Any, Union, BinaryIO, Optional
import re
import statistics

# Try PyMuPDF first for rich formatting, fallback to PyPDF
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

from pypdf import PdfReader


class PdfParser:
    """Parses PDF documents to a hierarchical structure of elements."""

    def __init__(self):
        self.current_heading_level = 0
        # Font size thresholds for heading detection
        self.heading_font_threshold = 1.15  # Fonts 15% larger than average = headings
        self.use_pymupdf = HAS_PYMUPDF
        
    def apply(self, file_input: Union[str, BinaryIO]) -> list[dict[str, Any]]:
        """Parse PDF and return a hierarchical list of element dictionaries.
        
        Args:
            file_input: Either a file path (str) or a file-like object (BinaryIO)
        """
        if self.use_pymupdf:
            return self._apply_with_pymupdf(file_input)
        else:
            return self._apply_with_pypdf(file_input)
    
    def _apply_with_pymupdf(self, file_input: Union[str, BinaryIO]) -> list[dict[str, Any]]:
        """Parse PDF using PyMuPDF for rich formatting extraction."""
        # Open document with PyMuPDF
        if isinstance(file_input, str):
            doc = fitz.open(file_input)
        else:
            # For BytesIO, read content and open from memory
            if hasattr(file_input, 'read'):
                content = file_input.read()
                if hasattr(file_input, 'seek'):
                    file_input.seek(0)  # Reset for potential future use
                doc = fitz.open(stream=content, filetype="pdf")
            else:
                raise ValueError("Unsupported file input type for PyMuPDF")
        
        flat_elements = []
        self.current_heading_level = 0
        
        # Extract text blocks with rich formatting from all pages
        all_text_blocks = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            blocks = self._extract_blocks_with_pymupdf(page)
            all_text_blocks.extend(blocks)
        
        doc.close()
        
        # Calculate font statistics for heading detection
        font_stats = self._calculate_font_statistics(all_text_blocks)
        
        # Process blocks into structured elements
        for block in all_text_blocks:
            element = self._process_block_with_formatting(block, font_stats)
            if element:
                flat_elements.append(element)
        
        # Reconstruct hierarchy
        hierarchical_elements = self._reconstruct_hierarchy(flat_elements)
        return hierarchical_elements
    
    def _apply_with_pypdf(self, file_input: Union[str, BinaryIO]) -> list[dict[str, Any]]:
        """Parse PDF using PyPDF with enhanced heuristics (fallback method)."""
        reader = PdfReader(file_input)
        flat_elements = []
        self.current_heading_level = 0
        
        # Extract text with enhanced heuristics
        all_text_blocks = []
        for page in reader.pages:
            page_text_blocks = self._extract_text_blocks_enhanced_heuristics(page)
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
        
        # Reconstruct hierarchy
        hierarchical_elements = self._reconstruct_hierarchy(flat_elements)
        return hierarchical_elements
    
    def _extract_blocks_with_pymupdf(self, page) -> list[dict[str, Any]]:
        """Extract text blocks with rich formatting using PyMuPDF."""
        blocks = []
        
        # Get text dictionary with detailed formatting
        text_dict = page.get_text("dict")
        
        for block in text_dict.get("blocks", []):
            # Skip image blocks
            if "lines" not in block:
                continue
            
            # Group lines into paragraphs based on spatial and formatting analysis
            paragraphs = self._group_lines_into_paragraphs(block["lines"])
            
            for paragraph_lines in paragraphs:
                if not paragraph_lines:
                    continue
                    
                # Combine all lines in the paragraph
                paragraph_text = ""
                all_fonts = []
                all_sizes = []
                all_flags = []
                paragraph_bbox = None
                
                for line_data in paragraph_lines:
                    line_text = line_data['text']
                    paragraph_text += line_text + " "
                    all_fonts.extend(line_data['fonts'])
                    all_sizes.extend(line_data['sizes'])
                    all_flags.extend(line_data['flags'])
                    
                    # Update paragraph bounding box
                    if paragraph_bbox is None:
                        paragraph_bbox = line_data['bbox']
                    else:
                        # Expand bbox to include this line
                        paragraph_bbox = [
                            min(paragraph_bbox[0], line_data['bbox'][0]),  # min x
                            min(paragraph_bbox[1], line_data['bbox'][1]),  # min y
                            max(paragraph_bbox[2], line_data['bbox'][2]),  # max x
                            max(paragraph_bbox[3], line_data['bbox'][3])   # max y
                        ]
                
                if paragraph_text.strip():
                    # Calculate paragraph-level formatting
                    avg_size = statistics.mean(all_sizes) if all_sizes else 12
                    is_bold = any(flags & 2**4 for flags in all_flags)  # Bold flag
                    is_italic = any(flags & 2**1 for flags in all_flags)  # Italic flag
                    font_family = max(set(all_fonts), key=all_fonts.count) if all_fonts else ""
                    
                    blocks.append({
                        'text': paragraph_text.strip(),
                        'font_size': avg_size,
                        'font_family': font_family,
                        'is_bold': is_bold,
                        'is_italic': is_italic,
                        'x': paragraph_bbox[0] if paragraph_bbox else 0,
                        'y': paragraph_bbox[1] if paragraph_bbox else 0,
                        'bbox': paragraph_bbox if paragraph_bbox else [0, 0, 0, 0]
                    })
        
        return blocks
    
    def _group_lines_into_paragraphs(self, lines: list) -> list[list[dict[str, Any]]]:
        """Group lines into paragraphs based on spatial relationships and formatting consistency."""
        if not lines:
            return []
        
        # First, extract line data with formatting information
        processed_lines = []
        for line in lines:
            line_text = ""
            line_fonts = []
            line_sizes = []
            line_flags = []
            
            for span in line.get("spans", []):
                span_text = span.get("text", "")
                if span_text.strip():
                    line_text += span_text
                    line_fonts.append(span.get("font", ""))
                    line_sizes.append(span.get("size", 12))
                    line_flags.append(span.get("flags", 0))
            
            if line_text.strip():
                processed_lines.append({
                    'text': line_text.strip(),
                    'fonts': line_fonts,
                    'sizes': line_sizes,
                    'flags': line_flags,
                    'bbox': line.get("bbox", [0, 0, 0, 0]),
                    'avg_size': statistics.mean(line_sizes) if line_sizes else 12,
                    'is_bold': any(flags & 2**4 for flags in line_flags),
                    'font_family': max(set(line_fonts), key=line_fonts.count) if line_fonts else ""
                })
        
        if not processed_lines:
            return []
        
        # Group lines into paragraphs
        paragraphs = []
        current_paragraph = [processed_lines[0]]
        
        for i in range(1, len(processed_lines)):
            prev_line = processed_lines[i-1]
            curr_line = processed_lines[i]
            
            # Calculate vertical distance between lines
            prev_bottom = prev_line['bbox'][3]  # y2 of previous line
            curr_top = curr_line['bbox'][1]     # y1 of current line
            vertical_gap = abs(curr_top - prev_bottom)
            
            # Calculate expected line spacing based on font size
            avg_font_size = (prev_line['avg_size'] + curr_line['avg_size']) / 2
            normal_line_spacing = avg_font_size * 0.3  # Typical line spacing is ~30% of font size
            paragraph_break_threshold = avg_font_size * 0.8  # Larger gaps indicate paragraph breaks
            
            # Check for paragraph continuation vs. new paragraph
            should_continue_paragraph = (
                # Similar formatting
                abs(prev_line['avg_size'] - curr_line['avg_size']) < 1 and
                prev_line['font_family'] == curr_line['font_family'] and
                prev_line['is_bold'] == curr_line['is_bold'] and
                
                # Reasonable vertical spacing (not too far apart)
                vertical_gap <= paragraph_break_threshold and
                
                # Content flow indicators
                self._lines_likely_connected(prev_line['text'], curr_line['text'])
            )
            
            if should_continue_paragraph:
                current_paragraph.append(curr_line)
            else:
                # Start new paragraph
                if current_paragraph:
                    paragraphs.append(current_paragraph)
                current_paragraph = [curr_line]
        
        # Don't forget the last paragraph
        if current_paragraph:
            paragraphs.append(current_paragraph)
        
        return paragraphs
    
    def _lines_likely_connected(self, prev_text: str, curr_text: str) -> bool:
        """Determine if two lines are likely part of the same paragraph based on content."""
        prev_text = prev_text.strip()
        curr_text = curr_text.strip()
        
        # Empty lines break paragraphs
        if not prev_text or not curr_text:
            return False
        
        # Lines ending with sentence punctuation often end paragraphs
        if prev_text.endswith(('.', '!', '?')):
            # But check if next line looks like a continuation
            # (starts with lowercase, doesn't look like a heading)
            if (curr_text and curr_text[0].islower() and 
                not curr_text.endswith(':') and
                len(curr_text) > 20):  # Reasonably long line, not likely a heading
                return True
            return False
        
        # Lines ending with commas, semicolons, or no punctuation likely continue
        if prev_text.endswith((',', ';', ':')) or not prev_text[-1] in '.!?':
            return True
        
        # Check if current line starts with lowercase (likely continuation)
        if curr_text and curr_text[0].islower():
            return True
        
        # Default to continuation if no clear break indicators
        return True
    
    def _calculate_font_statistics(self, blocks: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate font statistics for better heading detection."""
        font_sizes = [block['font_size'] for block in blocks if block['font_size']]
        
        if not font_sizes:
            return {'avg_size': 12, 'median_size': 12, 'std_size': 0}
        
        avg_size = statistics.mean(font_sizes)
        median_size = statistics.median(font_sizes)
        
        if len(font_sizes) > 1:
            std_size = statistics.stdev(font_sizes)
        else:
            std_size = 0
            
        return {
            'avg_size': avg_size,
            'median_size': median_size,
            'std_size': std_size,
            'min_size': min(font_sizes),
            'max_size': max(font_sizes)
        }
    
    def _process_block_with_formatting(self, block: dict[str, Any], font_stats: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Process a text block with rich formatting information."""
        text = block['text'].strip()
        if not text:
            return None
            
        font_size = block.get('font_size', 12)
        is_bold = block.get('is_bold', False)
        is_italic = block.get('is_italic', False)
        
        # Enhanced heading detection using multiple signals
        is_heading = self._is_heading_with_formatting(block, font_stats)
        
        if is_heading:
            heading_level = self._determine_heading_level_advanced(block, font_stats)
            self.current_heading_level = heading_level
            return {
                "type": "heading",
                "level": heading_level,
                "content": text
            }
        
        # List item detection with improved heuristics
        list_match = self._detect_list_item_advanced(text, block)
        if list_match:
            return {
                "type": "list_item",
                "level": list_match['level'],
                "content": list_match['content'],
                "num_id": list_match['num_id']
            }
        
        # Table detection (enhanced)
        if self._is_table_row_advanced(text, block):
            # For now, treat as paragraph - TODO: implement proper table grouping
            pass
        
        # Default to paragraph
        return {
            "type": "paragraph",
            "level": self.current_heading_level if self.current_heading_level > 0 else 0,
            "content": text
        }
    
    def _is_heading_with_formatting(self, block: dict[str, Any], font_stats: dict[str, Any]) -> bool:
        """Determine if block is a heading using multiple formatting signals."""
        text = block['text'].strip()
        font_size = block.get('font_size', 12)
        is_bold = block.get('is_bold', False)
        font_family = block.get('font_family', '')
        
        avg_size = font_stats['avg_size']
        
        # Multiple signals for heading detection
        signals = {
            'large_font': font_size > avg_size * self.heading_font_threshold,
            'bold_text': is_bold,
            'short_line': len(text) < 100 and not text.endswith('.'),
            'title_case': text.istitle(),
            'all_caps': text.isupper() and len(text) < 50,
            'ends_with_colon': text.endswith(':'),
            'no_sentence_end': not text.endswith(('.', '!', '?')),
            'significant_size': font_size > avg_size * 1.1
        }
        
        # Weight the signals
        score = 0
        if signals['large_font']: score += 3
        if signals['bold_text']: score += 2
        if signals['short_line']: score += 1
        if signals['title_case']: score += 1
        if signals['all_caps']: score += 1
        if signals['ends_with_colon']: score += 1
        if signals['no_sentence_end']: score += 1
        if signals['significant_size']: score += 1
        
        # Threshold for heading classification
        return score >= 3
    
    def _determine_heading_level_advanced(self, block: dict[str, Any], font_stats: dict[str, Any]) -> int:
        """Determine heading level using font size and formatting."""
        font_size = block.get('font_size', 12)
        is_bold = block.get('is_bold', False)
        avg_size = font_stats['avg_size']
        
        ratio = font_size / avg_size
        
        # Adjust level based on formatting
        if is_bold:
            ratio *= 1.1  # Bold text gets slight boost
            
        if ratio >= 2.0:
            return 1
        elif ratio >= 1.6:
            return 2
        elif ratio >= 1.4:
            return 3
        elif ratio >= 1.2:
            return 4
        elif ratio >= 1.1:
            return 5
        else:
            return 6
    
    def _detect_list_item_advanced(self, text: str, block: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Enhanced list item detection using text and positioning."""
        # Use the existing list detection logic but with position awareness
        basic_detection = self._detect_list_item(text)
        
        if basic_detection:
            # Enhance with positioning information if available
            x_pos = block.get('x', 0)
            
            # Use x-position to determine indentation level more accurately
            if x_pos > 0:
                # Assume every 36 points (0.5 inch) is an indent level
                position_level = max(0, int(x_pos // 36))
                # Use the more reliable of the two methods
                level = max(basic_detection['level'], position_level)
                basic_detection['level'] = level
                
        return basic_detection
    
    def _is_table_row_advanced(self, text: str, block: dict[str, Any]) -> bool:
        """Enhanced table row detection using positioning and content."""
        # Use existing basic detection
        basic_table = self._is_table_row(text)
        
        # TODO: Add position-based table detection
        # This could analyze alignment patterns and spacing
        
        return basic_table
    
    def _extract_text_blocks_enhanced_heuristics(self, page) -> list[dict[str, Any]]:
        """Extract text blocks with enhanced heuristics (PyPDF fallback method)."""
        text_blocks = []
        
        try:
            # Enhanced text extraction for PyPDF
            full_text = page.extract_text()
            
            # Split into paragraphs more intelligently
            # Look for paragraph breaks (double newlines, section breaks)
            paragraphs = re.split(r'\n\s*\n|\n(?=\s*[A-Z][^.]*:)|\n(?=\s*\d+\.)', full_text)
            
            for paragraph in paragraphs:
                lines = paragraph.strip().split('\n')
                current_paragraph = []
                
                for line in lines:
                    line = line.strip()
                    if line:
                        # Group lines that likely belong together
                        if (current_paragraph and 
                            not self._looks_like_new_section(line) and
                            len(line) > 10 and 
                            not line.endswith(':')):
                            # Likely continuation of previous line
                            current_paragraph.append(line)
                        else:
                            # Process previous paragraph if any
                            if current_paragraph:
                                combined_text = ' '.join(current_paragraph)
                                font_size = self._estimate_font_size(combined_text)
                                text_blocks.append({
                                    'text': combined_text,
                                    'font_size': font_size,
                                    'x': 0,
                                    'y': 0
                                })
                            
                            # Start new paragraph
                            current_paragraph = [line]
                
                # Don't forget the last paragraph
                if current_paragraph:
                    combined_text = ' '.join(current_paragraph)
                    font_size = self._estimate_font_size(combined_text)
                    text_blocks.append({
                        'text': combined_text,
                        'font_size': font_size,
                        'x': 0,
                        'y': 0
                    })
                    
        except Exception:
            # Ultimate fallback
            text_blocks.append({
                'text': page.extract_text() or "",
                'font_size': 12,
                'x': 0,
                'y': 0
            })
            
        return text_blocks
    
    def _looks_like_new_section(self, text: str) -> bool:
        """Determine if a line looks like the start of a new section."""
        text = text.strip()
        
        # Check for common section indicators
        section_indicators = [
            text.isupper() and len(text) < 50,  # All caps headings
            text.endswith(':') and len(text) < 50,  # Headings ending with colon
            re.match(r'^\d+\.\d*\s', text),  # Numbered sections like "1.1 "
            re.match(r'^[A-Z]\w*\s+\w+', text) and len(text) < 50,  # Title case short lines
            text.startswith(('Chapter', 'Section', 'Part', 'Appendix')),  # Explicit sections
        ]
        
        return any(section_indicators)
    
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