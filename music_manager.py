import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
# 在第6行添加缺失的导入
import json
from kivy.graphics import Color, Rectangle
from kivy.uix.behaviors import FocusBehavior

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
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.properties import (
    StringProperty, NumericProperty, ListProperty, 
    BooleanProperty, ObjectProperty, DictProperty
)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.metrics import dp, sp
from kivy.utils import platform

# 数据库和扫描器
from core.database import MusicDatabase
from core.scanner import AudioFileScanner
from core.equalizer import AudioEqualizer
from core.lyrics import LyricsManager
from core.queue import PlayQueue
from core.smartplaylist import SmartPlaylist
from core.timer import SleepTimer
from core.gesture import GestureController

class EnhancedMusicPlayer:
    """增强版音乐播放器"""
    
    def __init__(self):
        self.sound = None
        self.is_playing = False
        self.volume = 1.0
        self.playback_speed = 1.0
        self.fade_duration = 0  # 淡入淡出时长
        self.equalizer = AudioEqualizer()
        
    def load(self, file_path):
        """加载音频文件"""
        self.stop()
        
        try:
            self.sound = SoundLoader.load(file_path)
            if self.sound:
                self.sound.volume = self.volume
                return True
        except Exception as e:
            print(f"加载音频失败: {e}")
        
        return False
    
    def play(self, fade_in=False):
        """播放音频"""
        if self.sound and not self.is_playing:
            if fade_in and self.fade_duration > 0:
                self.fade_in(self.fade_duration)
            else:
                self.sound.play()
            self.is_playing = True
            return True
        return False
    
    def pause(self, fade_out=False):
        """暂停音频"""
        if self.sound and self.is_playing:
            if fade_out and self.fade_duration > 0:
                self.fade_out(self.fade_duration)
            else:
                self.sound.stop()
            self.is_playing = False
            return True
        return False
    
    def stop(self):
        """停止音频"""
        if self.sound:
            self.sound.stop()
            self.is_playing = False
            self.sound.unload()
            self.sound = None
        return True
    
    def seek(self, position):
        """跳转到指定位置"""
        if self.sound and hasattr(self.sound, 'seek'):
            self.sound.seek(position)
            return True
        return False
    
    def fade_in(self, duration):
        """淡入效果"""
        if self.sound:
            self.sound.volume = 0
            self.sound.play()
            
            def increase_volume(dt):
                if self.sound.volume < self.volume:
                    self.sound.volume += self.volume / (duration * 60)
                else:
                    Clock.unschedule(fade_in_event)
            
            fade_in_event = Clock.schedule_interval(increase_volume, 1/60)
    
    def fade_out(self, duration):
        """淡出效果"""
        if self.sound and self.is_playing:
            def decrease_volume(dt):
                if self.sound.volume > 0:
                    self.sound.volume -= self.volume / (duration * 60)
                else:
                    self.sound.stop()
                    self.is_playing = False
                    Clock.unschedule(fade_out_event)
            
            fade_out_event = Clock.schedule_interval(decrease_volume, 1/60)
    
    def set_playback_speed(self, speed):
        """设置播放速度"""
        # 注意：Kivy的SoundLoader可能不支持变速播放
        # 这里只是一个接口设计
        self.playback_speed = max(0.5, min(2.0, speed))
    
    def get_position(self):
        """获取当前位置"""
        if self.sound and hasattr(self.sound, 'get_pos'):
            return self.sound.get_pos()
        return 0
    
    def get_duration(self):
        """获取总时长"""
        if self.sound and hasattr(self.sound, 'length'):
            return self.sound.length
        return 0

class MusicManagerApp(App):
    """主应用 - 增强版"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 初始化核心组件
        self.db = MusicDatabase("music_library.db")
        self.scanner = AudioFileScanner()
        self.player = EnhancedMusicPlayer()
        self.queue = PlayQueue(self.db)
        self.lyrics_manager = LyricsManager(self.db)
        self.smart_playlist = SmartPlaylist(self.db)
        self.sleep_timer = SleepTimer()
        
        # 应用状态
        self.current_song_id = None
        self.current_lyrics = []
        self.dark_mode = False
        self.keep_screen_on = False
        
        # 缓存
        self.song_cache = {}
        self.album_cache = {}
        self.artist_cache = {}
    
    def build(self):
        """构建应用界面"""
        # 请求Android权限
        if self.is_android():
            self.request_android_permissions()
            self.setup_android_notifications()
        
        # 设置窗口
        if not self.is_android():
            Window.size = (400, 700)
            Window.minimum_width = 400
            Window.minimum_height = 600
        
        # 创建主布局
        self.root = BoxLayout(orientation='vertical')
        
        # 创建各个界面组件
        self.create_top_bar()
        self.create_tab_bar()
        self.create_main_content()
        self.create_bottom_player()
        self.create_side_menu()
        
        # 加载数据
        Clock.schedule_once(lambda dt: self.initialize_app(), 0.5)
        
        # 设置手势控制
        self.gesture_controller = GestureController(self)
        Window.bind(on_touch_down=self.on_touch_down)
        
        return self.root
    
    def initialize_app(self):
        """初始化应用数据"""
        # 加载统计信息
        self.load_stats()
        
        # 加载最近播放
        self.load_recent_songs()
        
        # 检查数据库是否需要更新
        self.check_database_update()
        
        # 启动自动扫描（可选）
        if self.get_setting('auto_scan', False):
            self.auto_scan_music()
    
    def create_tab_bar(self):
        """创建标签栏"""
        tab_bar = BoxLayout(
            size_hint_y=None,
            height=dp(48),
            spacing=dp(2)
        )
        
        tabs = [
            ('library', '音乐库', 'music'),
            ('playlists', '播放列表', 'playlist-music'),
            ('artists', '艺术家', 'account-music'),
            ('albums', '专辑', 'album'),
            ('genres', '流派', 'tag-multiple')
        ]
        
        for tab_id, tab_name, tab_icon in tabs:
            tab = Button(
                text=f'[font=MaterialIcons]{tab_icon}[/font]\n{tab_name}',
                markup=True,
                size_hint_x=1,
                font_size=sp(12)
            )
            tab.bind(on_press=lambda x, tid=tab_id: self.switch_tab(tid))
            tab_bar.add_widget(tab)
        
        self.root.add_widget(tab_bar)
    
    def switch_tab(self, tab_id):
        """切换标签页"""
        # 更新标签页状态
        for child in self.root.children:
            if hasattr(child, 'tab_id'):
                child.opacity = 0.5 if child.tab_id != tab_id else 1
        
        # 加载对应内容
        if tab_id == 'library':
            self.load_songs()
        elif tab_id == 'playlists':
            self.load_playlists()
        elif tab_id == 'artists':
            self.load_artists()
        elif tab_id == 'albums':
            self.load_albums()
        elif tab_id == 'genres':
            self.load_genres()
    
    def create_side_menu(self):
        """创建侧边菜单（滑动菜单）"""
        # 这里需要实现滑动菜单
        pass
    
    def show_song_detail(self, song_id):
        """显示歌曲详情"""
        # 获取歌曲信息
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM songs WHERE id = ?", (song_id,))
        song = dict(cursor.fetchone())
        
        # 创建详情弹窗
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # 专辑封面
        if self.get_song_cover(song_id):
            cover = Image(
                source=self.get_song_cover(song_id),
                size_hint=(1, 0.4),
                keep_ratio=True
            )
            content.add_widget(cover)
        
        # 歌曲信息
        info_box = BoxLayout(orientation='vertical', spacing=dp(5))
        
        title = Label(
            text=song.get('title', '未知标题'),
            size_hint_y=None,
            height=dp(30),
            font_size=sp(18),
            bold=True
        )
        
        artist = Label(
            text=f"艺术家: {song.get('artist', '未知艺术家')}",
            size_hint_y=None,
            height=dp(25)
        )
        
        album = Label(
            text=f"专辑: {song.get('album', '未知专辑')}",
            size_hint_y=None,
            height=dp(25)
        )
        
        info_box.add_widget(title)
        info_box.add_widget(artist)
        info_box.add_widget(album)
        content.add_widget(info_box)
        
        # 技术信息
        tech_box = GridLayout(cols=2, spacing=dp(5), size_hint_y=None, height=dp(80))
        
        tech_info = [
            ('时长', f"{int(song.get('duration', 0)//60)}:{int(song.get('duration', 0)%60):02d}"),
            ('格式', song.get('file_format', '未知')),
            ('比特率', f"{song.get('bitrate', 0)} kbps" if song.get('bitrate') else '未知'),
            ('采样率', f"{song.get('sample_rate', 0)} Hz" if song.get('sample_rate') else '未知'),
        ]
        
        for label, value in tech_info:
            tech_box.add_widget(Label(text=label, size_hint_x=0.4))
            tech_box.add_widget(Label(text=value, size_hint_x=0.6))
        
        content.add_widget(tech_box)
        
        # 操作按钮
        button_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        
        play_btn = Button(text='播放', on_press=lambda x: self.play_song(song_id))
        add_to_queue = Button(text='添加到队列', on_press=lambda x: self.add_to_queue(song_id))
        edit_btn = Button(text='编辑信息', on_press=lambda x: self.edit_song_info(song_id))
        
        button_box.add_widget(play_btn)
        button_box.add_widget(add_to_queue)
        button_box.add_widget(edit_btn)
        
        content.add_widget(button_box)
        
        # 创建弹窗
        popup = Popup(
            title='歌曲详情',
            content=content,
            size_hint=(0.8, 0.8)
        )
        
        popup.open()
    
    def show_equalizer(self):
        """显示均衡器设置"""
        eq_settings = self.player.equalizer.get_eq_settings()
        
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # 均衡器开关
        switch_box = BoxLayout(size_hint_y=None, height=dp(40))
        switch_box.add_widget(Label(text='启用均衡器'))
        eq_switch = Switch(active=eq_settings['enabled'])
        eq_switch.bind(active=lambda x, v: self.player.equalizer.set_enabled(v))
        switch_box.add_widget(eq_switch)
        content.add_widget(switch_box)
        
        # 预设选择
        preset_box = BoxLayout(orientation='vertical', spacing=dp(5))
        preset_box.add_widget(Label(text='预设:', size_hint_y=None, height=dp(25)))
        
        preset_grid = GridLayout(cols=3, spacing=dp(5), size_hint_y=None, height=dp(100))
        
        for preset in ['flat', 'pop', 'rock', 'jazz', 'classical', 'bass_boost']:
            btn = Button(
                text=preset.replace('_', ' ').title(),
                size_hint=(1, None),
                height=dp(40)
            )
            btn.bind(on_press=lambda x, p=preset: self.player.equalizer.set_preset(p))
            preset_grid.add_widget(btn)
        
        preset_box.add_widget(preset_grid)
        content.add_widget(preset_box)
        
        # 频段调节器
        bands_box = BoxLayout(orientation='vertical', spacing=dp(5))
        bands_box.add_widget(Label(text='频段调节:', size_hint_y=None, height=dp(25)))
        
        for i, (band, gain) in enumerate(zip(self.player.equalizer.bands, eq_settings['bands'])):
            band_box = BoxLayout(size_hint_y=None, height=dp(40))
            band_box.add_widget(Label(text=f'{band}Hz', size_hint_x=0.3))
            
            slider = Slider(
                min=-12,
                max=12,
                value=gain,
                size_hint_x=0.7
            )
            slider.bind(value=lambda x, v, idx=i: self.player.equalizer.set_band_gain(idx, v))
            band_box.add_widget(slider)
            
            bands_box.add_widget(band_box)
        
        content.add_widget(bands_box)
        
        popup = Popup(
            title='均衡器设置',
            content=content,
            size_hint=(0.9, 0.8)
        )
        
        popup.open()
    
    def show_sleep_timer(self):
        """显示睡眠定时器设置"""
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # 定时器状态
        status_box = BoxLayout(size_hint_y=None, height=dp(40))
        status_text = '定时器已开启' if self.sleep_timer.timer_active else '定时器已关闭'
        status_box.add_widget(Label(text=status_text))
        
        if self.sleep_timer.timer_active:
            remaining = self.sleep_timer.get_remaining_time()
            mins = remaining // 60
            secs = remaining % 60
            time_label = Label(text=f'剩余时间: {mins}:{secs:02d}')
            status_box.add_widget(time_label)
        
        content.add_widget(status_box)
        
        # 时间选择
        time_box = BoxLayout(orientation='vertical', spacing=dp(5))
        time_box.add_widget(Label(text='定时时间:', size_hint_y=None, height=dp(25)))
        
        time_buttons = BoxLayout(spacing=dp(5), size_hint_y=None, height=dp(40))
        
        for minutes in [15, 30, 45, 60, 90]:
            btn = Button(
                text=f'{minutes}分钟',
                on_press=lambda x, m=minutes: self.set_sleep_timer(m)
            )
            time_buttons.add_widget(btn)
        
        time_box.add_widget(time_buttons)
        content.add_widget(time_box)
        
        # 结束动作选择
        action_box = BoxLayout(orientation='vertical', spacing=dp(5))
        action_box.add_widget(Label(text='结束后动作:', size_hint_y=None, height=dp(25)))
        
        action_buttons = BoxLayout(spacing=dp(5))
        
        actions = [
            ('stop', '停止播放'),
            ('pause', '暂停播放'),
            ('volume', '渐降音量')
        ]
        
        for action_id, action_text in actions:
            btn = Button(
                text=action_text,
                on_press=lambda x, a=action_id: self.set_sleep_timer_action(a)
            )
            action_buttons.add_widget(btn)
        
        action_box.add_widget(action_buttons)
        content.add_widget(action_box)
        
        # 控制按钮
        control_box = BoxLayout(spacing=dp(5), size_hint_y=None, height=dp(40))
        
        if self.sleep_timer.timer_active:
            stop_btn = Button(text='停止定时', on_press=lambda x: self.sleep_timer.stop())
            control_box.add_widget(stop_btn)
        else:
            start_btn = Button(text='开始定时', on_press=lambda x: self.start_sleep_timer())
            control_box.add_widget(start_btn)
        
        content.add_widget(control_box)
        
        popup = Popup(
            title='睡眠定时器',
            content=content,
            size_hint=(0.8, 0.6)
        )
        
        popup.open()
    
    def set_sleep_timer(self, minutes):
        """设置睡眠定时器时间"""
        self.sleep_timer.start(minutes)
        self.show_notification('睡眠定时器', f'定时器已设置为{minutes}分钟后结束')
    
    def start_sleep_timer(self):
        """启动睡眠定时器"""
        # 这里应该从UI获取设置的时间
        self.sleep_timer.start(30)  # 默认30分钟
        self.show_notification('睡眠定时器', '定时器已启动')
    
    def show_notification(self, title, message):
        """显示通知"""
        if platform == 'android':
            try:
                from jnius import autoclass
                
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Context = autoclass('android.content.Context')
                NotificationCompatBuilder = autoclass('androidx.core.app.NotificationCompat$Builder')
                NotificationManagerCompat = autoclass('androidx.core.app.NotificationManagerCompat')
                
                context = PythonActivity.mActivity
                
                # 创建通知渠道（Android 8.0+）
                if autoclass('android.os.Build$VERSION').SDK_INT >= 26:
                    NotificationChannel = autoclass('android.app.NotificationChannel')
                    notification_service = context.getSystemService(Context.NOTIFICATION_SERVICE)
                    
                    channel_id = 'music_manager_channel'
                    channel_name = '音乐通知'
                    channel = NotificationChannel(channel_id, channel_name, 
                                                 NotificationChannel.IMPORTANCE_DEFAULT)
                    notification_service.createNotificationChannel(channel)
                
                # 创建通知
                builder = NotificationCompatBuilder(context, channel_id)
                builder.setContentTitle(title)
                builder.setContentText(message)
                builder.setSmallIcon(context.getApplicationInfo().icon)
                builder.setAutoCancel(True)
                
                # 显示通知
                notification_manager = NotificationManagerCompat.from(context)
                notification_manager.notify(1, builder.build())
                
            except Exception as e:
                print(f"Android通知发送失败: {e}")
        else:
            # 桌面系统使用弹窗
            Clock.schedule_once(lambda dt: self.show_toast(message), 0)
    
    def show_toast(self, message, duration=2):
        """显示Toast消息"""
        toast = Label(
            text=message,
            size_hint=(None, None),
            size=(dp(200), dp(40)),
            pos_hint={'center_x': 0.5, 'center_y': 0.1},
            color=(1, 1, 1, 1),
            background_color=(0, 0, 0, 0.7)
        )
        
        self.root.add_widget(toast)
        
        def remove_toast(dt):
            self.root.remove_widget(toast)
        
        Clock.schedule_once(remove_toast, duration)
    
    def is_android(self):
        """检查是否在Android平台"""
        return platform == 'android'
    
    def request_android_permissions(self):
        """请求Android权限"""
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                
                permissions = [
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.RECORD_AUDIO,
                    Permission.MODIFY_AUDIO_SETTINGS,
                    Permission.WAKE_LOCK,
                    Permission.FOREGROUND_SERVICE
                ]
                
                request_permissions(permissions)
                
            except Exception as e:
                print(f"权限请求失败: {e}")
    
    def setup_android_notifications(self):
        """设置Android通知"""
        if platform == 'android':
            try:
                from jnius import autoclass
                
                # 设置前台服务（保持应用在后台运行）
                Service = autoclass('org.kivy.android.PythonService')
                Intent = autoclass('android.content.Intent')
                Context = autoclass('android.content.Context')
                
                service_intent = Intent(Context.BIND_AUTO_CREATE)
                service_intent.setClassName(
                    Context.getPackageName(),
                    'org.kivy.android.PythonService'
                )
                
                # 启动服务
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                activity.startService(service_intent)
                
            except Exception as e:
                print(f"服务启动失败: {e}")
    
    def on_pause(self):
        """应用暂停时保存状态"""
        # 保存当前播放状态
        self.save_playback_state()
        
        # 停止播放（可选）
        if not self.get_setting('play_in_background', True):
            self.player.pause()
        
        return True
    
    def on_resume(self):
        """应用恢复时恢复状态"""
        # 恢复播放状态
        self.restore_playback_state()
        return True
    
    def save_playback_state(self):
        """保存播放状态"""
        state = {
            'current_song_id': self.current_song_id,
            'position': self.player.get_position() if self.player.sound else 0,
            'volume': self.player.volume,
            'queue': self.queue.get_queue_info()
        }
        
        # 保存到文件或数据库
        try:
            import json
            with open('playback_state.json', 'w') as f:
                json.dump(state, f)
        except:
            pass
    
    def restore_playback_state(self):
        """恢复播放状态"""
        try:
            import json
            with open('playback_state.json', 'r') as f:
                state = json.load(f)
                
                # 恢复状态
                if state.get('current_song_id'):
                    self.current_song_id = state['current_song_id']
                    # 恢复播放位置等
                    
        except:
            pass
    
    def get_setting(self, key, default=None):
        """获取设置"""
        # 这里应该从数据库或配置文件中读取
        return default
    
    def auto_scan_music(self):
        """自动扫描音乐"""
        if self.is_android():
            from android.storage import primary_external_storage_path
            music_dirs = [
                os.path.join(primary_external_storage_path(), 'Music'),
                os.path.join(primary_external_storage_path(), 'Download'),
                os.path.join(primary_external_storage_path(), 'Documents')
            ]
        else:
            music_dirs = [
                os.path.expanduser('~/Music'),
                os.path.expanduser('~/Downloads')
            ]
        
        def scan_callback(results):
            if results:
                self.show_toast(f'自动扫描完成，找到 {len(results)} 首歌曲')
                self.load_songs()  # 刷新列表
        
        AudioFileScanner.scan_directories_async(music_dirs, scan_callback)

# 运行应用
if __name__ == '__main__':
    MusicManagerApp().run()