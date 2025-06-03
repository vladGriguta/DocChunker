from typing import Any
import docx
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P

class DocxParser:
    """Parses DOCX to a hierarchical structure of elements."""

    def __init__(self):
        self.current_heading_level = 0

    def parse(self, file_path: str) -> list[dict[str, Any]]:
        """Parse DOCX and return a hierarchical list of element dictionaries."""
        doc = docx.Document(file_path)
        flat_elements = []
        self.current_heading_level = 0

        for element in doc.element.body:
            if isinstance(element, CT_P):
                para = self._find_paragraph(doc, element)
                if para and para.text.strip():
                    processed_para_element = self._process_paragraph(para)
                    flat_elements.append(processed_para_element)
            
            elif isinstance(element, CT_Tbl):
                table = self._find_table(doc, element)
                if table:
                    processed_table_element = self._process_table(table)
                    flat_elements.append(processed_table_element)

        hierarchical_elements = self._reconstruct_hierarchy(flat_elements)
        return hierarchical_elements
    
    def _reconstruct_hierarchy(self, flat_elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Reconstructs a hierarchical structure from a flat list of elements.
        Each node in the output will have a 'children' key.
        """
        root_nodes: list[dict[str, Any]] = []
        # Stack stores references to parent nodes that can have children.
        # Each item on the stack is a dictionary representing a node already in the tree.
        parent_stack: list[dict[str, Any]] = []

        for element_data in flat_elements:
            # Create the node for the current element, adding a 'children' list
            node = {**element_data, 'children': []}

            if node['type'] == 'heading':
                # Pop from stack if current heading is shallower or same level as stack top,
                # or if stack top is a list (headings close lists).
                while parent_stack and \
                      ((parent_stack[-1]['type'] == 'heading' and parent_stack[-1]['level'] >= node['level']) or \
                       (parent_stack[-1]['type'] in ['list_container', 'list_item'])):
                    parent_stack.pop()

                if not parent_stack:
                    root_nodes.append(node)
                else:
                    parent_stack[-1]['children'].append(node)
                parent_stack.append(node) # This heading becomes the new current parent

            elif node['type'] == 'list_item':
                li_level = node['level']  # This is the ilvl
                li_num_id = node['num_id']

                # Adjust stack to find appropriate parent for this list item or its container.
                # We need to find a heading, or a list_container/list_item of the same num_id.
                while parent_stack:
                    p_on_stack = parent_stack[-1]
                    if p_on_stack['type'] == 'list_container':
                        if p_on_stack['num_id'] == li_num_id:
                            if p_on_stack['level'] == li_level: break  # Correct container for this item
                            elif p_on_stack['level'] < li_level: break # Item is for a new nested list under this container's scope
                            else: parent_stack.pop() # Item is for a shallower list container (or different list)
                        else: parent_stack.pop() # Different list (num_id mismatch)
                    elif p_on_stack['type'] == 'list_item': # A list_item can parent a list_container for a nested list
                        if p_on_stack['num_id'] == li_num_id and li_level > p_on_stack['level']: break # Current item is nested under this list_item
                        else: parent_stack.pop() # Not a valid parent for nesting or belongs to different list
                    elif p_on_stack['type'] == 'heading': break # List will be child of this heading
                    else: # e.g. paragraph, should not be parent of list item/container
                        parent_stack.pop()

                current_parent_on_stack = parent_stack[-1] if parent_stack else None

                # Case 1: Add item to existing list_container of the same num_id and level (ilvl)
                if current_parent_on_stack and \
                   current_parent_on_stack['type'] == 'list_container' and \
                   current_parent_on_stack['num_id'] == li_num_id and \
                   current_parent_on_stack['level'] == li_level:
                    current_parent_on_stack['children'].append(node)
                    # list_item can be a parent for a nested list_container, so push it
                    parent_stack.append(node)
                # Case 2: Need to create a new list_container
                else:
                    # This new container will hold items of level 'li_level' and num_id 'li_num_id'
                    list_container_node = {
                        'type': 'list_container',
                        'level': li_level,
                        'num_id': li_num_id,
                        'children': [node] # Add current list_item as its first child
                    }

                    if not current_parent_on_stack: # No valid parent on stack, container is a root node
                        root_nodes.append(list_container_node)
                    else:
                        # If parent_on_stack is a list_item, new container is child of that list_item (nested list)
                        # Otherwise, child of current_parent_on_stack (e.g. heading)
                        current_parent_on_stack['children'].append(list_container_node)

                    parent_stack.append(list_container_node) # Push the new list_container
                    parent_stack.append(node)                # Push the list_item itself (can parent further nesting)

            elif node['type'] in ['paragraph', 'table']:
                # Paragraphs and tables close list_item and list_container contexts they are not part of.
                while parent_stack and parent_stack[-1]['type'] in ['list_item', 'list_container']:
                    parent_stack.pop()
                
                if not parent_stack:
                    root_nodes.append(node)
                else:
                    parent_stack[-1]['children'].append(node)
                # Paragraphs and tables are considered leaf nodes in terms of parenting further block elements,
                # so they are not pushed to parent_stack.

        return root_nodes

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
        """Process a table into an element dictionary with type, content (raw text), and level."""
        cell_texts = []
        for row in table.rows:
            for cell in row.cells:
                cell_para_texts = [p.text.strip() for p in cell.paragraphs if p.text.strip()]
                if cell_para_texts:
                    cell_texts.append(" ".join(cell_para_texts))
        
        table_content = "\n---\n".join(cell_texts)

        return {
            "type": "table",
            "level": self.current_heading_level if self.current_heading_level > 0 else 0,
            "rows": len(table.rows),
            "cols": len(table.columns),
            "content": table_content
        }