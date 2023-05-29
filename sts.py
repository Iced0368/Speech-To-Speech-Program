import os, threading, time, io
import speech_recognition as sr
import googletrans
from queue import Queue
import gtts
from playsound import playsound
from typing import Optional, Callable, Union

def execFunc(func, *args):
    return func(*args) if func is not None else None

class ListenerThread:
    pass
class RecognizeThread:
    pass
class SpeakerThread:
    pass

class ListenerThread(threading.Thread):
    noise_cancel: bool
    recognizer: RecognizeThread
    listenEvent: Optional[Callable] = None
    device_index: Optional[int] = None

    def __init__(self, recognizer, noise_cancel=False):
        super().__init__()
        self.noise_cancel = noise_cancel
        self.recognizer = recognizer
        self.event = threading.Event()
    
    def run(self) -> None:
        while True:
            if self.event.is_set():
                audio = self.listen()
                if audio != None and self.event.is_set():
                    execFunc(self.listenEvent, audio)
                    self.recognizer.put(audio)
            else:
                self.event.wait()

    def listen(self):
        #get microphone device on notebook or desk top
        listener = sr.Recognizer()
        listener.dynamic_energy_adjustment_damping=0.2
        listener.pause_threshold = 0.6
        listener.energy_threshold = 600
        
        with sr.Microphone(device_index=self.device_index) as raw_voice:
            if self.noise_cancel:
                listener.adjust_for_ambient_noise(raw_voice)
            try:
                audio = listener.listen(raw_voice, timeout=2)
                return audio
            except:
                pass
            return None


class transText:
    origin: str
    translated: str
    def __init__(self, origin, translated=None):
        self.origin = origin
        self.translated = translated

class RecognizeThread(threading.Thread):
    queue: Queue[Union[sr.AudioData, str]]
    speaker: SpeakerThread
    recognizeEvent: Optional[Callable] = None
    input_lang: str = 'ko'
    output_lang: str = 'ko'
    translator = googletrans.Translator()

    def __init__(self, speaker):
        super().__init__()
        self.speaker = speaker

    def run(self) -> None:
        self.queue = Queue()
        while True:
            audio = self.queue.get()
            if audio == None:
                self.speaker.put(None)
                break

            text = self.recognize(audio)
            if text != None:
                execFunc(self.recognizeEvent, text)
                if text.translated != "":
                    self.speaker.put(text.translated)

    def recognize(self, audio):
        text = ""
        if isinstance(audio, str):
            text = audio
        else:
            listener = sr.Recognizer()
            try:
                text = listener.recognize_google(audio, language=self.input_lang)
            except sr.UnknownValueError:
                print("could not understand audio")
                return transText("", "")
        
        text = str(text)
        if self.input_lang == self.output_lang:
            return transText(text, text)
        else:
            trans_text = self.translator.translate(text, src=self.input_lang, dest=self.output_lang).text
            return transText(text, trans_text)
    
    def put(self, audio):
        self.queue.put(audio)
        print("Put Audio")



class SpeakerThread(threading.Thread):
    queue: Queue[sr.AudioData]
    speakEvent: Optional[Callable] = None
    speak: Callable
    lang: str = 'ko'
    device_index: Optional[int] = None

    def run(self) -> None:
        self.queue = Queue()
        while True:
            text = self.queue.get()
            if text == None:
                break
            if text != None:
                execFunc(self.speakEvent)
                self.speak(text)

    def put(self, text):
        self.queue.put(text)

    def speak(self, text: str):
        filename = "assets/output.mp3"
        try:
            tts = gtts.gTTS(text=text, lang=self.lang, lang_check=False, slow=False)
            tts.save(filename)
        except gtts.tts.gTTSError:
            print("Unsupported language!")
            return
        playsound(filename)
        os.remove(filename)

class SpeechToSpeech:
    listener: ListenerThread
    recognizer: RecognizeThread
    speaker: SpeakerThread

    noise_cancel: bool

    def __init__(self, noise_cancel=False):
        self.speaker = SpeakerThread()
        self.recognizer = RecognizeThread(speaker= self.speaker)
        self.listener = ListenerThread(recognizer= self.recognizer, noise_cancel=noise_cancel)
        self.listener.start()
        self.recognizer.start()
        self.speaker.start()

    def run(self):
        print("Run!")
        self.listener.event.set()

    def stop(self):
        print("Stop!")
        self.listener.event.clear()

    def on_closing(self):
        self.stop()
        print("finish work")
        os._exit(1)
    
    def set_input_lang(self, lang):
        self.recognizer.input_lang = lang
    
    def set_output_lang(self, lang):
        self.speaker.lang = lang
        self.recognizer.output_lang = lang