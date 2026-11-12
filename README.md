# ProTyping Assistant

ProTyping Assistant is a Windows desktop typing helper that runs in the background and provides spelling suggestions, offline English voice typing, online Urdu voice typing, and custom text expansion shortcuts.

## Features

- **Word suggestions** (`Alt+F8`): Select a word and get correction/suggestion candidates using SymSpell, prefix/fuzzy matching, and your custom dictionary.
- **Voice typing** (`Alt+F9`): Toggle dictation mode.
  - **English (offline)** via Vosk.
  - **Urdu (online)** via Google Speech Recognition (`ur-PK`).
- **Language switching** (`Alt+F11`): Switch between English and Urdu voice modes with spoken feedback.
- **Custom word expansion** (`Alt+F10`): Expand short codes from `custom_dictionary.txt` into full phrases.
- **Settings dialog** (`Alt+F7`): Configure "Start with Windows" and open instructions.
- **Exit** (`Alt+F12`): Quit the assistant.

## How it works

- Built with **Python + PyQt5** for the UI/dialogs.
- Uses **keyboard** hooks for global hotkeys and clipboard-based text replacement.
- Uses **SymSpell** for spelling suggestions and **Vosk** for offline English speech recognition.
- Stores user-specific state (custom dictionary, voice corrections, instructions copy, pid) under a local app data folder (e.g. `%LOCALAPPDATA%\ProTyping Assistant`).

## Project structure

- `main.py` — main application logic (hotkeys, suggestions, voice typing, settings).
- `instructions.txt` — end-user usage guide (English and Roman Urdu).
- `file_version_info.txt` — Windows version info for packaged executable.
- `ProTyping Assistant.spec` — PyInstaller spec/build configuration.
- `.gitignore` — excludes build artifacts, binaries, models, and local packaging assets.

> Note: Large/binary assets such as the Vosk `model/`, packaged executables/installers, and icon files are intentionally excluded from source control by `.gitignore`.

## Requirements

Typical dependencies include:

- PyQt5
- keyboard
- pyperclip
- pyaudio
- pyttsx3
- SpeechRecognition
- vosk
- symspellpy

(Install according to your environment; some packages like `pyaudio` and global `keyboard` hooks may require Windows-specific setup.)

## Running from source

```bash
python main.py
```

Run on Windows. The app starts in the background and shows a settings dialog on startup.

## Building (Windows)

An example PyInstaller command used for packaging:

```bash
pyinstaller --noconsole --onefile --name="ProTyping Assistant" --icon="icon.ico" --version-file="file_version_info.txt" --add-data "model;model" --add-data "instructions.txt;." --collect-all vosk --collect-all symspellpy --collect-all pyttsx3 --collect-all keyboard --collect-all pyperclip --collect-all pyaudio --collect-all speech_recognition main.py
```

## Custom dictionary & voice corrections

The app creates/uses editable files in its state folder:

- `custom_dictionary.txt` — map short codes to expanded text, e.g. `PK: Pakistan`
- `voice_corrections.txt` — map misheard phrases/words to corrected output

## License

No license file is included in this repository.
