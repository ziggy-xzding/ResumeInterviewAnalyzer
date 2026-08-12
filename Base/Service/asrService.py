import logging
import os

from Base.Client import get_asr_client
from Base.RicUtils.audioFileUtils import AudioFileHandler
from Base.RicUtils.redisUtils import cache_with_params

logger = logging.getLogger(__name__)

@cache_with_params(key_template="audio_2_text_with_cache:{audio_path}{max_workers}", expire=3600)
def audio_file_2_text_with_cache(audio_path: str, max_workers: int = 50):
    """
    Redis 缓存封装版本 audio_file_2_text
    :param audio_path:
    :param max_workers:
    :return:
    """
    temp_file_list = []
    try:

        handler = AudioFileHandler()
        # 将文件拆成碎片
        temp_file_list = handler.split_audio_with_overlap_ffmpeg(input_audio_path=audio_path
                                                                 , max_segment_duration=100
                                                                 , overlap_duration=2
                                                                 , output_format='wav')
        result = get_asr_client().audio_2_text(file_path=temp_file_list,max_workers=max_workers)

        return result
    except Exception as e:
        logger.error(f"音频文件转文本失败：{e}")
        raise e
    finally:
        for file in temp_file_list:
            if os.path.exists(file):
                os.remove(file)