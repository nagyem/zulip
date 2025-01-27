from zerver.lib.integrations import (
    DOC_SCREENSHOT_CONFIG,
    INTEGRATIONS,
    NO_SCREENSHOT_WEBHOOKS,
    WEBHOOK_INTEGRATIONS,
    BaseScreenshotConfig,
    EmbeddedBotIntegration,
    Integration,
    ScreenshotConfig,
    WebhookIntegration,
    get_fixture_and_image_paths,
    split_fixture_path,
)
from zerver.lib.test_classes import ZulipTestCase


class IntegrationsTestCase(ZulipTestCase):
    def test_split_fixture_path(self) -> None:
        path = "zerver/webhooks/semaphore/fixtures/push.json"
        integration_name, fixture_name = split_fixture_path(path)
        self.assertEqual(integration_name, "semaphore")
        self.assertEqual(fixture_name, "push")

    def test_get_fixture_and_image_paths(self) -> None:
        integration = INTEGRATIONS["airbrake"]
        assert isinstance(integration, WebhookIntegration)
        screenshot_config = ScreenshotConfig("error_message.json", "002.png", "ci")
        fixture_path, image_path = get_fixture_and_image_paths(integration, screenshot_config)
        self.assertEqual(fixture_path, "zerver/webhooks/airbrake/fixtures/error_message.json")
        self.assertEqual(image_path, "static/images/integrations/ci/002.png")

    def test_get_fixture_and_image_paths_non_webhook(self) -> None:
        integration = INTEGRATIONS["nagios"]
        assert isinstance(integration, Integration)
        screenshot_config = BaseScreenshotConfig("service_notify.json", "001.png")
        fixture_path, image_path = get_fixture_and_image_paths(integration, screenshot_config)
        self.assertEqual(fixture_path, "zerver/integration_fixtures/nagios/service_notify.json")
        self.assertEqual(image_path, "static/images/integrations/nagios/001.png")

    def test_get_bot_avatar_path_generic_bot(self) -> None:
        integration = INTEGRATIONS["alertmanager"]
        self.assertEqual(
            integration.get_bot_avatar_path(), "images/integrations/bot_avatars/prometheus.png"
        )

        # New instance with logo parameter not set
        integration = WebhookIntegration("alertmanager", ["misc"])
        self.assertIsNotNone(integration.get_bot_avatar_path())
        self.assertEqual(
            integration.get_bot_avatar_path(), "images/integrations/bot_avatars/generic.png"
        )

    def test_no_missing_doc_screenshot_config(self) -> None:
        webhook_names = {webhook.name for webhook in WEBHOOK_INTEGRATIONS}
        webhooks_with_screenshot_config = set(DOC_SCREENSHOT_CONFIG.keys())
        missing_webhooks = webhook_names - webhooks_with_screenshot_config - NO_SCREENSHOT_WEBHOOKS
        message = (
            f"These webhooks are missing screenshot config: {missing_webhooks}.\n"
            "Add them to zerver.lib.integrations.DOC_SCREENSHOT_CONFIG"
        )
        self.assertFalse(missing_webhooks, message)

    def test_get_logo_url_generic_bot(self) -> None:
        embedded_bot = EmbeddedBotIntegration("test_bot", [])
        default_logo_path = embedded_bot.get_logo_path()
        self.assertEqual(default_logo_path, "images/integrations/logos/generic.png")
