import tkinter as tk
from tkinter import ttk, messagebox
import re

from config.settings import AppConfig, LLMConfig, ProxyConfig, SearchConfig, FeishuConfig
from config.encryption import PasswordManager
from gui.styles import DesignSystem


class SettingsDialog:
    """设置对话框"""

    def __init__(self, parent, config: AppConfig, pm: PasswordManager):
        self.config = config
        self.pm = pm
        self.result = False
        self.proxy_enabled_vars = {}  # 初始化代理变量字典
        self._proxy_vars = {}  # 初始化代理控件变量字典

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("设置")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 600) // 2
        y = (self.dialog.winfo_screenheight() - 500) // 2
        self.dialog.geometry(f"600x500+{x}+{y}")

        # 设置背景色
        self.dialog.configure(bg=DesignSystem.COLORS['background'])

        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        # Notebook
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab页
        self.llm_frame = ttk.Frame(notebook)
        self.search_frame = ttk.Frame(notebook)
        self.llm_proxy_frame = ttk.Frame(notebook)
        self.search_proxy_frame = ttk.Frame(notebook)
        self.feishu_frame = ttk.Frame(notebook)

        notebook.add(self.llm_frame, text="大模型")
        notebook.add(self.search_frame, text="搜索引擎")
        notebook.add(self.llm_proxy_frame, text="大模型代理")
        notebook.add(self.search_proxy_frame, text="爬虫代理")
        notebook.add(self.feishu_frame, text="飞书")

        # 加载各Tab内容
        self._setup_llm_tab()
        self._setup_search_tab()
        self._setup_proxy_tab(self.llm_proxy_frame, "llm_proxy")
        self._setup_proxy_tab(self.search_proxy_frame, "search_proxy")
        self._setup_feishu_tab()

        # 按钮
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="保存", style="Primary.TButton", command=self._save).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="取消", style="Secondary.TButton", command=self.dialog.destroy).pack(side=tk.RIGHT)

    def _setup_llm_tab(self):
        """大模型设置Tab"""
        frame = self.llm_frame
        padding = 10

        # Provider预设
        ttk.Label(frame, text="Provider预设：").grid(row=0, column=0, sticky=tk.W, pady=5, padx=padding)
        self.provider_var = tk.StringVar(value=self.config.llm.provider)
        provider_combo = ttk.Combobox(
            frame,
            textvariable=self.provider_var,
            values=["minimax", "deepseek", "qwen", "custom"],
            state="readonly"
        )
        provider_combo.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=padding)
        provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        # Base URL
        ttk.Label(frame, text="Base URL：").grid(row=1, column=0, sticky=tk.W, pady=5, padx=padding)
        self.base_url_var = tk.StringVar(value=self.config.llm.base_url)
        ttk.Entry(frame, textvariable=self.base_url_var).grid(row=1, column=1, sticky=tk.EW, pady=5, padx=padding)

        # API Key
        ttk.Label(frame, text="API Key：").grid(row=2, column=0, sticky=tk.W, pady=5, padx=padding)
        self.api_key_var = tk.StringVar(value=self.config.llm.api_key)
        ttk.Entry(frame, textvariable=self.api_key_var, show="*").grid(row=2, column=1, sticky=tk.EW, pady=5, padx=padding)

        # Model
        ttk.Label(frame, text="Model：").grid(row=3, column=0, sticky=tk.W, pady=5, padx=padding)
        self.model_var = tk.StringVar(value=self.config.llm.model)
        ttk.Entry(frame, textvariable=self.model_var).grid(row=3, column=1, sticky=tk.EW, pady=5, padx=padding)

        # Temperature
        ttk.Label(frame, text="Temperature：").grid(row=4, column=0, sticky=tk.W, pady=5, padx=padding)
        self.temp_var = tk.DoubleVar(value=self.config.llm.temperature)
        ttk.Spinbox(frame, from_=0.0, to=2.0, increment=0.1, textvariable=self.temp_var).grid(row=4, column=1, sticky=tk.EW, pady=5, padx=padding)

        # System Prompt
        ttk.Label(frame, text="System Prompt：").grid(row=5, column=0, sticky=tk.NW, pady=5, padx=padding)
        self.system_prompt_text = tk.Text(frame, height=8, wrap=tk.WORD,
            bg=DesignSystem.COLORS['surface'],
            fg=DesignSystem.COLORS['text_primary'],
            insertbackground=DesignSystem.COLORS['text_primary'],
            font=DesignSystem.FONTS['body'],
            relief='solid',
            bd=1,
            padx=8,
            pady=8
        )
        self.system_prompt_text.grid(row=5, column=1, sticky=tk.EW, pady=5, padx=padding)
        self.system_prompt_text.insert("1.0", self.config.llm.system_prompt)

        # 列权重
        frame.columnconfigure(1, weight=1)

    def _setup_search_tab(self):
        """搜索引擎设置Tab"""
        frame = self.search_frame
        padding = 10

        # Provider
        ttk.Label(frame, text="搜索引擎：").grid(row=0, column=0, sticky=tk.W, pady=5, padx=padding)
        self.search_provider_var = tk.StringVar(value=self.config.search.provider)
        search_combo = ttk.Combobox(
            frame,
            textvariable=self.search_provider_var,
            values=["ddgs", "brave", "tavily"],
            state="readonly"
        )
        search_combo.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=padding)

        # API Key
        ttk.Label(frame, text="API Key：").grid(row=1, column=0, sticky=tk.W, pady=5, padx=padding)
        self.search_api_key_var = tk.StringVar(value=self.config.search.api_key)
        ttk.Entry(frame, textvariable=self.search_api_key_var, show="*").grid(row=1, column=1, sticky=tk.EW, pady=5, padx=padding)

        # 说明
        ttk.Label(
            frame,
            text="说明：\n"
            "- DuckDuckGo (ddgs): 无需API Key，免费使用\n"
            "- Brave Search: 需要API Key，每月2000次免费\n"
            "- Tavily: 需要API Key，每月1000次免费"
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=20, padx=padding)

        frame.columnconfigure(1, weight=1)

    def _setup_proxy_tab(self, frame, proxy_type: str):
        """代理设置Tab"""
        padding = 10

        # 获取对应的配置
        if proxy_type == "llm_proxy":
            proxy_config = self.config.llm_proxy
        else:
            proxy_config = self.config.search_proxy

        # 启用
        self.proxy_enabled_vars[proxy_type] = tk.BooleanVar(value=proxy_config.enabled)
        ttk.Checkbutton(
            frame,
            text="启用代理",
            variable=self.proxy_enabled_vars[proxy_type]
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5, padx=padding)

        # 协议
        ttk.Label(frame, text="协议：").grid(row=1, column=0, sticky=tk.W, pady=5, padx=padding)
        protocol_var = tk.StringVar(value=proxy_config.protocol)
        self._proxy_vars[f'{proxy_type}_protocol'] = protocol_var
        ttk.Combobox(
            frame,
            textvariable=protocol_var,
            values=["http", "https", "socks5"],
            state="readonly"
        ).grid(row=1, column=1, sticky=tk.EW, pady=5, padx=padding)

        # 地址
        ttk.Label(frame, text="地址：").grid(row=2, column=0, sticky=tk.W, pady=5, padx=padding)
        host_var = tk.StringVar(value=proxy_config.host)
        self._proxy_vars[f'{proxy_type}_host'] = host_var
        ttk.Entry(frame, textvariable=host_var).grid(row=2, column=1, sticky=tk.EW, pady=5, padx=padding)

        # 端口
        ttk.Label(frame, text="端口：").grid(row=3, column=0, sticky=tk.W, pady=5, padx=padding)
        port_var = tk.IntVar(value=proxy_config.port)
        self._proxy_vars[f'{proxy_type}_port'] = port_var
        ttk.Spinbox(frame, from_=1, to=65535, textvariable=port_var).grid(row=3, column=1, sticky=tk.EW, pady=5, padx=padding)

        # 用户名
        ttk.Label(frame, text="用户名：").grid(row=4, column=0, sticky=tk.W, pady=5, padx=padding)
        username_var = tk.StringVar(value=proxy_config.username)
        self._proxy_vars[f'{proxy_type}_username'] = username_var
        ttk.Entry(frame, textvariable=username_var).grid(row=4, column=1, sticky=tk.EW, pady=5, padx=padding)

        # 密码
        ttk.Label(frame, text="密码：").grid(row=5, column=0, sticky=tk.W, pady=5, padx=padding)
        password_var = tk.StringVar(value=proxy_config.password)
        self._proxy_vars[f'{proxy_type}_password'] = password_var
        ttk.Entry(frame, textvariable=password_var, show="*").grid(row=5, column=1, sticky=tk.EW, pady=5, padx=padding)

        # 设置列权重
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=1)

    def _setup_feishu_tab(self):
        """飞书设置Tab（预留）"""
        frame = self.feishu_frame
        padding = 10

        ttk.Label(
            frame,
            text="飞书集成（预留接口）",
            style="Title.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=10, padx=padding)

        # 启用
        self.feishu_enabled_var = tk.BooleanVar(value=self.config.feishu.enabled)
        ttk.Checkbutton(
            frame,
            text="启用飞书",
            variable=self.feishu_enabled_var
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5, padx=padding)

        # CLI路径
        ttk.Label(frame, text="CLI路径：").grid(row=2, column=0, sticky=tk.W, pady=5, padx=padding)
        self.feishu_cli_var = tk.StringVar(value=self.config.feishu.cli_path)
        ttk.Entry(frame, textvariable=self.feishu_cli_var).grid(row=2, column=1, sticky=tk.EW, pady=5, padx=padding)

        # App ID
        ttk.Label(frame, text="App ID：").grid(row=3, column=0, sticky=tk.W, pady=5, padx=padding)
        self.feishu_app_id_var = tk.StringVar(value=self.config.feishu.app_id)
        ttk.Entry(frame, textvariable=self.feishu_app_id_var).grid(row=3, column=1, sticky=tk.EW, pady=5, padx=padding)

        # App Secret
        ttk.Label(frame, text="App Secret：").grid(row=4, column=0, sticky=tk.W, pady=5, padx=padding)
        self.feishu_secret_var = tk.StringVar(value=self.config.feishu.app_secret)
        ttk.Entry(frame, textvariable=self.feishu_secret_var, show="*").grid(row=4, column=1, sticky=tk.EW, pady=5, padx=padding)

        ttk.Label(
            frame,
            text="注：飞书功能暂预留，后续版本支持"
        ).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=20, padx=padding)

        frame.columnconfigure(1, weight=1)

    def _on_provider_change(self, event=None):
        """Provider变化时更新URL"""
        provider = self.provider_var.get()
        urls = {
            "minimax": "https://api.minimax.chat/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "custom": "https://api.openai.com/v1"
        }
        if provider in urls:
            self.base_url_var.set(urls[provider])

    def _save(self):
        """保存设置"""
        # 更新配置
        self.config.llm.provider = self.provider_var.get()
        self.config.llm.base_url = self.base_url_var.get()
        self.config.llm.api_key = self.api_key_var.get()
        self.config.llm.model = self.model_var.get()
        self.config.llm.temperature = self.temp_var.get()
        self.config.llm.system_prompt = self.system_prompt_text.get("1.0", tk.END).strip()

        self.config.search.provider = self.search_provider_var.get()
        self.config.search.api_key = self.search_api_key_var.get()

        # 代理
        self.config.llm_proxy.enabled = self.proxy_enabled_vars["llm_proxy"].get()
        self.config.llm_proxy.protocol = self._proxy_vars.get("llm_proxy_protocol", tk.StringVar()).get()
        self.config.llm_proxy.host = self._proxy_vars.get("llm_proxy_host", tk.StringVar()).get()
        self.config.llm_proxy.port = self._proxy_vars.get("llm_proxy_port", tk.IntVar()).get()
        self.config.llm_proxy.username = self._proxy_vars.get("llm_proxy_username", tk.StringVar()).get()
        self.config.llm_proxy.password = self._proxy_vars.get("llm_proxy_password", tk.StringVar()).get()

        self.config.search_proxy.enabled = self.proxy_enabled_vars["search_proxy"].get()
        self.config.search_proxy.protocol = self._proxy_vars.get("search_proxy_protocol", tk.StringVar()).get()
        self.config.search_proxy.host = self._proxy_vars.get("search_proxy_host", tk.StringVar()).get()
        self.config.search_proxy.port = self._proxy_vars.get("search_proxy_port", tk.IntVar()).get()
        self.config.search_proxy.username = self._proxy_vars.get("search_proxy_username", tk.StringVar()).get()
        self.config.search_proxy.password = self._proxy_vars.get("search_proxy_password", tk.StringVar()).get()

        # 飞书
        self.config.feishu.enabled = self.feishu_enabled_var.get()
        self.config.feishu.cli_path = self.feishu_cli_var.get()
        self.config.feishu.app_id = self.feishu_app_id_var.get()
        self.config.feishu.app_secret = self.feishu_secret_var.get()

        # 保存
        try:
            self.pm.save_config(self.config)
            messagebox.showinfo("成功", "设置已保存")
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")

    def show(self) -> bool:
        """显示对话框并返回结果"""
        self.dialog.wait_window()
        return self.result
