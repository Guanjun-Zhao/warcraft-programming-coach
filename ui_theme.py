"""
UI theme tokens and shared QSS builders.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox, QWidget

COLORS = {
    "bg_page": "#0d1117",
    "text_main": "#e6edf3",
    "text_light": "#ecf3fb",
    "text_secondary": "#c3d4e7",
    "text_muted": "#9bb0c7",
    "accent_gold": "#f4c96b",
    "accent_gold_strong": "#f6c453",
    "accent_blue": "#8ec9ff",
    "primary_btn_bg": "#8a5d1f",
    "primary_btn_text": "#fff7e8",
    "btn_bg": "#1f2c3f",
    "btn_bg_secondary": "#1a2433",
    "btn_border": "#334862",
    "tool_bg": "#1d293a",
    "tool_border": "#3a516d",
    "input_bg": "#0f1620",
    "input_border": "#34485f",
    "panel_bg": "#121a26",
    "panel_border": "#243246",
    "hero_bg": "#111827",
    "hero_border": "#233347",
    "info_bg": "#151f2e",
    "info_border": "#2a3d56",
    "campaign_bg": "#101722",
    "campaign_border": "#2b3950",
    "tree_selected_bg": "#1f3552",
    "tree_selected_border": "#4f6b8b",
    "danger_bg": "#2c1f28",
    "danger_border": "#6d3f57",
    "danger_text": "#e9c7d8",
    "bubble_user_bg": "#1e4d6e",
    "bubble_assistant_bg": "#3d4450",
    "bubble_text": "#ececec",
    "bubble_user_caption": "#8ecae6",
    "bubble_assistant_caption": "#c5cdd8",
    "chat_history_bg": "#0f1620",
    "chat_history_border": "#2b3950",
    "bubble_user_border": "#4d7ea3",
    "bubble_assistant_border": "#596271",
    "avatar_user_bg": "#17384f",
    "avatar_assistant_bg": "#2a3140",
}

API_STATUS_STYLE_MAP: dict[str, tuple[str, str]] = {
    "no_key": (
        "\u672a\u914d\u7f6e",
        "background: #3a2b2b; color: #ffd4d4; border: 1px solid #9e4f4f;",
    ),
    "pending": (
        "\u5f85\u9a8c\u8bc1",
        "background: #2e3240; color: #d6ddff; border: 1px solid #6472a6;",
    ),
    "checking": (
        "\u9a8c\u8bc1\u4e2d",
        "background: #2d3a48; color: #c6e9ff; border: 1px solid #5e8cb3;",
    ),
    "success": (
        "\u9a8c\u8bc1\u6210\u529f",
        "background: #213c2a; color: #cbf9d5; border: 1px solid #4ca06b;",
    ),
    "failed": (
        "\u9a8c\u8bc1\u5931\u8d25",
        "background: #42262a; color: #ffd5d9; border: 1px solid #aa5a64;",
    ),
}


def home_stylesheet() -> str:
    c = COLORS
    return f"""
            QWidget#HomePage {{
                background-color: {c["bg_page"]};
                color: {c["text_main"]};
            }}
            QWidget#HomeContent {{
                background-color: {c["bg_page"]};
            }}
            QFrame#HeroCard {{
                background-color: {c["hero_bg"]};
                border: 1px solid {c["hero_border"]};
                border-radius: 12px;
            }}
            QFrame#PanelCard {{
                background-color: {c["panel_bg"]};
                border: 1px solid {c["panel_border"]};
                border-radius: 10px;
            }}
            QFrame#InfoCard {{
                background-color: {c["info_bg"]};
                border: 1px solid {c["info_border"]};
                border-radius: 10px;
            }}
            QFrame#CampaignCard {{
                background-color: {c["campaign_bg"]};
                border: 1px solid {c["campaign_border"]};
                border-radius: 10px;
            }}
            QLabel#HeroTitle {{
                font-size: 24px;
                font-weight: 700;
                color: {c["accent_gold_strong"]};
            }}
            QLabel#HeroSubtitle {{
                color: {c["text_secondary"]};
                font-size: 13px;
            }}
            QLabel#SectionTitle {{
                font-size: 16px;
                font-weight: 600;
                color: {c["accent_gold"]};
            }}
            QLabel#CampaignTitle {{
                font-size: 14px;
                font-weight: 600;
            }}
            QLabel#ProgressText {{
                color: {c["accent_blue"]};
                font-weight: 600;
            }}
            QLabel#MutedText {{
                color: {c["text_muted"]};
                font-size: 12px;
            }}
            QLabel#ApiStatusBadge {{
                padding: 3px 10px;
                border-radius: 10px;
                font-weight: 600;
            }}
            QPushButton {{
                background-color: {c["btn_bg"]};
                border: 1px solid {c["btn_border"]};
                border-radius: 8px;
                padding: 6px 12px;
                color: {c["text_main"]};
            }}
            QPushButton:hover {{
                border: 1px solid {c["accent_gold"]};
            }}
            QPushButton#PrimaryButton {{
                background-color: {c["primary_btn_bg"]};
                border: 1px solid {c["accent_gold"]};
                color: {c["primary_btn_text"]};
                font-weight: 600;
            }}
            QLineEdit, QComboBox {{
                background-color: {c["input_bg"]};
                border: 1px solid {c["input_border"]};
                border-radius: 6px;
                padding: 5px;
                color: {c["text_light"]};
            }}
            QToolButton {{
                background-color: {c["tool_bg"]};
                border: 1px solid {c["tool_border"]};
                border-radius: 6px;
                padding: 5px 8px;
                color: #dce8f6;
            }}
    """


def api_ping_dialog_stylesheet() -> str:
    c = COLORS
    return f"""
            QDialog#ApiPingDialog {{
                background-color: {c["panel_bg"]};
                border: 1px solid {c["panel_border"]};
                border-radius: 10px;
                color: {c["text_main"]};
            }}
            QDialog#ApiPingDialog QLabel#ApiPingTitle {{
                color: {c["accent_gold"]};
                font-size: 16px;
                font-weight: 600;
            }}
            QDialog#ApiPingDialog QLabel#ApiPingBody {{
                color: {c["text_secondary"]};
                font-size: 13px;
            }}
            QDialog#ApiPingDialog QLabel#ApiPingHint {{
                color: {c["text_muted"]};
                font-size: 12px;
            }}
            QDialog#ApiPingDialog QProgressBar {{
                background-color: {c["input_bg"]};
                border: 1px solid {c["input_border"]};
                border-radius: 5px;
            }}
            QDialog#ApiPingDialog QProgressBar::chunk {{
                background-color: {c["accent_blue"]};
                border-radius: 5px;
            }}
    """


def version_page_stylesheet() -> str:
    c = COLORS
    return f"""
      QWidget#VersionPage {{
        background-color: {c["bg_page"]};
        color: {c["text_main"]};
      }}
      QFrame#PanelCard {{
        background-color: {c["panel_bg"]};
        border: 1px solid {c["panel_border"]};
        border-radius: 10px;
      }}
      QLabel#VpTitle {{
        color: {c["accent_gold_strong"]};
        font-size: 20px;
        font-weight: 700;
      }}
      QLabel#VpMeta {{
        color: {c["text_secondary"]};
        font-size: 12px;
      }}
      QLabel#VpProgress {{
        color: {c["accent_blue"]};
        font-size: 13px;
        font-weight: 600;
      }}
      QLabel#PanelTitle {{
        color: {c["accent_gold"]};
        font-size: 14px;
        font-weight: 600;
      }}
      QLabel#MutedText {{
        color: {c["text_muted"]};
        font-size: 12px;
      }}
      QPushButton {{
        background-color: {c["btn_bg"]};
        border: 1px solid {c["btn_border"]};
        border-radius: 8px;
        padding: 6px 12px;
        color: {c["text_main"]};
      }}
      QPushButton:hover {{
        border: 1px solid {c["accent_gold"]};
      }}
      QPushButton#SecondaryButton {{
        background-color: {c["btn_bg_secondary"]};
      }}
      QPushButton#DangerGhostButton {{
        background-color: {c["danger_bg"]};
        border: 1px solid {c["danger_border"]};
        color: {c["danger_text"]};
      }}
      QToolButton#LeftPanelToggle {{
        background-color: {c["tool_bg"]};
        border: 1px solid {c["tool_border"]};
        border-radius: 6px;
        padding: 0px;
        color: #dce8f6;
      }}
      QToolButton#LeftPanelToggle:hover {{
        border: 1px solid {c["accent_gold"]};
      }}
      QTreeWidget, QPlainTextEdit {{
        background-color: {c["input_bg"]};
        border: 1px solid {c["input_border"]};
        border-radius: 8px;
        color: {c["text_light"]};
      }}
      QTreeWidget::item {{
        padding: 3px 2px;
      }}
      QTreeWidget::item:selected {{
        background-color: {c["tree_selected_bg"]};
        border: 1px solid {c["tree_selected_border"]};
      }}
    """


def chat_widget_stylesheet() -> str:
    c = COLORS
    return f"""
            QWidget#CoachPanel {{
                background-color: transparent;
                color: {c["text_main"]};
            }}
            QScrollArea#HistoryScroll {{
                background-color: {c["chat_history_bg"]};
                border: 1px solid {c["chat_history_border"]};
                border-radius: 10px;
            }}
            QWidget#HistoryContainer {{
                background-color: {c["chat_history_bg"]};
            }}
            QLabel#MutedText {{
                color: {c["text_muted"]};
                font-size: 12px;
            }}
            QLabel#MsgCaptionUser {{
                color: {c["bubble_user_caption"]};
                font-size: 11px;
            }}
            QLabel#MsgCaptionAssistant {{
                color: {c["bubble_assistant_caption"]};
                font-size: 11px;
            }}
            QLabel#MsgBody {{
                color: {c["bubble_text"]};
                font-size: 12px;
            }}
            QFrame#MsgBubbleUser {{
                background-color: {c["bubble_user_bg"]};
                border: 1px solid {c["bubble_user_border"]};
                border-radius: 14px;
            }}
            QFrame#MsgBubbleAssistant {{
                background-color: {c["bubble_assistant_bg"]};
                border: 1px solid {c["bubble_assistant_border"]};
                border-radius: 14px;
            }}
            QLabel#MsgAvatarUser {{
                background-color: {c["avatar_user_bg"]};
                border: 1px solid {c["bubble_user_border"]};
                border-radius: 10px;
                color: {c["text_main"]};
                font-size: 16px;
                padding: 0px;
            }}
            QLabel#MsgAvatarAssistant {{
                background-color: {c["avatar_assistant_bg"]};
                border: 1px solid {c["bubble_assistant_border"]};
                border-radius: 10px;
                color: {c["text_main"]};
                font-size: 18px;
                padding: 0px;
            }}
            QLabel#SendStateReady {{
                color: {c["text_muted"]};
                font-size: 12px;
            }}
            QLabel#SendStateBusy {{
                color: {c["accent_blue"]};
                font-size: 12px;
                font-weight: 600;
            }}
            QToolButton {{
                background-color: {c["tool_bg"]};
                border: 1px solid {c["tool_border"]};
                border-radius: 6px;
                padding: 3px 8px;
                color: #dce8f6;
            }}
            QPushButton {{
                background-color: {c["btn_bg"]};
                border: 1px solid {c["btn_border"]};
                border-radius: 8px;
                padding: 6px 12px;
                color: {c["text_main"]};
            }}
            QPushButton:hover {{
                border: 1px solid {c["accent_gold"]};
            }}
            QPushButton#PrimaryButton {{
                background-color: {c["primary_btn_bg"]};
                border: 1px solid {c["accent_gold"]};
                color: {c["primary_btn_text"]};
                font-weight: 600;
            }}
            QPushButton#DangerGhostButton {{
                background-color: {c["danger_bg"]};
                border: 1px solid {c["danger_border"]};
                color: {c["danger_text"]};
            }}
            QTextEdit {{
                background-color: {c["input_bg"]};
                border: 1px solid {c["input_border"]};
                border-radius: 8px;
                color: {c["text_light"]};
                padding: 6px;
            }}
    """


def message_box_stylesheet() -> str:
    c = COLORS
    return f"""
            QMessageBox {{
                background-color: {c["panel_bg"]};
                color: {c["text_main"]};
            }}
            QMessageBox QLabel {{
                color: {c["text_secondary"]};
                font-size: 12px;
            }}
            QMessageBox QPushButton {{
                min-width: 74px;
                background-color: {c["btn_bg"]};
                border: 1px solid {c["btn_border"]};
                border-radius: 8px;
                padding: 6px 12px;
                color: {c["text_main"]};
            }}
            QMessageBox QPushButton:hover {{
                border: 1px solid {c["accent_gold"]};
            }}
    """


def _show_message_box(
    parent: QWidget | None,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
) -> QMessageBox.StandardButton:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(icon)
    box.setStandardButtons(buttons)
    if default_button != QMessageBox.StandardButton.NoButton:
        box.setDefaultButton(default_button)
    box.setStyleSheet(message_box_stylesheet())
    return QMessageBox.StandardButton(box.exec())


def msg_info(parent: QWidget | None, title: str, text: str) -> QMessageBox.StandardButton:
    return _show_message_box(parent, QMessageBox.Icon.Information, title, text)


def msg_warn(parent: QWidget | None, title: str, text: str) -> QMessageBox.StandardButton:
    return _show_message_box(parent, QMessageBox.Icon.Warning, title, text)


def msg_question(
    parent: QWidget | None,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes
    | QMessageBox.StandardButton.No,
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.No,
) -> QMessageBox.StandardButton:
    return _show_message_box(
        parent,
        QMessageBox.Icon.Question,
        title,
        text,
        buttons,
        default_button,
    )
