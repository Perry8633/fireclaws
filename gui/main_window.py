import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import uuid
from datetime import datetime
from typing import Optional, Callable
from pathlib import Path
import json

from crawler.base_crawler import BaseCrawler, CrawlResult
from crawler.search_engine import SearchEngine
from crawler.sanctions_crawler import SanctionsCrawler
from llm.analyzer import LLMAgent, extract_report_sections
from llm.sanctions_analyzer import SanctionsAnalyzer
from config.settings import AppConfig, SearchConfig, ProxyConfig, LLMConfig, ScheduleConfig, HistoryItem, HistoryConfig, SanctionsConfig
from config.encryption import PasswordManager
from utils.scheduler import TaskScheduler
from gui.styles import DesignSystem


class TagInputFrame(ttk.Frame):
    """标签输入框组件"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.tags = []
        self.tag_vars = {}

        # 输入框
        self.entry = ttk.Entry(self)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 绑定回车事件
        self.entry.bind("<Return>", lambda e: self._add_tag())

        # 添加按钮
        self.add_btn = ttk.Button(self, text="添加", style="Secondary.TButton", command=self._add_tag)
        self.add_btn.pack(side=tk.LEFT, padx=(5, 0))

        # 标签容器
        self.tags_frame = ttk.Frame(self)
        self.tags_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

    def _add_tag(self):
        tag = self.entry.get().strip()
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self._render_tags()
        self.entry.delete(0, tk.END)

    def _remove_tag(self, tag: str):
        if tag in self.tags:
            self.tags.remove(tag)
            self._render_tags()

    def _render_tags(self):
        # 清除现有标签
        for widget in self.tags_frame.winfo_children():
            widget.destroy()

        # 重新渲染
        for tag in self.tags:
            tag_frame = ttk.Frame(self.tags_frame)
            tag_frame.pack(side=tk.LEFT, padx=(0, 5), pady=(0, 5))

            label = ttk.Label(tag_frame, text=tag, background=DesignSystem.COLORS['button_bg'], padding=(5, 2))
            label.pack(side=tk.LEFT)

            btn = ttk.Button(
                tag_frame, text="×",
                width=2,
                command=lambda t=tag: self._remove_tag(t)
            )
            btn.pack(side=tk.LEFT, padx=(2, 0))

    def get_tags(self) -> list:
        return self.tags.copy()

    def set_tags(self, tags: list):
        self.tags = tags.copy()
        self._render_tags()


class MainWindow:
    """主窗口"""

    def __init__(self, config: AppConfig, pm: PasswordManager):
        self.config = config
        self.pm = pm
        self.task_running = False
        self.scheduler = TaskScheduler()

        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("OFAC/BIS 制裁清单监测系统")
        self.root.geometry("1200x800")

        # 配置设计系统样式
        DesignSystem.configure_style()
        self.root.configure(bg=DesignSystem.COLORS['background'])

        self._setup_ui()
        self._load_config()

        # 启动调度器
        self.scheduler.start()
        self._update_next_run_time()

    def _setup_ui(self):
        """设置UI"""
        # 菜单栏
        self._create_menu()

        # 主布局
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧配置面板
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)

        # 右侧结果面板
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)

        self._setup_left_panel(left_frame)
        self._setup_right_panel(right_frame)

    def _create_menu(self):
        """创建菜单"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导出HTML", command=self._export_html)
        file_menu.add_command(label="导出Markdown", command=self._export_markdown)
        file_menu.add_command(label="导出JSON", command=self._export_json)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        # 设置菜单
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="打开设置", command=self._open_settings)
        settings_menu.add_command(label="修改密码", command=self._change_password)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._show_about)

    def _setup_left_panel(self, parent):
        """左侧配置面板 - OFAC/BIS制裁监测"""
        padding = 10

        # ===== 数据源选择 =====
        ttk.Label(parent, text="数据源：", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 5))

        source_frame = ttk.Frame(parent)
        source_frame.pack(fill=tk.X, pady=(0, 10))

        self.source_var = tk.StringVar(value="all")
        ttk.Radiobutton(source_frame, text="OFAC", variable=self.source_var, value="ofac").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(source_frame, text="BIS", variable=self.source_var, value="bis").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(source_frame, text="全部", variable=self.source_var, value="all").pack(side=tk.LEFT)

        # ===== 日期范围 =====
        ttk.Label(parent, text="日期范围：", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 5))

        date_frame = ttk.Frame(parent)
        date_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(date_frame, text="从").pack(side=tk.LEFT)
        self.date_start_var = tk.StringVar()
        start_entry = ttk.Entry(date_frame, textvariable=self.date_start_var, width=12)
        start_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(date_frame, text="至").pack(side=tk.LEFT)
        self.date_end_var = tk.StringVar()
        end_entry = ttk.Entry(date_frame, textvariable=self.date_end_var, width=12)
        end_entry.pack(side=tk.LEFT, padx=5)

        # 快捷按钮
        quick_frame = ttk.Frame(parent)
        quick_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(quick_frame, text="今日", style="Secondary.TButton",
                   command=lambda: self._set_date_range("today")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="近7天", style="Secondary.TButton",
                   command=lambda: self._set_date_range("7days")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="近30天", style="Secondary.TButton",
                   command=lambda: self._set_date_range("30days")).pack(side=tk.LEFT)

        # ===== 关键词 =====
        ttk.Label(parent, text="监控关键词：", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 5))

        self.keyword_input = TagInputFrame(parent)
        self.keyword_input.pack(fill=tk.X, pady=(0, 10))

        # ===== 任务描述 =====
        ttk.Label(parent, text="任务描述：", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 5))

        self.task_entry = tk.Text(parent, height=3, wrap=tk.WORD,
            bg=DesignSystem.COLORS['surface'],
            fg=DesignSystem.COLORS['text_primary'],
            insertbackground=DesignSystem.COLORS['text_primary'],
            font=DesignSystem.FONTS['body'],
            relief='solid',
            bd=1,
            padx=8,
            pady=8
        )
        self.task_entry.pack(fill=tk.X, pady=(0, 10))

        # ===== 邮件配置 =====
        ttk.Label(parent, text="邮件通知：", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 5))

        email_frame = ttk.LabelFrame(parent, text="邮件配置", style="Card.TLabelframe")
        email_frame.pack(fill=tk.X, pady=(0, 10))

        self.email_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(email_frame, text="启用邮件通知", variable=self.email_enabled_var).pack(anchor=tk.W, padx=10, pady=(5, 0))

        ttk.Label(email_frame, text="收件人（逗号分隔）：").pack(anchor=tk.W, padx=10, pady=(5, 0))
        self.email_recipients_var = tk.StringVar()
        ttk.Entry(email_frame, textvariable=self.email_recipients_var).pack(fill=tk.X, padx=10, pady=(0, 5))

        # ===== 定时任务 =====
        ttk.Label(parent, text="定时监控：", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 5))

        schedule_frame = ttk.LabelFrame(parent, text="定时执行", style="Card.TLabelframe")
        schedule_frame.pack(fill=tk.X, pady=(0, 10))

        # 启用定时任务
        self.schedule_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            schedule_frame,
            text="启用定时任务",
            variable=self.schedule_enabled_var,
            command=self._on_schedule_enabled_change
        ).pack(anchor=tk.W, padx=10, pady=(5, 0))

        # 周期选择
        period_frame = ttk.Frame(schedule_frame)
        period_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(period_frame, text="周期：").pack(side=tk.LEFT)
        self.schedule_type_var = tk.StringVar(value="daily")
        schedule_type_combo = ttk.Combobox(
            period_frame,
            textvariable=self.schedule_type_var,
            values=[("once", "单次"), ("daily", "每日"), ("weekly", "每周"), ("cron", "Cron表达式")],
            state="readonly",
            width=12
        )
        schedule_type_combo.pack(side=tk.LEFT, padx=(5, 10))
        schedule_type_combo.bind("<<ComboboxSelected>>", lambda e: self._update_schedule_ui())

        # 时间输入
        time_frame = ttk.Frame(schedule_frame)
        time_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(time_frame, text="时间：").pack(side=tk.LEFT)
        self.schedule_time_var = tk.StringVar(value="09:00")
        time_entry = ttk.Entry(time_frame, textvariable=self.schedule_time_var, width=8)
        time_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(time_frame, text="(HH:MM)").pack(side=tk.LEFT)

        # Cron表达式（仅cron模式显示）
        self.cron_frame = ttk.Frame(schedule_frame)
        self.cron_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(self.cron_frame, text="Cron：").pack(side=tk.LEFT)
        self.cron_expr_var = tk.StringVar(value="0 9 * * *")
        ttk.Entry(self.cron_frame, textvariable=self.cron_expr_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.cron_frame, text="例: 0 9 * * *").pack(side=tk.LEFT)

        # 隐藏cron_frame（初始状态）
        self.cron_frame.pack_forget()

        # 下次执行时间显示
        self.next_run_var = tk.StringVar(value="")
        ttk.Label(
            schedule_frame,
            textvariable=self.next_run_var,
            foreground=DesignSystem.COLORS['text_secondary']
        ).pack(anchor=tk.W, padx=10, pady=(0, 5))

        # ===== 按钮区域 =====
        # 开始监测按钮
        self.start_btn = ttk.Button(
            parent,
            text="开始监测",
            style="Primary.TButton",
            command=self._start_monitoring
        )
        self.start_btn.pack(fill=tk.X, pady=(0, 5))

        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            parent,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(parent, textvariable=self.status_var).pack(anchor=tk.W, pady=(0, 10))

        # 操作按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="导出报告", style="Secondary.TButton", command=self._export_report).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="发送邮件", style="Secondary.TButton", command=self._send_email).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="清空日志", style="Secondary.TButton", command=self._clear_log).pack(side=tk.LEFT)

    def _setup_right_panel(self, parent):
        """右侧结果面板"""
        # Tab控制
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        # 爬取内容Tab
        content_tab = ttk.Frame(notebook)
        notebook.add(content_tab, text="爬取内容")

        self.content_text = scrolledtext.ScrolledText(content_tab, wrap=tk.WORD,
            bg=DesignSystem.COLORS['surface'],
            fg=DesignSystem.COLORS['text_primary'],
            font=DesignSystem.FONTS['body']
        )
        self.content_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 分析结果Tab
        analysis_tab = ttk.Frame(notebook)
        notebook.add(analysis_tab, text="分析结果")

        self.analysis_text = scrolledtext.ScrolledText(analysis_tab, wrap=tk.WORD,
            bg=DesignSystem.COLORS['surface'],
            fg=DesignSystem.COLORS['text_primary'],
            font=DesignSystem.FONTS['body']
        )
        self.analysis_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 日志Tab
        log_tab = ttk.Frame(notebook)
        notebook.add(log_tab, text="执行日志")

        self.log_text = scrolledtext.ScrolledText(log_tab, wrap=tk.WORD,
            bg=DesignSystem.COLORS['dark'],
            fg='#ffffff',
            font=('Consolas', 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 保存notebook引用
        self.notebook = notebook

    def _load_config(self):
        """加载配置到UI"""
        # 加载制裁监测配置
        if hasattr(self.config, 'sanctions'):
            self.source_var.set("all")
            self.date_start_var.set(self.config.sanctions.date_range_start)
            self.date_end_var.set(self.config.sanctions.date_range_end)
            self.keyword_input.set_tags(self.config.sanctions.keywords)
            self.email_enabled_var.set(self.config.sanctions.email_enabled)
            self.email_recipients_var.set(",".join(self.config.sanctions.email_recipients))

        # 加载定时任务配置
        if hasattr(self.config, 'schedule'):
            self.schedule_enabled_var.set(self.config.schedule.enabled)
            self.schedule_type_var.set(self.config.schedule.schedule_type)
            self.schedule_time_var.set(self.config.schedule.daily_time)
            self.cron_expr_var.set(self.config.schedule.cron_expression)
            self._update_schedule_ui()

        # 设置默认任务描述
        if not self.task_entry.get("1.0", tk.END).strip():
            self.task_entry.insert("1.0", "分析OFAC/BIS制裁清单更新，识别涉及中国主体的制裁实体")

    def _set_date_range(self, preset: str):
        """设置日期范围快捷选项"""
        today = datetime.now()
        if preset == "today":
            self.date_start_var.set(today.strftime("%Y-%m-%d"))
            self.date_end_var.set(today.strftime("%Y-%m-%d"))
        elif preset == "7days":
            from datetime import timedelta
            week_ago = today - timedelta(days=7)
            self.date_start_var.set(week_ago.strftime("%Y-%m-%d"))
            self.date_end_var.set(today.strftime("%Y-%m-%d"))
        elif preset == "30days":
            from datetime import timedelta
            month_ago = today - timedelta(days=30)
            self.date_start_var.set(month_ago.strftime("%Y-%m-%d"))
            self.date_end_var.set(today.strftime("%Y-%m-%d"))

    def _on_schedule_enabled_change(self):
        """定时任务开关改变"""
        self._update_next_run_time()

    def _update_schedule_ui(self):
        """根据周期类型更新UI"""
        schedule_type = self.schedule_type_var.get()
        if schedule_type == "cron":
            self.cron_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        else:
            self.cron_frame.pack_forget()
        self._update_next_run_time()

    def _update_next_run_time(self):
        """更新下次执行时间显示"""
        if not self.schedule_enabled_var.get():
            self.next_run_var.set("")
            return

        schedule = self._get_schedule_config()
        next_time = self.scheduler.get_next_run_time(schedule)
        if next_time:
            self.next_run_var.set(f"下次执行: {next_time}")
        else:
            self.next_run_var.set("")

    def _get_schedule_config(self) -> ScheduleConfig:
        """获取定时任务配置"""
        return ScheduleConfig(
            enabled=self.schedule_enabled_var.get(),
            schedule_type=self.schedule_type_var.get(),
            daily_time=self.schedule_time_var.get(),
            weekly_time=self.schedule_time_var.get(),
            cron_expression=self.cron_expr_var.get()
        )

    def _update_history_combo(self):
        """更新历史记录下拉框"""
        history = self.config.history if hasattr(self.config, 'history') else HistoryConfig()
        items = history.items if history.items else []

        choices = []
        for item in items:
            # 显示格式：时间 - 任务描述前20字
            short_desc = item.task_desc[:20] if item.task_desc else "无描述"
            display = f"{item.timestamp[:16]} - {short_desc}..."
            choices.append(display)

        if choices:
            self.history_combo["values"] = choices
            self.history_combo.state(["!readonly"])
        else:
            self.history_combo["values"] = ["(无历史记录)"]
            self.history_combo.state(["readonly"])

    def _on_history_select(self, event=None):
        """选择历史记录"""
        idx = self.history_combo.current()
        history = self.config.history if hasattr(self.config, 'history') else HistoryConfig()
        items = history.items if history.items else []

        if 0 <= idx < len(items):
            item = items[idx]
            # 填充表单
            self.task_entry.delete("1.0", tk.END)
            self.task_entry.insert("1.0", item.task_desc)

            self.keyword_input.set_tags(item.keywords)

            self.urls_text.delete("1.0", tk.END)
            if item.urls:
                self.urls_text.insert("1.0", "\n".join(item.urls))

    def _save_to_history(self, task_desc: str, keywords: list, urls: list):
        """保存到历史记录"""
        if not task_desc and not urls:
            return

        # 创建新记录
        new_item = HistoryItem(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            task_desc=task_desc,
            keywords=keywords,
            urls=urls
        )

        # 获取现有历史
        if not hasattr(self.config, 'history') or not self.config.history:
            self.config.history = HistoryConfig()

        items = self.config.history.items or []

        # 检查是否与最近一条相同
        if items and items[0].task_desc == task_desc and items[0].urls == urls:
            return  # 相同，不保存

        # 添加到开头
        items.insert(0, new_item)

        # 保留最多6条
        if len(items) > self.config.history.max_items:
            items = items[:self.config.history.max_items]

        self.config.history.items = items

        # 保存
        self.pm.save_config(self.config)
        self._update_history_combo()

    def _clear_history(self):
        """清除历史记录"""
        if hasattr(self.config, 'history'):
            self.config.history.items = []
            self.pm.save_config(self.config)
            self._update_history_combo()
            messagebox.showinfo("成功", "历史记录已清除")

    def _get_urls_from_text(self) -> list:
        """从文本框获取URLs"""
        text = self.urls_text.get("1.0", tk.END)
        urls = [line.strip() for line in text.split('\n') if line.strip()]
        # 简单验证URL格式
        valid_urls = [u for u in urls if u.startswith('http://') or u.startswith('https://')]
        return valid_urls

    def _start_monitoring(self):
        """开始监测"""
        if self.task_running:
            return

        task_desc = self.task_entry.get("1.0", tk.END).strip()
        keywords = self.keyword_input.get_tags()

        if not keywords:
            messagebox.showwarning("提示", "请输入监控关键词")
            return

        # 检查是否启用了定时任务
        if self.schedule_enabled_var.get():
            # 保存任务参数到配置
            self._save_sanctions_config()
            self.config.schedule = self._get_schedule_config()
            self.pm.save_config(self.config)

            # 注册定时任务
            self._register_scheduled_monitoring(task_desc, keywords)
            self._update_next_run_time()
            self._update_status("定时任务已设置")
            messagebox.showinfo("定时任务", "定时任务已设置，将在指定时间自动执行")
            return

        # 立即执行
        self._execute_monitoring(task_desc, keywords)

    def _save_sanctions_config(self):
        """保存制裁监测配置"""
        recipients = self.email_recipients_var.get()
        email_list = [r.strip() for r in recipients.split(',') if r.strip()]

        self.config.sanctions.date_range_start = self.date_start_var.get()
        self.config.sanctions.date_range_end = self.date_end_var.get()
        self.config.sanctions.keywords = self.keyword_input.get_tags()
        self.config.sanctions.email_enabled = self.email_enabled_var.get()
        self.config.sanctions.email_recipients = email_list

    def _execute_monitoring(self, task_desc: str, keywords: list):
        """执行监测任务"""
        self.task_running = True
        self.start_btn.config(state=tk.DISABLED)
        self._update_status("正在监测...")

        # 在后台线程执行
        thread = threading.Thread(
            target=self._run_monitoring,
            args=(task_desc, keywords),
            daemon=True
        )
        thread.start()

    def _run_monitoring(self, task_desc: str, keywords: list):
        """后台执行监测"""
        try:
            # 保存配置
            self._save_sanctions_config()
            self.pm.save_config(self.config)

            # 获取数据源
            source = self.source_var.get()
            date_start = self.date_start_var.get()
            date_end = self.date_end_var.get()

            self._log(f"开始OFAC/BIS制裁清单监测...")
            self._log(f"数据源: {source}")
            self._log(f"日期范围: {date_start} 至 {date_end}")
            self._log(f"关键词: {', '.join(keywords)}")

            # 创建爬虫
            crawler = SanctionsCrawler(
                proxy=self.config.search_proxy if self.config.search_proxy.enabled else None
            )

            all_results = []

            # 爬取OFAC
            if source in ["ofac", "all"]:
                self._update_status("正在爬取OFAC...")
                self._log("正在爬取OFAC制裁清单...")
                ofac_results = crawler.crawl_ofac(keywords, date_start, date_end)
                self._log(f"OFAC: 发现 {len(ofac_results)} 条更新")
                all_results.extend(ofac_results)

                for r in ofac_results:
                    self._update_crawl_content(f"[OFAC] {r.date} - {r.title}\n")
                    if r.has_china:
                        self._update_crawl_content(f"  ⚠️ 涉及中国主体: {', '.join(r.matched_keywords)}\n")

            # 爬取BIS
            if source in ["bis", "all"]:
                self._update_status("正在爬取BIS...")
                self._log("正在爬取BIS实体清单...")
                bis_results = crawler.crawl_bis(keywords, date_start, date_end)
                self._log(f"BIS: 发现 {len(bis_results)} 条更新")
                all_results.extend(bis_results)

                for r in bis_results:
                    self._update_crawl_content(f"[BIS] {r.date} - {r.title}\n")
                    if r.has_china:
                        self._update_crawl_content(f"  ⚠️ 涉及中国主体: {', '.join(r.matched_keywords)}\n")

            self._update_progress(30)

            # 过滤涉及中国主体的结果
            china_results = [r for r in all_results if r.has_china]
            self._log(f"发现 {len(china_results)} 条涉及中国主体的更新")

            # LLM分析
            if china_results:
                self._update_status("正在进行LLM分析...")
                self._log("开始LLM深度分析...")

                analyzer = SanctionsAnalyzer(
                    llm_config=self.config.llm,
                    llm_proxy=self.config.llm_proxy if self.config.llm_proxy.enabled else None
                )

                self._update_analysis_content("# OFAC/BIS制裁分析报告\n\n")
                self._update_analysis_content(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                self._update_analysis_content(f"共发现 **{len(china_results)}** 个涉及中国主体的制裁实体\n\n")
                self._update_analysis_content("---\n\n")

                for i, result in enumerate(china_results):
                    self._log(f"分析中: {result.title or result.source}")
                    self._update_analysis_content(f"## {i+1}. {result.title or result.source}\n\n")

                    # 执行分析
                    analysis = analyzer.analyze_sync(result, task_desc)
                    self._update_analysis_content(analysis)
                    self._update_analysis_content("\n\n---\n\n")

                    self._update_progress(30 + int(60 * (i + 1) / len(china_results)))

            else:
                self._log("未发现涉及中国主体的制裁更新")
                self._update_analysis_content("# 分析结果\n\n")
                self._update_analysis_content("✅ 未发现涉及中国主体的制裁更新\n")

            self._update_progress(100)
            self._update_status("监测完成")
            self._log("监测任务完成")

        except Exception as e:
            self._log(f"错误: {e}")
            messagebox.showerror("错误", f"监测失败: {e}")
            self._update_status("监测失败")

        finally:
            self.task_running = False
            self.start_btn.config(state=tk.NORMAL)

    def _register_scheduled_monitoring(self, task_desc: str, keywords: list):
        """注册定时监测任务"""
        self._scheduled_params = {
            "task_desc": task_desc,
            "keywords": keywords
        }

        self.scheduler.remove_task("sanctions_task")

        schedule = self._get_schedule_config()
        self.scheduler.add_task(
            name="sanctions_task",
            schedule=schedule,
            callback=lambda: self._execute_scheduled_monitoring()
        )

    def _execute_scheduled_monitoring(self):
        """执行定时监测任务"""
        if hasattr(self, '_scheduled_params'):
            params = self._scheduled_params
            self.root.after(0, lambda: self._execute_monitoring(
                params["task_desc"],
                params["keywords"]
            ))

    def _log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.root.after(0, lambda: (
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n"),
            self.log_text.see(tk.END)
        ))

    def _register_scheduled_task(self, task_desc: str, urls: list, keywords: list):
        """注册定时任务"""
        # 保存任务参数
        self._scheduled_task_params = {
            "task_desc": task_desc,
            "urls": urls,
            "keywords": keywords
        }

        # 移除旧任务
        self.scheduler.remove_task("crawler_task")

        # 添加新任务
        schedule = self._get_schedule_config()
        self.scheduler.add_task(
            name="crawler_task",
            schedule=schedule,
            callback=lambda: self._execute_scheduled_task()
        )

    def _execute_scheduled_task(self):
        """执行定时任务（在调度器线程中调用）"""
        if hasattr(self, '_scheduled_task_params'):
            params = self._scheduled_task_params
            # 在主线程中执行任务
            self.root.after(0, lambda: self._execute_task(
                params["task_desc"],
                params["urls"],
                params["keywords"]
            ))

    def _update_status(self, status: str):
        """更新状态"""
        self.root.after(0, lambda: self.status_var.set(status))

    def _update_progress(self, value: float):
        """更新进度"""
        self.root.after(0, lambda: self.progress_var.set(value))

    def _update_crawl_content(self, text: str):
        """更新爬取内容"""
        def append():
            self.content_text.insert(tk.END, text)
            self.content_text.see(tk.END)
        self.root.after(0, append)

    def _update_llm_content(self, text: str):
        """更新LLM内容（兼容旧方法）"""
        def append():
            if text == "":
                self.analysis_text.delete("1.0", tk.END)
            else:
                self.analysis_text.insert(tk.END, text)
                self.analysis_text.see(tk.END)
        self.root.after(0, append)

    def _update_analysis_content(self, text: str):
        """更新分析结果内容"""
        def append():
            if text == "":
                self.analysis_text.delete("1.0", tk.END)
            else:
                self.analysis_text.insert(tk.END, text)
                self.analysis_text.see(tk.END)
        self.root.after(0, append)

    def _export_report(self):
        """导出报告"""
        content = self.analysis_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "没有内容可导出")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown文件", "*.md"), ("HTML文件", "*.html"), ("所有文件", "*.*")]
        )
        if filepath:
            if filepath.endswith('.html'):
                content = self._markdown_to_html(content)
            Path(filepath).write_text(content, encoding='utf-8')
            messagebox.showinfo("成功", f"已导出到 {filepath}")

    def _export_html(self):
        """导出HTML（兼容旧方法）"""
        self._export_report()

    def _export_markdown(self):
        """导出Markdown（兼容旧方法）"""
        content = self.analysis_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "没有内容可导出")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown文件", "*.md"), ("所有文件", "*.*")]
        )
        if filepath:
            Path(filepath).write_text(content, encoding='utf-8')
            messagebox.showinfo("成功", f"已导出到 {filepath}")

    def _export_json(self):
        """导出JSON"""
        content = self.analysis_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "没有内容可导出")
            return

        # 解析报告内容
        report = self._parse_report_to_json(content)

        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", f"已导出到 {filepath}")

    def _clear_log(self):
        """清空日志"""
        self.log_text.delete("1.0", tk.END)
        self._log("日志已清空")

    def _send_email(self):
        """发送邮件（预留功能）"""
        if not self.email_enabled_var.get():
            messagebox.showinfo("提示", "请先启用邮件通知")
            return

        recipients = self.email_recipients_var.get()
        if not recipients:
            messagebox.showwarning("提示", "请输入收件人")
            return

        messagebox.showinfo("提示", "邮件发送功能预留中")
        self._log("邮件发送功能预留中")

    def _parse_report_to_json(self, content: str) -> dict:
        """将Markdown报告解析为JSON结构"""
        report = {
            "title": "",
            "summary": "",
            "content": content,
            "sources": [],
            "generated_at": datetime.now().isoformat()
        }

        lines = content.split('\n')
        current_section = None
        content_buffer = []

        for line in lines:
            if line.startswith('# ') and not report["title"]:
                report["title"] = line[2:].strip()
                current_section = None
            elif line.startswith('## '):
                if current_section == "content":
                    report["content"] = '\n'.join(content_buffer).strip()
                    content_buffer = []
                elif current_section == "summary" and content_buffer:
                    report["summary"] = '\n'.join(content_buffer).strip()
                    content_buffer = []

                section_name = line[3:].strip().lower()
                if '概述' in section_name or 'summary' in section_name:
                    current_section = "summary"
                elif '详细' in section_name or 'content' in section_name:
                    current_section = "content"
            else:
                content_buffer.append(line)

        # 处理最后一部分
        if current_section == "content":
            report["content"] = '\n'.join(content_buffer).strip()
        elif current_section == "summary" and content_buffer:
            report["summary"] = '\n'.join(content_buffer).strip()

        return report

    def _markdown_to_html(self, markdown: str) -> str:
        """简单Markdown转HTML"""
        import re
        html = markdown

        # 标题
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # 粗体
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

        # 斜体
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # 链接
        html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)

        # 段落
        html = re.sub(r'\n\n', '</p><p>', html)

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>分析报告</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; line-height: 1.6; }}
h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
h2 {{ color: #555; margin-top: 30px; }}
h3 {{ color: #666; }}
blockquote {{ border-left: 4px solid #ddd; margin: 20px 0; padding-left: 20px; color: #666; }}
code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
a {{ color: #0066cc; }}
</style>
</head>
<body>
<p>{html}</p>
</body>
</html>"""

    def _send_feishu(self):
        """发送到飞书"""
        from feishu import FeishuSender
        content = self.llm_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "没有内容可发送")
            return

        sender = FeishuSender(self.config.feishu)
        if sender.send_document(title="爬虫分析报告", content=content):
            messagebox.showinfo("成功", "已发送到飞书")
        else:
            messagebox.showwarning("提示", "飞书发送功能预留中或未启用")

    def _open_settings(self):
        """打开设置"""
        from gui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.root, self.config, self.pm)
        if dialog.show():
            # 重新加载配置
            new_config = self.pm.load_config()
            if new_config:
                self.config = new_config
                self._load_config()

    def _change_password(self):
        """修改密码"""
        messagebox.showinfo("提示", "密码修改功能开发中")

    def _show_about(self):
        """关于"""
        messagebox.showinfo(
            "关于",
            "网页爬虫 + LLM 分析工具\n\n"
            "功能：\n"
            "- 搜索引擎发现相关URLs\n"
            "- 爬取网页内容和PDF\n"
            "- LLM分析并生成报告\n"
            "- 支持代理配置\n"
            "- 支持飞书发送（预留）"
        )

    def run(self):
        """运行"""
        self.root.mainloop()
