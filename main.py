"""
程序入口：启动 Qt 界面事件循环，创建并显示主窗口。

初学者可以这样理解：
1. PyQt 程序必须先有一个 QApplication（管理全局事件、字体等）。
2. 窗口要 .show() 才会出现在屏幕上。
3. app.exec() 进入「事件循环」，直到用户关闭窗口才结束；最后 sys.exit 把退出码交给操作系统。

类型标注：`from __future__ import annotations` 与其它模块一致；函数后的 `-> None` 表示「无返回值」，
仅给编辑器和类型检查器看，运行时不会执行任何额外逻辑。
"""

# 让当前文件里可以用「list[str]」这种写法标注类型（Python 3.9+ 也可不用这行；写上兼容旧习惯）
from __future__ import annotations

# 标准库：命令行参数列表（第 0 项是脚本名）；Qt 有时用它解析显示相关选项
import sys

# 第三方：QApplication 是整个图形界面程序的「总管家」，必须有且通常只有一个
from PyQt6.QtWidgets import QApplication

# 同项目：自定义的主窗口类，定义在 main_window.py 里
from main_window import MainWindow


def main() -> None:
    # 把命令行参数传给 Qt（骨架项目里参数通常只有脚本路径）
    app = QApplication(sys.argv)
    # 构造主窗口对象（内部会搭界面，但此时还未显示）
    win = MainWindow()
    # 非模态显示：窗口出现在桌面上
    win.show()
    # exec()：阻塞并处理事件循环；所有窗口关闭后返回整数退出码（通常 0 表示正常结束）
    # sys.exit(...)：把该退出码交给操作系统；不要在图形程序里省略，否则进程返回值不确定
    sys.exit(app.exec())


# Python 约定：直接运行 `python main.py` 时，模块名 __name__ 为 "__main__"，才调用 main()
# 若其它脚本 `import main`，则 __name__ 为 "main"，不会自动启动 GUI（便于测试或复用）
if __name__ == "__main__":
    main()
