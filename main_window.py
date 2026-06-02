"""
主窗口：应用只有一个 MainWindow；主页选版本 → 栈切换到 VersionPage → 返回再切回主页。

── PyQt 初学者可先对照下列概念读本文件 ──
1. QMainWindow（本类继承它）
   - 比 QWidget 多了「菜单栏 / 工具栏 / 状态栏 / 停靠区」等预留位置；最少也要设一个 centralWidget。
   - 本骨架没用菜单栏，只把 QStackedWidget 塞进中央区域，占满客户区。
2. QStackedWidget（核心容器）
   - 多个子页面叠在同一矩形区域，**任意时刻只显示其中一个**；像一摞扑克牌只翻开一张。
   - 用「索引」或「控件指针」切换当前页：setCurrentIndex / setCurrentWidget。
   - **顺序很重要**：本文件约定索引 **0 = 主页**，必须先 addWidget(home)，再往栈里追加各 VersionPage；
     `_go_home` 里写 setCurrentIndex(0) 才能稳定回到主页。
3. 布局（QVBoxLayout / QHBoxLayout）
   - 主页由竖排（标题 + 一整行按钮）拼出来；那一行按钮又用横排布局承载。
4. 信号槽（配合 version_page）
   - 主页按钮：`clicked` → lambda → `_open_version`。
   - 版本页：`VersionPage.back_requested` → `_go_home`（子页面不直接操作栈，只发信号）。
5. Python 闭包（按钮 lambda）
   - 循环里创建多个按钮时，用 `lambda checked, v=vid: ...` 把当前的 vid「冻结」进默认参数，
     避免四个按钮都指向最后一次循环的 vid（详见下方循环内注释）。

与其它文件的衔接：
- VERSION_ENTRIES 里的 vid（version1…）必须与 prompts/version*.txt、data/*.json 键名一致。
- VersionPage 构造后缓存在 `_version_pages`，避免重复创建、保留聊天记录所在控件不被销毁。

类型标注：`from __future__ import annotations` 与其它模块一致。
"""

# 让当前文件里可以用「list[str]」这种写法标注类型（Python 3.9+ 也可不用这行；写上兼容旧习惯）
from __future__ import annotations

import time

from PyQt6.QtCore import QEventLoop, QThread, QTimer, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# 同项目：某一魔兽版本的完整页面（左任务树 + 右 Tab）
from version_page import VersionPage

import ai_coach
import data_manager
import sections_loader
import ui_theme

# 主页四个按钮的数据源：每项 (内部 id, 按钮上显示的中文)。
# 内部 id 必须稳定（字符串），供 OpenAI/DeepSeek、路径 prompts、JSON 使用；中文 label 仅展示。
VERSION_ENTRIES = (
    ("version1", "魔兽世界一 · 备战"),
    ("version2", "魔兽世界二 · 装备"),
    ("version3", "魔兽世界三 · 开战"),
    ("version4", "魔兽世界四 · 终极版"),
)

MODEL_OPTIONS = (
    ("deepseek-v4-flash", "DeepSeek V4 Flash"),
    ("deepseek-v4-pro", "DeepSeek V4 Pro"),
    ("deepseek-chat", "deepseek-chat（兼容）"),
)

VERSION_META = {
    "version1": {"difficulty": "难度 1/4", "eta": "预计 30-45 分钟", "tag": "新手备战"},
    "version2": {"difficulty": "难度 2/4", "eta": "预计 45-70 分钟", "tag": "装备进阶"},
    "version3": {"difficulty": "难度 3/4", "eta": "预计 70-100 分钟", "tag": "战场推进"},
    "version4": {"difficulty": "难度 4/4", "eta": "预计 90-130 分钟", "tag": "终极挑战"},
}

API_PING_UI_SECONDS = int(ai_coach.API_PING_TIMEOUT_SECONDS)


class ApiPingThread(QThread):
    """后台调用 ai_coach.ping_api，避免阻塞 UI。"""

    finished_with_result = pyqtSignal(object)

    def run(self) -> None:
        self.finished_with_result.emit(ai_coach.ping_api())


class ApiPingDialog(QDialog):
    """API 验证专用进度窗口（纯 Qt，自定义主题，禁止手动关闭）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._allow_close = False
        self.setObjectName("ApiPingDialog")
        self.setWindowTitle("验证 API")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setMinimumWidth(480)
        self.setMinimumHeight(200)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(10)

        title = QLabel("正在连接 DeepSeek")
        title.setObjectName("ApiPingTitle")
        root.addWidget(title)

        self._status_label = QLabel("正在初始化校验流程…")
        self._status_label.setWordWrap(True)
        self._status_label.setObjectName("ApiPingBody")
        root.addWidget(self._status_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # busy / 不确定时长
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(10)
        root.addWidget(self._progress)

        self._hint_label = QLabel("请稍候，不建议重复点击保存。")
        self._hint_label.setObjectName("ApiPingHint")
        root.addWidget(self._hint_label)

        self.setStyleSheet(ui_theme.api_ping_dialog_stylesheet())

    def closeEvent(self, event) -> None:  # type: ignore[override]
        # 验证期间不允许用户手动关闭，防止中断流程。
        if self._allow_close:
            event.accept()
        else:
            event.ignore()

    def finish(self) -> None:
        self._allow_close = True
        self.done(0)

    def set_progress_text(self, elapsed_sec: float, rem_sec: int, max_sec: int) -> None:
        self._status_label.setText(
            "正在连接 DeepSeek 并校验 API…\n"
            f"已用约 {elapsed_sec:.0f} 秒；预计还需约 {rem_sec} 秒"
            f"（单次上限 {max_sec} 秒，为保守估计）。"
        )


class MainWindow(QMainWindow):
    """
    应用程序唯一的顶层窗口实例（main.py 里创建并 show）。

    主要职责：
    - 搭建「主页」UI，并为每个版本缓存一个 VersionPage；
    - 维护 QStackedWidget 的页面栈与「当前显示哪一页」。
    """

    def __init__(self) -> None:
        # QMainWindow 必须先初始化，才能使用 setCentralWidget 等 API
        super().__init__()
        # 窗口标题栏显示的字符串（操作系统任务栏、窗口左上角可见）
        self.setWindowTitle("AI 编程教练")
        self.resize(1200, 720)

        # ────────── 栈容器：所有「整页」界面都放在这里面 ──────────
        self._stack = QStackedWidget()

        # ────────── 第 0 页：主页（品牌+快速开始+战役卡片）──────────
        home = QWidget()
        home.setObjectName("HomePage")
        home_layout = QVBoxLayout(home)
        home_layout.setContentsMargins(0, 0, 0, 0)

        self._home_scroll = QScrollArea()
        self._home_scroll.setWidgetResizable(True)
        self._home_scroll.setFrameShape(QFrame.Shape.NoFrame)
        home_layout.addWidget(self._home_scroll)

        home_content = QWidget()
        home_content.setObjectName("HomeContent")
        self._home_scroll.setWidget(home_content)
        content_layout = QVBoxLayout(home_content)
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(14)

        hero_card = QFrame()
        hero_card.setObjectName("HeroCard")
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(20, 20, 20, 20)
        hero_layout.setSpacing(10)
        hero_title = QLabel("AI 编程教练 | 魔兽 OJ 实战通关系统")
        hero_title.setObjectName("HeroTitle")
        hero_layout.addWidget(hero_title)
        hero_subtitle = QLabel(
            "像教练一样拆解任务、验证代码和定位 Debug 问题。先配置 API，马上进入你的战役地图。"
        )
        hero_subtitle.setObjectName("HeroSubtitle")
        hero_subtitle.setWordWrap(True)
        hero_layout.addWidget(hero_subtitle)
        hero_btn_row = QHBoxLayout()
        hero_btn_row.setSpacing(8)
        start_setup_btn = QPushButton("立即开始配置")
        start_setup_btn.setObjectName("PrimaryButton")
        start_setup_btn.clicked.connect(self._focus_api_setup)
        hero_btn_row.addWidget(start_setup_btn)
        show_campaign_btn = QPushButton("查看学习路线")
        show_campaign_btn.clicked.connect(self._focus_campaign_map)
        hero_btn_row.addWidget(show_campaign_btn)
        hero_btn_row.addStretch(1)
        hero_layout.addLayout(hero_btn_row)
        content_layout.addWidget(hero_card)

        trust_row = QHBoxLayout()
        trust_row.setSpacing(10)
        trust_row.addWidget(
            self._make_info_card(
                "本地学习档案",
                "代码、进度与历史都写入本机目录，训练节奏不丢失。",
            )
        )
        trust_row.addWidget(
            self._make_info_card(
                "分章任务树",
                "每个版本按章节推进，进度实时累计，随时回到上次节点继续。",
            )
        )
        trust_row.addWidget(
            self._make_info_card(
                "Debug 对比验证",
                "先跑预置样例再分析差异，减少无效排查，定位更快。",
            )
        )
        content_layout.addLayout(trust_row)

        self._api_section = QFrame()
        self._api_section.setObjectName("PanelCard")
        api_panel_layout = QVBoxLayout(self._api_section)
        api_panel_layout.setContentsMargins(18, 16, 18, 16)
        api_panel_layout.setSpacing(10)
        api_head = QHBoxLayout()
        api_title = QLabel("快速开始（3 步）")
        api_title.setObjectName("SectionTitle")
        api_head.addWidget(api_title)
        api_head.addStretch(1)
        self._api_status_badge = QLabel("未配置")
        self._api_status_badge.setObjectName("ApiStatusBadge")
        api_head.addWidget(self._api_status_badge)
        api_panel_layout.addLayout(api_head)
        api_panel_layout.addWidget(QLabel("Step 1 选择模型  ->  Step 2 填写 API Key  ->  Step 3 验证并开始"))

        api_row = QHBoxLayout()
        api_row.setSpacing(8)
        api_row.addWidget(QLabel("模型"))
        self._model_combo = QComboBox()
        for model_id, label in MODEL_OPTIONS:
            self._model_combo.addItem(label, model_id)
        api_row.addWidget(self._model_combo, stretch=0)
        api_key_wrap = QWidget()
        api_key_wrap_layout = QHBoxLayout(api_key_wrap)
        api_key_wrap_layout.setContentsMargins(0, 0, 0, 0)
        api_key_wrap_layout.setSpacing(4)
        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setPlaceholderText("填写 DeepSeek API Key；仅保存到本机")
        api_key_wrap_layout.addWidget(self._api_key_input, stretch=1)
        self._api_key_visibility_btn = QToolButton()
        self._api_key_visibility_btn.setText("显示")
        self._api_key_visibility_btn.setCheckable(True)
        self._api_key_visibility_btn.setToolTip("显示 / 隐藏 API Key")
        self._api_key_visibility_btn.toggled.connect(self._on_api_key_visibility_toggled)
        api_key_wrap_layout.addWidget(self._api_key_visibility_btn, stretch=0)
        api_row.addWidget(api_key_wrap, stretch=1)
        save_api_btn = QPushButton("验证并开始")
        save_api_btn.setObjectName("PrimaryButton")
        save_api_btn.clicked.connect(self._save_api_settings)
        api_row.addWidget(save_api_btn)
        self._save_api_btn = save_api_btn
        api_panel_layout.addLayout(api_row)
        self._api_status_detail = QLabel(
            "安全提示：API Key 仅保存在本机 data/app_settings.json，不会写入仓库。"
        )
        self._api_status_detail.setObjectName("MutedText")
        self._api_status_detail.setWordWrap(True)
        api_panel_layout.addWidget(self._api_status_detail)
        content_layout.addWidget(self._api_section)

        self._campaign_section = QFrame()
        self._campaign_section.setObjectName("PanelCard")
        campaign_layout = QVBoxLayout(self._campaign_section)
        campaign_layout.setContentsMargins(18, 16, 18, 16)
        campaign_layout.setSpacing(10)
        campaign_layout.addWidget(QLabel("战役地图"))
        campaign_tip = QLabel("每个版本都包含完整任务树。建议按顺序推进，先稳后快。")
        campaign_tip.setObjectName("MutedText")
        campaign_tip.setWordWrap(True)
        campaign_layout.addWidget(campaign_tip)

        card_grid = QGridLayout()
        card_grid.setHorizontalSpacing(10)
        card_grid.setVerticalSpacing(10)
        self._home_version_buttons: list[tuple[str, QPushButton]] = []
        self._home_version_progress_labels: dict[str, QLabel] = {}
        self._home_version_hint_labels: dict[str, QLabel] = {}
        for idx, (vid, label) in enumerate(VERSION_ENTRIES):
            meta = VERSION_META[vid]
            card = QFrame()
            card.setObjectName("CampaignCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(8)
            title = QLabel(f"{label} · {meta['tag']}")
            title.setObjectName("CampaignTitle")
            title.setWordWrap(True)
            card_layout.addWidget(title)
            meta_info = QLabel(f"{meta['difficulty']}  |  {meta['eta']}")
            meta_info.setObjectName("MutedText")
            card_layout.addWidget(meta_info)
            progress_label = QLabel("进度：0/0")
            progress_label.setObjectName("ProgressText")
            card_layout.addWidget(progress_label)
            hint_label = QLabel("下一步：从第一章开始")
            hint_label.setObjectName("MutedText")
            card_layout.addWidget(hint_label)
            btn = QPushButton("从第一章开始")
            btn.clicked.connect(lambda checked, v=vid: self._open_version(v))
            card_layout.addWidget(btn)
            self._home_version_buttons.append((vid, btn))
            self._home_version_progress_labels[vid] = progress_label
            self._home_version_hint_labels[vid] = hint_label
            row_idx, col_idx = divmod(idx, 2)
            card_grid.addWidget(card, row_idx, col_idx)
        campaign_layout.addLayout(card_grid)
        content_layout.addWidget(self._campaign_section)

        motivation_card = QFrame()
        motivation_card.setObjectName("PanelCard")
        motivation_layout = QVBoxLayout(motivation_card)
        motivation_layout.setContentsMargins(18, 16, 18, 16)
        motivation_layout.setSpacing(8)
        motivation_title = QLabel("回访激励")
        motivation_title.setObjectName("SectionTitle")
        motivation_layout.addWidget(motivation_title)
        self._today_goal_label = QLabel("今日目标：完成 1 个叶子任务")
        self._today_goal_label.setWordWrap(True)
        motivation_layout.addWidget(self._today_goal_label)
        self._activity_label = QLabel("学习活跃度：0 个版本已开启")
        motivation_layout.addWidget(self._activity_label)
        self._last_focus_label = QLabel("建议下一步：先完成 API 验证")
        self._last_focus_label.setWordWrap(True)
        motivation_layout.addWidget(self._last_focus_label)
        self._recommended_btn = QPushButton("继续推荐版本")
        self._recommended_btn.clicked.connect(self._open_recommended_version)
        motivation_layout.addWidget(self._recommended_btn)
        self._recommended_version_id: str | None = None
        self._last_opened_version_id: str | None = None
        content_layout.addWidget(motivation_card)
        content_layout.addStretch(1)

        home.setStyleSheet(ui_theme.home_stylesheet())

        self._refresh_home_progress_labels()

        # 主页必须是栈里第一个 addWidget，从而索引恒为 0，供 _go_home 使用
        self._stack.addWidget(home)

        # version_id → 已创建的 VersionPage 实例；首次进入某版本时创建并缓存，返回主页不销毁
        # self._version_pages：实例属性；前导 _ 表示约定「类内部使用」。
        # dict[str, VersionPage]：类型标注（键为版本字符串，值为页面对象）；运行时不强制检查。
        self._version_pages: dict[str, VersionPage] = {}
        self._api_verified_ok = False

        # 把整个栈交给主窗口中央区域；此后可见内容完全由 _stack 当前页决定
        self.setCentralWidget(self._stack)
        self._apply_api_settings_from_disk()
        self._refresh_version_buttons_enabled()
        QTimer.singleShot(0, self._startup_api_verify_if_needed)

    def _make_info_card(self, title: str, body: str) -> QFrame:
        card = QFrame()
        card.setObjectName("InfoCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        layout.addWidget(title_label)
        body_label = QLabel(body)
        body_label.setObjectName("MutedText")
        body_label.setWordWrap(True)
        layout.addWidget(body_label)
        return card

    def _focus_api_setup(self) -> None:
        self._home_scroll.ensureWidgetVisible(self._api_section, yMargin=24)
        self._api_key_input.setFocus()

    def _focus_campaign_map(self) -> None:
        self._home_scroll.ensureWidgetVisible(self._campaign_section, yMargin=24)

    def _set_api_status(self, state: str, detail: str) -> None:
        text, style = ui_theme.API_STATUS_STYLE_MAP.get(
            state, ui_theme.API_STATUS_STYLE_MAP["pending"]
        )
        self._api_status_badge.setText(text)
        self._api_status_badge.setStyleSheet(style)
        self._api_status_detail.setText(detail)

    def _open_recommended_version(self) -> None:
        target = self._recommended_version_id
        if target is None:
            return
        self._open_version(target)

    def _model_id_from_combo(self) -> str:
        model_id = self._model_combo.currentData()
        if isinstance(model_id, str) and model_id.strip():
            return model_id.strip()
        return data_manager.DEFAULT_APP_MODEL

    def _set_model_combo(self, model_id: str) -> None:
        target = model_id.strip() or data_manager.DEFAULT_APP_MODEL
        for index in range(self._model_combo.count()):
            if self._model_combo.itemData(index) == target:
                self._model_combo.setCurrentIndex(index)
                return
        self._model_combo.setCurrentIndex(0)

    def _on_api_key_visibility_toggled(self, visible: bool) -> None:
        self._api_key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )
        self._api_key_visibility_btn.setText("隐藏" if visible else "显示")

    def _apply_api_settings_from_disk(self) -> None:
        settings = data_manager.load_app_settings()
        self._set_model_combo(settings["model"])
        self._api_key_input.setText(settings["api_key"])
        if self._api_key_visibility_btn.isChecked():
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        ai_coach.set_runtime_config(settings["api_key"], settings["model"])
        if ai_coach.has_api_key():
            self._set_api_status("pending", "已检测到本机 Key，请点击“验证并开始”或等待自动验证。")
        else:
            self._set_api_status(
                "no_key", "请先填写 API Key。你也可以先配置环境变量 DEEPSEEK_API_KEY。"
            )

    def _set_home_api_controls_enabled(self, enabled: bool) -> None:
        self._model_combo.setEnabled(enabled)
        self._api_key_input.setEnabled(enabled)
        self._api_key_visibility_btn.setEnabled(enabled)
        self._save_api_btn.setEnabled(enabled)

    def _refresh_version_buttons_enabled(self) -> None:
        """有 Key 且已通过 ping 才可进版本；无 Key 时按钮可点，由 _open_version 提示填写。"""
        can_enter = (not ai_coach.has_api_key()) or self._api_verified_ok
        for _vid, btn in self._home_version_buttons:
            btn.setEnabled(can_enter)
        if not ai_coach.has_api_key():
            self._set_api_status(
                "no_key", "请先填写 API Key 并点击“验证并开始”，再进入任意战役版本。"
            )
        elif self._api_verified_ok:
            self._set_api_status("success", "连接验证通过，可以直接进入任意版本继续学习。")
        else:
            self._set_api_status("pending", "模型与 Key 已保存，请完成验证后开始训练。")
        self._refresh_home_progress_labels()

    def _run_api_ping_modal(self) -> bool:
        """模态进度与倒计时；成功返回 True。无取消按钮，依赖客户端超时结束。"""
        self._set_api_status("checking", "正在验证 API 连通性，请稍候。")
        dlg = ApiPingDialog(self)
        dlg.show()

        self._set_home_api_controls_enabled(False)

        t0 = time.monotonic()
        err_out: list[str | None] = [None]
        loop = QEventLoop()

        th = ApiPingThread(None)

        def on_result(res: object) -> None:
            err_out[0] = res if isinstance(res, str) else None
            loop.quit()

        th.finished_with_result.connect(on_result)

        timer = QTimer(self)

        def tick() -> None:
            elapsed = time.monotonic() - t0
            rem = max(0, API_PING_UI_SECONDS - int(elapsed))
            dlg.set_progress_text(elapsed, rem, API_PING_UI_SECONDS)

        timer.timeout.connect(tick)
        tick()
        timer.start(200)
        th.start()
        loop.exec()
        timer.stop()
        th.wait()
        th.deleteLater()
        dlg.finish()
        self._set_home_api_controls_enabled(True)

        err = err_out[0]
        if err is not None:
            self._set_api_status("failed", f"验证失败：{err}")
            ui_theme.msg_warn(self, "API 验证失败", err)
            return False
        self._set_api_status("success", "连接验证通过，已准备就绪。")
        return True

    def _startup_api_verify_if_needed(self) -> None:
        if not ai_coach.has_api_key():
            self._api_verified_ok = False
            self._refresh_version_buttons_enabled()
            return
        ok = self._run_api_ping_modal()
        self._api_verified_ok = ok
        self._refresh_version_buttons_enabled()
        if not ok:
            ui_theme.msg_info(
                self,
                "API 未就绪",
                "已保存的 API Key 未能通过连接验证，暂不能进入版本页。\n"
                "请检查网络与 Key 后点击「保存」重试。",
            )

    def _save_api_settings(self) -> None:
        model = self._model_id_from_combo()
        api_key = self._api_key_input.text().strip()
        data_manager.save_app_settings({"api_key": api_key, "model": model})
        ai_coach.set_runtime_config(api_key, model)
        self._api_verified_ok = False
        self._refresh_version_buttons_enabled()

        if ai_coach.has_api_key():
            ok = self._run_api_ping_modal()
            self._api_verified_ok = ok
            self._refresh_version_buttons_enabled()
            if ok:
                ui_theme.msg_info(
                    self,
                    "已保存",
                    "API 配置已保存到本机，连接验证通过。",
                )
            else:
                ui_theme.msg_warn(
                    self,
                    "已保存",
                    "配置已写入本机，但连接验证未通过，暂不能进入版本页。\n"
                    "请检查网络与 Key 后再次点击「保存」。",
                )
        else:
            ui_theme.msg_info(
                self,
                "已保存",
                "API 配置已保存到本机。（当前无可用 Key：进入版本页时会提示填写。）",
            )

    def _refresh_home_progress_labels(self) -> None:
        """主页按钮展示「已勾选 / 左侧全部复选框」计数（见 sections_loader）。"""
        active_versions = 0
        total_num = 0
        total_den = 0
        progress_rows: list[tuple[str, int, int, float]] = []
        for vid, btn in self._home_version_buttons:
            state = data_manager.load_version_state(vid)
            den = sections_loader.progress_denominator(vid)
            num = sections_loader.progress_numerator(state, vid)
            total_num += num
            total_den += den
            if num > 0:
                active_versions += 1
            ratio = (num / den) if den else 0.0
            progress_rows.append((vid, num, den, ratio))
            progress_text = f"进度：{num}/{den}"
            self._home_version_progress_labels[vid].setText(progress_text)
            if num > 0:
                btn.setText("继续上次进度")
                self._home_version_hint_labels[vid].setText("下一步：继续已完成章节后的任务")
            else:
                btn.setText("从第一章开始")
                self._home_version_hint_labels[vid].setText("下一步：从第一章开始")

        self._today_goal_label.setText(
            f"今日目标：再完成 1 个叶子任务（总进度 {total_num}/{total_den}）"
        )
        self._activity_label.setText(f"学习活跃度：{active_versions} 个版本已开启")
        unfinished = [row for row in progress_rows if row[1] < row[2]]
        if unfinished:
            started_unfinished = [row for row in unfinished if row[1] > 0]
            if started_unfinished:
                # 已开始且未完成：优先推荐完成度更高的进行中版本。
                best_vid, _num, _den, _ratio = max(
                    started_unfinished, key=lambda x: (x[3], x[1], -x[2])
                )
            else:
                # 都未开始：保持版本顺序，推荐第一个未开始版本。
                best_vid = unfinished[0][0]
            best_label = next(l for v, l in VERSION_ENTRIES if v == best_vid)
            self._recommended_version_id = best_vid
            self._last_focus_label.setText(f"建议下一步：优先推进 {best_label}")
            self._recommended_btn.setText(f"继续推荐版本：{best_label}")
            self._recommended_btn.setEnabled(True)
            return

        # 全部完成：显示完成态文案，不再重复提示继续某个版本。
        if self._last_opened_version_id is not None and any(
            vid == self._last_opened_version_id for vid, _num, _den, _ratio in progress_rows
        ):
            self._recommended_version_id = self._last_opened_version_id
        elif progress_rows:
            review_vid, _num, _den, _ratio = max(
                progress_rows, key=lambda x: (x[1], x[3], -x[2])
            )
            self._recommended_version_id = review_vid
        else:
            self._recommended_version_id = None
        self._last_focus_label.setText("建议下一步：全部版本已完成，可复盘任意版本。")
        self._recommended_btn.setText("全部完成，回顾任意版本")
        self._recommended_btn.setEnabled(self._recommended_version_id is not None)

    def _open_version(self, version_id: str) -> None:
        """响应主页按钮：切换到对应版本的 VersionPage（必要时先创建）。"""
        self._apply_api_settings_from_disk()
        if not ai_coach.has_api_key():
            ui_theme.msg_info(
                self,
                "需要 API Key",
                "请先在主页顶部填写 API Key，并点击「保存」完成验证后再进入版本。",
            )
            return
        if not self._api_verified_ok:
            ui_theme.msg_info(
                self,
                "请完成验证",
                "请先点击「保存」并等待 API 连接验证通过后再进入版本。\n"
                "若刚启动应用，请等待自动验证结束或重新保存一次。",
            )
            return
        # version_id 与 VERSION_ENTRIES、prompts、JSON 中的键一致，例如 "version1"
        if version_id not in self._version_pages:
            page = VersionPage(version_id)
            # 用户在该页点「← 返回主页」时，VersionPage 发射 back_requested；这里订阅并转到首页
            page.back_requested.connect(self._go_home)
            page.version_records_cleared.connect(self._on_version_records_cleared)
            self._version_pages[version_id] = page
            # 为新页面分配栈中的下一个索引（跟在已有所有页后面）；索引 0 永远是主页
            self._stack.addWidget(page)

        # 已创建则直接切换可见页；setCurrentWidget 不重复添加控件，仅改变当前显示的子控件
        self._stack.setCurrentWidget(self._version_pages[version_id])
        self._last_opened_version_id = version_id
        self._version_pages[version_id].refresh_bootstrap()

    def _go_home(self) -> None:
        """
        槽函数：由 VersionPage 的 back_requested 触发，回到主页。

        setCurrentIndex(0) 依赖 __init__ 中「第一个 addWidget 是 home」的约定；
        若将来调整 addWidget 顺序，必须同步修改这里的索引或改用按对象切换。
        """
        self._stack.setCurrentIndex(0)
        self._refresh_home_progress_labels()

    def _on_version_records_cleared(self, _version_id: str) -> None:
        self._refresh_home_progress_labels()
