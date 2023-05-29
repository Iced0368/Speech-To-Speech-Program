import sys, time, os
import sounddevice as sd
import numpy as np
import threading
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from sts import SpeechToSpeech, transText
from queue import Queue
from typing import Optional, Callable, List

from objects import *


def execFunc(func, *args):
    return func(*args) if func is not None else None

def AssignWidget(widget: QWidget, pos=None, size=None):
    if pos != None:
        widget.move(*pos)
    if size != None:
        widget.resize(*size)
    return widget


class AudioMeasure(threading.Thread):
    flag: bool = False
    volume: float = 0.0
    callback: Optional[Callable] = None

    def run(self):
        self.flag= True
        while True:
            if self.flag:
                stream = sd.InputStream(callback=self.audio_callback)
                with stream:
                    sd.sleep(1000)
            else:
                time.sleep(0.1)

    def audio_callback(self, indata, frames, time, status):
        volume_norm = np.linalg.norm(indata)
        self.volume = volume_norm
        execFunc(self.callback, volume_norm)

    def stop(self):
        self.flag= False


mic_image = None
view_image = None

class MicButton(CircleButton):
    _enabled: bool = True
    sts: Optional[SpeechToSpeech]

    def __init__(self, parent=None, sts=None):
        super(MicButton, self).__init__(parent)
        self.sts = sts
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.drawImage(event.rect(), mic_image[self._enabled][self.underMouse()])

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._enabled = not self._enabled
        if self._enabled:
            execFunc(self.sts.run)
        else:
            execFunc(self.sts.stop)


class SettingButton(CircleButton):
    _toggle: bool = False
    widgets: List[QWidget]
    label: QLabel

    def __init__(self, parent=None, widgets=[], label=None):
        super(SettingButton, self).__init__(parent)
        self.widgets = widgets
        self.widgets[True].setVisible(False)
        self.label = label
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.drawImage(event.rect(), view_image[self._toggle][self.underMouse()])

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self._toggle = not self._toggle
        self.toggle()


    def toggle(self):
        for widget in self.widgets:
            widget.setVisible(not widget.isVisible())
        if self._toggle:
            self.label.setText("설정")
        else:
            self.label.setText("음성 로그")



class SpeechLog(QWidget):
    sts: SpeechToSpeech
    index: int
    unrecog: Queue
    unspoken: Queue

    def __init__(self, parent=None, sts=None):
        super(SpeechLog, self).__init__(parent)
        self.resize(100, 100)
        self.sts = sts
        self.index = 0
        self._removed = 0
        self.unrecog = Queue()
        self.unspoken = Queue()

        layout = QVBoxLayout()
        layout.setSpacing(10)

        self.log = ChatWidget()
        layout.addWidget(self.log)

        input_field = QHBoxLayout()
        input_field.setSpacing(5)
        layout.addLayout(input_field)

        self.message_input = QLineEdit()
        self.send_button = QPushButton("보내기")
        input_field.addWidget(self.message_input)
        input_field.addWidget(self.send_button)

        self.message_input.setStyleSheet("border-radius: 5px; border: 1px gray solid; padding-left: 5px;")
        self.message_input.setPlaceholderText('텍스트를 직접 입력하세요.')
        self.message_input.setFixedHeight(30)

        self.send_button.setFixedSize(50, 30)
        self.send_button.setStyleSheet("color: white; border-radius: 5px; border: 1px gray solid; background-color: gray;")
        
        def sendManual():
            text = self.message_input.text()
            self.message_input.clear()
            if text == "":
                return
            self.log.send_message((text, False))
            self.sts.recognizer.queue.put(text)
            self.unrecog.put(self.index)
            self.index += 1

        def sendUnrecog():
            self.unrecog.put(self.index)
            self.log.send_message(("[...]", False))
            self.index += 1
 
        def determineText(text):
            index = self.unrecog.get()-self._removed
            if text.origin == "":
                self.log.chat_model.remove_data(index)
                self._removed += 1
            else:
                if text.origin == text.translated:
                    text = text.origin
                else:
                    text = "{}\n{}".format(text.translated, text.origin)
                self.log.chat_model.update_data(index, (text, False))
                self.unspoken.put(index)

        def speakEvent():
            index = self.unspoken.get()
            text = self.log.chat_model.messages[index][0]
            self.log.chat_model.update_data(index, (text, True))

        
        self.sts.listener.listenEvent = lambda audio: sendUnrecog()
        self.sts.recognizer.recognizeEvent = determineText
        self.sts.speaker.speakEvent = speakEvent

        self.message_input.returnPressed.connect(sendManual)
        self.send_button.clicked.connect(sendManual)

        self.setLayout(layout)


import pyaudio
import speech_recognition as sr
from googletrans import LANGUAGES

class SettingsWidget(QWidget):
    def __init__(self, parent=None, sts=None):
        super(SettingsWidget, self).__init__(parent)
   
        self.sts = sts
        self.input_combobox = QComboBox()
        self.output_combobox= QComboBox()
        self.input_combobox.currentIndexChanged.connect(self.input_device_changed)
        self.output_combobox.currentIndexChanged.connect(self.output_device_changed)

        self.input_lang_combobox = QComboBox()
        self.output_lang_combobox = QComboBox()
        self.input_lang_combobox.currentIndexChanged.connect(self.input_lang_changed)
        self.output_lang_combobox.currentIndexChanged.connect(self.output_lang_changed)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Input Device"))
        layout.addWidget(self.input_combobox)
        layout.addWidget(QLabel("Output Device"))
        layout.addWidget(self.output_combobox)

        self.input_combobox.setFixedHeight(20)
        self.output_combobox.setFixedHeight(20)


        layout.addWidget(QLabel("Input Language"))
        layout.addWidget(self.input_lang_combobox)
        layout.addWidget(QLabel("Output Language"))
        layout.addWidget(self.output_lang_combobox)

        self.input_lang_combobox.setFixedHeight(20)
        self.output_lang_combobox.setFixedHeight(20)


        self.setLayout(layout) 

        self.audio_output = QAudioOutput(None)
        self.audio_input = QAudioInput(None)

        self.update_devices()

        for key, value in LANGUAGES.items():
            self.input_lang_combobox.addItem(value, key)
            self.output_lang_combobox.addItem(value, key)

        lang_index = list(LANGUAGES.keys()).index('ko')

        self.input_lang_combobox.setCurrentIndex(lang_index)
        self.output_lang_combobox.setCurrentIndex(lang_index)
        

    def update_devices(self):
        self.input_combobox.clear()
        self.output_combobox.clear()

        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')

        for i in range(0, numdevices):
            device = p.get_device_info_by_index(i)
            if device.get('maxInputChannels') > 0:
                self.input_combobox.addItem(device.get('name'), i)
            if device.get('maxOutputChannels') > 0:
                self.output_combobox.addItem(device.get('name'), i)

        input_index = self.input_combobox.findData(p.get_default_input_device_info().get('index'))
        output_index = self.output_combobox.findData(p.get_default_output_device_info().get('index'))
        self.input_combobox.setCurrentIndex(input_index)
        self.output_combobox.setCurrentIndex(output_index)
        
        p.terminate()


    def input_device_changed(self, index):
        device_index = self.input_combobox.itemData(index)
        self.sts.listener.device_index = device_index

    def output_device_changed(self, index):
        device_index = self.output_combobox.itemData(index)
        self.sts.speaker.device_index = device_index

    def input_lang_changed(self, index):
        lang = self.input_lang_combobox.itemData(index)
        self.sts.recognizer.input_lang = lang

    def output_lang_changed(self, index):
        lang = self.output_lang_combobox.itemData(index)
        self.sts.recognizer.output_lang = lang
        self.sts.speaker.lang = lang



class STSProgram(QMainWindow):
    log: Queue[str] = Queue()
    sts: SpeechToSpeech = SpeechToSpeech(noise_cancel=False)
    audio_measure: AudioMeasure

    def __init__(self):
        super().__init__()
        self.initUI() 

    def initUI(self):

        keyword1 = ["disabled", "enabled"]
        keyword2 = ["setting", "log"]
        keyword3 = ["", "_hover"]

        global mic_image, view_image

        mic_image = [[None, None], [None, None]]
        view_image = [[None, None], [None, None]]
        
        [QImage("assets/setting.png"), QImage("assets/log.png")]

        for flag in [False, True]:
            for hovered in [False, True]:
                mic_image[flag][hovered] = QImage("assets/mic_{enable}{hover}.png".format(enable=keyword1[flag], hover=keyword3[hovered]))
                view_image[flag][hovered] = QImage("assets/{tog}{hover}.png".format(tog=keyword2[flag], hover=keyword3[hovered]))

        self.setWindowTitle('Speech-To-Speech')
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        self.setFixedWidth(300)
        self.setMinimumHeight(300)
        self.resize(300, 600)
        
        volumeBar = AssignWidget(CircularProgressBar(self), pos=(22, 20), size=(120, 120))
        micbtn = AssignWidget(MicButton(self, sts=self.sts), pos=(32, 30), size=(100, 100))
        label = AssignWidget(QLabel("음성 로그", self), pos=(19, 150), size=(262, 30))

        self.speech_log = AssignWidget(SpeechLog(self, sts=self.sts), pos=(10, 180), size=(280, 410))   
        self.settings = AssignWidget(SettingsWidget(self, sts=self.sts), pos=(10, 180), size=(self.size().width()-20, 200))
        togbtn = AssignWidget(SettingButton(self, widgets=[self.speech_log, self.settings], label=label), pos=(168, 30), size=(100, 100))
        
        
        label.setStyleSheet("font-size: 14px; font-weight: bold; color: white; border-radius: 10px; background-color: #aaaaaa;")
        label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        def volumeLink(x):
            volumeBar.ratio = min(1, x)
            if not micbtn._enabled:
                volumeBar.ratio = 0
            volumeBar.update()
    
        self.audio_measure = AudioMeasure()
        self.audio_measure.callback = volumeLink
        self.audio_measure.start()

        self.sts.set_input_lang('ko')
        self.sts.set_output_lang('ko')

        self.sts.run()
        self.show()


    def closeEvent(self, QCloseEvent):
        self.audio_measure.stop()
        self.sts.on_closing()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.speech_log.setFixedHeight(event.size().height()-190)


app = QApplication(sys.argv)
ex = STSProgram()

sys.exit(app.exec())