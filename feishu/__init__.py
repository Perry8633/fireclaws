"""
飞书集成模块（预留接口）
暂不实现具体逻辑，后续可对接飞书CLI或飞书API
"""

from config.settings import FeishuConfig


class FeishuSender:
    """飞书发送器"""

    def __init__(self, config: FeishuConfig):
        self.config = config

    def send_document(self, title: str, content: str) -> bool:
        """
        发送文档到飞书（预留接口）

        Args:
            title: 文档标题
            content: 文档内容（Markdown格式）

        Returns:
            是否发送成功
        """
        if not self.config.enabled:
            print("飞书发送未启用")
            return False

        # TODO: 实现飞书文档发送逻辑
        # 可选方案：
        # 1. 飞书CLI: https://github.com/larksuite/oapi-sdk-cli
        # 2. 飞书开放API: https://open.feishu.cn/document/home/index
        print("飞书文档发送功能预留中...")
        return False

    def send_message(self, content: str) -> bool:
        """
        发送消息到飞书（预留接口）
        """
        if not self.config.enabled:
            return False

        # TODO: 实现飞书消息发送逻辑
        print("飞书消息发送功能预留中...")
        return False
