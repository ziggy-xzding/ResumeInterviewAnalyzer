from abc import ABC, abstractmethod
from typing import Any, Optional, List, Dict


class BaseVDBConnection(ABC):
    """
    向量数据库连接抽象基类
    所有向量数据库连接类都需要继承此类并实现相应方法
    """

    @property
    @abstractmethod
    def client(self):
        pass

    @abstractmethod
    def has_collection(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        pass

    @abstractmethod
    def create_collection(
            self,
            collection_name: str,
            schema: Any,
            description: Optional[str] = None,
            index_params: Optional[List[Dict]] = None
    ):
        """创建集合"""
        pass

    @abstractmethod
    def insert(self, collection_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """插入数据"""
        pass

    @abstractmethod
    def search(
            self,
            collection_name: str,
            data: Any,
            search_params: Optional[dict] = None,
            anns_field: Optional[str] = None,
            limit: int = 5,
            filter_expr: str = "",
            output_fields: List[str] = None
    ) -> List:
        """向量搜索"""
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def delete(self, collection_name: str, filter: str) -> Dict[str, Any]:
        """删除数据"""
        pass

    @abstractmethod
    def upsert(self, collection_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upsert（更新或插入）"""
        pass

    @abstractmethod
    def describe_collection(self, collection_name: str) -> Dict[str, Any]:
        """描述集合结构"""
        pass

    @abstractmethod
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
        pass


