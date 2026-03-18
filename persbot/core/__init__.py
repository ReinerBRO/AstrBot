import os

from persbot.core.config import PersbotConfig
from persbot.core.config.default import DB_PATH
from persbot.core.db.sqlite import SQLiteDatabase
from persbot.core.file_token_service import FileTokenService
from persbot.core.utils.pip_installer import (
    DependencyConflictError as DependencyConflictError,
)
from persbot.core.utils.pip_installer import (
    PipInstaller,
)
from persbot.core.utils.requirements_utils import (
    RequirementsPrecheckFailed as RequirementsPrecheckFailed,
)
from persbot.core.utils.requirements_utils import (
    find_missing_requirements as find_missing_requirements,
)
from persbot.core.utils.requirements_utils import (
    find_missing_requirements_or_raise as find_missing_requirements_or_raise,
)
from persbot.core.utils.shared_preferences import SharedPreferences
from persbot.core.utils.t2i.renderer import HtmlRenderer

from .log import LogBroker, LogManager  # noqa
from .utils.persbot_path import get_persbot_data_path

# 初始化数据存储文件夹
os.makedirs(get_persbot_data_path(), exist_ok=True)

DEMO_MODE = os.getenv("DEMO_MODE", "False").strip().lower() in ("true", "1", "t")

persbot_config = PersbotConfig()
t2i_base_url = persbot_config.get("t2i_endpoint", "https://t2i.soulter.top/text2img")
html_renderer = HtmlRenderer(t2i_base_url)
logger = LogManager.GetLogger(log_name="persbot")
LogManager.configure_logger(logger, persbot_config)
LogManager.configure_trace_logger(persbot_config)
db_helper = SQLiteDatabase(DB_PATH)
# 简单的偏好设置存储, 这里后续应该存储到数据库中, 一些部分可以存储到配置中
sp = SharedPreferences(db_helper=db_helper)
# 文件令牌服务
file_token_service = FileTokenService()
pip_installer = PipInstaller(
    persbot_config.get("pip_install_arg", ""),
    persbot_config.get("pypi_index_url", None),
)
