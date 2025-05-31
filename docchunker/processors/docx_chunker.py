import re
from typing import Any

from docchunker.models.chunk import Chunk


class TaggedChunker:
    """Step 2: Convert tagged elements to chunks"""
    
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
    
    def chunk(self, elements: list[dict[str, Any]], document_id: str) -> list[Chunk]:
        """Convert tagged elements to chunks"""
        chunks = []
        current_context = []  # Track heading hierarchy
        
        for element in elements:
            element_type = element['type']
            content = element['content']
            
            # Update context for headings
            if element_type == 'heading':
                level = element['level']
                # Remove deeper headings from context
                current_context = [h for h in current_context if h['level'] < level]
                # Add current heading
                current_context.append({
                    'level': level, 
                    'text': self._extract_text(content)
                })
            
            # Create chunk metadata
            metadata = {
                'type': element_type,
                'document_id': document_id,
                'context': current_context.copy(),
                'size': len(content)
            }
            
            # Add type-specific metadata
            if element_type == 'heading':
                metadata['level'] = element['level']
            elif element_type == 'table':
                metadata['rows'] = element.get('rows', 0)
                metadata['cols'] = element.get('cols', 0)
            
            # Create chunk
            chunk = Chunk(text=content, metadata=metadata)
            
            # Split if too large
            if len(content) > self.chunk_size:
                chunks.extend(self._split_large_chunk(chunk))
            else:
                chunks.append(chunk)
        
        return chunks
    
    def _extract_text(self, tagged_content: str) -> str:
        """Extract plain text from tagged content"""
        return re.sub(r'<[^>]+>', '', tagged_content).strip()
    
    def _split_large_chunk(self, chunk: Chunk) -> list[Chunk]:
        """Split large chunks while preserving context"""
        content = chunk.text
        
        # For tables, split by rows
        if '<TableRow>' in content:
            return self._split_table_chunk(chunk)
        
        # For lists, split by items  
        elif '<ListItem>' in content:
            return self._split_list_chunk(chunk)
        
        # For paragraphs, split by sentences
        else:
            return self._split_text_chunk(chunk)
    
    def _split_table_chunk(self, chunk: Chunk) -> list[Chunk]:
        """Split table by rows"""
        rows = re.findall(r'<TableRow>.*?</TableRow>', chunk.text, re.DOTALL)
        
        chunks = []
        current_rows = []
        current_size = len('<Table></Table>')
        
        for row in rows:
            if current_size + len(row) > self.chunk_size and current_rows:
                table_content = '<Table>' + ''.join(current_rows) + '</Table>'
                new_metadata = chunk.metadata.copy()
                new_metadata['size'] = len(table_content)
                new_metadata['partial_table'] = True
                
                chunks.append(Chunk(text=table_content, metadata=new_metadata))
                current_rows = [row]
                current_size = len('<Table></Table>') + len(row)
            else:
                current_rows.append(row)
                current_size += len(row)
        
        if current_rows:
            table_content = '<Table>' + ''.join(current_rows) + '</Table>'
            new_metadata = chunk.metadata.copy()
            new_metadata['size'] = len(table_content)
            new_metadata['partial_table'] = True
            
            chunks.append(Chunk(text=table_content, metadata=new_metadata))
        
        return chunks
    
    def _split_list_chunk(self, chunk: Chunk) -> list[Chunk]:
        """Split list by items"""
        items = re.findall(r'<ListItem>.*?</ListItem>', chunk.text, re.DOTALL)
        
        chunks = []
        current_items = []
        current_size = 0
        
        for item in items:
            if current_size + len(item) > self.chunk_size and current_items:
                new_metadata = chunk.metadata.copy()
                new_metadata['size'] = current_size
                new_metadata['partial_list'] = True
                
                chunks.append(Chunk(
                    text=''.join(current_items),
                    metadata=new_metadata
                ))
                current_items = [item]
                current_size = len(item)
            else:
                current_items.append(item)
                current_size += len(item)
        
        if current_items:
            new_metadata = chunk.metadata.copy()
            new_metadata['size'] = current_size
            new_metadata['partial_list'] = True
            
            chunks.append(Chunk(
                text=''.join(current_items),
                metadata=new_metadata
            ))
        
        return chunks
    
    def _split_text_chunk(self, chunk: Chunk) -> list[Chunk]:
        """Split text by sentences"""
        text = self._extract_text(chunk.text)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_text = ""
        
        for sentence in sentences:
            if len(current_text) + len(sentence) > self.chunk_size and current_text:
                new_metadata = chunk.metadata.copy()
                new_metadata['size'] = len(current_text)
                new_metadata['partial_paragraph'] = True
                
                chunks.append(Chunk(
                    text=f"<Paragraph>{current_text.strip()}</Paragraph>",
                    metadata=new_metadata
                ))
                current_text = sentence
            else:
                current_text += " " + sentence if current_text else sentence
        
        if current_text:
            new_metadata = chunk.metadata.copy()
            new_metadata['size'] = len(current_text)
            new_metadata['partial_paragraph'] = True
            
            chunks.append(Chunk(
                text=f"<Paragraph>{current_text.strip()}</Paragraph>",
                metadata=new_metadata
            ))
        
        return chunks