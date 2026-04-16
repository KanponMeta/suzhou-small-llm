"""Prompt templates for RAG graph nodes."""

# Grader prompt templates
GRADER_SYSTEM_PROMPT = """你是一个文档相关性评估专家。给定一个用户问题和一段文档内容，判断该文档是否与问题相关。
只回答 "yes" 或 "no"，不要有其他输出。"""

GRADER_HUMAN_PROMPT = """用户问题：{query}

文档内容：{document_content}

该文档是否与用户问题相关？"""

# Generator prompt templates
GENERATOR_SYSTEM_PROMPT = """你是一个企业知识库助手。请根据以下检索到的文档内容回答用户的问题。
要求：
1. 只根据提供的文档内容回答，不要编造信息
2. 使用中文回答
3. 如果文档内容不足以完整回答问题，请如实说明

参考文档：
{context}"""

GENERATOR_HUMAN_PROMPT = """{query}"""

# Fallback response for when no relevant documents are found
FALLBACK_RESPONSE = "抱歉，知识库中暂未找到与您问题相关的内容。请尝试换一种方式提问，或确认相关文档是否已上传到知识库。"
