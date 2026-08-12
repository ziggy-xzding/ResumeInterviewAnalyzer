# milvus_client.py
import logging
from typing import List, Dict, Any, Optional, Union

from pymilvus import CollectionSchema, FieldSchema, DataType, MilvusClient, Function, FunctionType

from Base.Config.setting import settings

logger = logging.getLogger(__name__)


class MilvusClientSingleton:
    """
    MilvusClient 封装类（基于 pymilvus.MilvusClient）
    支持单例、数据库管理、集合操作、增删改查封装
    使用方式参考：https://milvus.io/docs/zh/manage_databases.md
    """

    _instance = None
    _client: MilvusClient = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MilvusClientSingleton, cls).__new__(cls)
            cls._instance._initialize()
            logger.info("✅ MilvusVDBConnection 初始单例实例化成功")
        return cls._instance

    def _initialize(self):
        """初始化连接（只执行一次）"""
        if self._client is not None:
            return

        # 从 settings 获取 Milvus 配置
        milvus_settings = settings.milvus

        # 优先使用 URI，否则根据 host 和 port 构建
        if milvus_settings.uri:
            uri = milvus_settings.uri
        else:
            host = milvus_settings.host or "localhost"
            port = milvus_settings.port or 19530
            protocol = "https" if milvus_settings.secure else "http"
            uri = f"{protocol}://{host}:{port}"

        # 如果有用户名和密码，构建 token
        if milvus_settings.user and milvus_settings.password:
            token = f"{milvus_settings.user}:{milvus_settings.password}"
        else:
            token = None

        db_name = milvus_settings.database or "default"

        try:
            self._client = MilvusClient(
                uri=uri,
                token=token,
                db_name=db_name  # 自动切换到指定数据库
            )
            logger.info(f"✅ MilvusClient 成功连接 | URI: {uri} | DB: {db_name}")
        except Exception as e:
            logger.error(f"❌ 连接 Milvus 失败: {e}")
            raise

    def get_client(self):
        """返回底层的 MilvusClient 实例"""
        return self._client

    def change_or_create_database(self, db_name: str):
        """更改或创建数据库，不存在则创建"""
        if db_name not in self._client.list_databases():
            self._client.create_database(db_name)
            logger.info(f"✅ 数据库 '{db_name}' 已创建")

        # 切换到该数据库（后续操作都在此库）
        self._client.using_database(db_name)
        logger.info(f"🔁 已切换到数据库: {db_name}")

    @staticmethod
    def get_default_collection_schema(dim: int = None) -> Any:
        """
        获取默认集合 Schema（示例：id + 向量字段 + 文本字段 + 稀疏向量字段）
        默认 text 字段为核心文本字段
        :param dim 向量字段的维度，如果为 None 则使用 settings 中的默认维度
        """
        # 使用 settings 中的默认向量维度
        if dim is None:
            dim = settings.milvus.vector_dim or 768

        default_fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65500, enable_match=True, enable_analyzer=True),
            FieldSchema(name="sparse", dtype=DataType.SPARSE_FLOAT_VECTOR),
        ]
        _schema = CollectionSchema(default_fields, description="向量检索集合")
        # 定义BM25函数 基于 【input_field_names】 字段 进行BM25函数 稀疏向量化
        bm25_function = Function(
            name="text_bm25_emb",
            input_field_names=["text"],
            output_field_names=["sparse"],
            function_type=FunctionType.BM25,
        )
        _schema.add_function(bm25_function)
        return _schema

    def create_collection(
            self,
            collection_name: str,
            schema: Any,
            index_params: Optional[Union[Dict, List[Dict]]] = None,
            sparse_index_params=None,
            description: Optional[str] = None,
            index_filed: str = None,
            sparse_filed: str = None
    ):
        """
        如果集合不存在，则创建并建立索引
        默认索引字段 embedding 必然创建向量索引,
        默认稀疏索引字段 sparse 不存在该字段并且不设置自定义稀疏字段，则不会创建稀疏向量索引
        
        支持两种方式：
        1. 新方式：传入 index_params 列表（自动创建所有索引）
        2. 旧方式：传入单独的 index_params 和 sparse_index_params
        
        :param collection_name 表名
        :param schema: 字段信息
        :param index_params: 索引参数（可以是 Dict 或 List[Dict]）
        :param sparse_index_params: 稀疏索引参数（旧方式，兼容性）
        :param description:  表描述
        :param index_filed:  自定义索引字段,不想传index_params 使用默认params但是字段名变了
        :param sparse_filed:   自定义稀疏向量索引字段
        """
        if not self._client.has_collection(collection_name):
            self._client.create_collection(
                collection_name=collection_name,
                schema=schema,
                description=description
            )
            logger.info(f"✅ 集合 '{collection_name}' 已创建")

            # 判断使用新方式还是旧方式
            if isinstance(index_params, list):
                # 新方式：传入 index_params 列表
                self._create_index_list(collection_name=collection_name, index_params_list=index_params)
            else:
                # 旧方式：传入单独的参数（保持兼容性）
                self.create_index_optimized(
                    collection_name=collection_name,
                    index_params=index_params,
                    sparse_index_params=sparse_index_params,
                    index_filed=index_filed,
                    sparse_filed=sparse_filed
                )

        # 确保集合已加载（用于搜索）
        if not self._client.get_load_state(collection_name=collection_name).get("state") == "Loaded":
            self._client.load_collection(collection_name=collection_name)
            logger.info(f"📥 集合 '{collection_name}' 已加载到内存")

    def _create_index_list(self, collection_name: str, index_params_list: List[Dict[str, Any]]):
        """
        根据索引参数列表批量创建索引
        :param collection_name: 集合名称
        :param index_params_list: 索引参数列表
        """
        for index_config in index_params_list:
            field_name = index_config.get('field_name')
            index_type = index_config.get('index_type', 'HNSW')
            metric_type = index_config.get('metric_type', 'COSINE')
            params = index_config.get('params', {})
            
            # 准备索引参数
            prepared_index_params = self._client.prepare_index_params()
            prepared_index_params.add_index(
                field_name=field_name,
                index_type=index_type,
                metric_type=metric_type,
                params=params
            )
            
            # 创建索引
            self._client.create_index(
                collection_name=collection_name,
                index_params=prepared_index_params
            )
            
            # 记录日志
            if index_type.startswith('SPARSE'):
                logger.info(f"✅ {collection_name} 表的稀疏向量索引 '{field_name}' 已创建")
            else:
                logger.info(f"✅ {collection_name} 表的向量索引 '{field_name}' 已创建")

    def create_index_optimized(self,
                               collection_name: str,
                               index_params=None,
                               sparse_index_params=None,
                               index_filed: str = None,
                               sparse_filed: str = None):
        """
        创建索引
        :param collection_name:  表名
        :param index_params: 索引参数
        :param sparse_index_params: 稀疏向量字段索引
        :param index_filed: 索引字段
        :param sparse_filed: 稀疏向量字段

        :return:
        """
        if index_params is None:
            index_params = self._get_default_index_params(field_name=index_filed)

        # 创建索引
        self._client.create_index(
            collection_name=collection_name,
            index_params=index_params
        )
        logger.info(f"✅ {collection_name}表的向量索引已创建")

        if (bool(not sparse_index_params and self._check_sparse_exists(collection_name=collection_name))
                or bool(sparse_filed)):
            sparse_index_params = self._get_default_sparse_index_params(field_name=sparse_filed)

        if sparse_index_params:
            self._client.create_index(
                collection_name=collection_name,
                index_params=sparse_index_params
            )
            logger.info(f"✅ {collection_name}表的稀疏向量索引已创建")

    def _get_default_index_params(self, field_name: str = None):
        """
        获取默认向量字段的默认索引参数
        :return:
        """
        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name=field_name or 'embedding',
            index_type="HNSW",
            metric_type="COSINE",
            index_name="vector_index",
            params={"M": 8, "efConstruction": 64}
        )
        return index_params

    def _get_default_sparse_index_params(self, field_name: str = None):
        """
        获取默认稀疏向量字段的默认索引参数
        :return:
        """
        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name=field_name or "sparse",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="BM25",
            params={
                "inverted_index_algo": "DAAT_MAXSCORE",
                "bm25_k1": 1.2,
                "bm25_b": 0.75
            }
        )
        return index_params

    def _check_sparse_exists(self, collection_name: str) -> bool:
        """检查集合是否存在稀疏向量字段，如果集合不存在则返回 False"""
        if not self._client.has_collection(collection_name):
            return False
        fields = self.get_client().describe_collection(collection_name=collection_name)['fields']
        return any((item['name'] == 'sparse' and item['type'] == DataType.SPARSE_FLOAT_VECTOR) for item in fields)


    def insert(self, collection_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """插入数据"""
        try:
            self._client.insert(collection_name=collection_name, data=data)
            logger.info(f"✅ 成功插入 {len(data)} 条数据到集合: {collection_name}")
            return {"success": True, "insert_count": len(data)}
        except Exception as e:
            logger.error(f"❌ 插入失败: {e}")
            return {"success": False, "error": str(e)}

    def search(
            self,
            collection_name: str,
            data: Union[List[list], list] = None,
            search_params: Optional[dict] = None,
            anns_field: Optional[str] = None,
            limit: int = 5,
            filter_expr: str = "",
            output_fields: List[str] = None
    ) -> List:
        """
        向量检索
        :param collection_name: 表名
        :param data: 待检索向量
        :param search_params: 检索参数
        :param anns_field: 向量库表向量字段
        :param limit: 返回限制数
        :param filter_expr: 标量检索条件
        :param output_fields: 输出字段
        :return:
        """
        try:
            results = self._client.search(
                collection_name=collection_name,
                data=data,
                anns_field=anns_field,
                limit=limit,
                filter=filter_expr,
                output_fields=output_fields,
                search_params=search_params
            )
            return results
        except Exception as e:
            logger.error(f"❌ 向量检索失败: {e}")
            return []


    def query(self,
              collection_name: str,
              filter: str = "",
              output_fields: Optional[List[str]] = None,
              timeout: Optional[float] = None,
              ids: Optional[Union[List, str, int]] = None,
              partition_names: Optional[List[str]] = None,
              limit: Optional[int] = None,
              ):
        """
        标量检索
        :param collection_name: 表名
        :param filter:  检索条件
        :param output_fields:  输出字段
        :param timeout:  超时时间 秒
        :param ids:  id集
        :param partition_names: 分区名称
        :param limit: 返回结果数量限制
        :return:
        """
        try:
            return self._client.query(collection_name=collection_name,
                                      filter=filter,
                                      output_fields=output_fields,
                                      timeout=timeout,
                                      ids=ids,
                                      partition_names=partition_names,
                                      limit=limit)
        except Exception as e:
            logger.error(f"❌ 标量检索失败: {e}")
            return []


    def delete(self, collection_name: str, filter: str) -> Dict[str, Any]:
        """删除数据（支持表达式）"""
        try:
            result = self._client.delete(collection_name=collection_name, ids=[], filter=filter)
            logger.info(f"✅ 删除 {result['delete_count']} 条数据")
            return {"success": True, "delete_count": result["delete_count"]}
        except Exception as e:
            logger.error(f"❌ 删除失败: {e}")
            return {"success": False, "error": str(e)}

    def upsert(self, collection_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upsert（更新或插入）"""
        try:
            result = self._client.upsert(collection_name=collection_name, data=data)
            logger.info(f"✅ Upsert {result['upsert_count']} 条数据")
            return {"success": True, "upsert_count": result["upsert_count"]}
        except Exception as e:
            logger.error(f"❌ Upsert 失败: {e}")
            return {"success": False, "error": str(e)}

    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            logger.info("🔌 MilvusClient 已关闭")


if __name__ == "__main__":
    # =========================
    # 测试示例 1: 检查集合中是否存在稀疏向量字段
    # =========================
    print("=== 测试 1: 检查稀疏向量字段 ===")
    try:
        client = MilvusClientSingleton()
        collection_name = 'file_slice'
        has_sparse = client._check_sparse_exists(collection_name=collection_name)
        if not client._client.has_collection(collection_name):
            print(f"⚠️ 集合 '{collection_name}' 不存在，跳过检查")
        else:
            print(f"✅ 集合 '{collection_name}' 中是否存在稀疏向量字段: {has_sparse}")
    except Exception as e:
        print(f"测试失败: {e}")

    # =========================
    # 测试示例 2: 创建集合并插入数据
    # =========================
    print("\n=== 测试 2: 创建集合并插入数据 ===")
    try:
        client = MilvusClientSingleton()

        # 切换到测试数据库
        db_name = "test_db"
        client.change_or_create_database(db_name)

        # 定义集合名称
        collection_name = "test_collection"

        # 获取默认 schema（使用 settings 中的默认向量维度）
        schema = client.get_default_collection_schema()

        # 创建集合
        client.create_collection(
            collection_name=collection_name,
            schema=schema,
            description="测试集合"
        )

        # 准备测试数据
        dim = settings.milvus.vector_dim or 768
        test_data = [
            {"text": "这是第一条测试数据", "embedding": [0.1] * dim},
            {"text": "这是第二条测试数据", "embedding": [0.2] * dim},
        ]

        # 插入数据
        result = client.insert(collection_name=collection_name, data=test_data)
        print(f"插入结果: {result}")

        # 查询数据
        query_results = client.query(
            collection_name=collection_name,
            filter="text in ['这是第一条测试数据', '这是第二条测试数据']",
            output_fields=["text"]
        )
        print(f"查询结果数量: {len(query_results)}")
        for res in query_results[:2]:  # 只打印前两条
            print(f"  - {res}")

    except Exception as e:
        print(f"测试失败: {e}")

    # =========================
    # 测试示例 3: 向量搜索
    # =========================
    print("\n=== 测试 3: 向量搜索 ===")
    try:
        client = MilvusClientSingleton()

        # 创建测试向量（768维）
        dim = settings.milvus.vector_dim or 768
        search_vector = [[0.1] * dim]

        # 执行搜索
        search_results = client.search(
            collection_name="test_collection",
            data=search_vector,
            anns_field="embedding",
            limit=3,
            output_fields=["text"]
        )

        print(f"搜索结果数量: {len(search_results[0])}")
        for res in search_results[0][:2]:  # 只打印前两条
            print(f"  - 距离: {res['distance']:.4f}, 文本: {res['entity']['text']}")

    except Exception as e:
        print(f"测试失败: {e}")





