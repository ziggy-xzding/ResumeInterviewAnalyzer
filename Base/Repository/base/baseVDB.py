import logging
from abc import ABC
from typing import Optional, Dict, Any, List, Type, TypeVar, ClassVar, get_type_hints

from pydantic import BaseModel, ConfigDict
from pymilvus import CollectionSchema, FieldSchema, DataType, Function, FunctionType, AnnSearchRequest

from Base.Repository.base.baseVDBConnection import BaseVDBConnection
from Base.Repository.connections.milvusConnection import get_default_milvus_vdb_connection

logger = logging.getLogger(__name__)
T = TypeVar('T', bound='BaseVDBModel')


class VectorFieldInfo:
    """向量字段信息"""

    def __init__(
            self,
            field_name: str,
            vector_type: str,  # 'dense' or 'sparse'
            dim: Optional[int] = None,
            enable_index: bool = True,
            metric_type: str = "COSINE",
            index_type: str = "HNSW",
            index_params: Optional[Dict[str, Any]] = None
    ):
        self.field_name = field_name
        self.vector_type = vector_type
        self.dim = dim
        self.enable_index = enable_index
        self.metric_type = metric_type
        self.index_type = index_type
        self.index_params = index_params or {}


class BaseVDBModel(BaseModel, ABC):
    """
    向量数据库模型基类，继承自 Pydantic BaseModel 和 ABC

    特性：
    1. 自动根据子类字段生成 schema
        密集向量字段通过检查字段的 dim 属性识别，可能存在多个向量字段
        稀疏向量字段可选，需要指明对应映射的标量字段
        在Model实例化时检测是否存在对应表，不存在则自动创建表，用类字段标识是否已经有表，避免重复判断
    2. 支持基础增删改查

    Field 配置示例：
        # 主键字段
        id: int = Field(
            json_schema_extra={
                'is_primary': True,
                'auto_id': True
            }
        )

        # VARCHAR 字段（指定长度）
        title: str = Field(
            json_schema_extra={
                'max_length': 256
            }
        )

        # 带默认值和长度的 VARCHAR 字段
        content: str = Field(
            "默认值",
            json_schema_extra={
                'max_length': 65535
            }
        )

        # BM25 文本字段（用于生成稀疏向量）
        content: str = Field(
            json_schema_extra={
                'enable_match': True,
                'enable_analyzer': True,
                'max_length': 65535
            }
        )

        # 密集向量字段（通过 dim 属性声明）
        embedding: list[float] = Field(
            json_schema_extra={
                'dim': 768  # 指定向量维度
            }
        )

        # 稀疏向量字段（基于 BM25 文本字段生成）
        content_sparse: list[float] = Field(
            json_schema_extra={
                'is_sparse_vector': True,
                'bm25_source_field': 'content'
            }
        )
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        from_attributes=True,
        validate_assignment=False,  # 关闭赋值时的校验
        validate_default=False  # 关闭默认值的校验
    )

    # 类变量：集合名称别名（可选）
    collection_alias: ClassVar[Optional[str]] = None
    # 类变量：集合描述
    description: ClassVar[Optional[str]] = None
    # 类变量：是否在初始化时自动创建集合
    auto_create_collection: ClassVar[bool] = True

    # 类变量：向量字段配置（可选）
    # 格式：{field_name: {config_dict}}
    # config_dict: {'dim': int, 'metric_type': str, 'index_type': str, 'enable_index': bool}
    _vector_fields_config: ClassVar[Optional[Dict[str, Dict[str, Any]]]] = {
        'index_type': 'HNSW',
        'metric_type': 'COSINE',
        'params': {"M": 8, "efConstruction": 64}
    }

    # 类变量：稀疏向量字段配置（可选）
    # 格式：{field_name: {'bm25_text_field': str, 'metric_type': str}}
    _sparse_fields_config: ClassVar[Optional[Dict[str, Dict[str, Any]]]] = {
        'index_type': 'SPARSE_INVERTED_INDEX',
        'metric_type': 'BM25',
        'params': {
            "inverted_index_algo": "DAAT_MAXSCORE",
            "bm25_k1": 1.2,
            "bm25_b": 0.75
        }
    }

    # 类变量：BM25 函数配置（可选）
    _bm25_functions: ClassVar[Optional[List[Dict[str, str]]]] = None

    # 类变量：默认向量数据库连接（全局默认）
    _default_vdb_connection: ClassVar[Optional[BaseVDBConnection]] = get_default_milvus_vdb_connection()
    # 类变量：每个类可以有自己的连接
    _vdb_connection: ClassVar[Optional[BaseVDBConnection]] = get_default_milvus_vdb_connection()
    # 实例变量：实例级别的连接（优先级最高）
    _instance_vdb_connection: Optional[BaseVDBConnection] = get_default_milvus_vdb_connection()
    # 类变量：集合检查缓存（避免重复检查）
    _collection_checked: ClassVar[bool] = False

    def __init__(self, **data):
        """初始化模型实例，并在需要时自动创建集合"""
        super().__init__(**data)
        # 使用类方法调用，避免实例方法调用问题
        cls = self.__class__
        if cls.auto_create_collection and not cls._collection_checked:
            cls._check_and_create_collection()

    @classmethod
    def get_connection(cls) -> BaseVDBConnection:
        """
        获取数据库连接（优先级：实例级别 > 类级别 > 全局默认）
        """
        return cls._vdb_connection or cls._default_vdb_connection

    @classmethod
    def set_connection(cls, connection: BaseVDBConnection, is_global: bool = False):
        """
        设置数据库连接

        Args:
            connection: 数据库连接实例
            is_global: 是否设置为全局默认连接
        """
        if is_global:
            cls._default_vdb_connection = connection
        else:
            cls._vdb_connection = connection

    @classmethod
    def get_collection_name(cls) -> str:
        """
        获取集合名称（优先级：别名 > 类名）
        """
        return cls.collection_alias or cls.__name__

    @classmethod
    def _get_exclude_fields(cls) -> set:
        """
        获取需要排除的字段（如 auto_id=True 的 id 字段）

        Returns:
            Set[str]: 需要排除的字段集合
        """
        exclude_fields = set()

        # 检查 id 字段的 auto_id 配置
        id_field_info = cls.model_fields.get('id')
        if id_field_info and id_field_info.json_schema_extra:
            if isinstance(id_field_info.json_schema_extra, dict):
                if id_field_info.json_schema_extra.get('auto_id', False):
                    # auto_id=True 时，排除 id 字段
                    exclude_fields.add('id')

        for i in cls._detect_sparse_fields():
            exclude_fields.add(i)
        return exclude_fields

    @classmethod
    def _detect_vector_fields(cls) -> List[str]:
        """
        检测密集向量字段（通过字段属性 dim 检测）
        只包含非 ClassVar 和非以下划线开头的实例变量
        排除标记为稀疏向量的字段

        密集向量字段需要在 json_schema_extra 中指定 dim 维度：
        embedding: list[float] = Field(
            json_schema_extra={'dim': 768}
        )
        """
        type_hints = get_type_hints(cls)
        vector_fields = []

        # 获取类变量注解
        class_vars = []
        for field_name, field_type in type_hints.items():
            if hasattr(field_type, '__origin__') and field_type.__origin__ is ClassVar:
                class_vars.append(field_name)

        # 先识别出稀疏向量字段
        sparse_fields = set()
        for field_name in type_hints.keys():
            if field_name in class_vars or field_name.startswith('_'):
                continue
            field_info = cls.model_fields.get(field_name)
            if field_info and isinstance(field_info.json_schema_extra, dict):
                if field_info.json_schema_extra.get('is_sparse_vector'):
                    sparse_fields.add(field_name)
                    logger.debug(f"检测到稀疏向量字段: {field_name}")

        # 检测密集向量字段：检查 json_schema_extra 中是否有 dim 属性
        for field_name in type_hints.keys():
            # 过滤条件：
            # 1. 跳过 ClassVar 类型的变量
            # 2. 跳过以 '_' 开头的字段
            # 3. 跳过稀疏向量字段
            if (field_name in class_vars or
                    field_name.startswith('_') or
                    field_name in sparse_fields):
                continue

            field_info = cls.model_fields.get(field_name)
            if field_info and isinstance(field_info.json_schema_extra, dict):
                # 检查是否有 dim 属性，如果有则认为是密集向量字段
                if 'dim' in field_info.json_schema_extra:
                    vector_fields.append(field_name)
                    logger.debug(f"检测到密集向量字段: {field_name}")

        return vector_fields

    @classmethod
    def _detect_sparse_fields(cls) -> List[str]:
        """
        检测稀疏向量字段
        通过检查字段是否有特定的稀疏向量标记或通过配置
        只包含非 ClassVar 和非以下划线开头的实例变量
        """
        type_hints = get_type_hints(cls)
        sparse_fields = []

        # 获取类变量注解
        class_vars = []
        for field_name, field_type in type_hints.items():
            if hasattr(field_type, '__origin__') and field_type.__origin__ is ClassVar:
                class_vars.append(field_name)

        for field_name in type_hints.keys():
            # 过滤条件：
            # 1. 跳过 ClassVar 类型的变量
            # 2. 跳过以 '_' 开头的字段
            if field_name in class_vars or field_name.startswith('_'):
                continue

            field_info = cls.model_fields.get(field_name)
            if field_info and isinstance(field_info.json_schema_extra, dict):
                if field_info.json_schema_extra.get('is_sparse_vector'):
                    sparse_fields.append(field_name)
                    logger.debug(f"检测到稀疏向量字段: {field_name}")

        return sparse_fields

    @classmethod
    def _get_sparse_field_config(cls, sparse_field_name: str) -> Optional[Dict[str, Any]]:
        """
        获取稀疏向量字段的配置

        Args:
            sparse_field_name: 稀疏向量字段名

        Returns:
            配置字典，包含 bm25_source_field 等信息
        """
        field_info = cls.model_fields.get(sparse_field_name)
        if not field_info or not field_info.json_schema_extra:
            return None

        if isinstance(field_info.json_schema_extra, dict):
            return field_info.json_schema_extra

        return None

    @classmethod
    def _get_bm25_source_fields(cls) -> Dict[str, str]:
        """
        获取稀疏向量字段与其源字段的映射关系

        Returns:
            {sparse_field_name: source_field_name}
        """
        sparse_fields = cls._detect_sparse_fields()
        mapping = {}

        for sparse_field in sparse_fields:
            config = cls._get_sparse_field_config(sparse_field)
            if config and 'bm25_source_field' in config:
                mapping[sparse_field] = config['bm25_source_field']

        return mapping

    @classmethod
    def _create_schema(cls) -> CollectionSchema:
        """
        根据 Model 字段自动生成 Milvus Collection Schema
        只包含子类中声明的非 ClassVar 和非以下划线开头的实例变量
        """
        type_hints = get_type_hints(cls)
        vector_fields = cls._detect_vector_fields()
        sparse_fields = cls._detect_sparse_fields()

        fields = []
        bm25_functions = []

        # 获取类变量注解（ClassVar 类型）
        class_vars = []
        for field_name, field_type in type_hints.items():
            if hasattr(field_type, '__origin__') and field_type.__origin__ is ClassVar:
                class_vars.append(field_name)

        # 处理标量字段
        for field_name, field_type in type_hints.items():
            # 过滤条件：
            # 1. 跳过向量字段
            # 2. 跳过稀疏向量字段
            # 3. 跳过 ClassVar 类型的变量
            # 4. 跳过以 '_' 开头的字段（类变量、私有变量、静态变量）
            if (field_name in vector_fields or
                    field_name in sparse_fields or
                    field_name in class_vars or
                    field_name.startswith('_')):
                continue

            field_info = cls.model_fields.get(field_name)

            # 检查是否为主键字段
            is_primary = False
            auto_id = False
            max_length = 1024  # VARCHAR 默认值
            enable_match = False
            enable_analyzer = False

            if field_info and field_info.json_schema_extra:
                if isinstance(field_info.json_schema_extra, dict):
                    is_primary = field_info.json_schema_extra.get('is_primary', False)
                    auto_id = field_info.json_schema_extra.get('auto_id', False)
                    # 从 Field 的 json_schema_extra 中读取 max_length
                    if 'max_length' in field_info.json_schema_extra:
                        max_length = field_info.json_schema_extra['max_length']
                    # BM25 相关配置
                    enable_match = field_info.json_schema_extra.get('enable_match', False)
                    enable_analyzer = field_info.json_schema_extra.get('enable_analyzer', False)

            # 其他标量字段
            dtype = cls._get_dtype_from_type(field_type)

            # VARCHAR 字段需要设置 max_length
            if dtype == DataType.VARCHAR:
                # 如果启用了 match 和 analyzer，需要设置 enable_analyzer 和 enable_match
                # 注意：在 pymilvus 中，这些参数需要在创建 FieldSchema 时传入
                if enable_match and enable_analyzer:
                    field_schema = FieldSchema(
                        name=field_name,
                        dtype=dtype,
                        max_length=max_length,
                        is_primary=is_primary,
                        auto_id=auto_id,
                        enable_analyzer=enable_analyzer,
                        enable_match=enable_match
                    )
                else:
                    field_schema = FieldSchema(
                        name=field_name,
                        dtype=dtype,
                        max_length=max_length,
                        is_primary=is_primary,
                        auto_id=auto_id
                    )
                fields.append(field_schema)
            else:
                fields.append(FieldSchema(
                    name=field_name,
                    dtype=dtype,
                    is_primary=is_primary,
                    auto_id=auto_id
                ))

        # 检查是否有稀疏向量字段
        if sparse_fields:
            # 获取稀疏向量字段与其源字段的映射关系
            sparse_source_mapping = cls._get_bm25_source_fields()

            # 为每个稀疏向量字段创建 BM25 函数
            for sparse_field, source_field in sparse_source_mapping.items():
                if source_field in type_hints:
                    function_name = f"bm25_{sparse_field}"
                    bm25_function = Function(
                        name=function_name,
                        function_type=FunctionType.BM25,
                        input_field_names=[source_field],
                        output_field_names=[sparse_field]
                    )
                    bm25_functions.append(bm25_function)
                    logger.debug(f"创建 BM25 函数: {function_name} <- {source_field}")

            # 添加稀疏向量字段到 schema
            for sparse_field in sparse_fields:
                fields.append(FieldSchema(
                    name=sparse_field,
                    dtype=DataType.SPARSE_FLOAT_VECTOR,
                    is_function_output=True
                ))

            # 存储 BM25 函数配置
            cls._bm25_functions = bm25_functions

        # 处理密集向量字段
        for vector_field in vector_fields:
            # 从字段配置中获取维度，或使用默认值
            field_info = cls.model_fields.get(vector_field)
            dim = 128  # 默认维度
            if field_info and field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
                dim = field_info.json_schema_extra.get('dim', 128)

            fields.append(FieldSchema(
                name=vector_field,
                dtype=DataType.FLOAT_VECTOR,
                dim=dim
            ))

        # 创建 schema
        schema = CollectionSchema(
            fields=fields,
            description=cls.description or f"Collection for {cls.__name__}",
            functions=bm25_functions
        )

        return schema

    @classmethod
    def _get_dtype_from_type(cls, field_type: Type) -> DataType:
        """
        将 Python 类型映射到 Milvus 数据类型
        """
        if field_type == int:
            return DataType.INT64
        elif field_type == float:
            return DataType.FLOAT
        elif field_type == bool:
            return DataType.BOOL
        elif field_type == str:
            return DataType.VARCHAR
        else:
            return DataType.VARCHAR

    @classmethod
    def _check_and_create_collection(cls) -> bool:
        """
        检查集合是否存在，不存在则创建
        使用类变量避免重复检查

        Returns:
            bool: 是否创建了新集合
        """
        if cls._collection_checked:
            return False

        connection = cls.get_connection()
        if connection is None:
            logger.warning(f"No database connection set for {cls.__name__}")
            return False

        collection_name = cls.get_collection_name()

        if not connection.has_collection(collection_name):
            logger.info(f"Creating collection '{collection_name}' for {cls.__name__}")
            schema = cls._create_schema()

            # 生成索引参数
            index_params = []
            vector_fields = cls._detect_vector_fields()
            sparse_fields = cls._detect_sparse_fields()

            # 为每个向量字段创建索引
            for vector_field in vector_fields:
                index_config = cls._vector_fields_config.copy()
                index_params.append({
                    'field_name': vector_field,
                    'index_type': index_config['index_type'],
                    'metric_type': index_config['metric_type'],
                    'params': index_config['params']
                })

            # 为每个稀疏向量字段创建索引
            for sparse_field in sparse_fields:
                index_config = cls._sparse_fields_config.copy()
                index_params.append({
                    'field_name': sparse_field,
                    'index_type': index_config['index_type'],
                    'metric_type': index_config['metric_type'],
                    'params': index_config['params']
                })

            connection.create_collection(
                collection_name=collection_name,
                schema=schema,
                description=cls.description,
                index_params=index_params if index_params else None
            )
            logger.info(f"Collection '{collection_name}' created successfully")
        else:
            logger.debug(f"Collection '{collection_name}' already exists")

        cls._collection_checked = True
        return True

    def save(self) -> Dict[str, Any]:
        """
        保存当前实例到数据库

        Returns:
            Dict: 插入结果
        """
        connection = self.get_connection()
        if connection is None:
            raise RuntimeError("No database connection set")

        collection_name = self.get_collection_name()

        # 获取需要排除的字段
        exclude_fields = self._get_exclude_fields()

        # 将模型转换为字典，排除 None 值和需要排除的字段
        data_dict = self.model_dump(exclude=exclude_fields if exclude_fields else None, exclude_none=True)

        # 插入数据
        result = connection.insert(collection_name, [data_dict])
        return result

    @classmethod
    def batch_insert(cls, instances: List[T]) -> Dict[str, Any]:
        """
        批量插入实例

        Args:
            instances: 模型实例列表

        Returns:
            Dict: 插入结果
        """
        if not instances:
            return {'insert_count': 0}

        connection = cls.get_connection()
        if connection is None:
            raise RuntimeError("No database connection set")

        collection_name = cls.get_collection_name()

        # 获取需要排除的字段
        exclude_fields = cls._get_exclude_fields()

        # 批量转换为字典
        data_list = []
        for instance in instances:
            data_dict = instance.model_dump(exclude=exclude_fields if exclude_fields else None, exclude_none=True)
            # 额外过滤：移除空列表和空字符串（这些是默认值，不应写入数据库）
            data_dict = {k: v for k, v in data_dict.items() if v != [] and v != ""}
            data_list.append(data_dict)

        return connection.insert(collection_name, data_list)

    @classmethod
    def hybrid_search(
            cls,
            queries: List[Dict[str, Any]],
            limit: int = 5,
            ranker: Optional[Any] = None,
            filter_expr: str = "",
            output_fields: Optional[List[str]] = None,
            weights: Optional[List[float]] = None
    ) -> List[Dict[str, Any]]:
        """
        高易用性的混合检索函数（支持密集向量 + 稀疏向量混合搜索）
        
        Args:
            queries: 查询列表，每个查询包含以下字段：
                - data: 向量数据（密集向量）或查询文本（稀疏向量）
                - field: 对应的字段名
                - type: 向量类型 ('dense' 或 'sparse')
                - params: 搜索参数（可选）
                - limit: 该查询的返回结果数（可选，默认使用全局limit）
            limit: 总体返回结果数量
            ranker: 排序器，默认使用 RRFRanker
            filter_expr: 全局过滤表达式
            output_fields: 返回的字段列表
            weights: 各查询的权重列表，用于加权融合（可选）
            
        Returns:
            List[Dict[str, Any]]: 搜索结果列表
            
        Example:
            # 密集向量 + 稀疏向量混合搜索
            results = MyModel.hybrid_search([
                {
                    'data': [0.1, 0.2, 0.3, ...],  # 密集向量
                    'field': 'embedding',
                    'type': 'dense',
                    'params': {'metric_type': 'COSINE', 'params': {'nprobe': 10}}
                },
                {
                    'data': "机器学习",  # 查询文本
                    'field': 'content_sparse',
                    'type': 'sparse',
                    'params': {'metric_type': 'BM25'}
                }
            ], limit=10, weights=[0.7, 0.3])
        """
        connection = cls.get_connection()
        if connection is None:
            raise RuntimeError("No database connection set")

        collection_name = cls.get_collection_name()

        # 验证输入参数
        if not queries:
            raise ValueError("queries 参数不能为空")

        # 如果没有提供 ranker，使用默认的 RRFRanker
        if ranker is None:

            # 如果提供了权重，使用加权 ranker
            if weights and len(weights) == len(queries):
                ranker_params = {
                    "reranker": "weighted",  # 改为支持的 weighted
                    "k": 60,
                    "weights": weights
                }
            else:
                ranker_params = {
                    "reranker": "rrf",
                    "k": 60
                }

            ranker = Function(
                name="rrf",
                input_field_names=[],
                function_type=FunctionType.RERANK,
                params=ranker_params
            )

        # 构建 AnnSearchRequest 列表
        search_requests = []

        for i, query in enumerate(queries):
            # 验证必需字段
            required_fields = ['data', 'field', 'type']
            for field in required_fields:
                if field not in query:
                    raise ValueError(f"查询 {i} 缺少必需字段: {field}")

            data = query['data']
            field_name = query['field']
            vector_type = query['type'].lower()
            search_params = query.get('params', {})
            query_limit = query.get('limit', limit)

            # 根据向量类型构建不同的搜索请求
            if vector_type == 'dense':
                # 密集向量搜索
                if not search_params:
                    search_params = {
                        "metric_type": cls._vector_fields_config.get('metric_type', 'COSINE'),
                        "params": {"nprobe": 10}
                    }

                # 处理单个向量
                if data and isinstance(data[0], float):
                    data = [data]

                search_param = {
                    "data": data,
                    "anns_field": field_name,
                    "param": search_params,
                    "limit": query_limit
                }
                if filter_expr:
                    search_param["expr"] = filter_expr

                search_request = AnnSearchRequest(**search_param)

            elif vector_type == 'sparse':
                # 稀疏向量搜索（BM25）
                if not search_params:
                    search_params = {
                        "metric_type": "BM25",
                        "params": {}
                    }

                # 稀疏向量搜索使用文本数据
                if isinstance(data, list):
                    data = " ".join(data)  # 将关键词列表转换为文本

                search_param = {
                    "data": [data],  # 文本需要包装成列表
                    "anns_field": field_name,
                    "param": search_params,
                    "limit": query_limit
                }
                if filter_expr:
                    search_param["expr"] = filter_expr

                search_request = AnnSearchRequest(**search_param)
            else:
                raise ValueError(f"不支持的向量类型: {vector_type}，支持的类型: dense, sparse")

            search_requests.append(search_request)
            logger.debug(f"构建搜索请求 {i}: 字段={field_name}, 类型={vector_type}")

        # 执行混合搜索
        try:
            # 使用 client.hybrid_search 而不是 connection.hybrid_search
            results = connection.client.hybrid_search(
                collection_name=collection_name,
                reqs=search_requests,
                ranker=ranker,
                limit=limit,
                output_fields=output_fields
            )

            # 正确处理返回结果 - 遍历 SearchResult 和 Hits
            formatted_results = []
            for hits in results:  # 遍历每个查询的结果 (Hits 对象)
                for hit in hits:  # 遍历每个命中的实体
                    result_dict = {
                        'id': hit.id,
                        'distance': hit.distance,
                        'score': hit.score
                    }
                    # 添加输出字段
                    if output_fields:
                        for field in output_fields:
                            if field not in ['id', 'distance', 'score']:
                                result_dict[field] = hit.get(field)
                    formatted_results.append(result_dict)

            logger.info(f"混合搜索完成，返回 {len(formatted_results)} 条结果")

            # 打印前三条数据的 distance 和 id
            if formatted_results and len(formatted_results) > 0:
                logger.info("前三条搜索结果:")
                for i, result in enumerate(formatted_results[:3]):
                    distance = result.get('distance', 'N/A')
                    score = result.get('score', 'N/A')
                    id_value = result.get('id', 'N/A')
                    logger.info(f"  [{i + 1}] ID: {id_value}, Distance: {distance}, Score: {score}")

            return formatted_results

        except Exception as e:
            logger.error(f"混合搜索执行失败: {e}")
            raise

    @classmethod
    def search(cls,
               data: list[float],
               anns_field: str = None,
               limit: int = 10,
               search_params: dict = None,
               output_fields: list[str] = None
               ):
        if anns_field is None:
            anns_field = cls._detect_vector_fields()[0]
        return cls.get_connection().search(
            collection_name=cls.get_collection_name(),
            data=[data],
            anns_field=anns_field,
            search_params=search_params or {"metric_type": "COSINE"},
            limit=limit,
            output_fields=output_fields or ["*"]
        )

    @classmethod
    def query(
            cls,
            filter: str = "",
            output_fields: Optional[List[str]] = None,
            limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        标量查询

        Args:
            filter: 过滤表达式
            output_fields: 返回的字段列表
            limit: 返回结果数量限制

        Returns:
            List: 查询结果列表
        """
        connection = cls.get_connection()
        if connection is None:
            raise RuntimeError("No database connection set")

        collection_name = cls.get_collection_name()

        return connection.query(
            collection_name=collection_name,
            filter=filter,
            output_fields=output_fields,
            limit=limit
        )

    @classmethod
    def find_by(
            cls,
            filter: str = "",
            output_fields: Optional[List[str]] = None,
            limit: Optional[int] = None
    ) -> List[T]:
        """
        根据条件查找并返回模型实例列表

        Args:
            filter: 过滤表达式
            output_fields: 返回的字段列表
            limit: 返回结果数量限制

        Returns:
            List[T]: 模型实例列表
        """
        connection = cls.get_connection()
        if connection is None:
            raise RuntimeError("No database connection set")

        collection_name = cls.get_collection_name()

        results = connection.query(
            collection_name=collection_name,
            filter=filter,
            output_fields=output_fields,
            limit=limit
        )

        # 将查询结果转换为模型实例
        return [cls(**item) for item in results]

    @classmethod
    def count(cls, filter: str = "") -> int:
        """
        统计记录数量

        Args:
            filter: 过滤表达式

        Returns:
            int: 记录数量
        """
        connection = cls.get_connection()
        if connection is None:
            raise RuntimeError("No database connection set")

        collection_name = cls.get_collection_name()

        # 通过查询来统计数量
        results = connection.query(
            collection_name=collection_name,
            filter=filter,
            output_fields=[],
            limit=None
        )

        return len(results)

    @classmethod
    def delete(cls, filter: str) -> Dict[str, Any]:
        """
        删除数据

        Args:
            filter: 过滤表达式

        Returns:
            Dict: 删除结果
        """
        connection = cls.get_connection()
        if connection is None:
            raise RuntimeError("No database connection set")

        collection_name = cls.get_collection_name()

        return connection.delete(collection_name, filter)

    @classmethod
    def upsert(cls, instances: List[T]) -> Dict[str, Any]:
        """
        Upsert（更新或插入）数据

        Args:
            instances: 模型实例列表

        Returns:
            Dict: Upsert 结果
        """
        if not instances:
            return {'upsert_count': 0}

        connection = cls.get_connection()
        if connection is None:
            raise RuntimeError("No database connection set")

        collection_name = cls.get_collection_name()

        # 获取需要排除的字段
        exclude_fields = cls._get_exclude_fields()

        data_list = [
            instance.model_dump(exclude=exclude_fields if exclude_fields else None, exclude_none=True)
            for instance in instances
        ]

        return connection.upsert(collection_name, data_list)
