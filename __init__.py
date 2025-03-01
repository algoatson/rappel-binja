import os
import sys
import types
import subprocess
import re

import binaryninja as bn

from PySide6.QtCore import QEvent, Qt, QThread, QProcess
from PySide6.QtWidgets import QApplication, QVBoxLayout, QPlainTextEdit, QLineEdit, QPushButton, QHBoxLayout, QLabel
from binaryninjaui import GlobalAreaWidget, GlobalArea
from binaryninja.log import log_info

# Hack required for bundled PySide6 to work with QtPy
sys.modules["PySide6.QtOpenGL"] = types.ModuleType("EmptyQtOpenGL")
sys.modules["PySide6.QtOpenGLWidgets"] = types.ModuleType("EmptyQtOpenGLWidgets")
sys.modules["PySide6.QtOpenGLWidgets"].QOpenGLWidget = types.ModuleType("EmptyQOpenGLWidget")
sys.modules["PySide6.QtPrintSupport"] = types.ModuleType("EmptyQtPrintSupport")
sys.modules["PySide6.QtPrintSupport"].QPageSetupDialog = types.ModuleType("EmptyQPageSetupDialog")
sys.modules["PySide6.QtPrintSupport"].QPrintDialog = types.ModuleType("EmptyQPageSetupDialog")
os.environ["QT_API"] = "PySide6"

class ColoredPlainTextEdit(QPlainTextEdit):
    def __init__(self):
        super().__init__()

    def append_colored_text(self, text):
        text = self.ansi_to_html(text)
        self.appendHtml(text)

    def ansi_to_html(self, text):
        colors = {
             "0": "white",
            "31": "red",
        }

        ansi_escape = re.compile(r'\033\[([0-9;]*)m')

        def replace(match):
            codes = match.group(1).split(';')
            color_code = codes[-1]
            color = colors.get(color_code)
            return f'<font color="{color}">'

        html_text = ansi_escape.sub(replace, text)
        html_text += '</font>'

        return html_text

class RappelWidget(GlobalAreaWidget):
    def __init__(self, name):
        super(RappelWidget, self).__init__(name)
        self.output = b""
        self.layout = QVBoxLayout()

        self.console_output = ColoredPlainTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("background: none; border: none; color: white;")

        self.prompt_label = QLabel(">>>")
        self.prompt_label.setStyleSheet("background: none; border: none; color: white;")

        self.console_input = QLineEdit()
        self.console_input.returnPressed.connect(self.send_input)

        self.enter_button = QPushButton("enter", self)
        self.enter_button.clicked.connect(self.send_input)

        self.input_layout = QHBoxLayout()
        self.input_layout.addWidget(self.prompt_label)
        self.input_layout.addWidget(self.console_input)
        self.input_layout.addWidget(self.enter_button)

        self.layout.addWidget(self.console_output)
        self.layout.addLayout(self.input_layout)
        self.setLayout(self.layout)

        self.process = QProcess(self)

        self.process.readyReadStandardOutput.connect(self.on_ready_read)
        self.process.readyReadStandardError.connect(self.on_ready_read)
        self.process.start("rappel")

        if not self.process.waitForStarted():
            self.console_output.appendPlainText("Error: process did not start successfully.")
            log_info("Rappel failed to start.")
            exit(-1)

        self.console_output.appendPlainText("Rappel started successfully.")
        log_info("Rappel started successfully.")


    def on_ready_read(self):
        self.output += self.process.readAllStandardOutput().data()
        error = self.process.readAllStandardError()

        if self.output:
            # this value may not be complete.
            if b"rax" in self.output and b"efl" in self.output:
                self.console_output.append_colored_text(str(self.output, encoding="utf-8"))
                self.output = b""

        if error:
            self.console_output.appendPlainText(str(error, encoding="utf-8"))

    def send_input(self):
        command = self.console_input.text()
        self.process.write(command.encode('utf-8') + b"\n")
        # clear both input and output.
        self.console_input.clear()
        self.console_output.clear()

GlobalArea.addWidget(
    lambda _: RappelWidget('Rappel Console')
)
