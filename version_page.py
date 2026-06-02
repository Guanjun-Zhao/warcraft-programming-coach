"""
版本页：左侧任务树 + 中列 code.cpp + 右侧 AI 对话区。
"""

from __future__ import annotations

import time

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from chat_widget import ChatWidget

import data_manager
import sections_loader
import ui_theme

ROLE_TASK = Qt.ItemDataRole.UserRole
ROLE_H2 = Qt.ItemDataRole.UserRole + 1
ROLE_TITLE = Qt.ItemDataRole.UserRole + 2

VERSION_LABELS = {
  "version1": "魔兽世界一 · 备战",
  "version2": "魔兽世界二 · 装备",
  "version3": "魔兽世界三 · 开战",
  "version4": "魔兽世界四 · 终极版",
}
LEFT_PANEL_MINI_WIDTH = 36


class VersionPage(QWidget):
  back_requested = pyqtSignal()
  version_records_cleared = pyqtSignal(str)

  def __init__(self, version_id: str, parent: QWidget | None = None) -> None:
    super().__init__(parent)
    self._version_id = version_id

    self.setObjectName("VersionPage")

    back = QPushButton("← 返回主页")
    back.setObjectName("SecondaryButton")
    back.clicked.connect(self.back_requested.emit)
    self._back_btn = back
    clear_btn = QPushButton("清空此版本记录")
    clear_btn.setObjectName("DangerGhostButton")
    clear_btn.clicked.connect(self._on_clear_version_records_clicked)
    self._clear_version_btn = clear_btn

    self._page_title = QLabel(VERSION_LABELS.get(version_id, version_id))
    self._page_title.setObjectName("VpTitle")
    self._page_meta = QLabel("当前任务：-")
    self._page_meta.setObjectName("VpMeta")
    self._page_progress = QLabel("进度：0/0")
    self._page_progress.setObjectName("VpProgress")

    self._task_tree = QTreeWidget()
    self._task_tree.setHeaderHidden(True)
    self._task_tree.setAnimated(True)
    self._task_tree.setIndentation(16)
    self._task_tree.itemChanged.connect(self._on_tree_item_changed)
    self._task_tree.itemExpanded.connect(self._on_item_expanded_collapsed)
    self._task_tree.itemCollapsed.connect(self._on_item_expanded_collapsed)
    self._task_tree.currentItemChanged.connect(self._on_current_leaf_changed)

    first_tid = sections_loader.first_leaf_task_id(version_id) or "task1"
    self._code_editor = QPlainTextEdit()
    self._code_editor.setFont(QFont("Courier New", 10))
    self._code_editor.setPlaceholderText("在此编辑并保存完整程序（code.cpp）…")
    self._code_editor.textChanged.connect(self._on_code_changed)
    self._code_loading = False
    self._code_title = QLabel("完整程序（code.cpp）")
    self._code_title.setObjectName("PanelTitle")
    self._code_hint = QLabel("当前建议：先在左侧选择一个叶子任务，再修改代码。")
    self._code_hint.setObjectName("MutedText")
    self._code_hint.setWordWrap(True)
    self._code_save_status = QLabel("保存状态：已加载")
    self._code_save_status.setObjectName("MutedText")

    self._chat = ChatWidget(
      version_id,
      first_tid,
      program_loader=lambda: self._code_editor.toPlainText(),
    )

    top_row = QHBoxLayout()
    title_col = QVBoxLayout()
    title_col.setSpacing(2)
    title_col.addWidget(self._page_title)
    title_col.addWidget(self._page_meta)
    top_row.addLayout(title_col, 1)
    top_row.addWidget(self._page_progress, 0, Qt.AlignmentFlag.AlignVCenter)
    top_row.addWidget(self._clear_version_btn, 0, Qt.AlignmentFlag.AlignVCenter)
    top_row.addWidget(self._back_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    left_panel = QFrame()
    left_panel.setObjectName("PanelCard")
    self._left_panel = left_panel
    left = QVBoxLayout(left_panel)
    self._left_layout = left
    left.setContentsMargins(8, 8, 8, 8)
    left.setSpacing(8)
    left_title = QLabel("任务清单")
    left_title.setObjectName("PanelTitle")
    self._left_title_label = left_title
    self._left_toggle_btn = QToolButton()
    self._left_toggle_btn.setObjectName("LeftPanelToggle")
    self._left_toggle_btn.setFixedSize(22, 22)
    self._left_toggle_btn.clicked.connect(self._toggle_left_panel)
    left_header = QHBoxLayout()
    self._left_header_layout = left_header
    left_header.setContentsMargins(2, 0, 2, 0)
    left_header.setSpacing(6)
    left_header.addWidget(left_title, 1)
    left_header.addWidget(self._left_toggle_btn, 0, Qt.AlignmentFlag.AlignRight)
    left.addLayout(left_header)
    left.addWidget(self._task_tree, 1)

    center_panel = QFrame()
    center_panel.setObjectName("PanelCard")
    center = QVBoxLayout(center_panel)
    center.setContentsMargins(14, 12, 14, 12)
    center.setSpacing(8)
    center.addWidget(self._code_title)
    center.addWidget(self._code_hint)
    center.addWidget(self._code_save_status)
    center.addWidget(self._code_editor)

    right_panel = QFrame()
    right_panel.setObjectName("PanelCard")
    right = QVBoxLayout(right_panel)
    right.setContentsMargins(14, 12, 14, 12)
    right.setSpacing(8)
    right.addWidget(self._chat)

    self._left_panel_collapsed = False
    self._suppress_next_chat_bootstrap = False
    self._left_panel_target_width = max(220, left_panel.sizeHint().width())
    self._left_panel_anim = QPropertyAnimation(self._left_panel, b"maximumWidth", self)
    self._left_panel_anim.setDuration(180)
    self._left_panel_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
    self._left_panel_anim.finished.connect(self._on_left_panel_anim_finished)
    self._sync_left_toggle_state()

    body = QHBoxLayout()
    body.setSpacing(10)
    body.addWidget(left_panel, 1)
    body.addWidget(center_panel, 2)
    body.addWidget(right_panel, 2)

    outer = QVBoxLayout(self)
    outer.setContentsMargins(14, 12, 14, 12)
    outer.setSpacing(10)
    outer.addLayout(top_row)
    outer.addLayout(body)

    self.setStyleSheet(ui_theme.version_page_stylesheet())

    self._load_code_from_disk()
    self._rebuild_task_tree()
    current = self._task_tree.currentItem()
    current_title: str | None = None
    if current is not None:
      title_raw = current.data(0, ROLE_TITLE)
      if isinstance(title_raw, str) and title_raw:
        current_title = title_raw
    self._update_page_progress_and_meta(current_title)

  def _toggle_left_panel(self) -> None:
    if self._left_panel_anim.state() == QPropertyAnimation.State.Running:
      return
    if self._left_panel_collapsed:
      self._expand_left_panel()
    else:
      self._collapse_left_panel()

  def _collapse_left_panel(self) -> None:
    cur_width = self._left_panel.width()
    if cur_width > LEFT_PANEL_MINI_WIDTH:
      self._left_panel_target_width = cur_width
    self._left_panel_collapsed = True
    self._sync_left_toggle_state()
    self._left_panel.setVisible(True)
    self._left_panel.setMinimumWidth(0)
    self._left_panel.setMaximumWidth(max(cur_width, LEFT_PANEL_MINI_WIDTH))
    self._left_panel_anim.setStartValue(max(cur_width, LEFT_PANEL_MINI_WIDTH))
    self._left_panel_anim.setEndValue(LEFT_PANEL_MINI_WIDTH)
    self._left_panel_anim.start()

  def _expand_left_panel(self) -> None:
    target = max(220, self._left_panel_target_width)
    self._left_panel_collapsed = False
    self._sync_left_toggle_state()
    self._left_panel.setVisible(True)
    self._left_panel.setMinimumWidth(0)
    self._left_panel.setMaximumWidth(LEFT_PANEL_MINI_WIDTH)
    self._left_panel_anim.setStartValue(LEFT_PANEL_MINI_WIDTH)
    self._left_panel_anim.setEndValue(target)
    self._left_panel_anim.start()

  def _on_left_panel_anim_finished(self) -> None:
    if self._left_panel_collapsed:
      self._left_panel.setVisible(True)
      self._left_panel.setMinimumWidth(LEFT_PANEL_MINI_WIDTH)
      self._left_panel.setMaximumWidth(LEFT_PANEL_MINI_WIDTH)
      self._chat.refresh_message_layout_after_host_resize()
      return
    self._left_panel.setVisible(True)
    self._left_panel.setMinimumWidth(0)
    self._left_panel.setMaximumWidth(16777215)
    self._chat.refresh_message_layout_after_host_resize()

  def _sync_left_toggle_state(self) -> None:
    if self._left_panel_collapsed:
      self._left_toggle_btn.setText("▶")
      self._left_toggle_btn.setToolTip("展开任务栏")
      self._left_title_label.setVisible(False)
      self._task_tree.setVisible(False)
      self._left_layout.setContentsMargins(5, 6, 5, 6)
      self._left_header_layout.setContentsMargins(0, 0, 0, 0)
      self._left_header_layout.setSpacing(0)
      self._left_header_layout.setStretch(0, 0)
      self._left_header_layout.setAlignment(
        self._left_toggle_btn,
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
      )
      return
    self._left_toggle_btn.setText("◀")
    self._left_toggle_btn.setToolTip("收起任务栏")
    self._left_title_label.setVisible(True)
    self._task_tree.setVisible(True)
    self._left_layout.setContentsMargins(8, 8, 8, 8)
    self._left_header_layout.setContentsMargins(2, 0, 2, 0)
    self._left_header_layout.setSpacing(6)
    self._left_header_layout.setStretch(0, 1)
    self._left_header_layout.setAlignment(
      self._left_toggle_btn,
      Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
    )

  def refresh_bootstrap(self) -> None:
    self._chat.refresh_bootstrap()

  def _on_clear_version_records_clicked(self) -> None:
    ok = ui_theme.msg_question(
      self,
      "清空此版本本地记录",
      "确定清空当前版本的本地记录吗？\n"
      "将清空任务勾选状态与全部聊天记录，且不可恢复。",
      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
      QMessageBox.StandardButton.No,
    )
    if ok != QMessageBox.StandardButton.Yes:
      return
    data_manager.clear_version_local_records(self._version_id)
    self._suppress_next_chat_bootstrap = True
    self._rebuild_task_tree()
    current = self._task_tree.currentItem()
    current_title: str | None = None
    if current is not None:
      title_raw = current.data(0, ROLE_TITLE)
      if isinstance(title_raw, str) and title_raw:
        current_title = title_raw
    self._update_page_progress_and_meta(current_title)
    self.version_records_cleared.emit(self._version_id)
    ui_theme.msg_info(self, "已清空", "当前版本本地记录已清空。")

  def _load_code_from_disk(self) -> None:
    self._code_loading = True
    self._code_editor.setPlainText(data_manager.load_version_code(self._version_id))
    self._code_loading = False

  def _on_code_changed(self) -> None:
    if self._code_loading:
      return
    self._code_save_status.setText("保存状态：编辑中…")
    data_manager.save_version_code(
      self._version_id, self._code_editor.toPlainText()
    )
    now_text = time.strftime("%H:%M:%S")
    self._code_save_status.setText(f"保存状态：已保存（{now_text}）")

  def _label_for_tree_item(
    self,
    title: str,
    completed: bool,
    is_h2: bool,
    has_history: bool,
  ) -> str:
    if is_h2:
      prefix = "章节"
      state = "已完成" if completed else "未完成"
      return f"{prefix} · {title}  [{state}]"
    if completed:
      return f"{title}  [已完成]"
    if has_history:
      return f"{title}  [进行中]"
    return f"{title}  [未开始]"

  def _refresh_tree_item_visuals(self) -> None:
    for i in range(self._task_tree.topLevelItemCount()):
      top = self._task_tree.topLevelItem(i)
      if top is None:
        continue
      self._refresh_single_item_visual(top)
      for j in range(top.childCount()):
        child = top.child(j)
        if child is not None:
          self._refresh_single_item_visual(child)

  def _refresh_single_item_visual(self, item: QTreeWidgetItem) -> None:
    tid_raw = item.data(0, ROLE_TASK)
    h2_raw = item.data(0, ROLE_H2)
    title_raw = item.data(0, ROLE_TITLE)
    tid = tid_raw if isinstance(tid_raw, str) else ""
    h2 = h2_raw if isinstance(h2_raw, str) else ""
    base_title = title_raw if isinstance(title_raw, str) and title_raw else item.text(0)
    completed = item.checkState(0) == Qt.CheckState.Checked
    has_history = bool(tid and data_manager.load_task_history(self._version_id, tid))
    item.setText(0, self._label_for_tree_item(base_title, completed, bool(h2), has_history))
    font = item.font(0)
    font.setBold(bool(h2))
    item.setFont(0, font)

  def _update_page_progress_and_meta(self, task_title: str | None) -> None:
    state = data_manager.load_version_state(self._version_id)
    den = sections_loader.progress_denominator(self._version_id)
    num = sections_loader.progress_numerator(state, self._version_id)
    self._page_progress.setText(f"进度：{num}/{den}")
    if task_title:
      self._page_meta.setText(f"当前任务：{task_title}")
    else:
      self._page_meta.setText("当前任务：请选择叶子任务继续。")

  def _rebuild_task_tree(self) -> None:
    state = data_manager.load_version_state(self._version_id)
    tree_state = sections_loader.ensure_tree_state(state)
    exp = tree_state.setdefault("h2_expanded", {})
    h2_done = tree_state.setdefault("h2_completed", {})

    self._task_tree.blockSignals(True)
    self._task_tree.clear()

    spec = sections_loader.get_version_spec(self._version_id)
    first_select: QTreeWidgetItem | None = None

    if spec.get("planning"):
      p = spec["planning"]
      it = QTreeWidgetItem([str(p.get("title", "功能设计"))])
      it.setFlags(
        Qt.ItemFlag.ItemIsUserCheckable
        | Qt.ItemFlag.ItemIsEnabled
        | Qt.ItemFlag.ItemIsSelectable
      )
      tid = str(p.get("task_id", ""))
      it.setData(0, ROLE_TASK, tid)
      it.setData(0, ROLE_H2, "")
      it.setData(0, ROLE_TITLE, str(p.get("title", "功能设计")))
      done = bool((state.get(tid) or {}).get("completed"))
      it.setCheckState(0, Qt.CheckState.Checked if done else Qt.CheckState.Unchecked)
      self._task_tree.addTopLevelItem(it)
      first_select = it

    for g in spec.get("groups") or []:
      h2_id = str(g.get("h2_id") or "")
      title = str(g.get("h2_title") or h2_id)
      parent = QTreeWidgetItem([title])
      parent.setFlags(
        Qt.ItemFlag.ItemIsUserCheckable
        | Qt.ItemFlag.ItemIsEnabled
        | Qt.ItemFlag.ItemIsSelectable
      )
      parent.setData(0, ROLE_TASK, "")
      parent.setData(0, ROLE_H2, h2_id)
      parent.setData(0, ROLE_TITLE, title)
      parent.setCheckState(
        0,
        Qt.CheckState.Checked if h2_done.get(h2_id) else Qt.CheckState.Unchecked,
      )
      self._task_tree.addTopLevelItem(parent)
      for sec in g.get("sections") or []:
        child = QTreeWidgetItem([str(sec.get("title", sec.get("task_id", "")))])
        child.setFlags(
          Qt.ItemFlag.ItemIsUserCheckable
          | Qt.ItemFlag.ItemIsEnabled
          | Qt.ItemFlag.ItemIsSelectable
        )
        ctid = str(sec.get("task_id", ""))
        child.setData(0, ROLE_TASK, ctid)
        child.setData(0, ROLE_H2, "")
        child.setData(0, ROLE_TITLE, str(sec.get("title", sec.get("task_id", ""))))
        cdone = bool((state.get(ctid) or {}).get("completed"))
        child.setCheckState(
          0, Qt.CheckState.Checked if cdone else Qt.CheckState.Unchecked
        )
        parent.addChild(child)
      parent.setExpanded(bool(exp.get(h2_id, True)))

    dt = spec.get("debug_task_id")
    if dt:
      dts = str(dt)
      dbg = QTreeWidgetItem(["Debug"])
      dbg.setFlags(
        Qt.ItemFlag.ItemIsUserCheckable
        | Qt.ItemFlag.ItemIsEnabled
        | Qt.ItemFlag.ItemIsSelectable
      )
      dbg.setData(0, ROLE_TASK, dts)
      dbg.setData(0, ROLE_H2, "")
      dbg.setData(0, ROLE_TITLE, "Debug")
      ddone = bool((state.get(dts) or {}).get("completed"))
      dbg.setCheckState(0, Qt.CheckState.Checked if ddone else Qt.CheckState.Unchecked)
      self._task_tree.addTopLevelItem(dbg)

    if self._task_tree.topLevelItemCount() == 0:
      fb = QTreeWidgetItem(["示例任务（未找到 sections.json）"])
      fb.setFlags(
        Qt.ItemFlag.ItemIsUserCheckable
        | Qt.ItemFlag.ItemIsEnabled
        | Qt.ItemFlag.ItemIsSelectable
      )
      fb.setData(0, ROLE_TASK, "task1")
      fb.setData(0, ROLE_H2, "")
      fb.setData(0, ROLE_TITLE, "示例任务（未找到 sections.json）")
      fb.setCheckState(
        0,
        Qt.CheckState.Checked
        if bool((state.get("task1") or {}).get("completed"))
        else Qt.CheckState.Unchecked,
      )
      self._task_tree.addTopLevelItem(fb)
      first_select = fb

    self._task_tree.blockSignals(False)
    self._refresh_tree_item_visuals()

    if first_select is not None:
      self._task_tree.setCurrentItem(first_select)

  def _on_tree_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
    if column != 0:
      return
    state = data_manager.load_version_state(self._version_id)
    tree_state = sections_loader.ensure_tree_state(state)
    tid_raw = item.data(0, ROLE_TASK)
    h2_raw = item.data(0, ROLE_H2)
    tid = tid_raw if isinstance(tid_raw, str) else ""
    h2 = h2_raw if isinstance(h2_raw, str) else ""
    checked = item.checkState(0) == Qt.CheckState.Checked
    if tid:
      slot = data_manager.ensure_task_state(state, tid)
      slot["completed"] = checked
    elif h2:
      tree_state.setdefault("h2_completed", {})[h2] = checked
    data_manager.save_version_state(self._version_id, state)
    self._refresh_single_item_visual(item)
    current = self._task_tree.currentItem()
    current_title: str | None = None
    if current is not None:
      title_raw = current.data(0, ROLE_TITLE)
      if isinstance(title_raw, str) and title_raw:
        current_title = title_raw
    self._update_page_progress_and_meta(current_title)

  def _on_item_expanded_collapsed(self, item: QTreeWidgetItem) -> None:
    h2_raw = item.data(0, ROLE_H2)
    h2 = h2_raw if isinstance(h2_raw, str) else ""
    if not h2:
      return
    state = data_manager.load_version_state(self._version_id)
    tree_state = sections_loader.ensure_tree_state(state)
    tree_state.setdefault("h2_expanded", {})[h2] = item.isExpanded()
    data_manager.save_version_state(self._version_id, state)

  def _on_current_leaf_changed(
    self,
    current: QTreeWidgetItem | None,
    _previous: QTreeWidgetItem | None,
  ) -> None:
    if current is None:
      return
    title_raw = current.data(0, ROLE_TITLE)
    task_title = title_raw if isinstance(title_raw, str) else current.text(0)
    tid_raw = current.data(0, ROLE_TASK)
    if not isinstance(tid_raw, str) or not tid_raw:
      self._update_page_progress_and_meta(f"{task_title}（章节分组）")
      self._code_hint.setText("当前建议：这是章节分组，请点击其中的叶子任务进入具体练习。")
      return
    do_bootstrap = not self._suppress_next_chat_bootstrap
    self._suppress_next_chat_bootstrap = False
    self._chat.set_task(tid_raw, bootstrap=do_bootstrap)
    self._update_page_progress_and_meta(task_title)
    sec = sections_loader.get_leaf_section(self._version_id, tid_raw) or {}
    desc = str(sec.get("description") or "").strip()
    if desc:
      self._code_hint.setText(f"当前建议：{desc}")
    else:
      self._code_hint.setText("当前建议：先阅读本节说明，再在中栏修改并运行代码。")
