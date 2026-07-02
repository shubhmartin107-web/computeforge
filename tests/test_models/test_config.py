from computeforge.models.config import BrowserConfig, EngineConfig, SafetyConfig, StorageConfig


def test_browser_config_defaults():
    config = BrowserConfig()
    assert config.headless is True
    assert config.viewport_width == 1280
    assert config.viewport_height == 720
    assert config.locale == "en-US"
    assert config.user_agent is None
    assert config.slow_mo == 0
    assert config.timeout_ms == 30000


def test_safety_config_defaults():
    config = SafetyConfig()
    assert config.enabled is True
    assert config.policy_file is None
    assert config.risk_threshold == "high"
    assert "navigate" in config.require_confirmation_for
    assert config.blocklist_domains == []
    assert config.max_actions_per_session == 200
    assert config.allow_dangerous_js is False


def test_storage_config_defaults():
    config = StorageConfig()
    assert "sessions.db" in config.database_url
    assert "screenshots" in config.screenshot_dir
    assert "sessions" in config.session_dir
    assert config.max_screenshots_per_session == 500
    assert config.auto_cleanup_days == 30


def test_engine_config_defaults():
    config = EngineConfig()
    assert config.default_provider == "deepseek"
    assert config.max_concurrent_actions == 1
    assert config.log_level == "INFO"
    assert "computeforge" in config.workspace_dir
    assert isinstance(config.browser, BrowserConfig)
    assert isinstance(config.safety, SafetyConfig)
    assert isinstance(config.storage, StorageConfig)


def test_engine_config_env_prefix():
    assert EngineConfig.model_config["env_prefix"] == "COMPUTEFORGE_"


def test_nested_config_access():
    config = EngineConfig()
    config.browser.headless = False
    config.browser.viewport_width = 1920
    config.safety.enabled = False
    config.storage.max_screenshots_per_session = 100

    assert config.browser.headless is False
    assert config.browser.viewport_width == 1920
    assert config.safety.enabled is False
    assert config.storage.max_screenshots_per_session == 100


def test_engine_config_override():
    config = EngineConfig(
        default_provider="openai",
        max_concurrent_actions=3,
        log_level="DEBUG",
    )
    assert config.default_provider == "openai"
    assert config.max_concurrent_actions == 3
    assert config.log_level == "DEBUG"
