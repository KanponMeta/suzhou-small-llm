"""Tests for dataset exporter module."""
import io
import json
import zipfile

import pytest

from src.dataset.models import EvaluationData, TestCase
from src.dataset.exporter import export_dataset_to_zip


class TestExportDatasetToZip:
    """Test suite for export_dataset_to_zip function."""

    def test_export_creates_valid_zip(self):
        """Test that export creates a valid ZIP file."""
        # Arrange
        test_cases = [
            TestCase(
                id="test_001",
                task_type="chat:text",
                category="测试分类",
                user_prompt="测试问题",
                answer_type="free_form",
                correct_answer="测试答案"
            )
        ]
        data = EvaluationData(test_cases=test_cases)

        # Act
        result = export_dataset_to_zip(data)

        # Assert
        assert result is not None
        assert isinstance(result, io.BytesIO)

        # Verify it's a valid ZIP
        result.seek(0)
        with zipfile.ZipFile(result, mode='r') as zf:
            assert zipfile.is_zipfile(result)

    def test_export_contains_evaluation_data_json(self):
        """Test that ZIP contains evaluation_data.json file."""
        # Arrange
        test_cases = [
            TestCase(
                id="test_001",
                task_type="chat:text",
                category="测试",
                user_prompt="问题",
                answer_type="free_form",
                correct_answer="答案"
            )
        ]
        data = EvaluationData(test_cases=test_cases)

        # Act
        result = export_dataset_to_zip(data)

        # Assert
        result.seek(0)
        with zipfile.ZipFile(result, mode='r') as zf:
            assert 'evaluation_data.json' in zf.namelist()

    def test_export_contains_attachments_directory(self):
        """Test that ZIP contains attachments/ directory."""
        # Arrange
        test_cases = [
            TestCase(
                id="test_001",
                task_type="chat:text",
                category="测试",
                user_prompt="问题",
                answer_type="free_form",
                correct_answer="答案"
            )
        ]
        data = EvaluationData(test_cases=test_cases)

        # Act
        result = export_dataset_to_zip(data)

        # Assert
        result.seek(0)
        with zipfile.ZipFile(result, mode='r') as zf:
            assert 'attachments/' in zf.namelist()

    def test_export_excludes_source_metadata(self):
        """Test that source_document and source_chunk_id are excluded from export."""
        # Arrange
        test_cases = [
            TestCase(
                id="test_001",
                task_type="chat:text",
                category="测试",
                user_prompt="问题",
                answer_type="free_form",
                correct_answer="答案",
                source_document="test_document.pdf",
                source_chunk_id="chunk_0"
            )
        ]
        data = EvaluationData(test_cases=test_cases)

        # Act
        result = export_dataset_to_zip(data)

        # Assert
        result.seek(0)
        with zipfile.ZipFile(result, mode='r') as zf:
            json_content = zf.read('evaluation_data.json').decode('utf-8')
            json_data = json.loads(json_content)

            # Check that source_document and source_chunk_id are NOT in the output
            test_case = json_data['test_cases'][0]
            assert 'source_document' not in test_case
            assert 'source_chunk_id' not in test_case

    def test_export_preserves_chinese_characters(self):
        """Test that Chinese characters are preserved in export (ensure_ascii=False)."""
        # Arrange
        test_cases = [
            TestCase(
                id="test_001",
                task_type="chat:text",
                category="企业规章制度",
                user_prompt="请解释公司的年假政策是什么？",
                answer_type="free_form",
                correct_answer="根据公司规定，员工每年享有15天带薪年假。"
            )
        ]
        data = EvaluationData(test_cases=test_cases)

        # Act
        result = export_dataset_to_zip(data)

        # Assert
        result.seek(0)
        with zipfile.ZipFile(result, mode='r') as zf:
            json_content = zf.read('evaluation_data.json').decode('utf-8')

            # Verify Chinese characters are preserved (not escaped as \uXXXX)
            assert '企业规章制度' in json_content
            assert '请解释公司的年假政策是什么？' in json_content
            assert '根据公司规定，员工每年享有15天带薪年假。' in json_content

            # Verify not using unicode escapes
            assert '\\u' not in json_content

    def test_export_multiple_test_cases(self):
        """Test export with multiple test cases."""
        # Arrange
        test_cases = [
            TestCase(
                id="test_001",
                task_type="chat:text",
                category="分类A",
                user_prompt="问题1",
                answer_type="free_form",
                correct_answer="答案1"
            ),
            TestCase(
                id="test_002",
                task_type="chat:text",
                category="分类B",
                user_prompt="问题2",
                answer_type="free_form",
                correct_answer="答案2"
            ),
            TestCase(
                id="test_003",
                task_type="chat:text",
                category="分类C",
                user_prompt="问题3",
                answer_type="free_form",
                correct_answer="答案3"
            )
        ]
        data = EvaluationData(test_cases=test_cases)

        # Act
        result = export_dataset_to_zip(data)

        # Assert
        result.seek(0)
        with zipfile.ZipFile(result, mode='r') as zf:
            json_content = zf.read('evaluation_data.json').decode('utf-8')
            json_data = json.loads(json_content)

            assert len(json_data['test_cases']) == 3
            assert json_data['test_cases'][0]['id'] == 'test_001'
            assert json_data['test_cases'][1]['id'] == 'test_002'
            assert json_data['test_cases'][2]['id'] == 'test_003'

    def test_export_empty_evaluation_data(self):
        """Test export with empty test_cases list."""
        # Arrange
        data = EvaluationData(test_cases=[])

        # Act
        result = export_dataset_to_zip(data)

        # Assert
        result.seek(0)
        with zipfile.ZipFile(result, mode='r') as zf:
            json_content = zf.read('evaluation_data.json').decode('utf-8')
            json_data = json.loads(json_content)

            assert json_data['test_cases'] == []

    def test_export_json_structure_matches_spec(self):
        """Test that exported JSON structure matches 数据集提交指南.md spec."""
        # Arrange
        test_cases = [
            TestCase(
                id="chat_text_001",
                task_type="chat:text",
                category="通用问答",
                user_prompt="什么是人工智能？",
                answer_type="free_form",
                options=None,
                correct_answer="人工智能是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的一门新的技术科学。"
            )
        ]
        data = EvaluationData(test_cases=test_cases)

        # Act
        result = export_dataset_to_zip(data)

        # Assert
        result.seek(0)
        with zipfile.ZipFile(result, mode='r') as zf:
            json_content = zf.read('evaluation_data.json').decode('utf-8')
            json_data = json.loads(json_content)

            # Verify top-level key is 'test_cases'
            assert 'test_cases' in json_data

            # Verify test case structure
            tc = json_data['test_cases'][0]
            assert tc['id'] == 'chat_text_001'
            assert tc['task_type'] == 'chat:text'
            assert tc['category'] == '通用问答'
            assert tc['user_prompt'] == '什么是人工智能？'
            assert tc['answer_type'] == 'free_form'
            assert tc['options'] is None
            assert '人工智能' in tc['correct_answer']

            # Verify excluded fields are not present
            assert 'source_document' not in tc
            assert 'source_chunk_id' not in tc
