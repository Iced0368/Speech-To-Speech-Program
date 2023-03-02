from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtMultimedia import *

def achromatic(ratio: float):
    ratio = max(min(ratio, 1), 0)
    v = int(255*(1-ratio))
    return QColor(v, v, v)


class CircularProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ratio = 0.0
        self.setStyleSheet("background-color:transparent;")

    def paintEvent(self, event):
        division = 16
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        start_angle = 90
        painter.setPen(QPen(achromatic(1/3), 2))
        painter.drawEllipse(QPoint(0, 0), self.width() / 2 - 2, self.height() / 2 - 2)

        for i in range(division):
            color = QColor(0, 255, 0)
            color.setHsv(102, 255, 255*(1-0.75*i/division))
            painter.setBrush(QBrush(color))

            partial_ratio = int(min(1, division*self.ratio - i))
            if self.ratio >= i / division:
                painter.drawPie(QRect(-self.width()/2+2, -self.height()/2+2, self.width()-4, self.height()-4), start_angle * 16, partial_ratio* -22.5 * 16 * 16/division)
            
            start_angle -= 360/division


class CircleButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__isDown = False

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def mousePressEvent(self, event):
        self.__isDown = True
        self.update()

    def mouseReleaseEvent(self, event):
        self.__isDown = False
        self.update()

    def isDown(self):
        return self.__isDown

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.isDown():
            brushcolor = QColor("#cce4f7")
            pencolor = QColor("#005499")
        elif self.underMouse():
            brushcolor = QColor("#e5f1fb")
            pencolor = QColor("#0078d7")
        else:
            pencolor = achromatic(1/3)
            brushcolor = achromatic(1/8)

        painter.setPen(QPen(pencolor, 2, Qt.SolidLine))
        brush = QBrush(brushcolor)

        painter.setBrush(brush)
        painter.drawEllipse(2, 2, self.width() - 4, self.height() - 4)


class MessageDelegate(QStyledItemDelegate):
    text_option: QTextOption

    def __init__(self, parent=None):
        super(MessageDelegate, self).__init__(parent)
        self.text_option = QTextOption(Qt.AlignLeft | Qt.AlignVCenter)
        self.text_option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)

    def paint(self, painter, option, index):
        text, flag = index.model().data(index, Qt.DisplayRole)

        painter.save()
        bubblerect = option.rect.adjusted(10, 10, -15, 0)
        textrect = option.rect.adjusted(20, 15, -25, -5)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(achromatic(1/6) if flag else achromatic(1/2))
        painter.drawRoundedRect(bubblerect, 10, 10)

        painter.setPen(Qt.black if flag else Qt.white)
        painter.drawText(textrect, text, self.text_option)
        painter.restore()
        
    def sizeHint(self, option, index):
        text, flag = index.model().data(index, Qt.DisplayRole)
        font = option.font
        document = QTextDocument()
        document.setDefaultFont(font)
        document.setPlainText(text)
        document.setTextWidth(option.rect.width() - 30)
        document.setDefaultTextOption(self.text_option)
        
        return QSize(document.idealWidth() + 30, document.size().height() + 15)


class ChatMessage(QAbstractListModel):
    def __init__(self, *args, todos=None, **kwargs):
        super(ChatMessage, self).__init__(*args, **kwargs)
        self.messages = [] #(text, flag)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            text = self.messages[index.row()]
            return text

    def rowCount(self, index):
        return len(self.messages)

    def add_message(self, message):
        self.messages.append(message)
        self.layoutChanged.emit()

    def update_data(self, index, data):
        self.messages[index] = data
        self.dataChanged.emit(self.index(index), self.index(index), [Qt.DisplayRole])

    def remove_data(self, index):
        self.beginRemoveRows(QModelIndex(), index, index)
        del self.messages[index]
        self.endRemoveRows()



class ChatWidget(QListView):
    def __init__(self, parent=None):
        super(ChatWidget, self).__init__(parent)

        self.setStyleSheet("background-color:white; border-radius: 10px; border:transparent;")
        self.scroll_bar = QScrollBar(self)
        self.scroll_bar.setStyleSheet(
            """
             QScrollBar:vertical {
                background: #bbbbbb;
                width: 10px;
                margin: 0px 0px 0px 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #bbbbbb;
                min-height: 20;
                border-radius: 2px;
            }
            """
        )
        self.setVerticalScrollBar(self.scroll_bar)
        
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setItemDelegate(MessageDelegate())
        self.chat_model = ChatMessage()
        self.setModel(self.chat_model)

    def send_message(self, text):
        self.chat_model.add_message(text)
        self.scrollToBottom()
