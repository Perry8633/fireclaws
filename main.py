#!/usr/bin/env python3
"""
网页爬虫 + LLM 分析工具
主入口
"""

import sys
import os
from pathlib import Path

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入后创建必要目录
data_dirs = ["data/configs", "data/downloads", "data/logs"]
for d in data_dirs:
    Path(d).mkdir(parents=True, exist_ok=True)

from config.settings import AppConfig
from config.encryption import PasswordManager
from utils.logger import setup_logger, get_logger
from gui.main_window import MainWindow


def main():
    """主函数"""
    # 设置日志
    logger = setup_logger()
    logger.info("启动应用...")

    # 密码管理器
    pm = PasswordManager()

    # 尝试加载配置
    config = pm.load_config()

    if config is None:
        # 首次运行，创建默认配置
        logger.info("首次运行，创建默认配置...")
        config = AppConfig()

        # 如果没有密码，先设置密码
        if not pm.has_password():
            password = input("请设置管理员密码（首次运行）：")
            config.password_hash = pm.set_password(password)

        # 保存默认配置
        pm.save_config(config)
        logger.info("默认配置已保存")

    # 解锁配置
    password = input("请输入管理员密码：")
    if not pm.unlock(password, config):
        logger.error("密码错误")
        print("密码错误，拒绝访问")
        sys.exit(1)

    logger.info("密码验证成功")

    # 创建并运行主窗口
    app = MainWindow(config, pm)
    app.run()


if __name__ == "__main__":
    main()
