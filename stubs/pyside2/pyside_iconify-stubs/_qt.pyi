"""Qt 名字的类型来源：整个包里只有这个文件写死具体的 Qt 绑定。

由 tools/gen_qt_stubs.py 生成，不要手改。
"""

from PySide2 import (
    QtCore as QtCore,
    QtGui as QtGui,
    QtWidgets as QtWidgets,
    QtNetwork as QtNetwork,
    QtSvg as QtSvg,
)
from PySide2.QtCore import (
    QByteArray as QByteArray,
    QCoreApplication as QCoreApplication,
    QEvent as QEvent,
    QEventLoop as QEventLoop,
    QObject as QObject,
    QRectF as QRectF,
    QSize as QSize,
    QStandardPaths as QStandardPaths,
    QThread as QThread,
    QTimer as QTimer,
    QUrl as QUrl,
    Qt as Qt,
)
from PySide2.QtGui import (
    QColor as QColor,
    QFontMetrics as QFontMetrics,
    QIcon as QIcon,
    QIconEngine as QIconEngine,
    QImage as QImage,
    QPaintEvent as QPaintEvent,
    QPainter as QPainter,
    QPalette as QPalette,
    QPen as QPen,
    QPixmap as QPixmap,
    QStandardItem as QStandardItem,
)
from PySide2.QtWidgets import (
    QAbstractButton as QAbstractButton,
    QAction as QAction,
    QApplication as QApplication,
    QListWidgetItem as QListWidgetItem,
    QSizePolicy as QSizePolicy,
    QStyle as QStyle,
    QStyleOption as QStyleOption,
    QTabWidget as QTabWidget,
    QTreeWidgetItem as QTreeWidgetItem,
    QWidget as QWidget,
)
from PySide2.QtNetwork import (
    QNetworkAccessManager as QNetworkAccessManager,
    QNetworkReply as QNetworkReply,
    QNetworkRequest as QNetworkRequest,
)
from PySide2.QtSvg import (
    QSvgRenderer as QSvgRenderer,
)
from PySide2.QtCore import Signal as Signal

BINDING: str
IS_QT5: bool
ENV_VAR: str

def run_event_loop(loop: QEventLoop) -> None: ...
