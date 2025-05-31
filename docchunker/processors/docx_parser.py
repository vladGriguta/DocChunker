from typing import Any
import docx
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P

class DocxParser:
    """Step 1: Parse DOCX to tagged elements"""
    
    def parse(self, file_path: str) -> list[dict[str, Any]]:
        """Parse DOCX and return tagged elements"""
        doc = docx.Document(file_path)
        elements = []

        for element in doc.element.body:
            if isinstance(element, CT_P):
                para = self._find_paragraph(doc, element)
                if para and para.text.strip():
                    elements.append(self._process_paragraph(para))
            
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
    

    def _process_paragraph(self, para):
        """Process a paragraph into tagged format"""
        text = para.text.strip()
        
        if para.style.name.startswith('Heading'):
            level = para.style.name.replace('Heading', '').strip() or '1'
            return {
                "type": "heading",
                "level": int(level),
                "content": f"<Heading level=\"{level}\">{text}</Heading>"
            }

        # Check for list item via oxml numPr (numbering properties)
        # para._p is the underlying CT_P element
        is_list_item_from_oxml = False
        if para._p.pPr is not None and para._p.pPr.numPr is not None:
            is_list_item_from_oxml = True
            # You could potentially extract list level (ilvl) and numbering id (numId) here
            # list_level = para._p.pPr.numPr.ilvl.val if para._p.pPr.numPr.ilvl is not None else 0
            # num_id = para._p.pPr.numPr.numId.val if para._p.pPr.numPr.numId is not None else 0
            
        if is_list_item_from_oxml:
            return {
                "type": "list_item", 
                "content": f"<ListItem>{text}</ListItem>" # Consider adding level/num_id if needed
            }
        
        # Fallback: Simple list detection based on style name (less reliable but can catch some cases)
        style_name_lower = para.style.name.lower()
        if 'list' in style_name_lower or 'bullet' in style_name_lower or 'number' in style_name_lower:
            return {
                "type": "list_item",
                "content": f"<ListItem>{text}</ListItem>"
            }

        # Fallback: Text-based list detection (least reliable)
        elif text.startswith(('- ', '• ', '* ')) or (text.split('.')[0].isdigit() and len(text.split('.')[0]) < 3):
            return {
                "type": "list_item", 
                "content": f"<ListItem>{text}</ListItem>"
            }

        else:
            return {
                "type": "paragraph",
                "content": f"<Paragraph>{text}</Paragraph>"
            }
    
    def _process_table(self, table):
        """Process a table into tagged format"""
        rows = []
        for row in table.rows:
            cells = []
            for cell in row.cells:
                # Handle nested content in cells
                cell_content = []
                for para in cell.paragraphs:
                    if para.text.strip():
                        if para.text.strip().startswith(('- ', '• ', '* ')):
                            cell_content.append(f"<ListItem>{para.text.strip()}</ListItem>")
                        else:
                            cell_content.append(f"<Paragraph>{para.text.strip()}</Paragraph>")
                
                cells.append("<Cell>" + "".join(cell_content) + "</Cell>")
            
            rows.append("<TableRow>" + "".join(cells) + "</TableRow>")
        
        return {
            "type": "table",
            "rows": len(table.rows),
            "cols": len(table.columns),
            "content": "<Table>" + "".join(rows) + "</Table>"
        }