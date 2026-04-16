"""Tests for dataset generator models and Q&A pair generation."""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestTestCaseModel:
    """Test the TestCase Pydantic model."""

    def test_testcase_accepts_valid_chat_text_freeform_data(self):
        """Test 1: TestCase model accepts valid chat:text free_form data and serializes to JSON with all 7 fields present."""
        from src.dataset.models import TestCase

        tc = TestCase(
            id="chat_text_freeform_001",
            task_type="chat:text",
            category="通用问答",
            user_prompt="请简要解释什么是'人工智能'。",
            answer_type="free_form",
            options=None,
            correct_answer="人工智能（AI）是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的一门新的技术科学。"
        )

        dumped = tc.model_dump()
        # Should have exactly 7 keys after excluding source_document and source_chunk_id
        assert "id" in dumped
        assert "task_type" in dumped
        assert "category" in dumped
        assert "user_prompt" in dumped
        assert "answer_type" in dumped
        assert "options" in dumped
        assert "correct_answer" in dumped

    def test_testcase_rejects_missing_required_fields(self):
        """Test 2: TestCase model rejects missing required fields."""
        from src.dataset.models import TestCase
        from pydantic import ValidationError

        # Missing id
        with pytest.raises(ValidationError):
            TestCase(
                task_type="chat:text",
                category="测试",
                user_prompt="问题",
                answer_type="free_form",
                correct_answer="答案"
            )

    def test_testcase_enforces_task_type_literal(self):
        """Test 3: TestCase model enforces task_type literal value 'chat:text'."""
        from src.dataset.models import TestCase
        from pydantic import ValidationError

        # Invalid task_type should raise
        with pytest.raises(ValidationError):
            TestCase(
                id="test_001",
                task_type="invalid_type",
                category="测试",
                user_prompt="问题",
                answer_type="free_form",
                correct_answer="答案"
            )

    def test_testcase_enforces_answer_type_literal(self):
        """Test 4: TestCase model enforces answer_type literal value 'free_form'."""
        from src.dataset.models import TestCase
        from pydantic import ValidationError

        # Invalid answer_type should raise
        with pytest.raises(ValidationError):
            TestCase(
                id="test_001",
                task_type="chat:text",
                category="测试",
                user_prompt="问题",
                answer_type="invalid_type",
                correct_answer="答案"
            )

    def test_evaluation_data_model(self):
        """Test 5: EvaluationData model wraps a list of TestCase objects under test_cases key."""
        from src.dataset.models import TestCase, EvaluationData

        tc1 = TestCase(
            id="test_001",
            task_type="chat:text",
            category="测试",
            user_prompt="问题1",
            answer_type="free_form",
            correct_answer="答案1"
        )
        tc2 = TestCase(
            id="test_002",
            task_type="chat:text",
            category="测试",
            user_prompt="问题2",
            answer_type="free_form",
            correct_answer="答案2"
        )

        eval_data = EvaluationData(test_cases=[tc1, tc2])
        dumped = eval_data.model_dump()

        assert "test_cases" in dumped
        assert len(dumped["test_cases"]) == 2

    def test_testcase_model_dump_exact_keys(self):
        """Test 6: TestCase.model_dump() output matches exact JSON key names from 数据集提交指南.md."""
        from src.dataset.models import TestCase

        tc = TestCase(
            id="chat_text_freeform_001",
            task_type="chat:text",
            category="通用问答",
            user_prompt="请简要解释什么是'人工智能'。",
            answer_type="free_form",
            options=None,
            correct_answer="人工智能（AI）是研究、开发..."
        )

        dumped = tc.model_dump()

        # Should have exactly 7 keys, no source_document or source_chunk_id
        expected_keys = {"id", "task_type", "category", "user_prompt", "answer_type", "options", "correct_answer"}
        assert set(dumped.keys()) == expected_keys, f"Expected {expected_keys}, got {set(dumped.keys())}"

    def test_testcase_options_defaults_to_none(self):
        """Test 7: options field defaults to None, category field is required string."""
        from src.dataset.models import TestCase

        tc = TestCase(
            id="test_001",
            task_type="chat:text",
            category="测试",
            user_prompt="问题",
            answer_type="free_form",
            correct_answer="答案"
        )

        # options should default to None
        assert tc.options is None

        # category should be required
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            TestCase(
                id="test_002",
                task_type="chat:text",
                user_prompt="问题",
                answer_type="free_form",
                correct_answer="答案"
            )


class TestQAGeneration:
    """Test the Q&A pair generation functions."""

    @patch('src.dataset.generator.settings')
    @patch('src.dataset.generator.ChatQwen')
    def test_generate_qa_from_chunks_returns_testcases(self, mock_chatqwen, mock_settings):
        """Test 1: generate_qa_from_chunks() returns a list of TestCase objects."""
        from src.dataset.generator import generate_qa_from_chunks
        from src.dataset.models import TestCase

        # Mock settings
        mock_settings.DASHSCOPE_API_KEY = "test-key"

        # Mock the LLM response
        mock_llm_instance = MagicMock()
        mock_chatqwen.return_value = mock_llm_instance

        # Simulate LLM returning valid JSON
        mock_response = MagicMock()
        mock_response.content = json.dumps([
            {"user_prompt": "问题1", "correct_answer": "答案1来自文档内容"},
            {"user_prompt": "问题2", "correct_answer": "答案2来自文档内容"}
        ])
        mock_llm_instance.invoke.return_value = mock_response

        chunks = ["这是一个很长的文档内容段落，包含足够的信息来生成问答对。" * 10]
        source_name = "测试文档.pdf"
        category = "测试"

        result = generate_qa_from_chunks(chunks, source_name, category)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(tc, TestCase) for tc in result)

    @patch('src.dataset.generator.settings')
    @patch('src.dataset.generator.ChatQwen')
    def test_generate_qa_grounding_check(self, mock_chatqwen, mock_settings):
        """Test 2: Each returned TestCase has correct_answer with content from input chunk."""
        from src.dataset.generator import generate_qa_from_chunks

        # Mock settings
        mock_settings.DASHSCOPE_API_KEY = "test-key"

        # Mock the LLM response - include content from chunk in answer
        mock_llm_instance = MagicMock()
        mock_chatqwen.return_value = mock_llm_instance

        chunk_text = "人工智能是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的人工智能应用领域。" * 2

        mock_response = MagicMock()
        mock_response.content = json.dumps([
            {"user_prompt": "什么是人工智能？", "correct_answer": chunk_text}
        ])
        mock_llm_instance.invoke.return_value = mock_response

        chunks = [chunk_text]
        result = generate_qa_from_chunks(chunks, "test.pdf", "测试")

        # Verify at least one key phrase from chunk is in correct_answer
        assert any("人工智能" in tc.correct_answer for tc in result)

    @patch('src.dataset.generator.settings')
    @patch('src.dataset.generator.ChatQwen')
    def test_generate_qa_unique_ids(self, mock_chatqwen, mock_settings):
        """Test 3: generate_qa_from_chunks() assigns unique IDs to each TestCase."""
        from src.dataset.generator import generate_qa_from_chunks

        # Mock settings
        mock_settings.DASHSCOPE_API_KEY = "test-key"

        mock_llm_instance = MagicMock()
        mock_chatqwen.return_value = mock_llm_instance

        mock_response = MagicMock()
        mock_response.content = json.dumps([
            {"user_prompt": "问题1", "correct_answer": "答案1"},
            {"user_prompt": "问题2", "correct_answer": "答案2"},
            {"user_prompt": "问题3", "correct_answer": "答案3"}
        ])
        mock_llm_instance.invoke.return_value = mock_response

        chunks = ["文档内容" * 20]
        result = generate_qa_from_chunks(chunks, "test.pdf", "测试")

        ids = [tc.id for tc in result]
        assert len(ids) == len(set(ids)), "IDs should be unique"

    @patch('src.dataset.generator.settings')
    @patch('src.dataset.generator.ChatQwen')
    def test_generate_qa_category_populated(self, mock_chatqwen, mock_settings):
        """Test 4: category field is populated based on document source/content."""
        from src.dataset.generator import generate_qa_from_chunks

        # Mock settings
        mock_settings.DASHSCOPE_API_KEY = "test-key"

        mock_llm_instance = MagicMock()
        mock_chatqwen.return_value = mock_llm_instance

        mock_response = MagicMock()
        mock_response.content = json.dumps([
            {"user_prompt": "问题", "correct_answer": "答案"}
        ])
        mock_llm_instance.invoke.return_value = mock_response

        chunks = ["内容"]
        category = "企业规章制度"
        result = generate_qa_from_chunks(chunks, "规章制度.pdf", category)

        assert all(tc.category == category for tc in result)

    @patch('src.dataset.generator.get_vectorstore')
    @patch('src.dataset.generator.settings')
    @patch('src.dataset.generator.ChatQwen')
    def test_generate_qa_pairs_retrieves_from_chromadb(self, mock_chatqwen, mock_settings, mock_get_vectorstore):
        """Test 5: generate_qa_pairs() retrieves all chunks from ChromaDB and produces TestCases."""
        from src.dataset.generator import generate_qa_pairs
        from src.dataset.models import TestCase

        # Mock settings
        mock_settings.DASHSCOPE_API_KEY = "test-key"

        # Mock vectorstore
        mock_vs = MagicMock()
        mock_get_vectorstore.return_value = mock_vs

        # Mock collection get - returns documents with metadata
        mock_vs._collection.get.return_value = {
            "ids": ["chunk1", "chunk2"],
            "documents": ["文档内容A" * 50, "文档内容B" * 50],
            "metadatas": [{"source": "文档A.pdf"}, {"source": "文档B.pdf"}]
        }

        # Mock LLM
        mock_llm_instance = MagicMock()
        mock_chatqwen.return_value = mock_llm_instance
        mock_response = MagicMock()
        mock_response.content = json.dumps([
            {"user_prompt": "问题", "correct_answer": "答案"}
        ])
        mock_llm_instance.invoke.return_value = mock_response

        result = generate_qa_pairs(mock_vs)

        assert isinstance(result, object)
        assert hasattr(result, "test_cases")
        assert len(result.test_cases) > 0
        assert all(isinstance(tc, TestCase) for tc in result.test_cases)
