import json
import hashlib
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .settings import AppConfig


class PasswordManager:
    """密码管理和配置加密"""

    SALT_FILE = Path("data/configs/.salt")
    CONFIG_FILE = Path("data/configs/config.json")

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._salt: Optional[bytes] = None

    def _get_salt(self) -> bytes:
        """获取或生成盐值"""
        if self.SALT_FILE.exists():
            return self.SALT_FILE.read_bytes()
        salt = Fernet.generate_key()[:32]
        self.SALT_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.SALT_FILE.write_bytes(salt)
        return salt

    def _derive_key(self, password: str) -> bytes:
        """PBKDF2密钥派生"""
        salt = self._get_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def _hash_password(self, password: str) -> str:
        """生成密码哈希"""
        salt = self._get_salt()
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000).hex()

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """验证密码"""
        return self._hash_password(password) == stored_hash

    def set_password(self, password: str) -> str:
        """设置密码，返回哈希"""
        return self._hash_password(password)

    def unlock(self, password: str, config: AppConfig) -> bool:
        """解锁配置"""
        if not self.verify_password(password, config.password_hash):
            return False
        self._fernet = Fernet(self._derive_key(password))
        return True

    def lock(self):
        """锁定配置"""
        self._fernet = None

    def is_unlocked(self) -> bool:
        return self._fernet is not None

    def encrypt_config(self, config: AppConfig) -> str:
        """加密配置并返回JSON字符串"""
        if not self._fernet:
            raise ValueError("配置已锁定，请先解锁")
        json_str = config.model_dump_json()
        encrypted = self._fernet.encrypt(json_str.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_config(self, encrypted_data: str) -> AppConfig:
        """解密配置"""
        if not self._fernet:
            raise ValueError("配置已锁定，请先解锁")
        encrypted = base64.b64decode(encrypted_data.encode())
        decrypted = self._fernet.decrypt(encrypted)
        return AppConfig.model_validate_json(decrypted)

    def save_config(self, config: AppConfig):
        """保存加密后的配置"""
        encrypted = self.encrypt_config(config)
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.CONFIG_FILE.write_text(encrypted)

    def load_config(self) -> Optional[AppConfig]:
        """加载配置"""
        if not self.CONFIG_FILE.exists():
            return None
        try:
            encrypted = self.CONFIG_FILE.read_text()
            return self.decrypt_config(encrypted)
        except Exception:
            return None

    def has_password(self) -> bool:
        """检查是否已设置密码"""
        config = self.load_config()
        return config is not None and bool(config.password_hash)
