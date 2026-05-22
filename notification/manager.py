"""
Production-Ready Notification Module - Multi-Channel Push Notifications
支援 Discord, Telegram, Email 等多渠道推送
Author: Market Structure Platform Team
"""

import logging
import os
import requests
import json
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class NotificationBase(ABC):
    """通知基類"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Notification.{name}")
        self.enabled = False
        self.retry_count = 3
        self.timeout = 10
    
    @abstractmethod
    def send(self, message: str, title: Optional[str] = None, **kwargs) -> bool:
        """
        發送通知
        
        Args:
            message: 通知內容
            title: 標題（可選）
            **kwargs: 其他參數
        
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """驗證配置"""
        pass


class DiscordNotification(NotificationBase):
    """
    Discord 通知 - 使用 Webhook 發送消息
    適合實時報警與定期報告推送
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        super().__init__("Discord")
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        self.enabled = self.validate_config()
    
    def validate_config(self) -> bool:
        """驗證 Discord 配置"""
        if not self.webhook_url:
            self.logger.warning("Discord webhook URL not configured")
            return False
        
        if not self.webhook_url.startswith("https://discord.com/api/webhooks/"):
            self.logger.warning("Invalid Discord webhook URL format")
            return False
        
        return True
    
    def send(
        self,
        message: str,
        title: Optional[str] = None,
        color: str = "0x3498db",
        **kwargs
    ) -> bool:
        """
        發送 Discord 消息
        
        Args:
            message: 消息內容
            title: 標題
            color: 嵌入顏色 (十六進制)
            **kwargs: 其他參數
        
        Returns:
            bool: 是否成功
        """
        if not self.enabled:
            return False
        
        try:
            # 構建 Discord Embed 消息
            embed = {
                "title": title or "Market Structure Platform Alert",
                "description": message,
                "color": int(color.replace("0x", ""), 16),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "footer": {
                    "text": "Market Structure Platform"
                }
            }
            
            payload = {
                "embeds": [embed],
                "username": "Market Structure Bot"
            }
            
            # 發送請求
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 204:
                self.logger.info(f"Discord message sent successfully")
                return True
            else:
                self.logger.error(f"Discord API error: {response.status_code}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error sending Discord message: {e}")
            return False


class TelegramNotification(NotificationBase):
    """
    Telegram 通知 - 使用 Bot API 發送消息
    適合及時通知與市場警報
    """
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        super().__init__("Telegram")
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = self.validate_config()
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""
    
    def validate_config(self) -> bool:
        """驗證 Telegram 配置"""
        if not self.bot_token or not self.chat_id:
            self.logger.warning("Telegram bot token or chat ID not configured")
            return False
        
        return True
    
    def send(
        self,
        message: str,
        title: Optional[str] = None,
        parse_mode: str = "HTML",
        **kwargs
    ) -> bool:
        """
        發送 Telegram 消息
        
        Args:
            message: 消息內容
            title: 標題
            parse_mode: 解析模式 (HTML, Markdown, MarkdownV2)
            **kwargs: 其他參數
        
        Returns:
            bool: 是否成功
        """
        if not self.enabled:
            return False
        
        try:
            # 構建消息
            if title:
                full_message = f"<b>{title}</b>\n\n{message}"
            else:
                full_message = message
            
            payload = {
                "chat_id": self.chat_id,
                "text": full_message,
                "parse_mode": parse_mode
            }
            
            # 發送請求
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.logger.info("Telegram message sent successfully")
                return True
            else:
                self.logger.error(f"Telegram API error: {response.status_code}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {e}")
            return False


class EmailNotification(NotificationBase):
    """
    Email 通知 - 發送結構化電郵報告
    適合詳細的每日或每週報告
    """
    
    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: int = 587,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None,
        recipient_email: Optional[str] = None
    ):
        super().__init__("Email")
        self.smtp_server = smtp_server or os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = smtp_port
        self.sender_email = sender_email or os.getenv("EMAIL_SENDER")
        self.sender_password = sender_password or os.getenv("EMAIL_PASSWORD")
        self.recipient_email = recipient_email or os.getenv("EMAIL_RECIPIENT")
        self.enabled = self.validate_config()
    
    def validate_config(self) -> bool:
        """驗證 Email 配置"""
        if not all([self.sender_email, self.sender_password, self.recipient_email]):
            self.logger.warning("Email configuration incomplete")
            return False
        
        return True
    
    def send(
        self,
        message: str,
        title: Optional[str] = None,
        is_html: bool = True,
        **kwargs
    ) -> bool:
        """
        發送 Email
        
        Args:
            message: 消息內容
            title: 主題
            is_html: 是否 HTML 格式
            **kwargs: 其他參數
        
        Returns:
            bool: 是否成功
        """
        if not self.enabled:
            return False
        
        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import smtplib
            
            # 構建郵件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = title or "Market Structure Platform Report"
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            
            # 添加正文
            if is_html:
                part = MIMEText(message, 'html')
            else:
                part = MIMEText(message, 'plain')
            msg.attach(part)
            
            # 發送
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            self.logger.info(f"Email sent successfully to {self.recipient_email}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False


class NotificationManager:
    """
    統一通知管理器
    支持多渠道同時推送，自動失敗重試，異步發送
    """
    
    def __init__(self):
        self.channels: Dict[str, NotificationBase] = {}
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.logger = logging.getLogger("NotificationManager")
        
        # 初始化各通知渠道
        self._init_channels()
    
    def _init_channels(self):
        """初始化通知渠道"""
        # Discord
        discord = DiscordNotification()
        if discord.enabled:
            self.channels['discord'] = discord
            self.logger.info("Discord channel initialized")
        
        # Telegram
        telegram = TelegramNotification()
        if telegram.enabled:
            self.channels['telegram'] = telegram
            self.logger.info("Telegram channel initialized")
        
        # Email
        email = EmailNotification()
        if email.enabled:
            self.channels['email'] = email
            self.logger.info("Email channel initialized")
    
    def send(
        self,
        message: str,
        title: Optional[str] = None,
        channels: Optional[List[str]] = None,
        async_mode: bool = False,
        **kwargs
    ) -> Dict[str, bool]:
        """
        發送通知到指定渠道
        
        Args:
            message: 消息內容
            title: 標題
            channels: 指定渠道列表 (None = 全部)
            async_mode: 是否異步發送
            **kwargs: 其他參數
        
        Returns:
            Dict: {channel: success}
        """
        if channels is None:
            channels = list(self.channels.keys())
        
        results = {}
        
        for channel_name in channels:
            if channel_name not in self.channels:
                self.logger.warning(f"Channel '{channel_name}' not available")
                results[channel_name] = False
                continue
            
            channel = self.channels[channel_name]
            
            if async_mode:
                self.executor.submit(
                    self._send_with_retry,
                    channel,
                    message,
                    title,
                    channel_name,
                    results
                )
            else:
                results[channel_name] = self._send_with_retry(
                    channel,
                    message,
                    title,
                    channel_name
                )
        
        return results
    
    def _send_with_retry(
        self,
        channel: NotificationBase,
        message: str,
        title: Optional[str],
        channel_name: str,
        results: Optional[Dict] = None
    ) -> bool:
        """
        帶重試的發送
        
        Args:
            channel: 通知渠道
            message: 消息
            title: 標題
            channel_name: 渠道名稱
            results: 結果字典 (異步模式)
        
        Returns:
            bool: 是否成功
        """
        for attempt in range(channel.retry_count):
            try:
                success = channel.send(message, title)
                if success:
                    self.logger.info(f"✓ {channel_name} notification sent")
                    if results is not None:
                        results[channel_name] = True
                    return True
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {channel_name}: {e}")
        
        self.logger.error(f"✗ Failed to send {channel_name} notification after {channel.retry_count} attempts")
        if results is not None:
            results[channel_name] = False
        return False
    
    def send_market_report(
        self,
        regime: str,
        alpha_scores: pd.DataFrame,
        smart_money_signals: pd.DataFrame,
        bubble_alerts: pd.DataFrame,
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        發送市場分析報告
        
        Args:
            regime: 市場狀態
            alpha_scores: Alpha 評分
            smart_money_signals: 機構吸籌信號
            bubble_alerts: 泡沫警報
            channels: 指定渠道
        
        Returns:
            Dict: 發送結果
        """
        import pandas as pd
        
        # 構建報告內容
        report = f"""
<b>📊 Market Structure Analysis Report</b>
<i>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</i>

<b>Market Regime:</b> {regime}

<b>🎯 Top Alpha Picks (Top 5):</b>
"""
        
        if not alpha_scores.empty:
            for idx, row in alpha_scores.head(5).iterrows():
                report += f"\n  • {row['Ticker']}: {row['Alpha_Score']:.1f}"
        
        report += f"""

<b>💰 Smart Money Signals Detected:</b>
{smart_money_signals[smart_money_signals['SmartMoney']].shape[0]} stocks
"""
        
        if not bubble_alerts.empty:
            report += f"""

<b>🚨 Bubble Alerts (High Risk):</b>
"""
            for idx, row in bubble_alerts[bubble_alerts['IsBubble']].head(5).iterrows():
                report += f"\n  ⚠️  {row['Ticker']}: {row['BubbleScore']:.1f}"
        
        return self.send(
            report,
            title="Market Analysis Report",
            channels=channels,
            async_mode=True
        )
    
    def send_alert(
        self,
        alert_type: str,
        ticker: str,
        details: str,
        severity: str = "INFO",
        channels: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        發送交易警報
        
        Args:
            alert_type: 警報類型 (SMART_MONEY, BUBBLE, etc.)
            ticker: 股票代碼
            details: 詳細信息
            severity: 嚴重級別 (INFO, WARNING, CRITICAL)
            channels: 指定渠道
        
        Returns:
            Dict: 發送結果
        """
        severity_emoji = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'CRITICAL': '🔴'
        }
        
        emoji = severity_emoji.get(severity, 'ℹ️')
        
        message = f"""
{emoji} <b>{severity} - {alert_type}</b>

<b>Ticker:</b> {ticker}
<b>Details:</b> {details}
<b>Time:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        return self.send(
            message,
            title=f"{alert_type} Alert: {ticker}",
            channels=channels,
            async_mode=True
        )


if __name__ == "__main__":
    import pandas as pd
    
    logging.basicConfig(level=logging.INFO)
    
    # 初始化管理器
    manager = NotificationManager()
    
    # 測試簡單消息
    result = manager.send(
        "This is a test message from Market Structure Platform",
        title="Test Notification",
        channels=['discord', 'telegram']
    )
    
    print(f"Send result: {result}")
    
    # 測試警報
    alert_result = manager.send_alert(
        alert_type="SMART_MONEY",
        ticker="AAPL",
        details="Strong volume expansion detected with price consolidation",
        severity="WARNING"
    )
    
    print(f"Alert result: {alert_result}")
    
    def __init__(self):
        super().__init__("Discord")
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.enabled = bool(self.webhook_url)
    
    def validate_config(self) -> bool:
        """驗證 Discord 配置"""
        return bool(self.webhook_url)
    
    def send(self, message: str, title: Optional[str] = None, **kwargs) -> bool:
        """發送 Discord 消息"""
        try:
            import requests
            
            # 構造嵌入消息
            embed = {
                "title": title or "市場分析通知",
                "description": message,
                "color": kwargs.get("color", 0x3498db),  # 藍色
                "timestamp": datetime.now().isoformat(),
                "footer": {
                    "text": "Market Structure Platform"
                }
            }
            
            payload = {
                "embeds": [embed],
                "username": "Market Analyzer"
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                self.logger.info("✓ Discord notification sent")
                return True
            else:
                self.logger.error(f"✗ Discord API error: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"✗ Failed to send Discord notification: {e}")
            return False


class TelegramNotification(NotificationBase):
    """Telegram 通知"""
    
    def __init__(self):
        super().__init__("Telegram")
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self.chat_id)
    
    def validate_config(self) -> bool:
        """驗證 Telegram 配置"""
        return bool(self.bot_token and self.chat_id)
    
    def send(self, message: str, title: Optional[str] = None, **kwargs) -> bool:
        """發送 Telegram 消息"""
        try:
            import requests
            
            # 構造消息
            full_message = f"*{title}*\n\n{message}" if title else message
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": full_message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.logger.info("✓ Telegram notification sent")
                return True
            else:
                self.logger.error(f"✗ Telegram API error: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"✗ Failed to send Telegram notification: {e}")
            return False


class EmailNotification(NotificationBase):
    """郵件通知"""
    
    def __init__(self):
        super().__init__("Email")
        self.sender_email = os.getenv("EMAIL_SENDER")
        self.sender_password = os.getenv("EMAIL_PASSWORD")
        self.receiver_email = os.getenv("EMAIL_RECEIVER", self.sender_email)
        self.smtp_server = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self.enabled = bool(self.sender_email and self.sender_password)
    
    def validate_config(self) -> bool:
        """驗證郵件配置"""
        return bool(self.sender_email and self.sender_password and self.receiver_email)
    
    def send(self, message: str, title: Optional[str] = None, **kwargs) -> bool:
        """發送郵件"""
        try:
            # 構造郵件
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = self.receiver_email
            msg["Subject"] = title or "市場分析通知"
            
            # HTML 內容
            html_content = f"""
            <html>
                <body>
                    <h2>{title or "市場分析通知"}</h2>
                    <p>{message}</p>
                    <hr>
                    <p style="color: gray; font-size: 12px;">
                        生成時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    </p>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, "html"))
            
            # 發送郵件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            self.logger.info("✓ Email notification sent")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Failed to send email: {e}")
            return False


class WeChatNotification(NotificationBase):
    """企業微信通知"""
    
    def __init__(self):
        super().__init__("WeChat")
        self.webhook_url = os.getenv("WECHAT_WEBHOOK_URL")
        self.enabled = bool(self.webhook_url)
    
    def validate_config(self) -> bool:
        """驗證企業微信配置"""
        return bool(self.webhook_url)
    
    def send(self, message: str, title: Optional[str] = None, **kwargs) -> bool:
        """發送企業微信消息"""
        try:
            import requests
            
            # 構造 Markdown 消息
            markdown_content = f"# {title}\n\n{message}" if title else message
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": markdown_content
                }
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    self.logger.info("✓ WeChat notification sent")
                    return True
            
            self.logger.error(f"✗ WeChat API error: {response.text}")
            return False
            
        except Exception as e:
            self.logger.error(f"✗ Failed to send WeChat notification: {e}")
            return False


class FeishuNotification(NotificationBase):
    """飛書通知"""
    
    def __init__(self):
        super().__init__("Feishu")
        self.webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
        self.enabled = bool(self.webhook_url)
    
    def validate_config(self) -> bool:
        """驗證飛書配置"""
        return bool(self.webhook_url)
    
    def send(self, message: str, title: Optional[str] = None, **kwargs) -> bool:
        """發送飛書消息"""
        try:
            import requests
            
            # 構造飛書卡片消息
            card = {
                "config": {
                    "wide_screen_mode": True
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": f"**{title}**\n\n{message}" if title else message
                    }
                ],
                "header": {
                    "template": "blue",
                    "title": {
                        "content": title or "市場分析通知",
                        "tag": "plain_text"
                    }
                }
            }
            
            payload = {
                "msg_type": "interactive",
                "card": card
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    self.logger.info("✓ Feishu notification sent")
                    return True
            
            self.logger.error(f"✗ Feishu API error: {response.text}")
            return False
            
        except Exception as e:
            self.logger.error(f"✗ Failed to send Feishu notification: {e}")
            return False


class SlackNotification(NotificationBase):
    """Slack 通知"""
    
    def __init__(self):
        super().__init__("Slack")
        self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.channel_id = os.getenv("SLACK_CHANNEL_ID")
        self.enabled = bool(self.bot_token and self.channel_id)
    
    def validate_config(self) -> bool:
        """驗證 Slack 配置"""
        return bool(self.bot_token and self.channel_id)
    
    def send(self, message: str, title: Optional[str] = None, **kwargs) -> bool:
        """發送 Slack 消息"""
        try:
            import requests
            
            payload = {
                "channel": self.channel_id,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": title or "Market Analysis"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message
                        }
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {self.bot_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                "https://slack.com/api/chat.postMessage",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    self.logger.info("✓ Slack notification sent")
                    return True
            
            self.logger.error(f"✗ Slack API error: {response.text}")
            return False
            
        except Exception as e:
            self.logger.error(f"✗ Failed to send Slack notification: {e}")
            return False


class NotificationManager:
    """
    通知管理器
    管理多渠道通知，支持批量發送
    """
    
    def __init__(self):
        self.notifiers: Dict[str, NotificationBase] = {}
        self.logger = logging.getLogger("NotificationManager")
        self._initialize_notifiers()
    
    def _initialize_notifiers(self):
        """初始化所有通知渠道"""
        notifiers_config = [
            ("discord", DiscordNotification),
            ("telegram", TelegramNotification),
            ("email", EmailNotification),
            ("wechat", WeChatNotification),
            ("feishu", FeishuNotification),
            ("slack", SlackNotification),
        ]
        
        for name, notifier_class in notifiers_config:
            try:
                notifier = notifier_class()
                if notifier.enabled and notifier.validate_config():
                    self.notifiers[name] = notifier
                    self.logger.info(f"✓ {name} notifier enabled")
                else:
                    self.logger.debug(f"⊘ {name} notifier not configured")
            except Exception as e:
                self.logger.debug(f"⊘ {name} notifier initialization failed: {e}")
    
    def send(
        self,
        message: str,
        title: Optional[str] = None,
        channels: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, bool]:
        """
        發送通知到多個渠道
        
        Args:
            message: 通知內容
            title: 標題
            channels: 指定渠道列表 (None = 所有可用)
            **kwargs: 其他參數
        
        Returns:
            Dict[str, bool]: 各渠道發送結果
        """
        
        if not self.notifiers:
            self.logger.warning("⚠ No notification channels configured")
            return {}
        
        # 決定發送渠道
        target_channels = channels or list(self.notifiers.keys())
        results = {}
        
        for channel in target_channels:
            if channel not in self.notifiers:
                self.logger.warning(f"⚠ Channel '{channel}' not available")
                results[channel] = False
                continue
            
            try:
                notifier = self.notifiers[channel]
                success = notifier.send(message, title, **kwargs)
                results[channel] = success
            except Exception as e:
                self.logger.error(f"✗ Error sending via {channel}: {e}")
                results[channel] = False
        
        # 統計結果
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        self.logger.info(f"Notification sent: {success_count}/{total_count} channels")
        
        return results
    
    def broadcast(
        self,
        message: str,
        title: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        廣播到所有可用渠道
        
        Returns:
            bool: 至少有一個渠道成功
        """
        
        results = self.send(message, title, **kwargs)
        return any(results.values()) if results else False
    
    def get_available_channels(self) -> List[str]:
        """獲取所有可用渠道"""
        return list(self.notifiers.keys())
    
    def get_status(self) -> Dict[str, bool]:
        """獲取所有渠道狀態"""
        return {
            name: notifier.validate_config()
            for name, notifier in self.notifiers.items()
        }
