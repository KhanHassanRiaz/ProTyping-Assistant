import sys
import time
import threading
import tempfile
import keyboard
import pyperclip
import os
import winsound
import pyaudio
import json
import pyttsx3
import winreg
import shutil
import difflib
import speech_recognition as sr
from vosk import Model, KaldiRecognizer, SetLogLevel
from PyQt5.QtWidgets import QApplication, QListWidget, QDialog, QVBoxLayout, QCheckBox, QPushButton, QMessageBox
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QTimer
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
import symspellpy
from symspellpy import SymSpell, Verbosity

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def speak_text(text):
    try:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass

def play_welcome_message():
    speak_text("Welcome to Pro Typing Assistant.")

threading.Thread(target=play_welcome_message, daemon=True).start()

SetLogLevel(-1)

sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

try:
    dictionary_path = os.path.join(os.path.dirname(symspellpy.__file__), "frequency_dictionary_en_82_765.txt")
    sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1)
except Exception:
    dictionary_path = get_resource_path(os.path.join("symspellpy", "frequency_dictionary_en_82_765.txt"))
    sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1)

sorted_dict_items = sorted(sym_spell.words.items(), key=lambda x: x[1], reverse=True)
common_words_list = [item[0] for item in sorted_dict_items[:25000]]

custom_map = {}
is_urdu = False
last_lang_toggle_time = 0
last_exit_time = 0
last_listen_time = 0

def get_state_folder():
    preferred_root = os.environ.get("LOCALAPPDATA")
    fallback_root = os.path.join(os.path.expanduser("~"), "AppData", "Local")
    base_root = preferred_root or fallback_root
    for candidate in (
        os.path.join(base_root, "ProTyping Assistant"),
        os.path.join(os.path.expanduser("~"), "Documents", "ProTyping Assistant"),
        os.path.join(tempfile.gettempdir(), "ProTyping Assistant"),
    ):
        try:
            os.makedirs(candidate, exist_ok=True)
            return candidate
        except Exception:
            continue
    return os.path.join(tempfile.gettempdir(), "ProTyping Assistant")

documents_folder = get_state_folder()
legacy_documents_folder = os.path.join(os.path.expanduser("~"), "Documents", "ProTyping Assistant")

custom_dict_path = os.path.join(documents_folder, "custom_dictionary.txt")
if not os.path.exists(custom_dict_path):
    legacy_custom_dict_path = os.path.join(legacy_documents_folder, "custom_dictionary.txt")
    if os.path.exists(legacy_custom_dict_path):
        try:
            shutil.copyfile(legacy_custom_dict_path, custom_dict_path)
        except Exception:
            pass
    else:
        with open(custom_dict_path, "w", encoding="utf-8") as f:
            f.write("pqs: ProQuiz Simulator\n")

instructions_dest_path = os.path.join(documents_folder, "instructions.txt")
if not os.path.exists(instructions_dest_path):
    legacy_instructions_path = os.path.join(legacy_documents_folder, "instructions.txt")
    if os.path.exists(legacy_instructions_path):
        try:
            shutil.copyfile(legacy_instructions_path, instructions_dest_path)
        except Exception:
            pass
    bundled_instructions_path = get_resource_path("instructions.txt")
    if os.path.exists(bundled_instructions_path):
        try:
            shutil.copyfile(bundled_instructions_path, instructions_dest_path)
        except Exception:
            pass
    else:
        with open(instructions_dest_path, "w", encoding="utf-8") as f:
            f.write("")

def load_custom_dict():
    global custom_map
    custom_map = {}
    if os.path.exists(custom_dict_path):
        with open(custom_dict_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip().lower()
                    val = val.strip()
                    custom_map[key] = val
                    sym_spell.create_dictionary_entry(val.lower(), 999999)
                elif line:
                    sym_spell.create_dictionary_entry(line.lower(), 999999)

load_custom_dict()

model_path = get_resource_path("model")
try:
    vosk_model = Model(model_path)
except Exception:
    vosk_model = None

is_listening = False

def offline_english_listen_loop():
    global is_listening
    if vosk_model is None:
        winsound.Beep(400, 500)
        is_listening = False
        return
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
    stream.start_stream()
    rec = KaldiRecognizer(vosk_model, 16000)
    
    last_active_time = time.time()

    while is_listening and not is_urdu:
        try:
            data = stream.read(4000, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                text = res.get("text", "")
                if text:
                    text = text.capitalize()
                    keyboard.write(text + " ")
                last_active_time = time.time()
            else:
                res = json.loads(rec.PartialResult())
                if res.get("partial", ""):
                    last_active_time = time.time()
            
            if time.time() - last_active_time > 3.5:
                if is_listening:
                    is_listening = False
                    winsound.Beep(500, 200)
                break
        except Exception:
            pass
            
    try:
        res = json.loads(rec.FinalResult())
        text = res.get("text", "")
        if text:
            text = text.capitalize()
            keyboard.write(text + " ")
    except Exception:
        pass
        
    stream.stop_stream()
    stream.close()
    p.terminate()

def online_urdu_listen_loop():
    global is_listening
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.8
    
    with sr.Microphone() as source:
        try:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception:
            pass
            
        while is_listening and is_urdu:
            try:
                audio = recognizer.listen(source, timeout=3.5, phrase_time_limit=15)
                if not is_listening:
                    break
                text = recognizer.recognize_google(audio, language="ur-PK")
                if text:
                    keyboard.write(text + " ")
            except sr.WaitTimeoutError:
                if is_listening:
                    is_listening = False
                    winsound.Beep(500, 200)
                break
            except Exception:
                pass

def listen_loop():
    if is_urdu:
        online_urdu_listen_loop()
    else:
        offline_english_listen_loop()

def toggle_listening():
    global is_listening, last_listen_time
    if keyboard.is_pressed('down'):
        return
    current_time = time.time()
    if current_time - last_listen_time < 0.5:
        return
    last_listen_time = current_time
    
    if not is_listening:
        is_listening = True
        winsound.Beep(1000, 200)
        threading.Thread(target=listen_loop, daemon=True).start()
    else:
        is_listening = False
        winsound.Beep(500, 200)

def toggle_language():
    global is_urdu, is_listening, last_lang_toggle_time
    if keyboard.is_pressed('left'):
        return
    current_time = time.time()
    if current_time - last_lang_toggle_time < 0.5:
        return
    last_lang_toggle_time = current_time
    
    was_listening = is_listening
    if is_listening:
        is_listening = False
        time.sleep(0.4)
        
    is_urdu = not is_urdu
    
    if is_urdu:
        threading.Thread(target=speak_text, args=("Switched to Urdu",), daemon=True).start()
    else:
        threading.Thread(target=speak_text, args=("Switched to English",), daemon=True).start()
        
    if was_listening:
        is_listening = True
        winsound.Beep(1000, 200)
        threading.Thread(target=listen_loop, daemon=True).start()

class SignalHelper(QObject):
    show_suggestions = pyqtSignal(list, str)
    show_settings = pyqtSignal()

def paste_text(text_to_paste):
    time.sleep(0.15)
    keyboard.release('alt')
    old_clip = pyperclip.paste()
    pyperclip.copy(text_to_paste)
    keyboard.send('ctrl+v')
    time.sleep(0.2)
    pyperclip.copy(old_clip)

class SuggestionDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProTyping Assistant")
        self.setAccessibleName("Suggestions")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.resize(300, 300)
        self.raw_word = ""
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setAccessibleName("Suggestions")
        font = self.list_widget.font()
        font.setPointSize(14)
        self.list_widget.setFont(font)
        self.list_widget.itemActivated.connect(self.accept_selection)
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
            threading.Thread(target=paste_text, args=(self.raw_word,), daemon=True).start()
        else:
            super().keyPressEvent(event)

    def accept_selection(self):
        selected_item = self.list_widget.currentItem()
        if selected_item:
            selected_word = selected_item.text()
            self.hide()
            if selected_word == "No matches found":
                threading.Thread(target=paste_text, args=(self.raw_word,), daemon=True).start()
            else:
                leading_space = self.raw_word[:len(self.raw_word)-len(self.raw_word.lstrip())]
                trailing_space = self.raw_word[len(self.raw_word.rstrip()):]
                if not trailing_space:
                    trailing_space = " "
                final_word = leading_space + selected_word + trailing_space
                threading.Thread(target=paste_text, args=(final_word,), daemon=True).start()

def get_extended_suggestions(word):
    suggestions = []
    word_lower = word.lower()
    
    if word_lower in custom_map:
        suggestions.append(custom_map[word_lower])

    prefix_matches = [w for w in common_words_list if w.startswith(word_lower)]
    for w in prefix_matches[:7]:
        if w not in suggestions:
            suggestions.append(w)

    suggestions_obj = sym_spell.lookup(word_lower, Verbosity.ALL, max_edit_distance=2, include_unknown=False)
    for suggestion in suggestions_obj[:5]:
        if suggestion.term not in suggestions:
            suggestions.append(suggestion.term)

    if len(suggestions) < 10:
        fuzzy_matches = difflib.get_close_matches(word_lower, common_words_list, n=7, cutoff=0.6)
        for w in fuzzy_matches:
            if w not in suggestions:
                suggestions.append(w)

    if not suggestions or (len(suggestions) == 1 and suggestions[0] == word_lower):
        if len(word_lower) >= 3:
            substring_matches = [w for w in common_words_list if word_lower in w]
            for w in substring_matches[:5]:
                if w not in suggestions:
                    suggestions.append(w)

    if not suggestions or (len(suggestions) == 1 and suggestions[0] == word_lower):
        suggestions = ["No matches found"]

    return suggestions[:15]

def get_clipboard_text_safely():
    raw_word = ""
    for _ in range(15):
        time.sleep(0.05)
        raw_word = pyperclip.paste()
        if raw_word.strip():
            break
    return raw_word

def on_correction_hotkey():
    time.sleep(0.4)
    keyboard.release('alt')
    old_clipboard = pyperclip.paste()
    pyperclip.copy('')
    keyboard.send('ctrl+c')
    
    raw_word = get_clipboard_text_safely()
    
    if not raw_word.strip():
        winsound.Beep(400, 300)
        pyperclip.copy(old_clipboard)
        return
        
    keyboard.send('backspace')
    pyperclip.copy(old_clipboard)
    word = raw_word.strip()
    candidates_list = get_extended_suggestions(word)
    signal_helper.show_suggestions.emit(candidates_list, raw_word)

def on_expand_shortcut():
    load_custom_dict()
    time.sleep(0.4)
    keyboard.release('alt')
    old_clipboard = pyperclip.paste()
    pyperclip.copy('')
    keyboard.send('ctrl+c')
    
    raw_word = get_clipboard_text_safely()
    
    if not raw_word.strip():
        winsound.Beep(400, 300)
        pyperclip.copy(old_clipboard)
        return
        
    word_to_check = raw_word.strip().lower()
    if word_to_check in custom_map:
        keyboard.send('backspace')
        pyperclip.copy(old_clipboard)
        expanded_text = custom_map[word_to_check]
        leading_space = raw_word[:len(raw_word)-len(raw_word.lstrip())]
        trailing_space = raw_word[len(raw_word.rstrip()):]
        if not trailing_space:
            trailing_space = " "
        final_text = leading_space + expanded_text + trailing_space
        threading.Thread(target=paste_text, args=(final_text,), daemon=True).start()
    else:
        winsound.Beep(400, 300)
        pyperclip.copy(old_clipboard)

def quit_program():
    global last_exit_time
    current_time = time.time()
    if current_time - last_exit_time < 0.5:
        return
    last_exit_time = current_time
    speak_text("exit")
    time.sleep(0.5)
    os._exit(0)

def set_autostart(enable):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "ProTypingAssistant"
    if getattr(sys, 'frozen', False):
        app_path = f'"{sys.executable}"'
    else:
        app_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
    except Exception:
        pass

def check_autostart():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "ProTypingAssistant"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False

class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings - ProTyping Assistant")
        self.setAccessibleName("ProTyping Assistant Settings")
        self.resize(400, 200)
        layout = QVBoxLayout()
        
        self.autostart_switch = QCheckBox("Start with Windows Sign-in")
        self.autostart_switch.setAccessibleName("Start with Windows Sign-in")
        self.autostart_switch.setChecked(check_autostart())
        
        self.how_to_use_button = QPushButton("How to use me")
        self.how_to_use_button.setAccessibleName("How to use me")
        self.how_to_use_button.clicked.connect(self.open_instructions)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.setAccessibleName("OK")
        self.ok_button.clicked.connect(self.apply_settings)
        
        layout.addWidget(self.autostart_switch)
        layout.addWidget(self.how_to_use_button)
        layout.addWidget(self.ok_button)
        self.setLayout(layout)

    def open_instructions(self):
        try:
            os.startfile(instructions_dest_path)
        except Exception:
            pass

    def apply_settings(self):
        set_autostart(self.autostart_switch.isChecked())
        self.hide()

def on_settings_hotkey():
    signal_helper.show_settings.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    server_name = "ProTypingAssistant_SingleInstance_Server"
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    if socket.waitForConnected(500):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("ProTyping Assistant")
        msg.setText("You can run only 1 version at a same time.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        sys.exit(0)

    server = QLocalServer()
    server.removeServer(server_name)
    server.listen(server_name)

    signal_helper = SignalHelper()
    dialog = SuggestionDialog()
    settings_dialog = SettingsDialog()
    
    def handle_new_connection():
        client_socket = server.nextPendingConnection()
        client_socket.disconnectFromServer()

    server.newConnection.connect(handle_new_connection)
    
    def handle_show_suggestions(suggestions, raw_word):
        dialog.list_widget.clear()
        dialog.list_widget.addItems(suggestions)
        dialog.raw_word = raw_word
        
        dialog.setWindowState(Qt.WindowActive)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        app.processEvents()
        
        def focus_and_select():
            dialog.list_widget.setFocus()
            if dialog.list_widget.count() > 0:
                dialog.list_widget.setCurrentRow(0)
                item = dialog.list_widget.item(0)
                if item:
                    item.setSelected(True)
            
        QTimer.singleShot(100, focus_and_select)
        
    def handle_show_settings():
        settings_dialog.autostart_switch.setChecked(check_autostart())
        settings_dialog.setWindowState(Qt.WindowActive)
        settings_dialog.show()
        settings_dialog.raise_()
        settings_dialog.activateWindow()
        settings_dialog.autostart_switch.setFocus()
        
    signal_helper.show_suggestions.connect(handle_show_suggestions)
    signal_helper.show_settings.connect(handle_show_settings)
    
    dialog.setWindowOpacity(0.0)
    dialog.list_widget.addItem("initializing")
    dialog.show()
    app.processEvents()
    
    def hide_dummy_window():
        dialog.hide()
        dialog.setWindowOpacity(1.0)
        dialog.list_widget.clear()
        handle_show_settings()
        
    QTimer.singleShot(500, hide_dummy_window)
    
    keyboard.add_hotkey('alt+f7', on_settings_hotkey)
    keyboard.add_hotkey('alt+f8', on_correction_hotkey)
    keyboard.add_hotkey('alt+f9', toggle_listening)
    keyboard.add_hotkey('alt+f10', on_expand_shortcut)
    keyboard.add_hotkey('alt+f11', toggle_language)
    keyboard.add_hotkey('alt+f12', quit_program)
        
    sys.exit(app.exec_())