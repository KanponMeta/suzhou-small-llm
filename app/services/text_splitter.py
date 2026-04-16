"""Chinese-aware text splitting service."""
from langchain_text_splitters import RecursiveCharacterTextSplitter


def get_text_splitter(
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> RecursiveCharacterTextSplitter:
    """Create a text splitter with Chinese-aware separators.

    Uses Chinese punctuation marks as primary separators,
    falling back to newlines and spaces.
    """
    return RecursiveCharacterTextSplitter(
        separators=[
            "\n\n",   # Paragraph breaks (highest priority)
            "\n",     # Line breaks
            "。",     # Chinese period
            "！",     # Chinese exclamation
            "？",     # Chinese question mark
            "；",     # Chinese semicolon
            "，",     # Chinese comma
            ". ",     # English period
            " ",      # Space
            "",       # Character-level fallback
        ],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )


def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list[str]:
    """Split text into chunks using Chinese-aware separators.

    Args:
        text: The full document text.
        chunk_size: Target size of each chunk in characters.
        chunk_overlap: Overlap between adjacent chunks.

    Returns:
        List of text chunks.
    """
    splitter = get_text_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text)
