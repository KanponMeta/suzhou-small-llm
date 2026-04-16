"""Q&A pair generation engine for evaluation dataset."""
import json
import uuid
import logging
from typing import List, Optional
from collections import defaultdict

from pydantic import BaseModel

from langchain_qwq import ChatQwen
from langchain_core.messages import HumanMessage

from src.dataset.models import TestCase, EvaluationData
from src.config import settings
from src.vectorstore import get_vectorstore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Grounding instruction constant
GROUNDING_INSTRUCTION = "仅基于以下文档内容生成问答对，不要使用任何外部知识。"


class QAGenerationPrompt:
    """Prompt template for Q&A generation from document chunks."""

    @staticmethod
    def build(chunk_text: str, num_pairs: int = 3) -> str:
        """Build the prompt for Q&A generation.

        Args:
            chunk_text: The document chunk content to generate Q&A from
            num_pairs: Number of Q&A pairs to generate (default: 3)

        Returns:
            Formatted prompt string
        """
        return f"""你是一个专业的评测数据集生成助手。请仅基于以下文档内容生成高质量的中文问答对。

{GROUNDING_INSTRUCTION}
严格要求：
1. 问题和答案必须完全基于提供的文档内容，禁止使用任何外部知识
2. 答案必须可以从文档中直接找到或推导出来
3. 问题应该多样化，覆盖文档中的不同知识点
4. 每个问答对的答案应该完整、准确

文档内容：
{chunk_text}

请生成 {num_pairs} 个问答对，以 JSON 数组格式输出：
[
  {{"user_prompt": "问题内容", "correct_answer": "基于文档的准确答案"}}
]

仅输出 JSON 数组，不要添加其他说明文字。"""


_DASHSCOPE_CN_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def get_llm() -> ChatQwen:
    """Get ChatQwen LLM instance configured for qwen-long model.

    Returns:
        Configured ChatQwen instance for long-document processing
    """
    return ChatQwen(
        model="qwen-long",
        api_key=settings.DASHSCOPE_API_KEY,
        api_base=_DASHSCOPE_CN_BASE,
    )


def parse_llm_response(response_content: str) -> List[dict]:
    """Parse LLM response content into list of Q&A dictionaries.

    Args:
        response_content: Raw string response from LLM

    Returns:
        List of dictionaries with user_prompt and correct_answer keys
    """
    try:
        # Try to parse as JSON
        data = json.loads(response_content)

        # Handle different response formats
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # If it's a dict, check for common wrapper keys
            if "test_cases" in data:
                return data["test_cases"]
            elif "qa_pairs" in data:
                return data["qa_pairs"]
            elif "pairs" in data:
                return data["pairs"]

        logger.warning(f"Unexpected LLM response format: {type(data)}")
        return []

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}")
        # Try to extract JSON array from response
        try:
            start = response_content.find('[')
            end = response_content.rfind(']') + 1
            if start >= 0 and end > start:
                data = json.loads(response_content[start:end])
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []


def generate_qa_from_chunks(
    chunks: List[str],
    source_name: str,
    category: str
) -> List[TestCase]:
    """Generate Q&A pairs from document chunks.

    This function takes a list of document chunk texts and generates
    evaluation Q&A pairs using the ChatQwen model. Each chunk is processed
    individually to generate 2-3 Q&A pairs grounded in that chunk's content.

    Args:
        chunks: List of document chunk text strings
        source_name: Source document name (e.g., "企业规章制度.pdf")
        category: Category derived from document content

    Returns:
        List of TestCase objects with generated Q&A pairs
    """
    test_cases: List[TestCase] = []

    # Skip chunks that are too short
    MIN_CHUNK_LENGTH = 50

    llm = get_llm()

    for i, chunk in enumerate(chunks):
        # Skip chunks that are too short
        if len(chunk.strip()) < MIN_CHUNK_LENGTH:
            logger.info(f"Skipping chunk {i} - insufficient content (< {MIN_CHUNK_LENGTH} chars)")
            continue

        try:
            # Build prompt with grounding instruction
            prompt = QAGenerationPrompt.build(chunk, num_pairs=3)

            # Call LLM
            response = llm.invoke([HumanMessage(content=prompt)])

            # Parse response
            qa_pairs = parse_llm_response(response.content)

            # Create TestCase objects
            for qa in qa_pairs:
                if "user_prompt" not in qa or "correct_answer" not in qa:
                    logger.warning(f"Skipping invalid Q&A pair: {qa}")
                    continue

                tc = TestCase(
                    id=f"qa_{uuid.uuid4().hex[:8]}",
                    task_type="chat:text",
                    category=category,
                    user_prompt=qa["user_prompt"],
                    answer_type="free_form",
                    options=None,
                    correct_answer=qa["correct_answer"],
                    source_document=source_name,
                    source_chunk_id=f"chunk_{i}"
                )
                test_cases.append(tc)

        except Exception as e:
            logger.error(f"Error generating Q&A from chunk {i}: {e}")
            continue

    return test_cases


def generate_qa_pairs(vectorstore) -> EvaluationData:
    """Generate Q&A pairs from all documents in the vector store.

    This function retrieves all document chunks from the ChromaDB vector store,
    groups them by source document, and generates Q&A pairs for each document.

    Args:
        vectorstore: ChromaDB vector store instance (langchain_chroma.Chroma)

    Returns:
        EvaluationData containing all generated test cases
    """
    # Retrieve all documents from the collection
    try:
        result = vectorstore._collection.get()
    except AttributeError:
        # Fallback for different ChromaDB API
        result = vectorstore.get(limit=10000)

    ids = result.get("ids", [])
    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])

    if not documents:
        logger.warning("No documents found in vector store")
        return EvaluationData(test_cases=[])

    # Group chunks by source document
    chunks_by_source: dict[str, List[str]] = defaultdict(list)
    chunk_sources: dict[int, str] = {}  # index -> source

    for i, doc in enumerate(documents):
        if i < len(metadatas) and metadatas[i]:
            source = metadatas[i].get("source", f"document_{i}")
        else:
            source = f"document_{i}"

        chunks_by_source[source].append(doc)
        chunk_sources[i] = source

    logger.info(f"Found {len(chunks_by_source)} source documents")

    # Generate Q&A for each source document
    all_test_cases: List[TestCase] = []

    for source_name, chunks in chunks_by_source.items():
        # Derive category from source filename
        category = source_name
        if category.endswith('.pdf'):
            category = category[:-4]
        elif category.endswith('.docx'):
            category = category[:-5]
        elif category.endswith('.md'):
            category = category[:-3]

        # Generate Q&A pairs
        test_cases = generate_qa_from_chunks(chunks, source_name, category)
        all_test_cases.extend(test_cases)

        logger.info(f"Generated {len(test_cases)} Q&A pairs from {source_name}")

    return EvaluationData(test_cases=all_test_cases)
