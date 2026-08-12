import logging
import os
import warnings
from typing import List, Optional, Tuple, Generator, Dict

from Base.RicUtils.pathUtils import to_absolute_path

# 过滤掉 jieba 库的 pkg_resources 废弃警告
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

# 导入 jieba
import jieba
import jieba.analyse

logger = logging.getLogger(__name__)




class JiebaClient:
    """
    Jieba 分词客户端单例类，封装jieba中文分词的常用功能。
    包括：分词、自定义词典管理、关键词提取、词性标注等。
    """

    _instance: Optional['JiebaClient'] = None
    _initialized = False

    def __new__(cls):
        """
        实现单例模式，确保全局只有一个 JiebaClient 实例。
        """
        if cls._instance is None:
            cls._instance = super(JiebaClient, cls).__new__(cls)
        return cls._instance

    def __init__(self, user_dict_path: Optional[str] = None, hmm: bool = True):
        """
        初始化 Jieba 客户端。

        Args:
            user_dict_path: 用户自定义词典的路径（相对或绝对路径）
            hmm: 是否使用 HMM（隐马尔可夫模型）进行新词发现
        """
        if self._initialized:
            return

        # 设置 HMM 模型
        jieba.HMM = hmm

        # 加载用户自定义词典
        if user_dict_path:
            self.load_user_dict(user_dict_path)

        self._initialized = True
        logger.info("JiebaClient 单例已初始化")

    # ======================
    # 分词功能
    # ======================

    def cut(
        self,
        sentence: str,
        cut_all: bool = False,
        HMM: bool = True
    ) -> List[str]:
        """
        对句子进行分词。

        Args:
            sentence: 待分词的句子
            cut_all: 是否使用全模式分词
                - True: 全模式，生成所有可能的词语组合
                - False: 精确模式，尝试将句子最精确地切开
            HMM: 是否使用 HMM 模型进行新词发现

        Returns:
            分词结果列表

        Examples:
            >>> client = JiebaClient()
            >>> client.cut("我爱北京天安门")
            ['我', '爱', '北京', '天安门']

            >>> client.cut("我爱北京天安门", cut_all=True)
            ['我', '爱', '北京', '天安', '天安门']
        """
        try:
            words = list(jieba.cut(sentence, cut_all=cut_all, HMM=HMM))
            logger.debug(f"分词结果: {sentence} -> {words}")
            return words
        except Exception as e:
            logger.error(f"分词失败: {e}")
            return []

    def cut_for_search(
        self,
        sentence: str,
        HMM: bool = True
    ) -> List[str]:
        """
        搜索引擎模式分词。
        在精确模式的基础上，对长词再次切分，提高召回率。

        Args:
            sentence: 待分词的句子
            HMM: 是否使用 HMM 模型进行新词发现

        Returns:
            分词结果列表

        Examples:
            >>> client = JiebaClient()
            >>> client.cut_for_search("小明硕士毕业于中国科学院")
            ['小明', '硕士', '毕业', '于', '中国', '科学院', '中国科学院']
        """
        try:
            words = list(jieba.cut_for_search(sentence, HMM=HMM))
            logger.debug(f"搜索引擎模式分词结果: {sentence} -> {words}")
            return words
        except Exception as e:
            logger.error(f"搜索引擎模式分词失败: {e}")
            return []

    def cut_sentence_by_punctuation(
        self,
        text: str,
        delimiters: Optional[List[str]] = None
    ) -> List[str]:
        """
        按标点符号切分句子。

        Args:
            text: 待切分的文本
            delimiters: 自定义分隔符列表，默认为常见中文标点

        Returns:
            句子列表

        Examples:
            >>> client = JiebaClient()
            >>> client.cut_sentence_by_punctuation("你好。世界！大家好？")
            ['你好', '世界', '大家好']
        """
        if delimiters is None:
            delimiters = ['。', '！', '？', '；', '，', '、', '…', '！', '？', '.', '!', '?', ';', ',']

        import re
        # 构造正则表达式
        pattern = '|'.join(re.escape(d) for d in delimiters)
        sentences = [s.strip() for s in re.split(pattern, text) if s.strip()]
        return sentences

    # ======================
    # 自定义词典管理
    # ======================

    def load_user_dict(
        self,
        file_path: str,
        freq: Optional[int] = None,
        tag: Optional[str] = None
    ) -> bool:
        """
        加载用户自定义词典。

        词典文件格式（每行一个词）：
        词语 词频 词性（可选）

        Args:
            file_path: 词典文件路径
            freq: 默认词频（可选）
            tag: 默认词性（可选）

        Returns:
            成功返回 True，失败返回 False

        Examples:
            >>> client = JiebaClient()
            >>> client.load_user_dict("data/user_dict.txt")
        """
        try:
            # 使用通用工具函数转换路径
            abs_path = to_absolute_path(file_path)
            
            if not os.path.exists(abs_path):
                logger.error(f"词典文件不存在: {abs_path}")
                return False

            jieba.load_userdict(abs_path)
            logger.info(f"成功加载用户词典: {abs_path}")
            return True
        except Exception as e:
            logger.error(f"加载用户词典失败: {e}")
            return False

    def add_word(
        self,
        word: str,
        freq: Optional[int] = None,
        tag: Optional[str] = None
    ) -> None:
        """
        向词典中添加一个新词。

        Args:
            word: 词语
            freq: 词频（可选，词频越高越容易被切分）
            tag: 词性（可选，如 'n', 'v', 'adj' 等）

        Examples:
            >>> client = JiebaClient()
            >>> client.add_word("云计算", freq=100, tag="n")
            >>> client.cut("云计算技术")
            ['云计算', '技术']
        """
        try:
            jieba.add_word(word, freq=freq, tag=tag)
            logger.debug(f"添加词语: {word} (freq={freq}, tag={tag})")
        except Exception as e:
            logger.error(f"添加词语失败: {e}")

    def del_word(self, word: str) -> None:
        """
        从词典中删除一个词。

        Args:
            word: 要删除的词语

        Examples:
            >>> client = JiebaClient()
            >>> client.del_word("云计算")
        """
        try:
            jieba.del_word(word)
            logger.debug(f"删除词语: {word}")
        except Exception as e:
            logger.error(f"删除词语失败: {e}")

    def suggest_word(
        self,
        word: str,
        freq: Optional[int] = None,
        tag: Optional[str] = None
    ) -> bool:
        """
        调整词频，用于动态调整词语的优先级。
        如果词语不存在，效果等同于 add_word。

        Args:
            word: 词语
            freq: 词频
            tag: 词性

        Returns:
            成功返回 True，失败返回 False

        Examples:
            >>> client = JiebaClient()
            >>> client.suggest_word("云计算", freq=200)
        """
        try:
            jieba.suggest_freq(word, freq=freq, tag=tag)
            logger.debug(f"调整词频: {word} -> {freq}")
            return True
        except Exception as e:
            logger.error(f"调整词频失败: {e}")
            return False

    # ======================
    # 关键词提取
    # ======================

    def extract_tags(
        self,
        sentence: str,
        topK: int = 20,
        withWeight: bool = False,
        allowPOS: Optional[List[str]] = None,
        withFlag: bool = False
    ) -> List[str] | List[Tuple[str, float]] | List[Tuple[str, float, str]]:
        """
        提取句子中的关键词。

        Args:
            sentence: 待提取的文本
            topK: 返回关键词的最大数量
            withWeight: 是否返回权重值
            allowPOS: 指定词性，如 ['ns', 'n', 'vn', 'v'] 等
                常见词性:
                - ns: 地名
                - n: 普通名词
                - vn: 动名词
                - v: 动词
                - a: 形容词
            withFlag: 是否返回词性标记

        Returns:
            关键词列表或带权重的关键词列表

        Examples:
            >>> client = JiebaClient()
            >>> client.extract_tags("自然语言处理是人工智能的重要方向", topK=5, withWeight=True)
            [('人工智能', 0.9), ('自然语言', 0.8), ('处理', 0.6), ('重要', 0.4), ('方向', 0.3)]
        """
        try:
            if allowPOS is None:
                allowPOS = ['ns', 'n', 'vn', 'v']

            tags = jieba.analyse.extract_tags(
                sentence,
                topK=topK,
                withWeight=withWeight,
                allowPOS=allowPOS,
                withFlag=withFlag
            )
            logger.debug(f"关键词提取结果: {tags}")
            return tags
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return []

    def extract_tags_by_tfidf(
        self,
        sentence: str,
        topK: int = 20,
        withWeight: bool = False
    ) -> List[str] | List[Tuple[str, float]]:
        """
        使用 TF-IDF 算法提取关键词。

        Args:
            sentence: 待提取的文本
            topK: 返回关键词的最大数量
            withWeight: 是否返回权重值

        Returns:
            关键词列表或带权重的关键词列表
        """
        try:
            tags = jieba.analyse.extract_tags(
                sentence,
                topK=topK,
                withWeight=withWeight,
                allowPOS=None
            )
            logger.debug(f"TF-IDF 关键词提取结果: {tags}")
            return tags
        except Exception as e:
            logger.error(f"TF-IDF 关键词提取失败: {e}")
            return []

    def extract_tags_by_text_rank(
        self,
        sentence: str,
        topK: int = 20,
        withWeight: bool = False,
        allowPOS: Optional[List[str]] = None
    ) -> List[str] | List[Tuple[str, float]]:
        """
        使用 TextRank 算法提取关键词。
        基于图排序的关键词提取算法，适合提取文档的关键词。

        Args:
            sentence: 待提取的文本
            topK: 返回关键词的最大数量
            withWeight: 是否返回权重值
            allowPOS: 指定词性

        Returns:
            关键词列表或带权重的关键词列表
        """
        try:
            tags = jieba.analyse.textrank(
                sentence,
                topK=topK,
                withWeight=withWeight,
                allowPOS=allowPOS
            )
            logger.debug(f"TextRank 关键词提取结果: {tags}")
            return tags
        except Exception as e:
            logger.error(f"TextRank 关键词提取失败: {e}")
            return []

    # ======================
    # 词性标注
    # ======================

    def posseg_cut(
        self,
        sentence: str,
        HMM: bool = True
    ) -> List[Tuple[str, str]]:
        """
        带词性标注的分词。

        Args:
            sentence: 待分词的句子
            HMM: 是否使用 HMM 模型

        Returns:
            带词性标注的分词结果，每个元素为 (词, 词性) 元组

        Examples:
            >>> client = JiebaClient()
            >>> client.posseg_cut("我爱自然语言处理")
            [('我', 'r'), ('爱', 'v'), ('自然', 'n'), ('语言', 'n'), ('处理', 'v')]
        """
        try:
            words = list(jieba.posseg.cut(sentence, HMM=HMM))
            result = [(word.word, word.flag) for word in words]
            logger.debug(f"词性标注结果: {result}")
            return result
        except Exception as e:
            logger.error(f"词性标注失败: {e}")
            return []

    def get_words_by_pos(
        self,
        sentence: str,
        pos_list: List[str],
        HMM: bool = True
    ) -> List[str]:
        """
        提取指定词性的词语。

        Args:
            sentence: 待分词的句子
            pos_list: 词性列表，如 ['n', 'v', 'a']
            HMM: 是否使用 HMM 模型

        Returns:
            指定词性的词语列表

        Examples:
            >>> client = JiebaClient()
            >>> client.get_words_by_pos("我喜欢美丽的花朵", pos_list=['n', 'a'])
            ['喜欢', '美丽', '花朵']
        """
        try:
            words_with_pos = self.posseg_cut(sentence, HMM=HMM)
            result = [word for word, pos in words_with_pos if pos in pos_list]
            logger.debug(f"词性过滤结果: {result}")
            return result
        except Exception as e:
            logger.error(f"词性过滤失败: {e}")
            return []

    # ======================
    # 停用词处理
    # ======================

    def remove_stopwords(
        self,
        words: List[str],
        stopwords: Optional[List[str]] = None,
        stopwords_file: Optional[str] = None
    ) -> List[str]:
        """
        去除停用词。

        Args:
            words: 词语列表
            stopwords: 停用词列表
            stopwords_file: 停用词文件路径

        Returns:
            去除停用词后的词语列表

        Examples:
            >>> client = JiebaClient()
            >>> words = ['我', '是', '一个', '程序员']
            >>> client.remove_stopwords(words, stopwords=['我', '是', '一个'])
            ['程序员']
        """
        try:
            # 加载停用词文件
            if stopwords_file:
                # 使用通用工具函数转换路径
                abs_path = to_absolute_path(stopwords_file)
                
                if os.path.exists(abs_path):
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        file_stopwords = set(line.strip() for line in f if line.strip())
                    if stopwords:
                        stopwords = set(stopwords) | file_stopwords
                    else:
                        stopwords = file_stopwords

            if stopwords is None:
                return words

            result = [word for word in words if word not in stopwords]
            logger.debug(f"去除停用词: {len(words)} -> {len(result)}")
            return result
        except Exception as e:
            logger.error(f"去除停用词失败: {e}")
            return words

    # ======================
    # 批量处理
    # ======================

    def batch_cut(
        self,
        sentences: List[str],
        cut_all: bool = False,
        HMM: bool = True
    ) -> Generator[List[str], None, None]:
        """
        批量分词处理。

        Args:
            sentences: 句子列表
            cut_all: 是否使用全模式分词
            HMM: 是否使用 HMM 模型

        Yields:
            每个句子的分词结果
        """
        for sentence in sentences:
            yield self.cut(sentence, cut_all=cut_all, HMM=HMM)

    def batch_extract_tags(
        self,
        sentences: List[str],
        topK: int = 20,
        withWeight: bool = False
    ) -> Generator[List[str] | List[Tuple[str, float]], None, None]:
        """
        批量提取关键词。

        Args:
            sentences: 句子列表
            topK: 返回关键词的最大数量
            withWeight: 是否返回权重值

        Yields:
            每个句子的关键词
        """
        for sentence in sentences:
            yield self.extract_tags(sentence, topK=topK, withWeight=withWeight)

    # ======================
    # 工具函数
    # ======================

    def get_word_frequency(
        self,
        text: str,
        topN: Optional[int] = None
    ) -> Dict[str, int]:
        """
        统计文本中词频。

        Args:
            text: 待统计的文本
            topN: 返回前N个高频词，None表示返回全部

        Returns:
            词频字典，按词频降序排列

        Examples:
            >>> client = JiebaClient()
            >>> client.get_word_frequency("我爱北京，北京是中国首都", topN=3)
            {'北京': 2, '我': 1, '爱': 1}
        """
        try:
            words = self.cut(text)
            freq_dict = {}
            for word in words:
                if word.strip():  # 忽略空词
                    freq_dict[word] = freq_dict.get(word, 0) + 1

            # 按词频降序排序
            sorted_dict = dict(sorted(freq_dict.items(), key=lambda x: x[1], reverse=True))

            if topN:
                sorted_dict = dict(list(sorted_dict.items())[:topN])

            logger.debug(f"词频统计: {sorted_dict}")
            return sorted_dict
        except Exception as e:
            logger.error(f"词频统计失败: {e}")
            return {}


# 全局单例实例
jieba_client = JiebaClient()


# --- 使用示例 ---
if __name__ == "__main__":
    # 获取单例实例
    client = JiebaClient()
    sentence = "我爱自然语言处理和人工智能"


    def test1():
        print("=== 1. 基本分词 ===")
        print(f"精确模式: {client.cut(sentence)}")
        print(f"全模式: {client.cut(sentence, cut_all=True)}")
        print(f"搜索引擎模式: {client.cut_for_search(sentence)}")


    def test2():
        print("\n=== 2. 自定义词典 ===")
        # 添加新词
        client.add_word("自然语言处理", freq=100, tag="n")
        client.add_word("人工智能", freq=100, tag="n")
        print(f"添加新词后: {client.cut(sentence)}")


    def test3():
        print("\n=== 3. 关键词提取 ===")
        text = "自然语言处理是人工智能和语言学的交叉学科，致力于让计算机理解和处理人类语言。"
        print(f"TF-IDF 关键词: {client.extract_tags_by_tfidf(text, topK=5, withWeight=True)}")
        print(f"TextRank 关键词: {client.extract_tags_by_text_rank(text, topK=5, withWeight=True)}")


    def test4():
        print("\n=== 4. 词性标注 ===")
        print(f"词性标注: {client.posseg_cut(sentence)}")
        print(f"提取名词: {client.get_words_by_pos(sentence, pos_list=['n', 'vn'])}")


    def test5():
        print("\n=== 5. 停用词过滤 ===")
        stopwords = ['我', '和', '是']
        words = ['我', '爱', '自然语言', '和', '人工智能']
        print(f"原词: {words}")
        print(f"过滤后: {client.remove_stopwords(words, stopwords=stopwords)}")


    def test6():
        print("\n=== 6. 词频统计 ===")
        text = "北京是中国的首都，北京有很多名胜古迹。我爱北京。"
        print(f"词频统计: {client.get_word_frequency(text, topN=5)}")


    def test7():
        print("\n=== 7. 批量处理 ===")
        sentences = [
            "自然语言处理很有趣",
            "人工智能改变世界",
            "深度学习是AI的重要分支"
        ]
        print("批量分词:")
        for i, result in enumerate(client.batch_cut(sentences), 1):
            print(f"  句子{i}: {result}")


    def test8():
        print("\n=== 8. 加载用户词典 ===")
        # 测试文本
        test_text = "刘硕王桑正在开会讨论AI大数据班的项目"
        
        # 加载词典前的分词结果
        print(f"加载词典前: {client.cut(test_text)}")
        
        # 加载用户词典
        if client.load_user_dict("Base/Client/static/test_dict.txt"):
            print("用户词典加载成功！")
            
            # 加载词典后的分词结果
            print(f"加载词典后: {client.cut(test_text)}")
            
            # 验证词典中的词是否被正确识别
            words = client.cut(test_text)
            dict_words = ["刘硕", "王桑","AI大数据班"]
            recognized = [w for w in words if w in dict_words]
            print(f"词典中的词被识别: {recognized}")
        else:
            print("用户词典加载失败！")


    # test1()
    test6()
