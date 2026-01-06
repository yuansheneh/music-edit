import traceback
import logging
from functools import wraps

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def handle_exceptions(func):
    """异常处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            
            # 在Android上可以显示Toast消息
            try:
                from kivy.app import App
                app = App.get_running_app()
                if app and hasattr(app, 'show_toast'):
                    app.show_toast(f"操作失败: {str(e)[:50]}...")
            except:
                pass
            
            return None
    return wrapper

class SafeAudioLoader:
    """安全的音频加载器"""
    
    @staticmethod
    @handle_exceptions
    def load_audio(file_path: str):
        """安全加载音频文件"""
        from kivy.core.audio import SoundLoader
        
        if not file_path or not isinstance(file_path, str):
            raise ValueError("无效的文件路径")
        
        try:
            sound = SoundLoader.load(file_path)
            if sound:
                return sound
            else:
                logger.warning(f"无法加载音频文件: {file_path}")
                return None
        except Exception as e:
            logger.error(f"加载音频时出错: {e}")
            return None