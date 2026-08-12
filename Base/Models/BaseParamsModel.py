from datetime import datetime
from typing import Optional, ClassVar, List
from functools import lru_cache

from pydantic import Field

from Base.Repository.models.moduleDbModel import BaseModuleDBModel
from Base.RicUtils.decoratorUtils import timing_log


class BaseParamsModel(BaseModuleDBModel):
    """
    系统参数模型
    """
    table_alias: ClassVar[str] = "base_sys_params"
    create_table_sql: ClassVar[str] = f"""
                       -- 系统参数表
                       CREATE TABLE {table_alias}
                       (
                           -- 核心字段
                           `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
                           `code`        VARCHAR(100) NOT NULL COMMENT '参数编码',
                           `value`       TEXT COMMENT '参数值',
                           `desc`        VARCHAR(500) COMMENT '参数描述',
                           `parent_code` VARCHAR(100)          DEFAULT NULL COMMENT '父级参数编码（用于分组/层级）',
                           `type`        VARCHAR(100)          DEFAULT NULL COMMENT '参数类型, Base模块 or 其他模块',

                           -- 状态与排序
                           `status`      TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '状态：0-禁用，1-启用',
                           `sort_order`  INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '排序序号（越小越靠前）',

                           -- 时间戳
                           `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                           `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

                           -- 操作人
                           `created_by`  BIGINT UNSIGNED COMMENT '创建人ID',
                           `updated_by`  BIGINT UNSIGNED COMMENT '更新人ID',

                           -- 主键
                           PRIMARY KEY (`id`),

                           -- 索引
                           UNIQUE KEY `uk_code` (`code`),
                           KEY           `idx_parent_code` (`parent_code`),
                           KEY           `idx_status` (`status`),
                           KEY           `idx_sort_order` (`sort_order`),
                           KEY           `idx_created_at` (`created_at`)

                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统参数表';
                       """

    # 字段定义
    id: Optional[int] = Field(None, description="主键ID")
    code: str = Field(..., description="参数编码")
    value: Optional[str] = Field(None, description="参数值")
    desc: Optional[str] = Field(None, description="参数描述")
    parent_code: Optional[str] = Field(None, description="父级参数编码（用于分组/层级）")
    type: Optional[str] = Field("Base", description="参数类型, Base模块 or 其他模块")
    status: int = Field(1, description="状态：0-禁用，1-启用")
    sort_order: int = Field(0, description="排序序号（越小越靠前）")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    created_by: Optional[int] = Field(None, description="创建人ID")
    updated_by: Optional[int] = Field(None, description="更新人ID")

    @classmethod
    def get_param_by_code(cls, code: str, type: Optional[str] = None,parent_code: Optional[str] = None) -> Optional[dict]:
        """
        根据参数编码获取参数信息（只返回启用的）

        Args:
            code: 参数编码
            type: 参数类型（可选）
            parent_code: 父级参数编码（可选）

        Returns:
            包含 code、value、desc 的字典，未找到返回 None
        """
        return cls._cached_get_param_by_code(cls, code, type)

    @staticmethod
    @lru_cache(maxsize=128)
    def _cached_get_param_by_code(cls, code: str, type: Optional[str] = None, parent_code: Optional[str] = None) -> Optional[dict]:
        """
        带缓存的参数查询方法（内部使用）

        Args:
            cls: 类对象
            code: 参数编码
            type: 参数类型（可选）
            parent_code: 父级参数编码（可选）

        Returns:
            包含 code、value、desc 的字典，未找到返回 None
        """
        try:
            cls._ensure_table_exists()
            db = cls.get_db_connection()
            if db is None:
                return None

            table_name = cls.get_table_name_with_db()
            sql = f"SELECT `code`, `value`, `desc` FROM {table_name} WHERE `code` = %s AND `status` = 1"
            params = [code]

            if type is not None:
                sql += " AND `type` = %s"
                params.append(type)
            if parent_code is not None:
                sql += " AND `parent_code` = %s"
                params.append(parent_code)

            result = db.execute(sql, tuple(params))
            if result:
                return result[0]
            return None
        except Exception as e:
            logger = __import__('logging').getLogger(__name__)
            logger.error(f"get_param_by_code({code}) 失败：{str(e)}")
            return None

    @classmethod
    @timing_log
    def get_params_by_parent_code(cls, parent_code: str, type: Optional[str] = None) -> List[dict]:
        """
        根据父级参数编码获取参数列表（只返回启用的），按 sort_order 排序

        Args:
            parent_code: 父级参数编码
            type: 参数类型（可选）

        Returns:
            包含 code、value、desc 的字典列表
        """
        return cls._cached_get_params_by_parent_code(cls, parent_code, type)

    @staticmethod
    @lru_cache(maxsize=128)
    def _cached_get_params_by_parent_code(cls, parent_code: str, type: Optional[str] = None) -> List[dict]:
        """
        带缓存的父级参数查询方法（内部使用）

        Args:
            cls: 类对象
            parent_code: 父级参数编码
            type: 参数类型（可选）

        Returns:
            包含 code、value、desc 的字典列表
        """
        try:
            cls._ensure_table_exists()
            db = cls.get_db_connection()
            if db is None:
                return []

            table_name = cls.get_table_name()
            sql = f"SELECT `code`, `value`, `desc` FROM `{table_name}` WHERE `parent_code` = %s AND `status` = 1"
            params = [parent_code]

            if type is not None:
                sql += " AND `type` = %s"
                params.append(type)

            sql += " ORDER BY `sort_order` ASC"

            results = db.execute(sql, tuple(params))
            return results if results else []
        except Exception as e:
            logger = __import__('logging').getLogger(__name__)
            logger.error(f"get_params_by_parent_code({parent_code}) 失败：{str(e)}")
            return []

    @classmethod
    def clear_param_cache(cls):
        """
        清除参数查询缓存

        调用此方法后，下次查询会重新从数据库获取数据
        """
        cls._cached_get_param_by_code.cache_clear()
        cls._cached_get_params_by_parent_code.cache_clear()
        print("✓ 参数查询缓存已清除")


if __name__ == '__main__':


    print("\n=== 测试查询函数 ===")

    # 测试 get_param_by_code
    print("\n1. 测试 get_param_by_code:")
    param = BaseParamsModel.get_param_by_code('subject_math', 'Education')
    print(f"   查询 subject_math: {param}")

    # 测试 get_params_by_parent_code
    print("\n2. 测试 get_params_by_parent_code:")
    params_list = BaseParamsModel.get_params_by_parent_code('edu_subject', 'Education')
    params_list1 = BaseParamsModel.get_params_by_parent_code('edu_subject', 'Education')
    BaseParamsModel.clear_param_cache()
    params_list2 = BaseParamsModel.get_params_by_parent_code('edu_subject', 'Education')
    print(f"   查询 edu_subject 的所有子参数:")
    for p in params_list:
        print(f"   - {p}")
