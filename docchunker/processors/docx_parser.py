from typing import Any, Union, BinaryIO
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
import docx.document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P

class DocxParser:
    """Parses DOCX to a hierarchical structure of elements."""

    def __init__(self):
        self.current_heading_level = 0

    def apply(self, file_input: Union[str, BinaryIO]) -> list[dict[str, Any]]:
        """Parse DOCX and return a hierarchical list of element dictionaries.
        
        Args:
            file_input: Either a file path (str) or a file-like object (BinaryIO)
        """
        doc = docx.Document(file_input)
        self.current_heading_level = 0

        hierarchical_elements = self._parse_content_elements(doc)
        return hierarchical_elements
    
    def _parse_content_elements(self, document_object: docx.document.Document) -> list[dict[str, Any]]:
        """Parses a sequence of XML elements and reconstructs them into a hierarchical list."""
        root_nodes: list[dict[str, Any]] = []
        parent_stack: list[dict[str, Any]] = []
        xml_element_iterator = document_object.element.body.iterchildren()
        for element in xml_element_iterator:
            element_data: dict[str, Any] | None = None
            if isinstance(element, CT_P):
                para = self._find_paragraph(document_object, element)
                if para and para.text and para.text.strip():
                    element_data = self._process_paragraph(para)
            elif isinstance(element, CT_Tbl):
                table = self._find_table(document_object, element)
                if table:
                    element_data = self._process_table(table)
            else:
                print(f"Skipping unsupported element type: {type(element)}")
                continue

            if not element_data:
                continue

            # Create the node for the current element, adding a 'children' list
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
                            if p_on_stack['level'] == li_level: break
                            elif p_on_stack['level'] < li_level: break
                            else: parent_stack.pop()
                        else: parent_stack.pop()
                    elif p_on_stack['type'] == 'list_item':
                        if p_on_stack['num_id'] == li_num_id and li_level > p_on_stack['level']: break
                        else: parent_stack.pop()
                    elif p_on_stack['type'] == 'heading': break
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

    def _find_paragraph(self, doc: docx.document.Document, element: CT_P) -> Paragraph:
        """Find paragraph object by XML element"""
        for para in doc.paragraphs:
            if para._element == element:
                return para
        raise ValueError("Paragraph not found")

    def _find_table(self, doc: docx.document.Document, element: CT_Tbl) -> Table:
        """Find table object by XML element"""
        for table in doc.tables:
            if table._element == element:
                return table
        raise ValueError("Table not found")

    def _process_paragraph(self, para: Paragraph) -> dict[str, Any]:
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
            "level": self.current_heading_level if self.current_heading_level > 0 else 0,
            "content": text
        }

    def _process_table(self, table) -> dict[str, Any]:
        """
        Process a table into an element dictionary.
        The first row is assumed to be the header.
        Subsequent rows are stored individually.
        """
        header_cells: list[str] = []
        data_rows_content: list[list[str]] = []

        if table.rows:
            first_row_cells = table.rows[0].cells
            for cell in first_row_cells:
                cell_para_texts = [p.text.strip() for p in cell.paragraphs if p.text.strip()]
                header_cells.append(" ".join(cell_para_texts))

            # Process subsequent rows as data rows
            for i in range(1, len(table.rows)):
                row = table.rows[i]
                current_row_cells_text: list[str] = []
                for cell in row.cells:
                    cell_para_texts = [p.text.strip() for p in cell.paragraphs if p.text.strip()]
                    current_row_cells_text.append(" ".join(cell_para_texts))
                if any(current_row_cells_text): # Add row only if it has some content
                    data_rows_content.append(current_row_cells_text)

        # The 'content' field is removed in favor of structured header/rows.
        # If a single string representation is still needed elsewhere, 
        # it would need to be constructed by the consumer of this structure.
        return {
            "type": "table",
            "level": self.current_heading_level if self.current_heading_level > 0 else 0,
            "num_rows": len(table.rows), # Total rows including potential header
            "num_cols": len(table.columns) if table.columns else 0,
            "header": header_cells,
            "data_rows": data_rows_content # List of lists, where each inner list contains cell strings for a data row
        }
