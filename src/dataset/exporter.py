"""ZIP export functionality for evaluation dataset."""
import io
import json
import zipfile

from src.dataset.models import EvaluationData


def export_dataset_to_zip(data: EvaluationData) -> io.BytesIO:
    """Export evaluation data to a ZIP file compliant with 数据集提交指南.md.

    The ZIP file contains:
    - evaluation_data.json: UTF-8 encoded JSON with all test cases
    - attachments/: Empty directory (required by spec)

    The source_document and source_chunk_id fields are excluded from the
    exported JSON as they are internal metadata for traceability only.

    Args:
        data: EvaluationData object containing test cases to export

    Returns:
        io.BytesIO: ZIP file as in-memory bytes buffer
    """
    # Create in-memory buffer for ZIP
    buffer = io.BytesIO()

    # Create ZIP file with ZIP_STORED (no compression - faster for JSON)
    with zipfile.ZipFile(buffer, mode='w', compression=zipfile.ZIP_STORED) as zf:
        # Export evaluation_data.json with Chinese character preservation
        # Use model_dump() which respects exclude=True on source_document/source_chunk_id
        json_data = data.model_dump()

        # Convert to JSON string with UTF-8 encoding and Chinese preservation
        json_content = json.dumps(
            json_data,
            ensure_ascii=False,
            indent=2
        )

        # Write evaluation_data.json to ZIP
        zf.writestr('evaluation_data.json', json_content.encode('utf-8'))

        # Create empty attachments/ directory (required by spec)
        # Add a placeholder file to ensure the directory is included
        zf.writestr('attachments/', b'')

    # Seek to beginning of buffer for reading
    buffer.seek(0)

    return buffer
