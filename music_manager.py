import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Kivy相关导入
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.slider import Slider
from kivy.uix.switch import Switch
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.utils import platform
from kivy.metrics import dp, sp

# 修复：只导入实际存在的模块
from core.database import MusicDatabase
from core.scanner import AudioFileScanner
from core.equalizer import AudioEqualizer
from core.queue import PlayQueue
from core.timer import SleepTimer

class EnhancedMusicPlayer:
    """增强版音乐播放器（修正版）"""
    
    def __init__(self):
        self.sound = None
        self.is_playing = False
        self.volume = 1.0
        self.playback_speed = 1.0
        self.fade_duration = 0
        self.equalizer = AudioEqualizer()
        self.current_song_path = None
        
    def load(self, file_path):
        """加载音频文件"""
        try:
            self.stop()
            self.current_song_path = file_path
            
            if not os.path.exists(file_path):
                print(f"文件不存在: {file_path}")
                return False
            
            self.sound = SoundLoader.load(file_path)
            if self.sound:
                self.sound.volume = self.volume
                return True
            else:
                print(f"无法加载音频文件: {file_path}")
                return False
        except Exception as e:
            print(f"加载音频失败: {e}")
            return False
    
    def play(self, fade_in=False):
        """播放音频"""
        if self.sound and not self.is_playing:
            try:
                self.sound.play()
                self.is_playing = True
                return True
            except Exception as e:
                print(f"播放失败: {e}")
                return False
        return False
    
    def pause(self):
        """暂停音频"""
        if self.sound and self.is_playing:
            try:
                self.sound.stop()  # Kivy SoundLoader使用stop()暂停
                self.is_playing = False
                return True
            except Exception as e:
                print(f"暂停失败: {e}")
                return False
        return False
    
    def stop(self):
        """停止音频"""
        if self.sound:
            try:
                self.sound.stop()
                self.is_playing = False
                self.sound.unload()
                self.sound = None
                self.current_song_path = None
                return True
            except Exception as e:
                print(f"停止失败: {e}")
                return False
        return True
    
    def get_position(self):
        """获取当前位置"""
        try:
            if self.sound and hasattr(self.sound, 'get_pos'):
                return self.sound.get_pos()
        except:
            pass
        return 0
    
    def get_duration(self):
        """获取总时长"""
        try:
            if self.sound and hasattr(self.sound, 'length'):
                return self.sound.length
        except:
            pass
        return 0

class MusicManagerApp(App):
    """主应用 - 修正版"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 初始化核心组件
        self.db = MusicDatabase("music_library.db")
        self.scanner = AudioFileScanner()
        self.player = EnhancedMusicPlayer()
        self.queue = PlayQueue(self.db)
        self.sleep_timer = SleepTimer(notification_callback=self.show_notification)
        
        # 应用状态
        self.current_song_id = None
        self.dark_mode = False
        self.song_cache = {}
        self.album_cache = {}
        self.artist_cache = {}
        
        # UI组件引用
        self.search_input = None
        self.play_btn = None
        self.volume_slider = None
        self.song_container = None
        
    def build(self):
        """构建应用界面"""
        # 设置窗口大小
        if platform != 'android':
            Window.size = (400, 700)
            Window.minimum_width = 400
            Window.minimum_height = 600
        
        # 创建主布局
        self.root = BoxLayout(orientation='vertical')
        
        # 创建各个界面组件
        self.create_top_bar()
        self.create_search_bar()
        self.create_song_list()
        self.create_bottom_bar()
        
        # 加载数据
        Clock.schedule_once(lambda dt: self.initialize_app(), 0.5)
        
        return self.root
    
    def initialize_app(self):
        """初始化应用"""
        print("初始化应用...")
        self.load_songs()
        
        # 请求Android权限
        if self.is_android():
            Clock.schedule_once(lambda dt: self.request_android_permissions(), 1)
    
    def is_android(self):
        """检查是否在Android平台"""
        return platform == 'android'
    
    def request_android_permissions(self):
        """请求Android权限（修正版）"""
        if not self.is_android():
            return
            
        try:
            from android.permissions import request_permissions, Permission, check_permission
            
            # 修正权限列表
            required_permissions = [
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.RECORD_AUDIO,
                Permission.MODIFY_AUDIO_SETTINGS,
                Permission.WAKE_LOCK,
            ]
            
            # 检查哪些权限还没有被授予
            permissions_to_request = []
            for perm in required_permissions:
                if not check_permission(perm):
                    permissions_to_request.append(perm)
            
            if permissions_to_request:
                # 异步请求权限
                def permission_callback(permissions, grant_results):
                    granted = all(grant_results)
                    if granted:
                        print("所有权限已授予")
                        # 权限获取后扫描音乐
                        Clock.schedule_once(lambda dt: self.scan_music(None), 0.5)
                    else:
                        print("部分权限被拒绝")
                        self.show_toast("部分权限被拒绝，某些功能可能无法使用")
                
                request_permissions(permissions_to_request, permission_callback)
            else:
                print("所有必需权限已授予")
                # 扫描音乐
                Clock.schedule_once(lambda dt: self.scan_music(None), 0.5)
                
        except ImportError:
            print("不在Android平台或无法导入android模块")
        except Exception as e:
            print(f"权限请求失败: {e}")
    
    def create_top_bar(self):
        """创建顶部控制栏（修正版）"""
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
        
        # 设置按钮
        settings_btn = Button(
            text='设置',
            size_hint_x=None,
            width=dp(80)
        )
        settings_btn.bind(on_press=self.show_settings)
        top_bar.add_widget(settings_btn)
        
        self.root.add_widget(top_bar)
    
    def create_search_bar(self):
        """创建搜索栏"""
        search_bar = BoxLayout(
            size_hint_y=None,
            height=dp(40),
            spacing=dp(10),
            padding=[dp(10), dp(5)]
        )
        
        self.search_input = TextInput(
            hint_text='搜索歌曲...',
            multiline=False,
            size_hint_x=0.7
        )
        self.search_input.bind(on_text_validate=self.on_search)
        search_bar.add_widget(self.search_input)
        
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
        """创建底部控制栏（增强版）"""
        bottom_bar = BoxLayout(
            size_hint_y=None,
            height=dp(100),
            spacing=dp(10),
            padding=[dp(10), dp(5)]
        )
        
        # 左侧：歌曲信息
        song_info = BoxLayout(
            orientation='vertical',
            size_hint_x=0.3,
            spacing=dp(2)
        )
        
        self.current_title_label = Label(
            text='未选择歌曲',
            size_hint_y=None,
            height=dp(20),
            halign='left',
            text_size=(dp(150), None)
        )
        
        self.current_artist_label = Label(
            text='-',
            size_hint_y=None,
            height=dp(15),
            font_size=sp(12),
            color=[0.7, 0.7, 0.7, 1],
            halign='left',
            text_size=(dp(150), None)
        )
        
        song_info.add_widget(self.current_title_label)
        song_info.add_widget(self.current_artist_label)
        bottom_bar.add_widget(song_info)
        
        # 中间：播放控制
        controls = BoxLayout(
            orientation='horizontal',
            size_hint_x=0.5,
            spacing=dp(5)
        )
        
        prev_btn = Button(
            text='上一首',
            size_hint_x=0.2
        )
        prev_btn.bind(on_press=self.play_previous)
        controls.add_widget(prev_btn)
        
        self.play_btn = Button(
            text='播放',
            size_hint_x=0.3
        )
        self.play_btn.bind(on_press=self.toggle_play)
        controls.add_widget(self.play_btn)
        
        next_btn = Button(
            text='下一首',
            size_hint_x=0.2
        )
        next_btn.bind(on_press=self.play_next)
        controls.add_widget(next_btn)
        
        # 进度条
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_x=0.3
        )
        controls.add_widget(self.progress_bar)
        
        bottom_bar.add_widget(controls)
        
        # 右侧：音量和附加功能
        right_panel = BoxLayout(
            orientation='vertical',
            size_hint_x=0.2,
            spacing=dp(2)
        )
        
        # 音量控制
        volume_box = BoxLayout(size_hint_y=None, height=dp(30))
        volume_box.add_widget(Label(text='音量:', size_hint_x=0.3))
        
        self.volume_slider = Slider(
            min=0,
            max=100,
            value=80,
            size_hint_x=0.7
        )
        self.volume_slider.bind(value=self.on_volume_change)
        volume_box.add_widget(self.volume_slider)
        
        right_panel.add_widget(volume_box)
        
        # 附加功能按钮
        extra_buttons = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(2))
        
        eq_btn = Button(
            text='均衡器',
            size_hint_x=0.5,
            font_size=sp(10)
        )
        eq_btn.bind(on_press=self.show_equalizer)
        extra_buttons.add_widget(eq_btn)
        
        timer_btn = Button(
            text='定时器',
            size_hint_x=0.5,
            font_size=sp(10)
        )
        timer_btn.bind(on_press=self.show_sleep_timer)
        extra_buttons.add_widget(timer_btn)
        
        right_panel.add_widget(extra_buttons)
        
        bottom_bar.add_widget(right_panel)
        
        self.root.add_widget(bottom_bar)
        
        # 启动进度更新定时器
        Clock.schedule_interval(self.update_progress, 0.5)
    
    def load_songs(self, filter_by=None, search_term=None):
        """加载歌曲到列表（修正版）"""
        # 清空当前列表
        self.song_container.clear_widgets()
        
        # 显示加载中
        loading = Label(
            text='加载中...',
            size_hint_y=None,
            height=dp(40)
        )
        self.song_container.add_widget(loading)
        
        def load_in_background():
            """在后台加载歌曲"""
            try:
                songs = self.db.get_songs(filter_by, search_term)
                Clock.schedule_once(lambda dt: self.render_songs(songs), 0)
            except Exception as e:
                print(f"加载歌曲失败: {e}")
                Clock.schedule_once(lambda dt: self.show_error("加载失败"), 0)
        
        threading.Thread(target=load_in_background, daemon=True).start()
    
    def render_songs(self, songs):
        """渲染歌曲列表"""
        self.song_container.clear_widgets()
        
        if not songs:
            empty_label = Label(
                text='没有找到歌曲',
                size_hint_y=None,
                height=dp(40)
            )
            self.song_container.add_widget(empty_label)
            return
        
        for song in songs:
            # 创建歌曲项
            song_item = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(60),
                spacing=dp(5),
                padding=[dp(10), dp(5)]
            )
            
            # 歌曲信息
            info_box = BoxLayout(orientation='vertical', size_hint_x=0.7)
            
            title_label = Label(
                text=song.get('title', song.get('file_name', '未知标题')),
                size_hint_y=0.6,
                halign='left',
                text_size=(dp(250), None)
            )
            
            artist_album = f"{song.get('artist', '未知艺术家')} - {song.get('album', '未知专辑')}"
            artist_label = Label(
                text=artist_album,
                size_hint_y=0.4,
                font_size=sp(12),
                color=[0.7, 0.7, 0.7, 1],
                halign='left',
                text_size=(dp(250), None)
            )
            
            info_box.add_widget(title_label)
            info_box.add_widget(artist_label)
            
            # 时长
            duration = song.get('duration', 0)
            if duration > 0:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "0:00"
            
            duration_label = Label(
                text=duration_str,
                size_hint_x=0.15,
                font_size=sp(12)
            )
            
            # 操作按钮
            action_box = BoxLayout(size_hint_x=0.15, spacing=dp(2))
            
            play_btn = Button(
                text='▶',
                size_hint_x=0.5,
                font_size=sp(12)
            )
            play_btn.bind(on_press=lambda x, s=song: self.play_song(s))
            
            detail_btn = Button(
                text='ℹ',
                size_hint_x=0.5,
                font_size=sp(12)
            )
            detail_btn.bind(on_press=lambda x, s=song: self.show_song_detail(s))
            
            action_box.add_widget(play_btn)
            action_box.add_widget(detail_btn)
            
            song_item.add_widget(info_box)
            song_item.add_widget(duration_label)
            song_item.add_widget(action_box)
            
            # 绑定点击事件
            song_item.bind(on_touch_down=lambda instance, touch, s=song: 
                          self.on_song_item_touch(instance, touch, s))
            
            self.song_container.add_widget(song_item)
    
    def on_song_item_touch(self, instance, touch, song):
        """处理歌曲项触摸事件"""
        if instance.collide_point(*touch.pos) and touch.is_double_tap:
            self.play_song(song)
            return True
    
    def play_song(self, song_data):
        """播放歌曲（修正版）"""
        try:
            file_path = song_data.get('file_path')
            song_id = song_data.get('id')
            
            if not file_path or not os.path.exists(file_path):
                self.show_error("歌曲文件不存在")
                return
            
            # 添加到播放队列
            self.queue.add_song(song_data, play_now=True)
            self.current_song_id = song_id
            
            # 加载并播放
            if self.player.load(file_path):
                if self.player.play():
                    # 更新播放次数
                    self.db.update_play_count(song_id)
                    
                    # 更新UI
                    self.play_btn.text = '暂停'
                    self.current_title_label.text = song_data.get('title', '未知标题')
                    self.current_artist_label.text = song_data.get('artist', '未知艺术家')
                    
                    # 更新进度条最大值
                    duration = self.player.get_duration()
                    if duration > 0:
                        self.progress_bar.max = duration
                    
                    print(f"正在播放: {song_data.get('title')}")
                else:
                    self.show_error("播放失败")
            else:
                self.show_error("加载歌曲失败")
                
        except Exception as e:
            print(f"播放错误: {e}")
            self.show_error(f"播放错误: {str(e)[:50]}")
    
    def toggle_play(self, instance):
        """切换播放/暂停"""
        if not self.player.sound:
            return
        
        if self.player.is_playing:
            if self.player.pause():
                self.play_btn.text = '播放'
        else:
            if self.player.play():
                self.play_btn.text = '暂停'
    
    def play_previous(self, instance):
        """播放上一首"""
        prev_song = self.queue.previous_song()
        if prev_song:
            self.play_song(prev_song)
    
    def play_next(self, instance):
        """播放下一首"""
        next_song = self.queue.next_song()
        if next_song:
            self.play_song(next_song)
        else:
            self.player.stop()
            self.play_btn.text = '播放'
            self.current_title_label.text = '未选择歌曲'
            self.current_artist_label.text = '-'
    
    def on_volume_change(self, instance, value):
        """音量改变"""
        volume = value / 100.0
        if self.player.sound:
            self.player.sound.volume = volume
        self.player.volume = volume
    
    def update_progress(self, dt):
        """更新播放进度"""
        if self.player.sound and self.player.is_playing:
            position = self.player.get_position()
            duration = self.player.get_duration()
            
            if duration > 0:
                self.progress_bar.value = position
    
    def scan_music(self, instance):
        """扫描音乐文件（修正版）"""
        # 获取Android音乐目录
        if self.is_android():
            try:
                from android.storage import primary_external_storage_path
                base_path = primary_external_storage_path()
                music_dirs = [
                    os.path.join(base_path, 'Music'),
                    os.path.join(base_path, 'Download'),
                    os.path.join(base_path, 'Documents')
                ]
            except:
                music_dirs = ['/sdcard/Music', '/sdcard/Download']
        else:
            music_dirs = [
                os.path.expanduser('~/Music'),
                os.path.expanduser('~/Downloads')
            ]
        
        # 创建进度弹窗
        popup_content = BoxLayout(orientation='vertical', padding=dp(10))
        popup_content.add_widget(Label(text='正在扫描音乐文件...'))
        
        progress = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(20))
        popup_content.add_widget(progress)
        
        status_label = Label(text='准备扫描...', size_hint_y=None, height=dp(20))
        popup_content.add_widget(status_label)
        
        popup = Popup(
            title='扫描音乐',
            content=popup_content,
            size_hint=(0.8, 0.4),
            auto_dismiss=False
        )
        
        def scan_thread():
            """扫描线程"""
            found_files = []
            valid_dirs = []
            
            # 找到存在的目录
            for music_dir in music_dirs:
                if os.path.exists(music_dir):
                    valid_dirs.append(music_dir)
            
            if not valid_dirs:
                Clock.schedule_once(lambda dt: self.show_error("未找到音乐目录"), 0)
                Clock.schedule_once(lambda dt: popup.dismiss(), 0)
                return
            
            total_files = 0
            for directory in valid_dirs:
                for root, dirs, files in os.walk(directory):
                    total_files += len(files)
            
            processed = 0
            
            for directory in valid_dirs:
                if os.path.exists(directory):
                    for root, dirs, files in os.walk(directory):
                        for file in files:
                            if self.scanner.is_supported_format(file):
                                file_path = os.path.join(root, file)
                                found_files.append(file_path)
                                
                                # 获取音频信息并添加到数据库
                                try:
                                    audio_info = self.scanner.get_audio_info(file_path)
                                    self.db.add_song(audio_info)
                                except Exception as e:
                                    print(f"处理文件失败 {file_path}: {e}")
                            
                            processed += 1
                            if processed % 10 == 0:  # 每10个文件更新一次进度
                                progress_value = (processed / max(1, total_files)) * 100
                                Clock.schedule_once(
                                    lambda dt, p=progress_value, f=processed, t=total_files: 
                                    update_progress(p, f, t), 0
                                )
            
            # 扫描完成
            Clock.schedule_once(
                lambda dt, count=len(found_files): 
                self.show_toast(f"扫描完成，找到 {count} 首歌曲"), 0
            )
            Clock.schedule_once(lambda dt: popup.dismiss(), 0)
            Clock.schedule_once(lambda dt: self.load_songs(), 0.5)
        
        def update_progress(value, processed, total):
            """更新进度"""
            progress.value = value
            status_label.text = f"已扫描 {processed}/{total} 个文件"
        
        # 开始扫描
        popup.open()
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def show_song_detail(self, song_data):
        """显示歌曲详情（修正版）"""
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # 歌曲标题
        title = Label(
            text=song_data.get('title', song_data.get('file_name', '未知标题')),
            size_hint_y=None,
            height=dp(30),
            font_size=sp(18),
            bold=True
        )
        content.add_widget(title)
        
        # 详细信息
        details = GridLayout(cols=2, spacing=dp(5), size_hint_y=None, height=dp(120))
        
        info_pairs = [
            ('艺术家', song_data.get('artist', '未知艺术家')),
            ('专辑', song_data.get('album', '未知专辑')),
            ('流派', song_data.get('genre', '未知')),
            ('时长', f"{int(song_data.get('duration', 0)//60)}:{int(song_data.get('duration', 0)%60):02d}"),
            ('格式', song_data.get('file_format', '未知')),
            ('比特率', f"{song_data.get('bitrate', 0)} kbps"),
        ]
        
        for label, value in info_pairs:
            details.add_widget(Label(text=label + ':', size_hint_x=0.4, halign='right'))
            details.add_widget(Label(text=str(value), size_hint_x=0.6, halign='left'))
        
        content.add_widget(details)
        
        # 操作按钮
        button_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        
        play_btn = Button(text='播放')
        play_btn.bind(on_press=lambda x: (popup.dismiss(), self.play_song(song_data)))
        
        add_btn = Button(text='添加到队列')
        add_btn.bind(on_press=lambda x: (self.queue.add_song(song_data), 
                                        self.show_toast("已添加到队列")))
        
        button_box.add_widget(play_btn)
        button_box.add_widget(add_btn)
        
        content.add_widget(button_box)
        
        popup = Popup(
            title='歌曲详情',
            content=content,
            size_hint=(0.8, 0.5)
        )
        popup.open()
    
    def show_equalizer(self, instance):
        """显示均衡器设置（修正版）"""
        eq_settings = self.player.equalizer.get_eq_settings()
        
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # 均衡器开关
        switch_box = BoxLayout(size_hint_y=None, height=dp(40))
        switch_box.add_widget(Label(text='启用均衡器:', size_hint_x=0.6))
        
        eq_switch = Switch(active=eq_settings['enabled'])
        def on_switch(switch, value):
            self.player.equalizer.set_enabled(value)
        
        eq_switch.bind(active=on_switch)
        switch_box.add_widget(eq_switch)
        content.add_widget(switch_box)
        
        # 预设选择
        preset_label = Label(
            text='预设:',
            size_hint_y=None,
            height=dp(25)
        )
        content.add_widget(preset_label)
        
        preset_grid = GridLayout(cols=3, spacing=dp(5), size_hint_y=None, height=dp(120))
        
        presets = [
            ('flat', '平直'),
            ('pop', '流行'),
            ('rock', '摇滚'),
            ('jazz', '爵士'),
            ('classical', '古典'),
            ('bass_boost', '重低音')
        ]
        
        for preset_id, preset_name in presets:
            btn = Button(
                text=preset_name,
                background_color=(0.4, 0.4, 0.8, 1) if eq_settings['preset'] == preset_id else (0.6, 0.6, 0.6, 1)
            )
            btn.bind(on_press=lambda x, pid=preset_id: self.set_equalizer_preset(pid))
            preset_grid.add_widget(btn)
        
        content.add_widget(preset_grid)
        
        # 关闭按钮
        close_btn = Button(
            text='关闭',
            size_hint_y=None,
            height=dp(40)
        )
        close_btn.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(close_btn)
        
        popup = Popup(
            title='均衡器设置',
            content=content,
            size_hint=(0.9, 0.6)
        )
        popup.open()
    
    def set_equalizer_preset(self, preset_id):
        """设置均衡器预设"""
        if self.player.equalizer.set_preset(preset_id):
            self.show_toast(f"已切换到{preset_id}预设")
    
    def show_sleep_timer(self, instance):
        """显示睡眠定时器设置（修正版）"""
        remaining = self.sleep_timer.get_remaining_time()
        is_active = self.sleep_timer.timer_active
        
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # 状态显示
        if is_active:
            mins = remaining // 60
            secs = remaining % 60
            status_text = f"定时器运行中\n剩余时间: {mins}:{secs:02d}"
        else:
            status_text = "定时器未启用"
        
        status_label = Label(
            text=status_text,
            size_hint_y=None,
            height=dp(60),
            halign='center'
        )
        content.add_widget(status_label)
        
        # 时间选择
        time_label = Label(
            text='选择定时时间:',
            size_hint_y=None,
            height=dp(25)
        )
        content.add_widget(time_label)
        
        time_grid = GridLayout(cols=3, spacing=dp(5), size_hint_y=None, height=dp(80))
        
        times = [15, 30, 45, 60, 90, 120]
        for minutes in times:
            btn = Button(
                text=f'{minutes}分钟',
                size_hint_y=None,
                height=dp(40)
            )
            btn.bind(on_press=lambda x, m=minutes: self.set_sleep_timer(m))
            time_grid.add_widget(btn)
        
        content.add_widget(time_grid)
        
        # 控制按钮
        control_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        
        if is_active:
            stop_btn = Button(text='停止定时')
            stop_btn.bind(on_press=lambda x: (self.sleep_timer.stop(), 
                                             popup.dismiss(),
                                             self.show_toast("定时器已停止")))
            control_box.add_widget(stop_btn)
        else:
            start_btn = Button(text='开始定时')
            start_btn.bind(on_press=lambda x: (self.start_sleep_timer(30),
                                              popup.dismiss(),
                                              self.show_toast("定时器已启动")))
            control_box.add_widget(start_btn)
        
        close_btn = Button(text='关闭')
        close_btn.bind(on_press=lambda x: popup.dismiss())
        control_box.add_widget(close_btn)
        
        content.add_widget(control_box)
        
        popup = Popup(
            title='睡眠定时器',
            content=content,
            size_hint=(0.8, 0.5)
        )
        popup.open()
    
    def set_sleep_timer(self, minutes):
        """设置睡眠定时器"""
        self.sleep_timer.start(minutes)
        self.show_toast(f"定时器已设置为{minutes}分钟")
    
    def start_sleep_timer(self, minutes=30):
        """启动睡眠定时器"""
        self.sleep_timer.start(minutes)
    
    def show_settings(self, instance):
        """显示设置"""
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # 主题切换
        theme_box = BoxLayout(size_hint_y=None, height=dp(40))
        theme_box.add_widget(Label(text='深色模式:', size_hint_x=0.6))
        
        theme_switch = Switch(active=self.dark_mode)
        def on_theme_switch(switch, value):
            self.dark_mode = value
            self.toggle_dark_mode(value)
        
        theme_switch.bind(active=on_theme_switch)
        theme_box.add_widget(theme_switch)
        content.add_widget(theme_box)
        
        # 自动扫描
        auto_scan_box = BoxLayout(size_hint_y=None, height=dp(40))
        auto_scan_box.add_widget(Label(text='启动时自动扫描:', size_hint_x=0.6))
        
        auto_scan_switch = Switch(active=True)
        auto_scan_box.add_widget(auto_scan_switch)
        content.add_widget(auto_scan_box)
        
        # 数据库管理
        db_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        
        clear_db_btn = Button(text='清空数据库')
        clear_db_btn.bind(on_press=lambda x: self.clear_database())
        
        export_btn = Button(text='导出数据')
        export_btn.bind(on_press=lambda x: self.export_data())
        
        db_box.add_widget(clear_db_btn)
        db_box.add_widget(export_btn)
        content.add_widget(db_box)
        
        # 关闭按钮
        close_btn = Button(
            text='关闭',
            size_hint_y=None,
            height=dp(40)
        )
        close_btn.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(close_btn)
        
        popup = Popup(
            title='设置',
            content=content,
            size_hint=(0.8, 0.5)
        )
        popup.open()
    
    def toggle_dark_mode(self, enabled):
        """切换深色模式"""
        # 这里可以实现深色模式切换逻辑
        self.show_toast("深色模式已" + ("启用" if enabled else "禁用"))
    
    def clear_database(self):
        """清空数据库"""
        # 这里应该添加确认对话框
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM songs")
            conn.commit()
            self.show_toast("数据库已清空")
            self.load_songs()
        except Exception as e:
            self.show_error(f"清空数据库失败: {e}")
    
    def export_data(self):
        """导出数据"""
        try:
            songs = self.db.get_songs()
            
            # 创建导出数据
            export_data = {
                'export_date': datetime.now().isoformat(),
                'total_songs': len(songs),
                'songs': songs
            }
            
            # 保存到文件
            export_file = 'music_library_export.json'
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.show_toast(f"数据已导出到 {export_file}")
            
        except Exception as e:
            self.show_error(f"导出数据失败: {e}")
    
    def on_search(self, instance):
        """处理搜索"""
        search_term = self.search_input.text.strip()
        if search_term:
            self.load_songs(search_term=search_term)
        else:
            self.load_songs()
    
    def show_notification(self, title, message):
        """显示通知"""
        print(f"{title}: {message}")
        self.show_toast(message)
    
    def show_toast(self, message, duration=2):
        """显示Toast消息（修正版）"""
        # 使用Popup模拟Toast
        toast_content = Label(
            text=message,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(dp(200), dp(40))
        )
        
        toast = Popup(
            content=toast_content,
            size_hint=(None, None),
            size=(dp(200), dp(40)),
            pos_hint={'center_x': 0.5, 'center_y': 0.2},
            background='',
            separator_height=0,
            auto_dismiss=True
        )
        
        toast.open()
        Clock.schedule_once(lambda dt: toast.dismiss(), duration)
    
    def show_error(self, message):
        """显示错误消息"""
        self.show_toast(f"错误: {message}")
    
    def on_stop(self):
        """应用停止时清理资源"""
        self.player.stop()
        self.db.close()

# 运行应用
if __name__ == '__main__':
    import threading
    MusicManagerApp().run()