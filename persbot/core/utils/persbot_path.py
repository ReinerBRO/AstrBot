"""Persbot统一路径获取

项目路径：固定为源码所在路径
根目录路径：默认为当前工作目录，可通过环境变量 PERSBOT_ROOT 指定
数据目录路径：固定为根目录下的 data 目录
配置文件路径：固定为数据目录下的 config 目录
插件目录路径：固定为数据目录下的 plugins 目录
插件数据目录路径：固定为数据目录下的 plugin_data 目录
T2I 模板目录路径：固定为数据目录下的 t2i_templates 目录
WebChat 数据目录路径：固定为数据目录下的 webchat 目录
临时文件目录路径：固定为数据目录下的 temp 目录
Skills 目录路径：固定为数据目录下的 skills 目录
第三方依赖目录路径：固定为数据目录下的 site-packages 目录
"""

import os

from persbot.core.utils.runtime_env import is_packaged_desktop_runtime


def get_persbot_path() -> str:
    """获取Persbot项目路径"""
    return os.path.realpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../"),
    )


def get_persbot_root() -> str:
    """获取Persbot根目录路径"""
    if path := os.environ.get("PERSBOT_ROOT"):
        return os.path.realpath(path)
    if is_packaged_desktop_runtime():
        return os.path.realpath(os.path.join(os.path.expanduser("~"), ".persbot"))
    return os.path.realpath(os.getcwd())


def get_persbot_data_path() -> str:
    """获取Persbot数据目录路径"""
    return os.path.realpath(os.path.join(get_persbot_root(), "data"))


def get_persbot_config_path() -> str:
    """获取Persbot配置文件路径"""
    return os.path.realpath(os.path.join(get_persbot_data_path(), "config"))


def get_persbot_plugin_path() -> str:
    """获取Persbot插件目录路径"""
    return os.path.realpath(os.path.join(get_persbot_data_path(), "plugins"))


def get_persbot_plugin_data_path() -> str:
    """获取Persbot插件数据目录路径"""
    return os.path.realpath(os.path.join(get_persbot_data_path(), "plugin_data"))


def get_persbot_t2i_templates_path() -> str:
    """获取Persbot T2I 模板目录路径"""
    return os.path.realpath(os.path.join(get_persbot_data_path(), "t2i_templates"))


def get_persbot_webchat_path() -> str:
    """获取Persbot WebChat 数据目录路径"""
    return os.path.realpath(os.path.join(get_persbot_data_path(), "webchat"))


def get_persbot_temp_path() -> str:
    """获取Persbot临时文件目录路径"""
    return os.path.realpath(os.path.join(get_persbot_data_path(), "temp"))


def get_persbot_skills_path() -> str:
    """获取Persbot Skills 目录路径"""
    return os.path.realpath(os.path.join(get_persbot_data_path(), "skills"))


def get_persbot_site_packages_path() -> str:
    """获取Persbot第三方依赖目录路径"""
    return os.path.realpath(os.path.join(get_persbot_data_path(), "site-packages"))


def get_persbot_knowledge_base_path() -> str:
    """获取Persbot知识库根目录路径"""
    return os.path.realpath(os.path.join(get_persbot_data_path(), "knowledge_base"))


def get_persbot_backups_path() -> str:
    """获取Persbot备份目录路径"""
    return os.path.realpath(os.path.join(get_persbot_data_path(), "backups"))
