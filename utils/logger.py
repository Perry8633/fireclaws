import sys
from pathlib import Path
from loguru import logger


def setup_logger():
    """配置日志"""
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # 文件输出
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # 每天零点轮转
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG"
    )

    return logger


def get_logger():
    """获取logger实例"""
    return logger
