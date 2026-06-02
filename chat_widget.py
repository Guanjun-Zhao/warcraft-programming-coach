"""
AI 教练 Tab：滚动对话区（每条消息为独立气泡控件）+ 多行输入框 + 发送；读写 data/versionN/history/*.json。
"""

# 推迟解析类型注解，便于在类型里引用尚未定义的类名（与本项目其它文件一致）
from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QKeyEvent, QPalette
from PyQt6.QtWidgets import (  # 本文件用到的界面类
    QFrame,
    QHBoxLayout,  # 水平布局
    QLabel,  # 静态文字
    QMessageBox,  # 模态消息框
    QPushButton,  # 可点击按钮
    QScrollArea,
    QSizePolicy,
    QTextEdit,  # 多行富文本编辑/只读（仅输入框）
    QVBoxLayout,  # 垂直布局
    QWidget,  # 所有控件的基类
)

import ai_coach  # 调用大模型/占位回复
import data_manager
import sections_loader
import ui_theme

_PLANNING_BOOTSTRAP_TRIGGER = "请开始本节导读讲解。"
_CODING_BOOTSTRAP_TRIGGER = "请开始本节的学习引导讲解。"
_EMPTY_ASSISTANT_FALLBACK = "[模型未返回正文，请重试或更换模型。]"


def _normalize_assistant_reply(text: str) -> str:
    s = (text or "").strip()
    return s if s else _EMPTY_ASSISTANT_FALLBACK


def _is_planning_placeholder_bootstrap(hist: list[dict[str, Any]]) -> bool:
    if len(hist) != 2:
        return False
    u0, a0 = hist[0], hist[1]
    if u0.get("role") != "user" or a0.get("role") != "assistant":
        return False
    if u0.get("content") != _PLANNING_BOOTSTRAP_TRIGGER:
        return False
    return str(a0.get("content", "")).startswith("[占位回复]")


def _is_coding_placeholder_bootstrap(hist: list[dict[str, Any]]) -> bool:
    if len(hist) != 2:
        return False
    u0, a0 = hist[0], hist[1]
    if u0.get("role") != "user" or a0.get("role") != "assistant":
        return False
    if u0.get("content") != _CODING_BOOTSTRAP_TRIGGER:
        return False
    return str(a0.get("content", "")).startswith("[占位回复]")


class IntroBootstrapThread(QThread):
    """空历史自动引导：后台调用 ai_coach.chat，避免阻塞 UI。"""

    finished_ok = pyqtSignal(str, str, str, str)
    finished_err = pyqtSignal(str, str, str, str)

    def __init__(
        self,
        version_id: str,
        task_id: str,
        trigger: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._version_id = version_id
        self._task_id = task_id
        self._trigger = trigger

    @property
    def bootstrap_task_id(self) -> str:
        return self._task_id

    def run(self) -> None:
        try:
            reply = ai_coach.chat(
                self._version_id, self._task_id, [], self._trigger
            )
            self.finished_ok.emit(
                self._version_id, self._task_id, self._trigger, reply
            )
        except Exception as exc:
            self.finished_err.emit(
                self._version_id,
                self._task_id,
                self._trigger,
                f"{type(exc).__name__}: {exc}",
            )


class CoachChatThread(QThread):
    """后台执行 ai_coach.chat（带历史），避免主线程在请求 API 时冻结。"""

    finished_ok = pyqtSignal(str, str, str, str)
    finished_err = pyqtSignal(str, str, str, str)

    def __init__(
        self,
        version_id: str,
        task_id: str,
        messages: list[dict[str, Any]],
        user_message: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._version_id = version_id
        self._task_id = task_id
        self._messages = copy.deepcopy(messages)
        self._user_message = user_message

    @property
    def thread_task_id(self) -> str:
        return self._task_id

    def run(self) -> None:
        try:
            reply = ai_coach.chat(
                self._version_id,
                self._task_id,
                self._messages,
                self._user_message,
            )
            self.finished_ok.emit(
                self._version_id, self._task_id, self._user_message, reply
            )
        except Exception as exc:
            self.finished_err.emit(
                self._version_id,
                self._task_id,
                self._user_message,
                f"{type(exc).__name__}: {exc}",
            )


class DebugAnalyzeThread(QThread):
    """后台执行 ai_coach.analyze_debug_mismatch，避免 Debug 分析阻塞主线程。"""

    finished_ok = pyqtSignal(str, str, str, str)
    finished_err = pyqtSignal(str, str, str, str)

    def __init__(
        self,
        version_id: str,
        task_id: str,
        user_message: str,
        sample: dict[str, Any],
        user_output: str,
        program_source: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._version_id = version_id
        self._task_id = task_id
        self._user_message = user_message
        self._sample = copy.deepcopy(sample)
        self._user_output = user_output
        self._program_source = program_source

    @property
    def thread_task_id(self) -> str:
        return self._task_id

    def run(self) -> None:
        try:
            reply = ai_coach.analyze_debug_mismatch(
                self._version_id,
                self._sample,
                self._user_output,
                self._program_source,
            )
            self.finished_ok.emit(
                self._version_id, self._task_id, self._user_message, reply
            )
        except Exception as exc:
            self.finished_err.emit(
                self._version_id,
                self._task_id,
                self._user_message,
                f"{type(exc).__name__}: {exc}",
            )


class ComposerTextEdit(QTextEdit):
    """多行输入：Enter 发送，Shift+Enter 换行。"""

    send_requested = pyqtSignal()  # 无参信号：用户按 Enter 要求发送

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)  # 构造基类，挂到父控件对象树
        self.setAcceptRichText(False)  # 只收纯文本，避免粘贴进 HTML 隐患
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  # 按控件宽度自动换行
        self.setMinimumHeight(44)  # 输入区最小高度（约原设计一半）
        self.setMaximumHeight(100)  # 输入区最大高度，超出出竖向滚动条
        self.setPlaceholderText("Enter 发送 · Shift+Enter 换行。可粘贴代码片段或描述问题…")  # 空时灰色提示

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):  # 主键盘或数字区回车
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:  # 按住 Shift
                super().keyPressEvent(event)  # 默认行为：插入换行
                return  # 避免落到函数末尾再次 super，导致双换行
            else:  # 未按 Shift 的单独回车
                self.send_requested.emit()  # 通知外层执行发送
                event.accept()  # 事件已处理，不再向下传
                return  # 不调用 super，避免再插入换行
        super().keyPressEvent(event)  # 其它键走默认（字符、退格等）


class ChatWidget(QWidget):
    """
    当前版本（version_id）与任务（task_id）下的教练对话区。

    典型用法（见 VersionPage）：
      - 构造时传入初始 task_id，并 load_history()；
      - 左侧列表切换任务时调用 set_task(new_id)，内部会更新 self._task_id 并重新 load_history。

    线程说明：
      规划/编码小节在空历史时自动引导；普通发送在后台 QThread 中调用网络；无 Key 时占位仍同步。
    """

    def __init__(
        self,
        version_id: str,
        task_id: str,
        program_loader: Callable[[], str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("CoachPanel")
        self._version_id = version_id
        self._task_id = task_id
        self._program_loader = program_loader or (
            lambda: data_manager.load_version_code(version_id)
        )
        self._intro_bootstrap_thread: IntroBootstrapThread | None = None
        self._chat_send_thread: CoachChatThread | None = None
        self._debug_analyze_thread: DebugAnalyzeThread | None = None

        # ---------- 上方：对话记录（每条消息独立控件，避免 QTextEdit.insertHtml 表格与 Markdown 冲突）----------
        self._history_scroll = QScrollArea()
        self._history_scroll.setObjectName("HistoryScroll")
        self._history_scroll.setWidgetResizable(True)
        self._history_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._history_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._history_container = QWidget()
        self._history_container.setObjectName("HistoryContainer")
        self._history_layout = QVBoxLayout(self._history_container)
        self._history_layout.setContentsMargins(4, 4, 4, 8)
        self._history_layout.setSpacing(10)
        self._history_scroll.setWidget(self._history_container)
        _hp2 = self._history_container.palette()
        _hp2.setColor(
            QPalette.ColorRole.Window,
            self.palette().color(QPalette.ColorRole.Window),
        )
        self._history_container.setAutoFillBackground(True)
        self._history_container.setPalette(_hp2)

        # ---------- 下方：输入 + 发送 ----------
        self._input = ComposerTextEdit()  # 多行输入框
        self._input.send_requested.connect(self._on_send)  # Enter 发送与按钮共用槽

        self._clear_btn = QPushButton("清空聊天记录")  # 清当前任务持久化与界面
        self._clear_btn.setObjectName("DangerGhostButton")
        self._clear_btn.clicked.connect(self._on_clear_clicked)  # 先确认再清
        self._send_btn = QPushButton("发送")  # 显式发送
        self._send_btn.setObjectName("PrimaryButton")
        self._send_btn.clicked.connect(self._on_send)  # 与 Enter 行为一致

        actions_col = QWidget()  # 承载右侧竖排按钮的容器
        actions_layout = QVBoxLayout(actions_col)  # 上下叠放清空与发送
        actions_layout.setContentsMargins(0, 0, 0, 0)  # 与输入行贴齐，不额外留边
        actions_layout.setSpacing(6)  # 两钮间距 6 像素
        actions_layout.addWidget(self._clear_btn)  # 上：清空
        actions_layout.addWidget(self._send_btn)  # 下：发送
        actions_layout.addStretch(1)  # 下方弹性空白，两钮顶对齐

        row = QHBoxLayout()  # 底行：输入 + 右侧操作列
        row.addWidget(self._input, stretch=1)  # 输入区占满剩余宽
        row.addWidget(actions_col, stretch=0, alignment=Qt.AlignmentFlag.AlignTop)  # 右侧列不拉伸、顶对齐

        layout = QVBoxLayout(self)  # 本控件根布局
        self._ctx_label = QLabel("")  # 版本 / 任务 / 小节标题
        self._ctx_label.setObjectName("MutedText")
        self._send_state_label = QLabel("就绪：可发送问题或粘贴代码输出。")
        self._send_state_label.setObjectName("SendStateReady")
        self._send_state_label.setWordWrap(True)
        layout.addWidget(self._ctx_label)  # 标题行
        layout.addWidget(self._history_scroll, stretch=1)  # 中间：历史
        layout.addWidget(self._send_state_label)
        layout.addLayout(row)  # 底：输入行

        self.setStyleSheet(ui_theme.chat_widget_stylesheet())

        self._update_ctx_label()
        self.load_history()
        QTimer.singleShot(0, self._bootstrap_if_needed)
        QTimer.singleShot(0, self._refresh_message_bubble_max_widths)

    def _set_send_state(self, text: str, busy: bool) -> None:
        self._send_state_label.setText(text)
        self._send_state_label.setObjectName("SendStateBusy" if busy else "SendStateReady")
        # 重新触发样式应用，确保 objectName 变更生效
        self._send_state_label.style().unpolish(self._send_state_label)
        self._send_state_label.style().polish(self._send_state_label)
        self._send_state_label.update()
        self._send_btn.setEnabled(not busy)

    def _history_is_near_bottom(self, threshold: int = 40) -> bool:
        bar = self._history_scroll.verticalScrollBar()
        return (bar.maximum() - bar.value()) <= threshold

    def _force_history_reflow(self) -> None:
        self._history_container.layout().invalidate()
        self._history_container.adjustSize()
        self._history_container.updateGeometry()

    def refresh_message_layout_after_host_resize(self) -> None:
        keep_bottom = self._history_is_near_bottom()
        self._refresh_message_bubble_max_widths()
        self._force_history_reflow()
        if keep_bottom:
            self._scroll_history_to_bottom()
        QTimer.singleShot(
            0, lambda keep=keep_bottom: self._post_history_refresh(keep)
        )

    def _post_history_refresh(self, keep_bottom: bool) -> None:
        self._refresh_message_bubble_max_widths()
        self._force_history_reflow()
        if keep_bottom:
            self._scroll_history_to_bottom()

    def resizeEvent(self, event) -> None:
        keep_bottom = self._history_is_near_bottom()
        super().resizeEvent(event)
        self._refresh_message_bubble_max_widths()
        self._force_history_reflow()
        if keep_bottom:
            self._scroll_history_to_bottom()
        QTimer.singleShot(
            0, lambda keep=keep_bottom: self._post_history_refresh(keep)
        )

    def _refresh_message_bubble_max_widths(self) -> None:
        vp = max(0, self._history_scroll.viewport().width())
        usable = max(80, vp - 56)
        mx = max(120, int(usable * 0.9))
        # 与 inner 左右 contentsMargins 14+14 一致，供 QLabel 换行高度计算（否则 Markdown 会算出巨大 height）
        inner_text_w = max(50, mx - 28)
        for i in range(self._history_layout.count()):
            it = self._history_layout.itemAt(i)
            if it is None:
                continue
            w = it.widget()
            if w is None:
                continue
            bubble = getattr(w, "_bubble_frame", None)
            if bubble is not None:
                bubble.setMaximumWidth(mx)
                bubble.setMinimumWidth(0)
            body = getattr(w, "_body_label", None)
            if body is not None:
                body.setMaximumWidth(inner_text_w)
                body.setMinimumWidth(0)
                body.adjustSize()
                body.updateGeometry()
            cap = getattr(w, "_cap_label", None)
            if cap is not None:
                cap.setMaximumWidth(inner_text_w)
                cap.setMinimumWidth(0)
                cap.adjustSize()
                cap.updateGeometry()

    def _clear_history_rows(self) -> None:
        while self._history_layout.count():
            item = self._history_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    def _make_message_row_widget(self, role: str, content: str) -> QWidget:
        row = QWidget()
        row.setObjectName("MsgRowUser" if role == "user" else "MsgRowAssistant")
        row.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        outer = QHBoxLayout(row)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        bubble = QFrame()
        bubble.setObjectName("MsgBubbleUser" if role == "user" else "MsgBubbleAssistant")
        bubble.setFrameShape(QFrame.Shape.NoFrame)
        bubble.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Minimum,
        )
        inner = QVBoxLayout(bubble)
        inner.setContentsMargins(14, 10, 14, 10)
        inner.setSpacing(6)

        cap = QLabel(self._role_caption(role))
        cap.setObjectName("MsgCaptionUser" if role == "user" else "MsgCaptionAssistant")
        cap.setWordWrap(True)
        cap.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum,
        )
        body = QLabel()
        body.setObjectName("MsgBody")
        body.setWordWrap(True)
        body.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum,
        )
        body.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )

        if role == "user":
            body.setTextFormat(Qt.TextFormat.PlainText)
            body.setText(content or "")
            av = QLabel("👤")
            av.setObjectName("MsgAvatarUser")
            av.setFixedSize(40, 40)
            av.setAlignment(Qt.AlignmentFlag.AlignCenter)
            outer.addStretch(1)
            outer.addWidget(bubble, 0, Qt.AlignmentFlag.AlignTop)
            outer.addWidget(av, 0, Qt.AlignmentFlag.AlignTop)
        else:
            body.setTextFormat(Qt.TextFormat.MarkdownText)
            body.setText(content or "")
            av = QLabel("🐋")
            av.setObjectName("MsgAvatarAssistant")
            av.setFixedSize(40, 40)
            av.setAlignment(Qt.AlignmentFlag.AlignCenter)
            outer.addWidget(av, 0, Qt.AlignmentFlag.AlignTop)
            outer.addWidget(bubble, 0, Qt.AlignmentFlag.AlignTop)
            outer.addStretch(1)

        inner.addWidget(cap)
        inner.addWidget(body)
        row._bubble_frame = bubble  # type: ignore[attr-defined]
        row._body_label = body  # type: ignore[attr-defined]
        row._cap_label = cap  # type: ignore[attr-defined]
        return row

    def _debug_task_id(self) -> str | None:
        spec = sections_loader.get_version_spec(self._version_id)
        tid = spec.get("debug_task_id")
        return str(tid) if tid else None

    def _is_debug_task(self) -> bool:
        dt = self._debug_task_id()
        return bool(dt and self._task_id == dt)

    def _bootstrap_if_needed(self) -> None:
        if self._is_debug_task():
            self._bootstrap_debug_if_needed()
            return
        self._bootstrap_planning_if_needed()
        self._bootstrap_coding_if_needed()

    def _update_ctx_label(self) -> None:
        sec = sections_loader.get_leaf_section(self._version_id, self._task_id)
        title = sec.get("title") if sec else None
        suffix = f" · {title}" if title else ""
        base = f"AI 教练 · {self._version_id} / {self._task_id}{suffix}"
        chat_th = self._chat_send_thread
        chat_here = (
            chat_th
            and chat_th.isRunning()
            and chat_th.thread_task_id == self._task_id
        )
        intro_th = self._intro_bootstrap_thread
        intro_here = (
            intro_th
            and intro_th.isRunning()
            and intro_th.bootstrap_task_id == self._task_id
        )
        debug_th = self._debug_analyze_thread
        debug_here = (
            debug_th
            and debug_th.isRunning()
            and debug_th.thread_task_id == self._task_id
        )
        if chat_here:
            base += " · 正在请求回复…"
            self._set_send_state("状态：正在请求教练回复…", True)
        elif debug_here:
            base += " · 正在分析 Debug 输入…"
            self._set_send_state("状态：正在分析输出与代码差异…", True)
        elif intro_here:
            if sec and sec.get("role") == "planning":
                base += " · 正在获取导读…"
                self._set_send_state("状态：正在获取本节导读…", True)
            else:
                base += " · 正在生成本节引导…"
                self._set_send_state("状态：正在生成本节引导…", True)
        else:
            self._set_send_state("就绪：可发送问题或粘贴代码输出。", False)
        self._ctx_label.setText(base)

    def _intro_thread_running(self) -> bool:
        return bool(
            self._intro_bootstrap_thread and self._intro_bootstrap_thread.isRunning()
        )

    def _chat_send_thread_busy_for_current(self) -> bool:
        th = self._chat_send_thread
        return bool(th and th.isRunning() and th.thread_task_id == self._task_id)

    def _chat_send_thread_running(self) -> bool:
        return bool(self._chat_send_thread and self._chat_send_thread.isRunning())

    def _debug_analyze_thread_running(self) -> bool:
        return bool(
            self._debug_analyze_thread and self._debug_analyze_thread.isRunning()
        )

    def _debug_analyze_thread_busy_for_current(self) -> bool:
        th = self._debug_analyze_thread
        return bool(th and th.isRunning() and th.thread_task_id == self._task_id)

    def _may_overwrite_auto_intro(self) -> bool:
        """空磁盘或仍为「无 Key 占位」双条（导读或编码引导）时才允许覆盖。"""
        cur = data_manager.load_task_history(self._version_id, self._task_id)
        if not cur:
            return True
        return _is_planning_placeholder_bootstrap(cur) or _is_coding_placeholder_bootstrap(
            cur
        )

    def _save_auto_intro_messages(self, trigger: str, reply: str) -> None:
        if not self._may_overwrite_auto_intro():
            return
        data_manager.save_task_history(
            self._version_id,
            self._task_id,
            [
                {"role": "user", "content": trigger},
                {"role": "assistant", "content": reply},
            ],
        )
        self.load_history()

    def _start_intro_bootstrap_async(self, trigger: str) -> None:
        if self._intro_thread_running():
            return
        th = IntroBootstrapThread(
            self._version_id, self._task_id, trigger, None
        )
        th.finished_ok.connect(self._on_intro_bootstrap_finished_ok)
        th.finished_err.connect(self._on_intro_bootstrap_finished_err)
        th.finished.connect(th.deleteLater)
        th.finished.connect(lambda t=th: self._on_intro_bootstrap_thread_finished(t))
        self._intro_bootstrap_thread = th
        th.start()
        self._update_ctx_label()

    def _on_intro_bootstrap_thread_finished(self, th: QThread) -> None:
        if self._intro_bootstrap_thread is th:
            self._intro_bootstrap_thread = None
        self._update_ctx_label()
        QTimer.singleShot(0, self._bootstrap_if_needed)

    def _start_coach_chat_async(
        self, messages: list[dict[str, Any]], user_text: str
    ) -> None:
        if self._chat_send_thread_running():
            return
        th = CoachChatThread(
            self._version_id, self._task_id, messages, user_text, None
        )
        th.finished_ok.connect(self._on_coach_chat_finished_ok)
        th.finished_err.connect(self._on_coach_chat_finished_err)
        th.finished.connect(th.deleteLater)
        th.finished.connect(lambda t=th: self._on_coach_chat_thread_finished(t))
        self._chat_send_thread = th
        th.start()
        self._update_ctx_label()

    def _on_coach_chat_thread_finished(self, th: QThread) -> None:
        if self._chat_send_thread is th:
            self._chat_send_thread = None
        self._update_ctx_label()

    def _start_debug_analyze_async(
        self,
        user_text: str,
        sample: dict[str, Any],
        user_output: str,
        program_source: str,
    ) -> bool:
        if self._debug_analyze_thread_running():
            return False
        th = DebugAnalyzeThread(
            self._version_id,
            self._task_id,
            user_text,
            sample,
            user_output,
            program_source,
            None,
        )
        th.finished_ok.connect(self._on_debug_analyze_finished_ok)
        th.finished_err.connect(self._on_debug_analyze_finished_err)
        th.finished.connect(th.deleteLater)
        th.finished.connect(lambda t=th: self._on_debug_analyze_thread_finished(t))
        self._debug_analyze_thread = th
        th.start()
        self._update_ctx_label()
        return True

    def _on_debug_analyze_thread_finished(self, th: QThread) -> None:
        if self._debug_analyze_thread is th:
            self._debug_analyze_thread = None
        self._update_ctx_label()

    def _append_assistant_reply_for_user(
        self, user_text: str, reply_text: str, state_msg: str
    ) -> bool:
        hist = data_manager.load_task_history(self._version_id, self._task_id)
        if not hist:
            ui_theme.msg_info(
                self,
                "回复未写入",
                "本地对话记录为空，无法写入助手回复（可能已清空或切换了任务）。",
            )
            self._set_send_state("失败：未能写入回复。", False)
            return False
        last = hist[-1]
        if last.get("role") != "user" or last.get("content") != user_text:
            ui_theme.msg_info(
                self,
                "回复未写入",
                "当前对话末尾与发送时的内容不一致，上一条回复已丢弃，避免写错记录。",
            )
            self._set_send_state("失败：未能写入回复。", False)
            return False
        body = _normalize_assistant_reply(reply_text)
        self.append_message("assistant", body)
        hist.append({"role": "assistant", "content": body})
        self._save_history_with_feedback(hist, "追加助手回复")
        self._set_send_state(state_msg, False)
        return True

    def _save_history_with_feedback(
        self, messages: list[dict[str, Any]], scene: str
    ) -> None:
        data_manager.save_task_history(self._version_id, self._task_id, messages)
        err = data_manager.get_last_history_io_error()
        if not err:
            return
        ui_theme.msg_warn(
            self,
            "聊天记录写入异常",
            f"{scene} 时写入本地 history 失败，可能导致记录缺失。\n{err}",
        )

    def _shutdown_threads(self) -> None:
        """窗口销毁前等待后台线程收尾，避免 QThread 析构告警。"""
        for th in (
            self._intro_bootstrap_thread,
            self._chat_send_thread,
            self._debug_analyze_thread,
        ):
            if th and th.isRunning():
                # run() 内是同步网络调用，quit() 无法中断，这里等待其自然结束。
                th.wait()
        self._intro_bootstrap_thread = None
        self._chat_send_thread = None
        self._debug_analyze_thread = None

    def closeEvent(self, event: QCloseEvent) -> None:
        self._shutdown_threads()
        super().closeEvent(event)

    def _on_coach_chat_finished_ok(
        self, vid: str, tid: str, user_text: str, reply: str
    ) -> None:
        if vid != self._version_id or tid != self._task_id:
            ui_theme.msg_info(
                self,
                "回复未写入",
                "您已切换到其他版本或任务，上一条网络回复已丢弃，未写入当前对话。",
            )
            return
        self._append_assistant_reply_for_user(
            user_text, reply, "完成：已收到教练回复。"
        )

    def _on_coach_chat_finished_err(
        self, vid: str, tid: str, user_text: str, err: str
    ) -> None:
        if vid != self._version_id or tid != self._task_id:
            ui_theme.msg_info(
                self,
                "错误未写入",
                "您已切换到其他版本或任务，该次请求失败信息未写入当前对话。",
            )
            return
        ui_theme.msg_warn(self, "教练请求失败", err)
        self._append_assistant_reply_for_user(
            user_text, f"[错误] {err}", "失败：请求出错，可修改问题后重试。"
        )

    def _on_debug_analyze_finished_ok(
        self, vid: str, tid: str, user_text: str, reply: str
    ) -> None:
        if vid != self._version_id or tid != self._task_id:
            return
        self._append_assistant_reply_for_user(
            user_text, reply, "完成：已更新本轮 Debug 反馈。"
        )

    def _on_debug_analyze_finished_err(
        self, vid: str, tid: str, user_text: str, err: str
    ) -> None:
        if vid != self._version_id or tid != self._task_id:
            return
        ui_theme.msg_warn(self, "Debug 分析失败", err)
        self._append_assistant_reply_for_user(
            user_text,
            f"[错误] {err}",
            "失败：Debug 分析异常，请调整输入后重试。",
        )

    def _on_intro_bootstrap_finished_ok(
        self, vid: str, tid: str, trigger: str, reply: str
    ) -> None:
        if vid != self._version_id or tid != self._task_id:
            return
        self._save_auto_intro_messages(
            trigger, _normalize_assistant_reply(reply)
        )

    def _on_intro_bootstrap_finished_err(
        self, vid: str, tid: str, trigger: str, err: str
    ) -> None:
        if vid != self._version_id or tid != self._task_id:
            return
        self._save_auto_intro_messages(trigger, f"[错误] {err}")

    def _bootstrap_planning_if_needed(self) -> None:
        sec = sections_loader.get_leaf_section(self._version_id, self._task_id)
        if not sec or sec.get("role") != "planning":
            return
        if self._intro_thread_running():
            return
        hist = data_manager.load_task_history(self._version_id, self._task_id)
        trigger = _PLANNING_BOOTSTRAP_TRIGGER
        if hist:
            if _is_planning_placeholder_bootstrap(hist) and ai_coach.has_api_key():
                self._start_intro_bootstrap_async(trigger)
            return
        if ai_coach.has_api_key():
            self._start_intro_bootstrap_async(trigger)
        else:
            reply = ai_coach.chat(self._version_id, self._task_id, [], trigger)
            self._save_auto_intro_messages(
                trigger, _normalize_assistant_reply(reply)
            )

    def _bootstrap_coding_if_needed(self) -> None:
        sec = sections_loader.get_leaf_section(self._version_id, self._task_id)
        if not sec or sec.get("role") in ("planning", "debug"):
            return
        if self._intro_thread_running():
            return
        hist = data_manager.load_task_history(self._version_id, self._task_id)
        trigger = _CODING_BOOTSTRAP_TRIGGER
        if hist:
            if _is_coding_placeholder_bootstrap(hist) and ai_coach.has_api_key():
                self._start_intro_bootstrap_async(trigger)
            return
        if ai_coach.has_api_key():
            self._start_intro_bootstrap_async(trigger)
        else:
            reply = ai_coach.chat(self._version_id, self._task_id, [], trigger)
            self._save_auto_intro_messages(
                trigger, _normalize_assistant_reply(reply)
            )

    def refresh_bootstrap(self) -> None:
        """主页保存 API 后再次进入本版本页时调用，用于补发导读等占位重试。"""
        self._bootstrap_if_needed()

    def _bootstrap_debug_if_needed(self) -> None:
        hist = data_manager.load_task_history(self._version_id, self._task_id)
        if hist:
            return
        samples = data_manager.load_version_samples(self._version_id)
        if not samples:
            intro = "（暂无样例，请在 data/versionN/samples.json 中配置。）"
            data_manager.save_task_history(
                self._version_id,
                self._task_id,
                [{"role": "assistant", "content": intro}],
            )
            self.load_history()
            return
        state = data_manager.load_version_state(self._version_id)
        data_manager.ensure_task_state(state, self._task_id)
        state[self._task_id]["current_sample_index"] = 0
        data_manager.save_version_state(self._version_id, state)
        lines = ["所有编码节已完成，现在开始调试。"]
        if not sections_loader.all_coding_leaves_completed(
            state, self._version_id
        ):
            lines.append("提示：建议先完成左侧各编码小节的勾选后再系统调试。")
        lines.append(
            "请在本地用中列完整程序运行，并将**完整**程序输出粘贴回对话框。"
        )
        lines.append(f"这是第 1 条样例输入：\n{samples[0].get('input', '')}")
        intro = "\n".join(lines)
        self._save_history_with_feedback(
            [
                {"role": "assistant", "content": intro},
            ],
            "初始化 Debug 引导",
        )
        self.load_history()

    def set_task(self, task_id: str, *, bootstrap: bool = True) -> None:
        """
        左侧任务列表切换时由 VersionPage 调用。
        更新内存中的 task_id 后立刻 load_history，使右侧文本与磁盘里该任务的记录一致。
        """
        self._task_id = task_id  # 更新当前任务
        self._update_ctx_label()
        self.load_history()
        if bootstrap:
            self._bootstrap_if_needed()

    def load_history(self) -> None:
        hist = data_manager.load_task_history(self._version_id, self._task_id)
        self._clear_history_rows()
        for m in hist:
            role = str(m.get("role", ""))
            content = str(m.get("content", ""))
            self._history_layout.addWidget(self._make_message_row_widget(role, content))
        self.refresh_message_layout_after_host_resize()

    def clear(self) -> None:
        data_manager.clear_task_history(self._version_id, self._task_id)
        if self._is_debug_task():
            state = data_manager.load_version_state(self._version_id)
            slot = data_manager.ensure_task_state(state, self._task_id)
            slot["current_sample_index"] = 0
            data_manager.save_version_state(self._version_id, state)
        self._clear_history_rows()
        QTimer.singleShot(0, self._safe_bootstrap_after_clear)

    def _safe_bootstrap_after_clear(self) -> None:
        try:
            self._bootstrap_if_needed()
        except Exception as exc:
            ui_theme.msg_warn(
                self,
                "恢复对话",
                f"清空后自动重建导读失败：\n{type(exc).__name__}: {exc}\n\n"
                "可稍后手动发送一条消息重试。",
            )

    def _on_clear_clicked(self) -> None:
        ok = ui_theme.msg_question(
            self,
            "清空聊天记录",
            "确定清空当前版本与任务下的教练对话吗？将同步删除本地 history 中对应记录，且不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ok == QMessageBox.StandardButton.Yes:  # 用户确认
            self.clear()  # 执行持久化清空

    def append_message(self, role: str, content: str) -> None:
        """在对话区末尾追加一条气泡；不负责写入 JSON。"""
        self._history_layout.addWidget(self._make_message_row_widget(role, content))
        self._refresh_message_bubble_max_widths()
        self._force_history_reflow()
        self._scroll_history_to_bottom()
        QTimer.singleShot(0, lambda: self._post_history_refresh(True))

    @staticmethod
    def _role_caption(role: str) -> str:
        return {"user": "用户", "assistant": "助手"}.get(role, role or "?")  # 界面展示用中文角色名

    def _scroll_history_to_bottom(self) -> None:
        def _go() -> None:
            bar = self._history_scroll.verticalScrollBar()
            bar.setValue(bar.maximum())

        QTimer.singleShot(0, _go)
        QTimer.singleShot(16, _go)

    def _on_send(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            return
        if self._chat_send_thread_busy_for_current() or self._debug_analyze_thread_busy_for_current():
            ui_theme.msg_info(
                self,
                "请稍候",
                "上一条消息仍在请求中，请等待回复后再发送。",
            )
            return
        self._input.clear()
        self._set_send_state("状态：已发送，等待教练回复…", True)
        if self._is_debug_task():
            self._on_send_debug(text)
            return
        hist = data_manager.load_task_history(self._version_id, self._task_id)
        self.append_message("user", text)
        hist.append({"role": "user", "content": text})
        data_manager.save_task_history(self._version_id, self._task_id, hist)

        if ai_coach.has_api_key():
            self._start_coach_chat_async(hist[:-1], text)
            return

        try:
            reply = ai_coach.chat(
                self._version_id,
                self._task_id,
                hist[:-1],
                text,
            )
        except Exception as exc:
            reply = f"[错误] {exc}"
            ui_theme.msg_warn(self, "教练请求失败", str(exc))
        reply = _normalize_assistant_reply(reply)
        self.append_message("assistant", reply)
        hist.append({"role": "assistant", "content": reply})
        data_manager.save_task_history(self._version_id, self._task_id, hist)
        self._set_send_state("完成：已收到教练回复。", False)

    def _on_send_debug(self, text: str) -> None:
        try:
            samples = data_manager.load_version_samples(self._version_id)
            state = data_manager.load_version_state(self._version_id)
            slot = data_manager.ensure_task_state(state, self._task_id)
            index_raw = slot.get("current_sample_index", 0)
            index = index_raw if isinstance(index_raw, int) else 0
            hist = data_manager.load_task_history(self._version_id, self._task_id)
            self.append_message("user", text)
            hist.append({"role": "user", "content": text})
            self._save_history_with_feedback(hist, "追加用户 Debug 输入")

            mode = data_manager.classify_debug_user_input(text)
            if mode == "question":
                if ai_coach.has_api_key():
                    self._start_coach_chat_async(hist[:-1], text)
                    return
                reply = ai_coach.chat(
                    self._version_id,
                    self._task_id,
                    hist[:-1],
                    text,
                )
                self._append_assistant_reply_for_user(
                    text, reply, "完成：已收到 Debug 问答回复。"
                )
                return

            if index >= len(samples):
                self._append_assistant_reply_for_user(
                    text,
                    "所有样例已测试完成。若尚未勾选左侧 Debug，请手动勾选。",
                    "完成：Debug 样例流程已结束。",
                )
                return

            sample = samples[index]
            expected = data_manager.normalize_program_output(str(sample.get("output", "")))
            extracted = data_manager.extract_likely_program_output(text)
            candidate_output = (
                extracted
                if mode == "mixedOrCode"
                else data_manager.normalize_program_output(text)
            )
            actual = data_manager.normalize_program_output(candidate_output)

            if actual and actual == expected:
                n = index + 1
                reply = f"样例 {n} 通过。"
                slot["current_sample_index"] = index + 1
                data_manager.save_version_state(self._version_id, state)
                if index + 1 < len(samples):
                    nxt = index + 2
                    reply += f"\n下面是第 {nxt} 条样例输入：\n{samples[index + 1].get('input', '')}"
                else:
                    reply += "\n所有样例已通过。请在左侧手动勾选 Debug 复选框标记完成。"
                self._append_assistant_reply_for_user(
                    text, reply, "完成：已更新本轮 Debug 反馈。"
                )
                return

            program = self._program_loader()
            analysis_input = text
            if extracted:
                analysis_input = (
                    f"[用户原文]\n{text}\n\n"
                    f"[提取的疑似程序输出]\n{extracted}\n\n"
                    f"[期望输出]\n{expected}"
                )
            elif mode == "mixedOrCode":
                analysis_input = (
                    "[说明] 用户输入疑似为自然语言+代码/输出混合，未能稳定提取完整输出。\n\n"
                    f"[用户原文]\n{text}\n\n"
                    f"[期望输出]\n{expected}"
                )
            if ai_coach.has_api_key() and self._start_debug_analyze_async(
                text, sample, analysis_input, program
            ):
                return
            reply = ai_coach.analyze_debug_mismatch(
                self._version_id, sample, analysis_input, program
            )
            self._append_assistant_reply_for_user(
                text, reply, "完成：已更新本轮 Debug 反馈。"
            )
        except Exception as exc:
            ui_theme.msg_warn(
                self,
                "Debug 处理异常",
                f"{type(exc).__name__}: {exc}",
            )
            self._set_send_state("失败：Debug 处理异常，请重试。", False)
