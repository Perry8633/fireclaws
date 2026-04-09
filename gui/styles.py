"""
GUI 设计系统样式模块
基于 awesome-design-md 设计系统
"""
import tkinter as tk
from tkinter import ttk


class DesignSystem:
    """设计系统颜色和样式常量"""

    # 色彩系统
    COLORS = {
        'primary': '#c96442',        # Terracotta Brand - 主品牌色
        'accent': '#d97757',         # Coral Accent - 强调色
        'background': '#f5f4ed',     # Parchment - 背景色
        'surface': '#faf9f5',        # Ivory - 卡片色
        'button_bg': '#e8e6dc',      # Warm Sand - 按钮背景
        'text_primary': '#4d4c48',    # Charcoal Warm - 主文字
        'text_secondary': '#5e5d59',  # Olive Gray - 次要文字
        'border': '#f0eee6',         # Border Cream - 边框色
        'dark': '#30302e',           # Dark Surface - 深色强调
        'error': '#b53333',          # Error Crimson - 错误色
        'success': '#2d7a4f',        # Success Green - 成功色
        'ring': '#d1cfc5',           # Ring Warm - 环阴影
    }

    # 圆角
    RADIUS = {
        'small': 4,
        'medium': 8,
        'large': 12,
    }

    # 字体
    FONTS = {
        'title': ('Georgia', 25, 'bold'),
        'heading': ('Georgia', 20, 'bold'),
        'subheading': ('Arial', 16, 'bold'),
        'body': ('Arial', 14),
        'label': ('Arial', 12),
        'button': ('Arial', 14),
    }

    @staticmethod
    def configure_style():
        """配置 ttk 样式"""
        style = ttk.Style()
        style.theme_use('clam')  # 使用可自定义的主题

        # 主窗口背景
        style.configure('TFrame', background=DesignSystem.COLORS['background'])

        # 卡片框架
        style.configure('Card.TFrame', background=DesignSystem.COLORS['surface'])

        # 标签
        style.configure('TLabel',
            background=DesignSystem.COLORS['background'],
            foreground=DesignSystem.COLORS['text_primary'],
            font=DesignSystem.FONTS['body']
        )

        # 标题标签
        style.configure('Title.TLabel',
            background=DesignSystem.COLORS['background'],
            foreground=DesignSystem.COLORS['text_primary'],
            font=DesignSystem.FONTS['title']
        )

        # 次要标签
        style.configure('Secondary.TLabel',
            background=DesignSystem.COLORS['background'],
            foreground=DesignSystem.COLORS['text_secondary'],
            font=DesignSystem.FONTS['label']
        )

        # 主要按钮样式 (Terracotta 品牌色)
        style.configure('Primary.TButton',
            background=DesignSystem.COLORS['primary'],
            foreground='#ffffff',
            font=DesignSystem.FONTS['button'],
            padding=(20, 10)
        )
        style.map('Primary.TButton',
            background=[('active', DesignSystem.COLORS['accent'])],
            foreground=[('active', '#ffffff')]
        )

        # 次要按钮样式 (Warm Sand)
        style.configure('Secondary.TButton',
            background=DesignSystem.COLORS['button_bg'],
            foreground=DesignSystem.COLORS['text_primary'],
            font=DesignSystem.FONTS['button'],
            padding=(15, 8)
        )
        style.map('Secondary.TButton',
            background=[('active', DesignSystem.COLORS['ring'])]
        )

        # 成功按钮样式
        style.configure('Success.TButton',
            background=DesignSystem.COLORS['success'],
            foreground='#ffffff',
            font=DesignSystem.FONTS['button'],
            padding=(15, 8)
        )
        style.map('Success.TButton',
            background=[('active', '#3d9a6f')]
        )

        # 输入框
        style.configure('TEntry',
            fieldbackground=DesignSystem.COLORS['surface'],
            bordercolor=DesignSystem.COLORS['border'],
            lightcolor=DesignSystem.COLORS['border'],
            darkcolor=DesignSystem.COLORS['border'],
            padding=8
        )
        style.configure('Text.TEntry',
            fieldbackground=DesignSystem.COLORS['surface'],
            bordercolor=DesignSystem.COLORS['border'],
            padding=8
        )

        # 文本框背景
        style.configure('Textarea.TFrame',
            background=DesignSystem.COLORS['surface'],
            bordercolor=DesignSystem.COLORS['border'],
            relief='solid'
        )

        # 进度条
        style.configure('Horizontal.TProgressbar',
            background=DesignSystem.COLORS['primary'],
            troughcolor=DesignSystem.COLORS['border']
        )

        # 标签框 (Labelframe) - 卡片风格
        style.configure('Card.TLabelframe',
            background=DesignSystem.COLORS['surface'],
            foreground=DesignSystem.COLORS['text_primary'],
            font=DesignSystem.FONTS['subheading'],
            labelmargins=10
        )

        style.configure('Card.TLabelframe.Label',
            background=DesignSystem.COLORS['surface'],
            foreground=DesignSystem.COLORS['text_primary'],
            font=DesignSystem.FONTS['subheading']
        )

        # 下拉框
        style.configure('TCombobox',
            fieldbackground=DesignSystem.COLORS['surface'],
            background=DesignSystem.COLORS['button_bg'],
            bordercolor=DesignSystem.COLORS['border'],
            lightcolor=DesignSystem.COLORS['border'],
            darkcolor=DesignSystem.COLORS['border']
        )

        # 复选框
        style.configure('TCheckbutton',
            background=DesignSystem.COLORS['background'],
            foreground=DesignSystem.COLORS['text_primary'],
            font=DesignSystem.FONTS['body']
        )

        # 单选框
        style.configure('TRadiobutton',
            background=DesignSystem.COLORS['background'],
            foreground=DesignSystem.COLORS['text_primary'],
            font=DesignSystem.FONTS['body']
        )

        # 滚动条
        style.configure('TScrollbar',
            background=DesignSystem.COLORS['button_bg'],
            troughcolor=DesignSystem.COLORS['surface'],
            bordercolor=DesignSystem.COLORS['border'],
            lightcolor=DesignSystem.COLORS['button_bg'],
            darkcolor=DesignSystem.COLORS['button_bg']
        )

    @staticmethod
    def get_color(name: str) -> str:
        """获取颜色值"""
        return DesignSystem.COLORS.get(name, '#000000')

    @staticmethod
    def get_font(name: str) -> tuple:
        """获取字体配置"""
        return DesignSystem.FONTS.get(name, ('Arial', 14))
