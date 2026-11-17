import unittest
from unittest.mock import Mock, patch

from trendradar.core.loader import _load_webhook_config
from trendradar.notification.dispatcher import NotificationDispatcher
from trendradar.notification.senders import send_to_pushplus
from trendradar.report.formatter import format_title_for_platform


class PushPlusTests(unittest.TestCase):
    def test_title_format_uses_markdown_links_and_ranks(self):
        title_data = {
            "title": "Headline",
            "source_name": "News",
            "time_display": "10:00",
            "count": 1,
            "ranks": [1],
            "rank_threshold": 5,
            "rank_timeline": None,
            "url": "https://example.com/news",
            "mobile_url": "",
        }

        formatted = format_title_for_platform("pushplus", title_data)

        self.assertIn("[Headline](https://example.com/news)", formatted)
        self.assertIn("[News]", formatted)
        self.assertIn("**[1]**", formatted)

    def test_sender_posts_markdown_payload_with_optional_topic(self):
        response = Mock(status_code=200)
        response.json.return_value = {"code": 200, "msg": "success"}
        split_content = Mock(return_value=["news"])

        with patch(
            "trendradar.notification.senders.requests.post", return_value=response
        ) as post:
            result = send_to_pushplus(
                token="token",
                topic="group",
                report_data={},
                report_type="current",
                split_content_func=split_content,
            )

        self.assertTrue(result)
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://www.pushplus.plus/send")
        self.assertEqual(kwargs["json"]["token"], "token")
        self.assertEqual(kwargs["json"]["topic"], "group")
        self.assertEqual(kwargs["json"]["template"], "markdown")

    def test_sender_returns_false_when_pushplus_rejects_message(self):
        response = Mock(status_code=200)
        response.json.return_value = {"code": 500, "msg": "invalid token"}

        with patch("trendradar.notification.senders.requests.post", return_value=response):
            result = send_to_pushplus(
                token="token",
                topic="",
                report_data={},
                report_type="current",
                split_content_func=Mock(return_value=["news"]),
            )

        self.assertFalse(result)

    def test_webhook_config_prefers_environment_values(self):
        config_data = {
            "notification": {
                "channels": {
                    "pushplus": {"token": "config-token", "topic": "config-group"}
                }
            }
        }
        with patch.dict(
            "os.environ",
            {"PUSHPLUS_TOKEN": "env-token", "PUSHPLUS_TOPIC": "env-group"},
            clear=True,
        ):
            config = _load_webhook_config(config_data)

        self.assertEqual(config["PUSHPLUS_TOKEN"], "env-token")
        self.assertEqual(config["PUSHPLUS_TOPIC"], "env-group")

    def test_dispatcher_sends_when_pushplus_token_is_configured(self):
        dispatcher = NotificationDispatcher(
            config={"PUSHPLUS_TOKEN": "token", "PUSHPLUS_TOPIC": "group"},
            get_time_func=Mock(),
            split_content_func=Mock(),
        )
        report_data = {"stats": [], "new_titles": [], "failed_ids": [], "id_to_name": {}}

        with patch(
            "trendradar.notification.dispatcher.send_to_pushplus", return_value=True
        ) as send:
            results = dispatcher.dispatch_all(report_data, "current")

        self.assertTrue(results["pushplus"])
        self.assertEqual(send.call_args.kwargs["token"], "token")
        self.assertEqual(send.call_args.kwargs["topic"], "group")


if __name__ == "__main__":
    unittest.main()
