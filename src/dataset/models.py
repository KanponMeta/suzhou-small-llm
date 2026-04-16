"""Pydantic models for evaluation dataset schema."""
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict


class TestCase(BaseModel):
    """A single evaluation Q&A test case per 数据集提交指南.md spec.

    This model represents a single test case in the evaluation dataset.
    Fields marked with exclude=True are used internally for traceability
    but are not included in the exported JSON.
    """
    id: str = Field(..., description="Unique identifier for the test case")
    task_type: Literal["chat:text"] = Field(
        default="chat:text",
        description="Task type — always chat:text for this project"
    )
    category: str = Field(..., description="Category derived from document content/topic")
    user_prompt: str = Field(..., description="The question to ask the model")
    answer_type: Literal["free_form"] = Field(
        default="free_form",
        description="Answer type — always free_form for this project"
    )
    options: Optional[Dict[str, str]] = Field(
        default=None,
        description="Not used for free_form type"
    )
    correct_answer: str = Field(..., description="Ground-truth answer derived from document chunk")

    # Metadata (not serialized to evaluation_data.json, used internally for traceability)
    source_document: Optional[str] = Field(
        default=None,
        exclude=True,
        description="Source document filename for traceability"
    )
    source_chunk_id: Optional[str] = Field(
        default=None,
        exclude=True,
        description="ChromaDB chunk ID for traceability"
    )


class EvaluationData(BaseModel):
    """Top-level structure for evaluation_data.json per 数据集提交指南.md spec.

    This is the container for all test cases in an evaluation dataset.
    The JSON export uses 'test_cases' as the key per the specification.
    """
    test_cases: list[TestCase] = Field(..., description="List of evaluation test cases")
