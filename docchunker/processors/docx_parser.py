from typing import Any
import docx
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P

class DocxParser:
    def __init__(self):
        self.current_heading_level = 0 

    def parse(self, file_path: str) -> list[dict[str, Any]]:
        """Parse DOCX and return a flat list of element dictionaries."""
        doc = docx.Document(file_path)
        elements = []
        self.current_heading_level = 0

        for element in doc.element.body:
            if isinstance(element, CT_P):
                para = self._find_paragraph(doc, element)
                if para and para.text.strip():  # Process only if paragraph has non-whitespace text
                    processed_para_element = self._process_paragraph(para)
                    elements.append(processed_para_element)
            
            elif isinstance(element, CT_Tbl):
                table = self._find_table(doc, element)
                if table:
                    elements.append(self._process_table(table))
        
        return elements
    
    def _find_paragraph(self, doc, element):
        """Find paragraph object by XML element"""
        for para in doc.paragraphs:
            if para._element == element:
                return para
        return None
    
    def _find_table(self, doc, element):
        """Find table object by XML element"""
        for table in doc.tables:
            if table._element == element:
                return table
        return None

    def _process_paragraph(self, para) -> dict[str, Any]:
        """Process a paragraph into an element dictionary with type, content, level, and num_id for lists."""
        text = para.text.strip()
        
        # Heading
        if para.style.name.startswith('Heading'):
            level_str = para.style.name.replace('Heading', '').strip() or '1'
            heading_level = int(level_str)
            self.current_heading_level = heading_level  # Update current heading level
            return {
                "type": "heading",
                "level": heading_level,
                "content": text
            }

        # List item from oxml (most reliable)
        if para._p.pPr is not None and para._p.pPr.numPr is not None:
            num_pr = para._p.pPr.numPr
            # ilvl (indentation level) is 0-indexed
            ilvl = num_pr.ilvl.val if num_pr.ilvl is not None and num_pr.ilvl.val is not None else 0
            # numId references the numbering definition
            num_id = num_pr.numId.val if num_pr.numId is not None and num_pr.numId.val is not None else 0 
            
            return {
                "type": "list_item",
                "level": ilvl,  # Use ilvl as the 'level' for list items
                "content": text,
                "num_id": num_id
            }
        
        # Fallback: Style-based list detection
        style_name_lower = para.style.name.lower()
        if 'list' in style_name_lower or 'bullet' in style_name_lower or 'number' in style_name_lower:
            return {
                "type": "list_item",
                "level": 0,  # Default ilvl if unknown
                "content": text,
                "num_id": -1 # Indicate unknown num_id for fallback
            }

        # Fallback: Text-based list detection
        # Improved to check for dot after number for numbered lists
        if text.startswith(('- ', '• ', '* ')) or \
           (text.split('.', 1)[0].isdigit() and len(text.split('.', 1)[0]) < 3 and '.' in text):
            return {
                "type": "list_item",
                "level": 0,  # Default ilvl if unknown
                "content": text,
                "num_id": -1 # Indicate unknown num_id for fallback
            }

        # Paragraph
        return {
            "type": "paragraph",
            # Assign level based on the current heading context
            "level": self.current_heading_level if self.current_heading_level > 0 else 0,
            "content": text
        }
    
    def _process_table(self, table) -> dict[str, Any]:
        """Process a table into an element dictionary with type, content (raw text), and level."""
        cell_texts = []
        for row in table.rows:
            for cell in row.cells:
                # Concatenate text from all paragraphs within a cell
                cell_para_texts = [p.text.strip() for p in cell.paragraphs if p.text.strip()]
                if cell_para_texts:
                    cell_texts.append(" ".join(cell_para_texts))

        # For simplicity, table content is a single string of all cell texts joined
        table_content = "\n---\n".join(cell_texts)

        return {
            "type": "table",
            # Assign level based on the current heading context
            "level": self.current_heading_level if self.current_heading_level > 0 else 0,
            "rows": len(table.rows),
            "cols": len(table.columns),
            "content": table_content
        }