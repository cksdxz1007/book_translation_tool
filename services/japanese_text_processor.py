import re
import logging
from janome.tokenizer import Tokenizer

logger = logging.getLogger(__name__)

class JapaneseTextProcessor:
    """日文文本处理器"""
    
    def __init__(self):
        try:
            self.tokenizer = Tokenizer()
        except Exception as e:
            logger.warning(f"日文分词器初始化失败: {e}")
            self.tokenizer = None
    
    def is_japanese_text(self, text):
        """检测是否为日文文本"""
        # 检测平假名、片假名、汉字
        japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'
        japanese_chars = len(re.findall(japanese_pattern, text))
        total_chars = len(re.sub(r'\s', '', text))
        
        if total_chars == 0:
            return False
        
        # 如果日文字符占比超过30%，认为是日文文本
        return japanese_chars / total_chars > 0.3
    
    def detect_vertical_text_markers(self, text):
        """检测直排文本标记"""
        vertical_markers = [
            '｜',  # 竖线
            '︙',  # 垂直省略号
            '︰',  # 垂直冒号
            '︱',  # 垂直线
        ]
        return any(marker in text for marker in vertical_markers)
    
    def split_japanese_sentences(self, text):
        """日文句子分割"""
        # 日文句号、问号、感叹号
        sentence_endings = r'[。！？]'
        sentences = re.split(sentence_endings, text)
        
        # 重新添加标点符号
        result = []
        for i, sentence in enumerate(sentences[:-1]):
            if sentence.strip():
                # 找到对应的标点符号
                match = re.search(sentence_endings, text[len(''.join(sentences[:i+1])):])
                if match:
                    result.append(sentence.strip() + match.group())
                else:
                    result.append(sentence.strip())
        
        # 添加最后一个句子（如果有内容）
        if sentences[-1].strip():
            result.append(sentences[-1].strip())
        
        return [s for s in result if s.strip()]
    
    def tokenize_japanese(self, text):
        """日文分词"""
        if not self.tokenizer:
            return [text]
        
        try:
            tokens = []
            for token in self.tokenizer.tokenize(text):
                tokens.append(token.surface)
            return tokens
        except Exception as e:
            logger.error(f"日文分词失败: {e}")
            return [text]
