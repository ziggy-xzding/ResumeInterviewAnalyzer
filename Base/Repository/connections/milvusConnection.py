import logging
from typing import Any, Dict, List, Optional

from pymilvus import RRFRanker, AnnSearchRequest

from Base.Repository.base.baseVDBConnection import BaseVDBConnection
from Base.Client.milvusClient import MilvusClientSingleton

logger = logging.getLogger(__name__)


class MilvusVDBConnection(BaseVDBConnection):
    """
    Milvus 向量数据库连接适配器
    实现 BaseVDBConnection 接口，使 MilvusClient 可以用于 BaseVDBModel
    """

    def __init__(self, client: Optional[Any] = None):
        """
        初始化 Milvus 连接
        
        Args:
            client: MilvusClient 实例，如果为 None 则使用默认的单例
        """
        self._client = client or MilvusClientSingleton()


    @property
    def client(self):
        """获取底层 MilvusClient 实例"""
        return self._client.get_client()

    def has_collection(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        return self.client.has_collection(collection_name)

    def create_collection(
        self,
        collection_name: str,
        schema: Any,
        description: Optional[str] = None,
        index_params: Optional[List[Dict]] = None
    ):
        """创建集合"""
        self._client.create_collection(
            collection_name=collection_name,
            schema=schema,
            description=description,
            index_params=index_params
        )
        logger.info(f"✅ 集合 '{collection_name}' 创建成功")

    def insert(
        self,
        collection_name: str,
        data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """插入数据"""
        return self._client.insert(collection_name=collection_name, data=data)

    def search(
        self,
        collection_name: str,
        data: Any,
        search_params: Optional[dict] = None,
        anns_field: Optional[str] = None,
        limit: int = 5,
        filter_expr: str = "",
        output_fields: Optional[List[str]] = None
    ) -> List:
        """向量搜索"""
        return self._client.search(
            collection_name=collection_name,
            data=data,
            search_params=search_params,
            anns_field=anns_field,
            limit=limit,
            filter_expr=filter_expr,
            output_fields=output_fields
        )

    def query(
        self,
        collection_name: str,
        filter: str = "",
        output_fields: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        ids: Optional[Any] = None,
        partition_names: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ):
        """标量查询"""
        return self._client.query(
            collection_name=collection_name,
            filter=filter,
            output_fields=output_fields,
            timeout=timeout,
            ids=ids,
            partition_names=partition_names,
            limit=limit
        )

    def delete(
        self,
        collection_name: str,
        filter: str
    ) -> Dict[str, Any]:
        """删除数据"""
        return self._client.delete(collection_name=collection_name, filter=filter)

    def upsert(
        self,
        collection_name: str,
        data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Upsert（更新或插入）"""
        return self._client.upsert(collection_name=collection_name, data=data)

    def describe_collection(self, collection_name: str) -> Dict[str, Any]:
        """描述集合结构"""
        return self.client.describe_collection(collection_name)

    def hybrid_search(
            self,
            collection_name: str,
            reqs: List[Any],
            limit: int = 5,
            ranker: Optional[Any] = None,
            filter: str = "",
            output_fields: List[str] = None
    ) -> List:
        """混合检索（密集向量 + 稀疏向量）"""
        # 如果没有提供 ranker，使用默认的 RRFRanker
        if ranker is None:
            ranker = RRFRanker()

        return self.client.hybrid_search(
            collection_name=collection_name,
            reqs=reqs,
            ranker=ranker,
            limit=limit,
            filter=filter,
            output_fields=output_fields
        )


    def change_or_create_database(self, db_name: str):
        """更改或创建数据库"""
        self._client.change_or_create_database(db_name)

    def using_database(self, db_name: str):
        """切换到指定数据库"""
        self._client._client.using_database(db_name)
        logger.info(f"🔁 已切换到数据库: {db_name}")


def get_default_milvus_vdb_connection() -> BaseVDBConnection:
    """获取默认的 MilvusVDBConnection 实例"""
    return MilvusVDBConnection()

if __name__ == "__main__":
    # =========================
    # 测试 MilvusVDBConnection
    # =========================
    print("=== 测试 MilvusVDBConnection ===")

    # 创建连接
    vdb_connection = MilvusVDBConnection()

    # 测试基本操作
    try:
        # 切换到测试数据库
        db_name = "test_db"
        vdb_connection.change_or_create_database(db_name)

        # 检查集合是否存在
        collection_name = "test_collection"
        has_collection = vdb_connection.has_collection(collection_name)
        print(f"集合 '{collection_name}' 是否存在: {has_collection}")

        # 查询集合信息（如果存在）
        if has_collection:
            collection_info = vdb_connection.describe_collection(collection_name)
            print(f"集合信息: {collection_info}")

        print("✅ MilvusVDBConnection 测试通过")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
