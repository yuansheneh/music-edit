# -*- coding: utf-8 -*-
"""
音乐元数据管理器 - Android版（修正版）
修复了权限处理、文件扫描、UI交互等问题
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.utils import platform
from kivy.graphics import Color, RoundedRectangle

import os
import json
from pathlib import Path

# 尝试导入音频元数据库
try:
    from mutagen import File as MutagenFile
    from mutagen.easyid3 import EasyID3
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    print("警告: mutagen未安装,某些功能将受限")


class MusicFile:
    """音乐文件类,封装元数据（已修正）"""
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.title = ""
        self.artist = ""
        self.album = ""
        self.year = ""
        self.genre = ""
        self.duration = ""
        
        self.load_metadata()
    
    def load_metadata(self):
        """加载音频元数据"""
        if not MUTAGEN_AVAILABLE:
            self.title = self.filename
            return
        
        try:
            audio = MutagenFile(self.filepath, easy=True)
            if audio is None:
                self.title = self.filename
                return
            
            # 提取元数据（增强异常处理）
            self.title = self._safe_get_tag(audio, 'title', self.filename)
            self.artist = self._safe_get_tag(audio, 'artist', '未知艺术家')
            self.album = self._safe_get_tag(audio, 'album', '未知专辑')
            self.year = self._safe_get_tag(audio, 'date', '')
            self.genre = self._safe_get_tag(audio, 'genre', '')
            
            # 获取时长
            if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                duration_sec = int(audio.info.length)
                minutes = duration_sec // 60
                seconds = duration_sec % 60
                self.duration = f"{minutes}:{seconds:02d}"
                
        except Exception as e:
            print(f"加载元数据失败 {self.filename}: {e}")
            self.title = self.filename
    
    def _safe_get_tag(self, audio, tag_name, default_value):
        """安全获取标签值"""
        try:
            if tag_name in audio:
                value = audio[tag_name]
                if isinstance(value, list) and len(value) > 0:
                    return str(value[0])
                elif isinstance(value, str):
                    return value
            return default_value
        except:
            return default_value
    
    def save_metadata(self, title, artist, album, year, genre):
        """保存音频元数据（增强错误处理）"""
        if not MUTAGEN_AVAILABLE:
            return False
        
        try:
            audio = MutagenFile(self.filepath, easy=True)
            if audio is None:
                print(f"无法打开文件: {self.filepath}")
                return False
            
            # 保存元数据
            audio['title'] = [title] if title else []
            audio['artist'] = [artist] if artist else []
            audio['album'] = [album] if album else []
            
            if year:
                audio['date'] = [year]
            elif 'date' in audio:
                del audio['date']
                
            if genre:
                audio['genre'] = [genre]
            elif 'genre' in audio:
                del audio['genre']
            
            audio.save()
            
            # 更新本地数据
            self.title = title
            self.artist = artist
            self.album = album
            self.year = year
            self.genre = genre
            
            return True
            
        except PermissionError:
            print(f"权限错误: 无法写入文件 {self.filepath}")
            return False
        except Exception as e:
            print(f"保存元数据失败: {e}")
            return False
    
    def to_dict(self):
        """转换为字典"""
        return {
            'filepath': self.filepath,
            'filename': self.filename,
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'year': self.year,
            'genre': self.genre,
            'duration': self.duration
        }


class MusicListItem(BoxLayout):
    """音乐列表项组件（优化动画）"""
    title = StringProperty("")
    artist = StringProperty("")
    duration = StringProperty("")
    music_file = ObjectProperty(None)
    
    def __init__(self, music_file, **kwargs):
        super().__init__(**kwargs)
        self.music_file = music_file
        self.title = music_file.title
        self.artist = music_file.artist
        self.duration = music_file.duration
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(80)
        self.padding = dp(10)
        self.spacing = dp(10)
        
        # 优化：延迟播放淡入动画
        self.opacity = 1  # 默认可见
        
    def play_fade_in(self):
        """播放淡入动画（按需调用）"""
        self.opacity = 0
        anim = Animation(opacity=1, duration=0.2)
        anim.start(self)


class MainScreen(Screen):
    """主屏幕（修正文件扫描逻辑）"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.music_files = []
        self.filtered_files = []
        Clock.schedule_once(self.init_ui, 0)
    
    def init_ui(self, dt):
        """初始化UI"""
        # 请求权限后再加载
        if platform == 'android':
            self.request_permissions()
            Clock.schedule_once(lambda dt: self.load_music_files(), 1)
        else:
            self.load_music_files()
    
    def request_permissions(self):
        """请求Android权限（修正版）"""
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                
                # 基本权限
                permissions = [
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE
                ]
                
                request_permissions(permissions)
                
                # Android 11+ 需要额外处理
                try:
                    from android import api_version
                    if api_version >= 30:
                        # 可以引导用户到设置授权 MANAGE_EXTERNAL_STORAGE
                        print("Android 11+: 可能需要手动授予所有文件访问权限")
                except:
                    pass
                    
            except Exception as e:
                print(f"权限请求失败: {e}")
    
    def get_music_directories(self):
        """获取音乐目录路径（增强兼容性）"""
        if platform == 'android':
            try:
                from android.storage import primary_external_storage_path
                storage_path = primary_external_storage_path()
            except:
                # 备用方案
                storage_path = '/sdcard'
            
            music_dirs = [
                os.path.join(storage_path, 'Music'),
                os.path.join(storage_path, 'Download'),
                os.path.join(storage_path, 'Documents'),
                storage_path
            ]
        else:
            # 桌面系统
            home = str(Path.home())
            music_dirs = [
                os.path.join(home, 'Music'),
                os.path.join(home, 'Downloads'),
                home
            ]
        
        return [d for d in music_dirs if os.path.exists(d)]
    
    def load_music_files(self):
        """加载音乐文件（修正扫描深度）"""
        self.music_files = []
        audio_extensions = ('.mp3', '.flac', '.m4a', '.ogg', '.wav', '.opus')
        
        music_dirs = self.get_music_directories()
        print(f"扫描目录: {music_dirs}")
        
        for music_dir in music_dirs:
            try:
                for root, dirs, files in os.walk(music_dir):
                    # 扫描当前目录的文件
                    for file in files:
                        if file.lower().endswith(audio_extensions):
                            try:
                                filepath = os.path.join(root, file)
                                music_file = MusicFile(filepath)
                                self.music_files.append(music_file)
                            except Exception as e:
                                print(f"加载文件失败 {file}: {e}")
                    
                    # 限制扫描深度为1级子目录
                    depth = root[len(music_dir):].count(os.sep)
                    if depth >= 1:
                        dirs[:] = []  # 清空dirs阻止更深层扫描
                        
            except PermissionError:
                print(f"无权限访问: {music_dir}")
            except Exception as e:
                print(f"扫描目录失败 {music_dir}: {e}")
        
        print(f"找到 {len(self.music_files)} 个音频文件")
        self.filtered_files = self.music_files.copy()
        self.update_music_list()
    
    def update_music_list(self):
        """更新音乐列表显示"""
        container = self.ids.music_list_container
        container.clear_widgets()
        
        if not self.filtered_files:
            no_music_label = Label(
                text="未找到音乐文件\n请将音乐放入Music或Download文件夹\n并确保已授予存储权限",
                halign='center',
                size_hint_y=None,
                height=dp(100),
                color=(0.4, 0.4, 0.4, 1)
            )
            container.add_widget(no_music_label)
            return
        
        for music_file in self.filtered_files:
            item = MusicListItem(music_file)
            item.bind(on_touch_down=lambda instance, touch, mf=music_file: 
                     self.on_music_item_click(instance, touch, mf))
            container.add_widget(item)
    
    def on_music_item_click(self, instance, touch, music_file):
        """音乐项点击事件"""
        if instance.collide_point(*touch.pos):
            self.show_detail_screen(music_file)
            return True
    
    def show_detail_screen(self, music_file):
        """显示详情屏幕"""
        detail_screen = self.manager.get_screen('detail')
        detail_screen.set_music_file(music_file)
        self.manager.transition = SlideTransition(direction='left')
        self.manager.current = 'detail'
    
    def search_music(self, search_text):
        """搜索音乐"""
        if not search_text:
            self.filtered_files = self.music_files.copy()
        else:
            search_lower = search_text.lower()
            self.filtered_files = [
                mf for mf in self.music_files
                if search_lower in mf.title.lower() or 
                   search_lower in mf.artist.lower() or
                   search_lower in mf.album.lower()
            ]
        
        self.update_music_list()
    
    def refresh_list(self):
        """刷新列表"""
        # 旋转动画
        try:
            refresh_btn = self.ids.refresh_button
            anim = Animation(rotation=360, duration=0.5)
            anim.bind(on_complete=lambda *args: setattr(refresh_btn, 'rotation', 0))
            anim.start(refresh_btn)
        except:
            pass
        
        self.load_music_files()


class DetailScreen(Screen):
    """详情屏幕（修正Toast和安全检查）"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_music_file = None
    
    def set_music_file(self, music_file):
        """设置当前音乐文件（增加安全检查）"""
        self.current_music_file = music_file
        
        # 确保UI已初始化
        if not hasattr(self, 'ids') or not self.ids:
            Clock.schedule_once(lambda dt: self.set_music_file(music_file), 0.1)
            return
        
        try:
            # 更新UI
            self.ids.title_input.text = music_file.title or ""
            self.ids.artist_input.text = music_file.artist or ""
            self.ids.album_input.text = music_file.album or ""
            self.ids.year_input.text = music_file.year or ""
            self.ids.genre_input.text = music_file.genre or ""
            self.ids.filename_label.text = f"文件名: {music_file.filename}"
            self.ids.duration_label.text = f"时长: {music_file.duration}"
        except AttributeError as e:
            print(f"UI未就绪: {e}")
            Clock.schedule_once(lambda dt: self.set_music_file(music_file), 0.1)
    
    def save_metadata(self):
        """保存元数据"""
        if not self.current_music_file:
            self.show_toast("没有选择文件", success=False)
            return
        
        try:
            title = self.ids.title_input.text.strip()
            artist = self.ids.artist_input.text.strip()
            album = self.ids.album_input.text.strip()
            year = self.ids.year_input.text.strip()
            genre = self.ids.genre_input.text.strip()
            
            # 验证输入
            if not title:
                self.show_toast("标题不能为空", success=False)
                return
            
            if self.current_music_file.save_metadata(title, artist, album, year, genre):
                self.show_toast("保存成功!", success=True)
                Clock.schedule_once(lambda dt: self.go_back(), 1)
            else:
                self.show_toast("保存失败,请检查权限", success=False)
                
        except Exception as e:
            print(f"保存时发生错误: {e}")
            self.show_toast("保存失败", success=False)
    
    def go_back(self):
        """返回主屏幕"""
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'main'
        # 刷新主屏幕列表
        main_screen = self.manager.get_screen('main')
        main_screen.update_music_list()
    
    def show_toast(self, message, success=True):
        """显示提示消息（修正版）"""
        toast_view = ModalView(
            size_hint=(None, None),
            size=(dp(250), dp(80)),
            auto_dismiss=True,
            background='',
            background_color=(0, 0, 0, 0)
        )
        
        # 创建带背景的容器
        container = BoxLayout(orientation='vertical')
        
        # 绘制圆角背景
        with container.canvas.before:
            Color(0.2, 0.7, 0.3, 0.9) if success else Color(0.8, 0.3, 0.2, 0.9)
            self.toast_rect = RoundedRectangle(
                pos=container.pos, 
                size=container.size,
                radius=[dp(10),]
            )
        
        def update_rect(instance, value):
            self.toast_rect.pos = instance.pos
            self.toast_rect.size = instance.size
        
        container.bind(pos=update_rect, size=update_rect)
        
        # 添加文字
        label = Label(
            text=message,
            color=(1, 1, 1, 1),
            font_size=dp(16),
            bold=True
        )
        container.add_widget(label)
        
        toast_view.add_widget(container)
        toast_view.open()
        
        Clock.schedule_once(lambda dt: toast_view.dismiss(), 1.5)


class MusicMetadataApp(App):
    """音乐元数据管理器主应用"""
    
    def build(self):
        Window.clearcolor = (0.95, 0.95, 0.95, 1)
        
        # 创建屏幕管理器
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(DetailScreen(name='detail'))
        
        return sm
    
    def on_start(self):
        """应用启动时"""
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE
                ])
            except Exception as e:
                print(f"权限请求失败: {e}")


if __name__ == '__main__':
    MusicMetadataApp().run()
