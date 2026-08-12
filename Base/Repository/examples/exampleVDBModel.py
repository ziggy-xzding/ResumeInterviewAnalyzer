from typing import Optional, ClassVar

from pydantic import Field

from Base.Repository.base.baseVDB import BaseVDBModel

if __name__ == "__main__":
    """
    测试示例：继承 BaseVDBModel 并创建集合、执行基本操作
    """
    import sys
    import os

    # 添加项目根目录到 Python 路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    from Base.Repository.connections.milvusConnection import MilvusVDBConnection


    # 定义测试模型
    class TestDocument(BaseVDBModel):
        """测试文档模型 - 支持密集向量和稀疏向量"""

        # 子类自己声明 id 字段作为主键
        id: Optional[int] = Field(
            default=0,  # auto_id 时提供默认值，避免校验失败
            json_schema_extra={
                'is_primary': True,
                'auto_id': True
            }
        )

        # VARCHAR 字段，在 Field 中配置 max_length
        title: Optional[str] = Field(
            default="",  # 提供默认值
            json_schema_extra={
                'max_length': 256
            }
        )

        # BM25 文本字段（用于生成稀疏向量）
        content: Optional[str] = Field(
            default="",  # 提供默认值
            json_schema_extra={
                'enable_match': True,
                'enable_analyzer': True,
                'max_length': 65535
            }
        )

        author: Optional[str] = Field(
            "default_author",  # 默认值
            json_schema_extra={
                'max_length': 128
            }
        )
        tags: Optional[list[str]] = Field(
            default=[],  # 默认值
            json_schema_extra={
                'max_length': 1024
            }
        )

        # 稀疏向量字段（基于 BM25 文本字段生成）
        content_sparse: Optional[list[float]] = Field(
            default=[],  # 提供默认值
            json_schema_extra={
                'is_sparse_vector': True,
                'bm25_source_field': 'content'
            }
        )

        # 密集向量字段
        embedding: Optional[list[float]] = Field(
            default=[],
            json_schema_extra={
                'dim': 1024
            }
        )

        # 类变量配置（这些不应该被包含在 schema 中）
        collection_alias = "test_documents"
        description = "测试文档集合"
        auto_create_collection = True
        _vdb_connection = MilvusVDBConnection()

        # 私有变量（这些不应该被包含在 schema 中）
        _private_field: ClassVar[str] = "private"
        _another_private = "test"

        # 向量字段配置（以下划线开头，不应包含在 schema 中）
        _vector_fields_config = {
            'index_type': 'HNSW',
            'metric_type': 'COSINE',
            'params': {"M": 8, "efConstruction": 64}
        }


    TestDocument()
