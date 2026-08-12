# Base.Ai 模块架构文档

## 概述

`Base.Ai` 模块提供了一个统一的大语言模型（LLM）集成框架，基于 OpenAI SDK 封装多种 LLM 服务。采用抽象工厂模式，支持快速扩展新模型，同时保持接口的一致性。

## 目录结构

```
Base/Ai/
├── base/                   # 抽象基类和配置
│   ├── baseLlm.py          # LLM 抽象基类
│   ├── baseMessages.py      # 消息封装
│   ├── baseEnum.py         # 枚举定义
│   └── baseSetting.py      # LLM 配置类
├── llms/                   # 具体模型实现
│   ├── qwenLlm.py         # 通义千问实现
│   └── deepseekLlm.py     # DeepSeek 实现
└── __init__.py             # 模块导出
```

## TODO:

* [ ] 持久化调用记录
* [ ] Emdedding支持引入
* [ ] 其他国内主流模型子类编写
* [ ] 记忆支持

## 核心架构设计

### 1. 抽象工厂模式

```
BaseLlm (抽象基类)
    ├── QwenLlm (通义千问)
    └── DeepSeekLlm (深度求索)
```

**设计优势**：

- ✅ 统一接口：所有 LLM 实现遵循相同的调用方式
- ✅ 易于扩展：新增模型只需继承 `BaseLlm` 并实现必要方法
- ✅ 代码复用：公共逻辑集中在基类

### 2. 三层架构

 ┌─────────────────────────────────────────┐
│     业务代码层                           │
│   invoke() / ainvoke()                  │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────┐
│    BaseLlm 抽象层                    │
│  - 参数准备                          │
│  - 响应处理                          │
│  - 错误处理                          │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│    OpenAI 兼容层                     │
│  - 统一 API 格式                     │
│  - 同步/异步支持                     │
│  - 流式/非流式支持                   │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│    具体实现层                        │
│  - QwenLlm                          │
│  - DeepSeekLlm                      │
│  - [未来: GPT, Claude...]            │
└──────────────────────────────────────┘

## 核心组件详解

### base/baseLlm.py - LLM 抽象基类

#### 核心接口

**同步方法**：

- `invoke(prompt, stream=False, **kwargs)`: 单轮对话
- `chat(messages, stream=False, **kwargs)`: 多轮对话

**异步方法**：

- `ainvoke(prompt, stream=False, **kwargs)`: 异步单轮对话
- `achat(messages, stream=False, **kwargs)`: 异步多轮对话

**抽象属性**（子类必须实现）：

- `init_model()`: 初始化模型客户端
- `context_window`: 上下文窗口大小
- `supports_streaming`: 是否支持流式输出

#### 功能特性

**1. 流式输出支持**

```python
# 非流式（一次性返回）
result = llm.invoke("讲一个笑话")

# 流式（生成器逐个返回）
for chunk in llm.invoke("讲一个笑话", stream=True):
    print(chunk, end="", flush=True)
```

**2. 思考过程支持（Qwen 特有）**

```python
for chunk in llm.invoke("解释量子计算", enable_thinking=True, stream=True):
    if chunk["type"] == "reasoning":
        print(f"思考中: {chunk['content']}")
    elif chunk["type"] == "content":
        print(f"回答: {chunk['content']}")
```

**3. 配置管理**

- 支持配置对象（`LLMConfig`）
- 支持运行时参数覆盖
- 自动参数合并和清理

**4. 错误处理**

- 统一的异常处理和日志记录
- 详细的调试日志

### base/baseSetting.py - 配置管理

#### LLMConfig（基础配置类）

**配置参数**：

| 参数                  | 类型      | 说明                |
| --------------------- | --------- | ------------------- |
| `model`             | str       | 模型名称            |
| `api_key`           | str       | API 密钥            |
| `base_url`          | str       | API 基础 URL        |
| `stream`            | bool      | 是否启用流式        |
| `temperature`       | float     | 温度参数（0.0-2.0） |
| `max_tokens`        | int       | 最大 token 数       |
| `top_p`             | float     | 核采样              |
| `frequency_penalty` | float     | 频率惩罚            |
| `presence_penalty`  | float     | 存在惩罚            |
| `stop`              | list[str] | 停止序列            |
| `timeout`           | float     | 超时时间（秒）      |

#### 专用配置类

**DashScopeConfig**：通义千问配置

- 自动从 `settings.dashscope` 获取配置
- 默认使用 DashScope 官方 API 地址

**DeepSeekConfig**：DeepSeek 配置

- 自动从 `settings.deepseek` 获取配置
- 默认使用 DeepSeek 官方 API 地址

### base/baseMessages.py - 消息封装

提供简洁的消息类型访问接口：

```python
from Base.Ai import UserMessages, AssistantMessages, SystemMessages

# 创建消息
user_msg = UserMessages("你好")
assistant_msg = AssistantMessages("你好！有什么可以帮助你的？")
system_msg = SystemMessages("你是一个专业的翻译助手")
developer_msg = DeveloperMessages("请优化以下代码")
```

**优势**：

- 简化 OpenAI 长类型名
- 统一的消息创建接口
- 支持所有角色类型

### base/baseEnum.py - 枚举定义

**LLMTypeEnum**：

- `QWEN`: 通义千问
- `DEEPSEEK`: DeepSeek

**用途**：

- 类型安全：避免字符串拼写错误
- 模型识别：用于日志和配置

### llms/qwenLlm.py - 通义千问实现

#### 核心特性

**1. 模型映射**

```python
CONTEXT_WINDOW = {
    "qwen-turbo": 8192,
    "qwen-plus": 32768,
    "qwen-max": 32768,
    "qwen-long": 1000000,
    "qwen2.5-72b-instruct": 131072,
    # ... 更多模型
}
```

**2. 思考模式**

- 支持 `enable_thinking` 参数
- 返回结构化流式输出（reasoning/content）
- 便于实时展示 AI 思考过程

**3. 便捷函数**

```python
from Base.Ai.llms.qwenLlm import create_qwen_llm

# 使用默认配置
llm = create_qwen_llm()

# 自定义配置
llm = create_qwen_llm(
    model="qwen-plus",
    temperature=0.7,
    max_tokens=2000
)
```

### llms/deepseekLlm.py - DeepSeek 实现

#### 核心特性

**1. 模型映射**

```python
CONTEXT_WINDOW = {
    "deepseek-chat": 128000,
    "deepseek-coder": 128000,
    "deepseek-reasoner": 64000,
}
```

**2. 便捷函数**

```python
from Base.Ai.llms.deepseekLlm import create_deepseek_llm

llm = create_deepseek_llm(
    model="deepseek-chat",
    temperature=0.7
)
```

## 使用 OpenAI 封装的意义

### 1. 统一接口规范

**问题**：不同 LLM 供应商 API 格式不一致

- OpenAI: `client.chat.completions.create()`
- Anthropic: `client.messages.create()`
- 通义千问: DashScope API
- DeepSeek: OpenAI 兼容 API

**解决方案**：OpenAI SDK 已成为事实标准

- DeepSeek、通义千问等采用 OpenAI 兼容 API
- 使用 OpenAI SDK 统一调用方式
- 减少学习成本

### 2. 生态成熟度

**OpenAI SDK 优势**：

- ✅ 成熟稳定的 SDK
- ✅ 完善的类型提示
- ✅ 同步/异步双支持
- ✅ 流式输出标准化
- ✅ 错误处理完善
- ✅ 广泛的社区支持

### 3. 向后兼容性

**未来扩展其他模型时**：

```python
class GPTLlm(BaseLlm):
    def init_model(self):
        # 使用 OpenAI 官方 API
        self.init_openai_client(
            api_key=settings.openai.api_key,
            base_url="https://api.openai.com/v1"
        )
```

### 4. 减少维护成本

**集中管理**：

- 一套代码支持多种模型
- 统一的配置管理
- 统一的错误处理和日志
- 升级 SDK 时只需修改一处

## 可扩展性设计

### 1. 添加新模型（3 步）

#### 步骤 1：创建配置类

在 `base/baseSetting.py` 添加：

```python
@dataclass
class NewModelConfig(LLMConfig):
    def __init__(self, api_key: str = None, model: str = None, **kwargs):
        super().__init__(
            api_key=api_key or settings.new_model.api_key,
            model=model or settings.new_model.default_model,
            **kwargs
        )
```

#### 步骤 2：创建实现类

在 `llms/` 目录创建 `newModelLlm.py`：

```python
from Base.Ai.base.baseLlm import BaseLlm
from Base.Ai.base.baseEnum import LLMTypeEnum

class NewModelLlm(BaseLlm):
    CONTEXT_WINDOW = {
        "new-model": 32768,
        # 更多模型...
    }

    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(
            model_name="new-model",
            model_type=LLMTypeEnum.NEW_MODEL,
            **kwargs
        )
        self.init_openai_client(
            api_key=api_key,
            base_url="https://api.new-model.com/v1"
        )

    @property
    def context_window(self) -> int:
        # 实现上下文窗口属性
        for key, size in self.CONTEXT_WINDOW.items():
            if key in self.model.lower():
                return size
        return 32768

    @property
    def supports_streaming(self) -> bool:
        # 实现是否支持流式输出
        return True
```

#### 步骤 3：添加便捷函数和导出

```python
def create_new_model_llm(api_key: str = None, **kwargs) -> NewModelLlm:
    # 实现便捷函数
    pass

# 在 llms/__init__.py 导出
```

### 2. 配置扩展

在 `Base/Config/setting.py` 添加新模型配置：

```python
class NewModelSettings(BaseEnvSettings):
    api_key: str = ""
    base_url: str = "https://api.new-model.com/v1"
    default_model: str = "new-model"

    model_config = SettingsConfigDict(
        env_prefix="NEW_MODEL_",
        extra="allow",
    )

class Settings(BaseEnvSettings):
    # ... 现有配置
    new_model: NewModelSettings = Field(default_factory=NewModelSettings)
```

### 3. 消息类型扩展

在 `base/baseMessages.py` 添加新角色：

```python
@staticmethod
def get_custom_messages(prompt: Any, name: str = None):
    # 添加自定义角色类型
    return ChatCompletionCustomMessageParam(
        content=str(prompt),
        role="custom",
        name=name
    )
```

## 二次开发友好性

### 1. 低学习成本

**统一的 API 设计**：

```python
# 所有 LLM 使用相同的接口
llm = create_qwen_llm()
result = llm.invoke("讲一个笑话")

# 切换到其他模型，接口不变
llm = create_deepseek_llm()
result = llm.invoke("讲一个笑话")
```

### 2. 类型安全

**完整的类型提示**：

- 所有方法都有类型注解
- IDE 自动补全和类型检查
- 减少运行时错误

### 3. 丰富的示例代码

每个实现类都包含：

- ✅ `__main__` 测试代码
- ✅ 同步/异步调用示例
- ✅ 流式/非流式示例
- ✅ 对话模式示例

### 4. 详细的错误处理

**三级错误处理**：

1. **配置验证**：初始化时检查必要参数
2. **API 调用**：捕获并记录 API 错误
3. **响应处理**：解析响应时的错误处理

```python
try:
    result = llm.invoke(prompt)
except Exception as e:
    logger.error(f"调用失败: {e}")
    # 统一的错误处理
```

### 5. 灵活的配置方式

**3 种配置方式**：

**方式 1：使用配置对象**

```python
config = DashScopeConfig(model="qwen-plus", temperature=0.7)
llm = QwenLlm(config=config)
```

**方式 2：使用便捷函数**

```python
llm = create_qwen_llm(temperature=0.7)
```

**方式 3：运行时参数**

```python
llm = QwenLlm()
result = llm.invoke(prompt, temperature=0.7, max_tokens=2000)
```

### 6. 调试友好

**详细的日志输出**：

- 模型初始化日志
- API 调用参数日志
- 响应内容日志
- 流式输出片段日志
- 错误堆栈日志

```python
logger.info(f"调用参数: {params}")
logger.debug(f"响应内容: {content[:100]}...")
logger.debug(f"流式片段: {content[:50]}...")
```

## 使用示例

### 基础调用

```python
from Base.Ai.llms.qwenLlm import create_qwen_llm

# 创建 LLM 实例
llm = create_qwen_llm(model="qwen-plus")

# 单轮对话（非流式）
response = llm.invoke("讲一个笑话")
print(response)

# 单轮对话（流式）
for chunk in llm.invoke("讲一个笑话", stream=True):
    print(chunk, end="", flush=True)
```

### 多轮对话

```python
from Base.Ai import UserMessages, SystemMessages

messages = [
    SystemMessages("你是一个专业的翻译助手"),
    UserMessages("请翻译：Hello, world!"),
    UserMessages("翻译成中文"),
]

response = llm.chat(messages)
print(response)
```

### 异步调用

```python
import asyncio
from Base.Ai.llms.deepseekLlm import create_deepseek_llm

async def main():
    llm = create_deepseek_llm()

    # 异步调用
    response = await llm.ainvoke("讲一个笑话")
    print(response)

    # 异步流式调用
    async for chunk in await llm.ainvoke("讲一个笑话", stream=True):
        print(chunk, end="", flush=True)

asyncio.run(main())
```

### 思考过程

```python
llm = create_qwen_llm(model="qwen-plus")

print("AI 思考中...")
print("-" * 50)

for chunk in llm.invoke("解释量子计算", enable_thinking=True, stream=True):
    if chunk["type"] == "reasoning":
        print(chunk["content"], flush=True)
    elif chunk["type"] == "content":
        print("\nAI 回答:")
        print(chunk["content"])
```

### 获取模型信息

```python
llm = create_qwen_llm()
info = llm.get_model_info()

print(f"模型: {info['model_name']}")
print(f"类型: {info['model_type']}")
print(f"上下文窗口: {info['context_window']}")
print(f"支持流式: {info['supports_streaming']}")
```

## 高级特性

### 1. 自定义响应处理

子类可以重写响应处理方法：

```python
class MyLlm(BaseLlm):
    def _handle_response(self, response):
        # 自定义响应处理逻辑
        content = response.choices[0].message.content
    
        # 自定义后处理
        processed_content = self.post_process(content)
    
        return processed_content
```

### 2. 参数预处理

子类可以重写参数准备方法：

```python
class MyLlm(BaseLlm):
    def _prepare_params(self, **kwargs):
        params = super()._prepare_params(**kwargs)
    
        # 自定义参数处理
        if "custom_param" in kwargs:
            params["custom_field"] = kwargs["custom_param"]
    
        return params
```

### 3. 扩展配置

支持额外的配置参数：

```python
config = DashScopeConfig(
    model="qwen-plus",
    temperature=0.7,
    additional_params={
        "enable_search": True,  # 自定义扩展参数
        "max_retries": 3
    }
)
```

## 配置最佳实践

### 1. 环境变量管理

在 `.env` 文件中配置：

```env
# 通义千问
DASHSCOPE_API_KEY=your-api-key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/api/v1
DASHSCOPE_DEFAULT_MODEL=qwen-plus

# DeepSeek
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_DEFAULT_MODEL=deepseek-chat

# 通用 LLM 配置
LLM_TIMEOUT=60
```

### 2. 配置分层

```python
# 全局默认配置（settings.llm.timeout）
     ↓
# 模型特定配置（DashScopeConfig.base_url）
     ↓
# 运行时参数（invoke(temperature=0.7)）
     ↓
# 最终参数（优先级：运行时 > 模型 > 全局）
```

### 3. 敏感信息保护

**不要硬编码 API Key**：

```python
# ❌ 错误
llm = QwenLlm(api_key="sk-xxx")

# ✅ 正确
llm = create_qwen_llm()  # 从 settings 读取
```

## 性能优化建议

### 1. 连接复用

- LLM 实例可以复用，避免重复初始化
- 异步场景下使用 `AsyncOpenAI` 连接池

### 2. 流式输出

对于长文本生成，使用流式输出：

- ✅ 更好的用户体验
- ✅ 减少首字延迟
- ✅ 适合实时展示

### 3. Token 管理

监控和管理 Token 使用：

- 设置合理的 `max_tokens`
- 监控响应的 token 消耗
- 针对不同模型选择合适的上下文窗口

## 故障排查

### 常见问题

**1. API Key 错误**

```
ValueError: 未配置Qwen模型的Base_Url
```

**解决方案**：在 `.env` 中配置 `DASHSCOPE_BASE_URL`

**2. 连接超时**

```
TimeoutError: Request timed out
```

**解决方案**：调整 `LLM_TIMEOUT` 或运行时 `timeout` 参数

**3. 流式输出不工作**

```
for chunk in llm.invoke(prompt, stream=True):
    # 没有输出
```

**解决方案**：检查模型的 `supports_streaming` 属性

**4. 思考模式异常**

```
TypeError: 'str' object is not subscriptable
```

**解决方案**：确保使用 `enable_thinking=True` 时也设置 `stream=True`

## 总结

`Base.Ai` 模块通过以下设计实现了高度的可扩展性和二次开发友好性：

### 核心优势

1. ✅ **统一接口**：所有 LLM 使用相同的调用方式
2. ✅ **易于扩展**：新增模型只需 3 步
3. ✅ **类型安全**：完整的类型提示和验证
4. ✅ **成熟生态**：基于 OpenAI SDK，稳定可靠
5. ✅ **丰富示例**：每个实现都有完整的使用示例
6. ✅ **详细日志**：便于调试和监控
7. ✅ **灵活配置**：支持多种配置方式
8. ✅ **异步支持**：同步/异步双支持
9. ✅ **流式输出**：支持实时内容生成
10. ✅ **思考过程**：支持展示 AI 推理过程

### 适用场景

- ✅ 快速集成新 LLM 模型
- ✅ 构建多模型支持的应用
- ✅ 需要灵活配置的项目
- ✅ 需要调试和监控的生产环境
- ✅ 需要同步/异步双支持的项目

通过合理的抽象和封装，`Base.Ai` 为开发者提供了强大而灵活的 LLM 集成框架。
