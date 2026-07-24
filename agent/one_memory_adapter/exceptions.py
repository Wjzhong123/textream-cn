"""
自定义异常
"""


class OneMemoryError(Exception):
    """One Memory 基础异常"""
    pass


class ConnectionError(OneMemoryError):
    """连接错误"""
    pass


class MemoryNotFoundError(OneMemoryError):
    """记忆不存在"""
    pass


class ValidationError(OneMemoryError):
    """参数验证失败"""
    pass
