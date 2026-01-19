🎵 音乐元数据管理器 (Music Meta Manager)
一个基于 Python + Kivy 开发的 Android 音乐元数据管理应用，提供优雅的用户界面和流畅的交互体验。

📋 目录
项目简介
核心特性
技术栈
项目结构
功能模块
安装部署
使用指南
开发说明
常见问题
🎯 项目简介
Music Meta Manager 是一款专为 Android 平台设计的音乐元数据管理工具。它能够扫描设备中的音乐文件，读取和编辑音乐的标题、艺术家、专辑、流派、年份等元数据信息。

适用场景
📱 整理手机音乐库
🎼 批量修改音乐信息
🔍 快速查看音乐元数据
✏️ 修正错误的音乐标签
✨ 核心特性
🎨 用户界面
Material Design 风格：现代化的扁平设计
清爽配色方案：浅灰背景 + 蓝色强调色
响应式布局：适配不同屏幕尺寸
直观的操作逻辑：简单易用，上手快
🎬 动画效果
按钮点击动画：透明度变化反馈
页面切换动画：平滑的左右滑动
列表滚动：流畅的滚动体验
🎵 音频格式支持
格式	扩展名	支持状态
MP3	.mp3	✅ 完全支持
FLAC	.flac	✅ 完全支持
M4A	.m4a	✅ 完全支持
MP4	.mp4	✅ 完全支持
📝 元数据字段
标题 (Title)
艺术家 (Artist)
专辑 (Album)
流派 (Genre)
年份 (Date)
🛡️ 稳定性保障
完善的异常处理：捕获所有可能的错误
权限自动请求：智能处理 Android 权限
数据验证：防止无效数据写入
安全的文件操作：避免数据损坏
🔧 技术栈
核心框架
Python 3.x          # 编程语言
├── Kivy 2.2.1      # 跨平台 GUI 框架
├── Mutagen 1.47.0  # 音频元数据处理库
└── Buildozer       # Android 打包工具
依赖库详解
Kivy
作用：提供跨平台的 GUI 框架
优势：原生支持触摸操作、丰富的动画系统
组件使用：
ScreenManager：页面管理
BoxLayout/GridLayout：布局管理
Animation：动画效果
ScrollView：滚动视图
Mutagen
作用：读写音频文件元数据
支持格式：MP3 (ID3)、FLAC、MP4/M4A
核心类：
EasyID3：简化的 MP3 标签接口
FLAC：FLAC 文件处理
MP4：MP4/M4A 文件处理
📁 项目结构
MusicMetaManager/
│
├── main.py                 # 主程序入口
│   ├── MusicFile          # 音乐文件类
│   ├── MusicListItem      # 列表项组件
│   ├── MainScreen         # 主界面
│   ├── EditScreen         # 编辑界面
│   └── MusicMetaManagerApp # 应用主类
│
├── buildozer.spec         # Android 构建配置
│   ├── [app]              # 应用配置
│   └── [buildozer]        # 构建选项
│
└── requirements.txt       # Python 依赖列表
🎮 功能模块
1️⃣ 主界面 (MainScreen)
界面布局
┌─────────────────────────────┐
│  音乐元数据管理    [扫描]    │  ← 标题栏
├─────────────────────────────┤
│ ┌─────────────────────────┐ │
│ │ 🎵 歌曲标题            │ │
│ │ 👤 艺术家名称    [编辑] │ │  ← 音乐列表项
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ 🎵 另一首歌            │ │
│ │ 👤 另一位艺术家  [编辑] │ │
│ └─────────────────────────┘ │
│          ⋮                  │  ← 可滚动
└─────────────────────────────┘
核心功能
🔍 扫描音乐

def scan_music(self, instance):
    # 1. 请求存储权限
    # 2. 遍历 /sdcard/Music 目录
    # 3. 识别支持的音频格式
    # 4. 加载元数据并显示
特点：

自动请求 Android 存储权限
递归扫描子目录
实时显示扫描结果
空结果友好提示
📋 音乐列表

显示歌曲标题和艺术家
点击"编辑"按钮进入编辑界面
支持滚动浏览大量歌曲
按钮点击有视觉反馈
2️⃣ 编辑界面 (EditScreen)
界面布局
┌─────────────────────────────┐
│     编辑音乐元数据           │  ← 标题
├─────────────────────────────┤
│  标题:   [____________]      │
│  艺术家: [____________]      │
│  专辑:   [____________]      │  ← 表单字段
│  流派:   [____________]      │
│  年份:   [____________]      │
├─────────────────────────────┤
│   [保存]        [取消]       │  ← 操作按钮
└─────────────────────────────┘
核心功能
✏️ 编辑元数据

def save_metadata(self, instance):
    # 1. 收集表单数据
    # 2. 调用 MusicFile.save_metadata()
    # 3. 写入音频文件
    # 4. 显示结果提示
特点：

自动填充现有元数据
实时输入验证
保存成功/失败提示
返回主界面刷新列表
3️⃣ 音乐文件类 (MusicFile)
类结构
class MusicFile:
    filepath: str           # 文件路径
    filename: str           # 文件名
    metadata: dict          # 元数据字典
    
    load_metadata()         # 加载元数据
    save_metadata()         # 保存元数据
元数据处理流程
读取流程：

文件路径 → 识别格式 → 选择解析器 → 读取标签 → 返回字典
写入流程：

新数据 → 验证格式 → 打开文件 → 更新标签 → 保存文件
错误处理：

文件不存在 → 返回空元数据
格式不支持 → 跳过处理
标签损坏 → 使用默认值
写入失败 → 返回 False
🚀 安装部署
环境要求
项目	要求
Python	3.7+
操作系统	Linux / macOS / Windows
Android SDK	API 21+ (Android 5.0+)
Android NDK	r23b
开发环境搭建
1. 安装 Python 依赖
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
2. 本地测试运行
python main.py
注意：本地测试时会使用 ~/Music 目录，而非 Android 的 /sdcard/Music

Android 打包部署
1. 安装 Buildozer
# Linux
pip install buildozer

# 安装系统依赖（Ubuntu/Debian）
sudo apt update
sudo apt install -y git zip unzip openjdk-11-jdk \
    python3-pip autoconf libtool pkg-config zlib1g-dev \
    libncurses5-dev libncursesw5-dev libtinfo5 cmake \
    libffi-dev libssl-dev
2. 初始化项目
buildozer init
# 会生成 buildozer.spec 配置文件
3. 编译 APK
# Debug 版本（用于测试）
buildozer android debug

# Release 版本（用于发布）
buildozer android release
编译时间：首次编译约 30-60 分钟（需下载 SDK/NDK）

4. 安装到设备
# 通过 USB 连接设备，启用 USB 调试

# 安装并运行
buildozer android deploy run

# 仅安装
adb install bin/*.apk
构建配置说明
buildozer.spec 关键配置
[app]
# 应用信息
title = Music Meta Manager          # 应用名称
package.name = musicmetamanager     # 包名
package.domain = org.example        # 域名

# 版本信息
version = 1.0                       # 版本号

# 依赖库
requirements = python3,kivy,mutagen

# 权限
permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Android 配置
android.api = 31                    # 目标 API 级别
android.minapi = 21                 # 最低 API 级别
android.arch = armeabi-v7a          # CPU 架构
📖 使用指南
首次使用
安装应用

从 APK 文件安装到 Android 设备
授予存储权限
扫描音乐

打开应用
点击右上角"扫描"按钮
等待扫描完成
编辑元数据

在列表中找到要编辑的歌曲
点击"编辑"按钮
修改信息后点击"保存"
操作技巧
批量整理音乐
将音乐文件放入 /sdcard/Music 目录
使用文件管理器创建子文件夹分类
在应用中扫描并逐个编辑
备份元数据
建议在编辑前：

备份原始音乐文件
或使用其他工具导出元数据
处理特殊字符
支持中文、日文、韩文等 Unicode 字符
避免使用特殊符号（如 / \ :）
常见操作流程
修正错误的歌曲信息
扫描 → 找到歌曲 → 编辑 → 修改标题/艺术家 → 保存
添加缺失的专辑信息
扫描 → 编辑 → 填写专辑名称 → 保存
统一流派标签
扫描 → 逐个编辑 → 设置相同流派 → 保存
👨‍💻 开发说明
代码架构
设计模式
MVC 模式：分离数据、视图、控制逻辑
组件化：可复用的 UI 组件
事件驱动：基于 Kivy 的事件系统
类关系图
MusicMetaManagerApp
    └── ScreenManager
        ├── MainScreen
        │   ├── MusicListItem (多个)
        │   └── MusicFile (多个)
        └── EditScreen
            └── MusicFile (当前编辑)
扩展开发
添加新的音频格式
# 在 MusicFile.load_metadata() 中添加
elif ext == '.ogg':
    from mutagen.oggvorbis import OggVorbis
    audio = OggVorbis(self.filepath)
添加新的元数据字段
# 1. 在 load_metadata() 中添加字段
self.metadata['composer'] = str(audio.get('composer', [''])[0])

# 2. 在 EditScreen.build_ui() 中添加输入框
('作曲家', 'composer')
自定义 UI 主题
# 修改颜色常量
PRIMARY_COLOR = (0.3, 0.6, 0.9, 1)    # 主色调
ACCENT_COLOR = (0.3, 0.7, 0.4, 1)     # 强调色
BACKGROUND_COLOR = (0.95, 0.95, 0.97, 1)  # 背景色
性能优化建议
大量文件处理
# 使用异步加载
from kivy.clock import Clock

def scan_music_async(self):
    def load_next_file(dt):
        # 每帧加载一个文件
        if files_to_load:
            file = files_to_load.pop(0)
            # 处理文件...
            Clock.schedule_once(load_next_file, 0)
    
    Clock.schedule_once(load_next_file, 0)
内存优化
使用生成器而非列表
及时释放不用的对象
限制同时显示的列表项数量
调试技巧
查看日志
# Android 设备日志
adb logcat | grep python

# Buildozer 日志
buildozer android logcat
常见错误
错误	原因	解决方案
Permission Denied	未授予存储权限	在设置中手动授权
Module not found	依赖未安装	检查 requirements
Build failed	SDK/NDK 问题	重新下载或更新
❓ 常见问题
Q1: 为什么扫描不到音乐文件？
A: 可能的原因：

未授予存储权限 → 在系统设置中授权
音乐不在 /sdcard/Music 目录 → 移动文件到该目录
文件格式不支持 → 检查是否为 MP3/FLAC/M4A/MP4
Q2: 保存后为什么音乐播放器看不到更改？
A: 需要刷新媒体库：

# 方法1：重启设备
# 方法2：使用媒体扫描器应用
# 方法3：重新插拔 SD 卡
Q3: 编译 APK 失败怎么办？
A: 检查清单：

[ ] Java JDK 已安装（版本 8 或 11）
[ ] 网络连接正常（需下载 SDK）
[ ] 磁盘空间充足（至少 10GB）
[ ] buildozer.spec 配置正确
Q4: 应用闪退怎么办？
A: 排查步骤：

查看 logcat 日志
检查权限是否授予
确认音乐文件未损坏
重新安装应用
Q5: 如何支持更多音频格式？
A: 修改代码添加格式支持：

# 在 MusicFile 类中添加新格式的处理逻辑
# 确保 mutagen 库支持该格式
Q6: 可以在 iOS 上运行吗？
A: 理论上可以，但需要：

使用 Kivy-iOS 工具链
重新配置构建脚本
处理 iOS 特有的权限和文件系统
Q7: 如何批量编辑多个文件？
A: 当前版本不支持批量编辑，可以：

逐个编辑（适合少量文件）
使用电脑端工具批量处理后传输到手机
📄 许可证
本项目仅供学习和个人使用。

🤝 贡献指南
欢迎提交 Issue 和 Pull Request！

贡献流程
Fork 本仓库
创建特性分支 (git checkout -b feature/AmazingFeature)
提交更改 (git commit -m 'Add some AmazingFeature')
推送到分支 (git push origin feature/AmazingFeature)
开启 Pull Request
📞 联系方式
如有问题或建议，欢迎反馈！

🎉 致谢
Kivy 团队 - 提供优秀的跨平台框架
Mutagen 开发者 - 强大的音频元数据库
开源社区 - 无私的知识分享
⭐ 如果这个项目对你有帮助，请给个 Star！
