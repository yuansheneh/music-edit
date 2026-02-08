[app]

# 应用信息
title = 音乐元数据管理器
package.name = musicmetadata
package.domain = org.example

# 源代码
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt

# 版本
version = 1.0.0

# 依赖
requirements = python3,kivy==2.3.0,mutagen,android

# 权限
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# API级别
android.api = 31
android.minapi = 21
android.ndk = 25b

# 图标和启动画面
#icon.filename = %(source.dir)s/data/icon.png
#presplash.filename = %(source.dir)s/data/presplash.png

# 方向
orientation = portrait

# 全屏
fullscreen = 1

# Android架构
android.archs = arm64-v8a,armeabi-v7a

[buildozer]

# 日志级别
log_level = 2

# 构建目录
warn_on_root = 1
