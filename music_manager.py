import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import threading
from datetime import datetime
import sqlite3

# Kivy相关导入
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.properties import (
    StringProperty, NumericProperty, ListProperty, 
    BooleanProperty, ObjectProperty
)
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp, sp

# 音频元数据读取
try:
    from mutagen import File
    from mutagen.flac import FLAC
    from mutagen.wav import WAVE
    from mutagen.mp3 import MP3
    from mutagen.oggvorbis import OggVorbis
    from mutagen.mp4 import MP4
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

# 数据库配置
DB_NAME = "music_library.db"

class MusicDatabase:
    """歌曲数据库管理"""
    
    def __init__(self):
        self.conn = None
        self.setup_database()
    
    def setup_database(self):
        """初始化数据库"""
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = self.conn.cursor()
        
        # 创建歌曲表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                file_size INTEGER,
                file_format TEXT,
                title TEXT,
                artist TEXT,
                album TEXT,
                track_number INTEGER,
                year INTEGER,
                genre TEXT,
                duration REAL,
                bitrate INTEGER,
                sample_rate INTEGER,
                channels INTEGER,
                last_modified TIMESTAMP,
                play_count INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 0,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建播放列表表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建播放列表-歌曲关联表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlist_songs (
                playlist_id INTEGER,
                song_id INTEGER,
                position INTEGER,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
                PRIMARY KEY (playlist_id, song_id)
            )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_songs_album ON songs(album)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_songs_genre ON songs(genre)')
        
        self.conn.commit()
    
    def add_song(self, song_data: Dict) -> int:
        """添加歌曲到数据库"""
        cursor = self.conn.cursor()
        
        # 检查歌曲是否已存在
        cursor.execute('SELECT id FROM songs WHERE file_path = ?', 
                      (song_data['file_path'],))
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            cursor.execute('''
                UPDATE songs SET
                file_size = ?, file_format = ?, title = ?, artist = ?,
                album = ?, track_number = ?, year = ?, genre = ?,
                duration = ?, bitrate = ?, sample_rate = ?, channels = ?,
                last_modified = ?, file_name = ?
                WHERE file_path = ?
            ''', (
                song_data.get('file_size'),
                song_data.get('file_format'),
                song_data.get('title'),
                song_data.get('artist'),
                song_data.get('album'),
                song_data.get('track_number'),
                song_data.get('year'),
                song_data.get('genre'),
                song_data.get('duration'),
                song_data.get('bitrate'),
                song_data.get('sample_rate'),
                song_data.get('channels'),
                song_data.get('last_modified'),
                song_data.get('file_name'),
                song_data['file_path']
            ))
            song_id = existing[0]
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO songs (
                    file_path, file_name, file_size, file_format,
                    title, artist, album, track_number, year, genre,
                    duration, bitrate, sample_rate, channels, last_modified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                song_data['file_path'],
                song_data.get('file_name'),
                song_data.get('file_size'),
                song_data.get('file_format'),
                song_data.get('title'),
                song_data.get('artist'),
                song_data.get('album'),
                song_data.get('track_number'),
                song_data.get('year'),
                song_data.get('genre'),
                song_data.get('duration'),
                song_data.get('bitrate'),
                song_data.get('sample_rate'),
                song_data.get('channels'),
                song_data.get('last_modified')
            ))
            song_id = cursor.lastrowid
        
        self.conn.commit()
        return song_id
    
    def get_songs(self, filter_by: str = None, search_term: str = None) -> List[Dict]:
        """获取歌曲列表"""
        cursor = self.conn.cursor()
        
        query = '''
            SELECT 
                id, file_path, file_name, file_format, title, 
                artist, album, genre, duration, play_count, rating
            FROM songs
        '''
        params = []
        
        if filter_by and search_term:
            if filter_by == 'artist':
                query += ' WHERE artist LIKE ?'
                params.append(f'%{search_term}%')
            elif filter_by == 'album':
                query += ' WHERE album LIKE ?'
                params.append(f'%{search_term}%')
            elif filter_by == 'genre':
                query += ' WHERE genre LIKE ?'
                params.append(f'%{search_term}%')
            elif filter_by == 'title':
                query += ' WHERE title LIKE ? OR file_name LIKE ?'
                params.extend([f'%{search_term}%', f'%{search_term}%'])
        
        query += ' ORDER BY artist, album, track_number, title'
        cursor.execute(query, params)
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def update_play_count(self, song_id: int):
        """更新播放次数"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE songs SET play_count = play_count + 1 
            WHERE id = ?
        ''', (song_id,))
        self.conn.commit()
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

class AudioFileScanner:
    """音频文件扫描器"""
    
    SUPPORTED_FORMATS = {
        '.flac': 'FLAC',
        '.wav': 'WAV',
        '.mp3': 'MP3',
        '.ogg': 'OGG',
        '.m4a': 'M4A',
        '.aac': 'AAC',
        '.wma': 'WMA',
        '.ape': 'APE'
    }
    
    @staticmethod
    def is_supported_format(filename: str) -> bool:
        """检查文件格式是否受支持"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in AudioFileScanner.SUPPORTED_FORMATS
    
    @staticmethod
    def get_audio_info(file_path: str) -> Dict:
        """获取音频文件信息"""
        if not HAS_MUTAGEN:
            return AudioFileScanner._get_basic_info(file_path)
        
        try:
            file_path = str(file_path)
            audio = File(file_path, easy=True)
            
            if audio is None:
                return AudioFileScanner._get_basic_info(file_path)
            
            # 获取通用信息
            info = AudioFileScanner._get_basic_info(file_path)
            
            # 尝试获取元数据
            try:
                info['title'] = audio.get('title', [info['file_name']])[0]
                info['artist'] = audio.get('artist', ['Unknown Artist'])[0]
                info['album'] = audio.get('album', ['Unknown Album'])[0]
                info['genre'] = audio.get('genre', ['Unknown'])[0]
                
                # 获取音轨号
                track = audio.get('tracknumber', ['0'])[0]
                if isinstance(track, str):
                    track = track.split('/')[0]
                info['track_number'] = int(track) if track.isdigit() else 0
                
                # 获取年份
                year = audio.get('date', ['0'])[0]
                if isinstance(year, str) and year.isdigit():
                    info['year'] = int(year)
                else:
                    info['year'] = 0
                
                # 获取音频技术信息
                if hasattr(audio.info, 'length'):
                    info['duration'] = audio.info.length
                
                if hasattr(audio.info, 'bitrate'):
                    info['bitrate'] = audio.info.bitrate // 1000 if audio.info.bitrate else 0
                
                if hasattr(audio.info, 'sample_rate'):
                    info['sample_rate'] = audio.info.sample_rate
                
                if hasattr(audio.info, 'channels'):
                    info['channels'] = audio.info.channels
                    
            except (KeyError, IndexError, AttributeError, ValueError) as e:
                print(f"Error reading metadata from {file_path}: {e}")
                # 如果读取元数据失败，使用基本信息
            
            return info
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return AudioFileScanner._get_basic_info(file_path)
    
    @staticmethod
    def _get_basic_info(file_path: str) -> Dict:
        """获取文件基本信息"""
        file_path = str(file_path)
        try:
            stat = os.stat(file_path)
            file_name = os.path.basename(file_path)
            ext = os.path.splitext(file_name)[1].lower()
            
            # 从文件名猜测标题
            title = os.path.splitext(file_name)[0]
            # 尝试从文件名中提取艺术家和标题（常见格式：艺术家 - 标题）
            if ' - ' in title:
                parts = title.split(' - ', 1)
                artist = parts[0].strip()
                title = parts[1].strip()
            else:
                artist = 'Unknown Artist'
            
            return {
                'file_path': file_path,
                'file_name': file_name,
                'file_format': AudioFileScanner.SUPPORTED_FORMATS.get(ext, 'Unknown'),
                'file_size': stat.st_size,
                'title': title,
                'artist': artist,
                'album': 'Unknown Album',
                'track_number': 0,
                'year': 0,
                'genre': 'Unknown',
                'duration': 0,
                'bitrate': 0,
                'sample_rate': 0,
                'channels': 0,
                'last_modified': datetime.fromtimestamp(stat.st_mtime)
            }
        except Exception as e:
            print(f"Error getting basic info for {file_path}: {e}")
            return {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_format': 'Unknown',
                'file_size': 0,
                'title': 'Unknown Title',
                'artist': 'Unknown Artist',
                'album': 'Unknown Album',
                'track_number': 0,
                'year': 0,
                'genre': 'Unknown',
                'duration': 0,
                'bitrate': 0,
                'sample_rate': 0,
                'channels': 0,
                'last_modified': datetime.now()
            }

class SongItem(ButtonBehavior, BoxLayout):
    """歌曲列表项"""
    title = StringProperty('')
    artist = StringProperty('')
    album = StringProperty('')
    duration = StringProperty('')
    song_id = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(60)

class SongList(RecycleView):
    """歌曲列表视图"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.layout = RecycleBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(2)
        )
        self.layout.bind(minimum_height=self.layout.setter('height'))
        
        self.viewclass = 'SongItem'
        self.add_widget(self.layout)

class MusicPlayer:
    """音乐播放器"""
    def __init__(self):
        self.current_song = None
        self.sound = None
        self.is_playing = False
        self.volume = 1.0
        
    def load_song(self, file_path: str):
        """加载歌曲"""
        self.stop()
        self.current_song = file_path
        
        try:
            self.sound = SoundLoader.load(file_path)
            if self.sound:
                self.sound.volume = self.volume
                return True
            else:
                print(f"Failed to load sound: {file_path}")
                return False
        except Exception as e:
            print(f"Error loading song {file_path}: {e}")
            return False
    
    def play(self):
        """播放歌曲"""
        if self.sound and not self.is_playing:
            self.sound.play()
            self.is_playing = True
            return True
        return False
    
    def pause(self):
        """暂停播放"""
        if self.sound and self.is_playing:
            self.sound.stop()
            self.is_playing = False
            return True
        return False
    
    def stop(self):
        """停止播放"""
        if self.sound:
            self.sound.stop()
            self.is_playing = False
            self.sound.unload()
            self.sound = None
        return True
    
    def set_volume(self, volume: float):
        """设置音量"""
        self.volume = max(0.0, min(1.0, volume))
        if self.sound:
            self.sound.volume = self.volume
    
    def get_position(self) -> float:
        """获取播放位置"""
        if self.sound and hasattr(self.sound, 'get_pos'):
            return self.sound.get_pos()
        return 0.0
    
    def get_duration(self) -> float:
        """获取歌曲时长"""
        if self.sound and hasattr(self.sound, 'length'):
            return self.sound.length
        return 0.0

class MusicManagerApp(App):
    """主应用"""
    
    def build(self):
        # 设置窗口大小（用于桌面测试）
        if not self.is_android():
            Window.size = (400, 700)
        
        # 初始化组件
        self.db = MusicDatabase()
        self.scanner = AudioFileScanner()
        self.player = MusicPlayer()
        
        # 创建主布局
        self.root = BoxLayout(orientation='vertical')
        
        # 创建顶部控制栏
        self.create_top_bar()
        
        # 创建搜索栏
        self.create_search_bar()
        
        # 创建歌曲列表
        self.create_song_list()
        
        # 创建底部控制栏
        self.create_bottom_bar()
        
        # 加载现有歌曲
        self.load_songs()
        
        return self.root
    
    def create_top_bar(self):
        """创建顶部控制栏"""
        top_bar = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10),
            padding=[dp(10), dp(5)]
        )
        
        # 扫描按钮
        scan_btn = Button(
            text='扫描音乐',
            size_hint_x=None,
            width=dp(100)
        )
        scan_btn.bind(on_press=self.scan_music)
        top_bar.add_widget(scan_btn)
        
        # 刷新按钮
        refresh_btn = Button(
            text='刷新',
            size_hint_x=None,
            width=dp(80)
        )
        refresh_btn.bind(on_press=lambda x: self.load_songs())
        top_bar.add_widget(refresh_btn)
        
        self.root.add_widget(top_bar)
    
    def create_search_bar(self):
        """创建搜索栏"""
        search_bar = BoxLayout(
            size_hint_y=None,
            height=dp(40),
            spacing=dp(10),
            padding=[dp(10), dp(5)]
        )
        
        # 搜索输入框
        self.search_input = TextInput(
            hint_text='搜索歌曲...',
            multiline=False,
            size_hint_x=0.7
        )
        self.search_input.bind(on_text_validate=self.on_search)
        search_bar.add_widget(self.search_input)
        
        # 搜索按钮
        search_btn = Button(
            text='搜索',
            size_hint_x=0.3
        )
        search_btn.bind(on_press=self.on_search)
        search_bar.add_widget(search_btn)
        
        self.root.add_widget(search_bar)
    
    def create_song_list(self):
        """创建歌曲列表"""
        self.song_list = ScrollView(size_hint=(1, 1))
        
        self.song_container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(2)
        )
        self.song_container.bind(minimum_height=self.song_container.setter('height'))
        
        self.song_list.add_widget(self.song_container)
        self.root.add_widget(self.song_list)
    
    def create_bottom_bar(self):
        """创建底部控制栏"""
        bottom_bar = BoxLayout(
            size_hint_y=None,
            height=dp(80),
            spacing=dp(10),
            padding=[dp(10), dp(5)]
        )
        
        # 播放/暂停按钮
        self.play_btn = Button(
            text='播放',
            size_hint_x=0.3
        )
        self.play_btn.bind(on_press=self.toggle_play)
        bottom_bar.add_widget(self.play_btn)
        
        # 上一首按钮
        prev_btn = Button(
            text='上一首',
            size_hint_x=0.2
        )
        prev_btn.bind(on_press=self.play_previous)
        bottom_bar.add_widget(prev_btn)
        
        # 下一首按钮
        next_btn = Button(
            text='下一首',
            size_hint_x=0.2
        )
        next_btn.bind(on_press=self.play_next)
        bottom_bar.add_widget(next_btn)
        
        # 音量控制
        self.volume_slider = ProgressBar(
            max=100,
            value=80,
            size_hint_x=0.3
        )
        bottom_bar.add_widget(self.volume_slider)
        
        self.root.add_widget(bottom_bar)
    
    def load_songs(self, filter_by: str = None, search_term: str = None):
        """加载歌曲到列表"""
        # 清空当前列表
        self.song_container.clear_widgets()
        
        # 从数据库获取歌曲
        songs = self.db.get_songs(filter_by, search_term)
        
        for song in songs:
            # 格式化时长
            duration = song.get('duration', 0)
            if duration > 0:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "未知"
            
            # 创建歌曲项
            song_item = SongItem(
                title=song.get('title', song.get('file_name', '未知标题')),
                artist=song.get('artist', '未知艺术家'),
                album=song.get('album', '未知专辑'),
                duration=duration_str,
                song_id=song['id']
            )
            song_item.bind(on_press=lambda x, s=song: self.play_song(s))
            
            self.song_container.add_widget(song_item)
    
    def scan_music(self, instance):
        """扫描音乐文件"""
        # 在Android上，使用特定目录
        if self.is_android():
            from android.storage import primary_external_storage_path
            music_dirs = [
                os.path.join(primary_external_storage_path(), 'Music'),
                os.path.join(primary_external_storage_path(), 'Download'),
                os.path.join(primary_external_storage_path(), 'Documents')
            ]
        else:
            # 在桌面系统上，使用示例目录
            music_dirs = [
                os.path.expanduser('~/Music'),
                os.path.expanduser('~/Downloads')
            ]
        
        # 创建进度弹窗
        popup = Popup(
            title='正在扫描...',
            size_hint=(0.8, 0.3)
        )
        progress = ProgressBar(max=100, value=0)
        popup.add_widget(progress)
        popup.open()
        
        def scan_in_thread():
            """在后台线程中扫描"""
            found_files = []
            
            for music_dir in music_dirs:
                if os.path.exists(music_dir):
                    for root, dirs, files in os.walk(music_dir):
                        for file in files:
                            if self.scanner.is_supported_format(file):
                                file_path = os.path.join(root, file)
                                found_files.append(file_path)
            
            # 处理文件
            total = len(found_files)
            for i, file_path in enumerate(found_files, 1):
                try:
                    # 获取音频信息
                    audio_info = self.scanner.get_audio_info(file_path)
                    
                    # 添加到数据库
                    self.db.add_song(audio_info)
                    
                    # 更新进度
                    progress.value = (i / total) * 100
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
            
            # 关闭弹窗并刷新列表
            Clock.schedule_once(lambda dt: popup.dismiss(), 0)
            Clock.schedule_once(lambda dt: self.load_songs(), 0)
        
        # 启动扫描线程
        threading.Thread(target=scan_in_thread, daemon=True).start()
    
    def play_song(self, song_data: Dict):
        """播放歌曲"""
        try:
            file_path = song_data['file_path']
            
            if self.player.load_song(file_path):
                if self.player.play():
                    # 更新播放次数
                    self.db.update_play_count(song_data['id'])
                    
                    # 更新播放按钮文本
                    self.play_btn.text = '暂停'
                    
                    print(f"正在播放: {song_data.get('title', '未知标题')}")
                else:
                    print("播放失败")
            else:
                print("加载歌曲失败")
                
        except Exception as e:
            print(f"播放错误: {e}")
    
    def toggle_play(self, instance):
        """切换播放/暂停"""
        if self.player.is_playing:
            self.player.pause()
            self.play_btn.text = '播放'
        else:
            if self.player.play():
                self.play_btn.text = '暂停'
    
    def play_previous(self, instance):
        """播放上一首"""
        # 实现播放上一首的逻辑
        print("播放上一首")
    
    def play_next(self, instance):
        """播放下一首"""
        # 实现播放下一首的逻辑
        print("播放下一首")
    
    def on_search(self, instance):
        """处理搜索"""
        search_term = self.search_input.text.strip()
        if search_term:
            self.load_songs(filter_by='title', search_term=search_term)
        else:
            self.load_songs()
    
    def is_android(self) -> bool:
        """检查是否在Android平台上运行"""
        try:
            from kivy.utils import platform
            return platform == 'android'
        except:
            return False
    
    def on_stop(self):
        """应用停止时清理资源"""
        self.player.stop()
        self.db.close()

if __name__ == '__main__':
    MusicManagerApp().run()