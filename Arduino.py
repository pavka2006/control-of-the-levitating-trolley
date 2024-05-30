from time import sleep
from PyQt5.uic import loadUi
from serial.tools.list_ports import comports
from sys import argv, exit
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from AdditionalFunctions import *
import subprocess
from Arduino_ui import Ui_MainWindow
from images import *


# ToDo: Дизайн - Начальное направление
# ToDo: Код - Проверить подключение


class CurrentSupplyControl:
    ui: QMainWindow
    """Дизайн главного окна"""
    message = pyqtSignal(str, str)
    """Сигнал для отправки сообщений"""
    current_supply: ResourceManager.open_resource
    """Открытый порт источника тока"""

    def block_for_supply(self):
        """Блокировка элементов управления источником тока"""
        for i in [self.ui.connectSupply, self.ui.CCSupply, self.ui.setCurrent, self.ui.offCurrent, self.ui.current]:
            i.setEnabled(False)
            i.setStyleSheet(style_sheets[0])

    def unblock_for_supply(self):
        """Разблокировка элементов управления источником тока"""
        for i in [self.ui.connectSupply, self.ui.CCSupply, self.ui.setCurrent, self.ui.offCurrent, self.ui.current]:
            i.setEnabled(True)
            i.setStyleSheet(style_sheets[0])

    def type_connect_supply(self, index):
        """
        Выбор типа подключения к источнику тока
        :param index: Номер выбранного типа
        """
        self.ui.connectSupply.setStyleSheet(style_sheets[0])
        self.ui.portSupply.clear()
        if index:
            pass
            self.ui.portSupply.setVisible(True)
            self.ui.label_12.setVisible(True)
            self.ui.label_5.setVisible(False)
            self.ui.idnSupply.setVisible(False)
            self.ui.portSupply.addItems(ResourceManager().list_resources())
        else:
            self.ui.label_12.setVisible(False)
            self.ui.portSupply.setVisible(False)
            self.ui.label_5.setVisible(True)
            self.ui.idnSupply.setVisible(True)
            self.ui.idnSupply.setText('HEWLETT-PACKARD,6671A,0,fA.03.00sA.01.06pA.02.01')

    @start_thread
    def connection_current_supply(self):
        """
        Подключение к источнику тока
        """
        self.block_for_supply()
        if len(ResourceManager().list_resources()) == 0:
            self.message.emit('Не найдено ни одного порта', 'Warning')
            self.ui.connectSupply.setEnabled(True)
            return
        elif len(self.ui.idnSupply.text()) == 0:
            self.ui.idnSupply.setStyleSheet(style_sheets[8])
            self.message.emit('Недопустимый идентификатор', 'Warning')
            self.ui.connectSupply.setEnabled(True)
            return
        if self.ui.connectArduino.isEnabled():
            list_ports = [self.ui.portSupply.currentText(),] if self.ui.typeConnectSupply.currentText() == 'Вручную' \
                else ResourceManager().list_resources()
            ic(list_ports)
            for i in list_ports:
                ic(i)
                try:
                    self.current_supply = ResourceManager().open_resource(i)
                    self.write('++eoi 1')
                    self.write("++auto 2")
                    self.write('++savecfg')
                    self.write("++addr {}".format(5))
                    answer = self.query('*IDN?')
                    if ((self.ui.typeConnectSupply.currentIndex() == 1 and self.ui.idnSupply.text() in answer) or
                            self.ui.typeConnectSupply.currentIndex() == 0):
                        self.ui.connectSupply.setStyleSheet(style_sheets[1])
                        self.ui.CCSupply.setEnabled(True)
                        ic()
                        return
                    else:
                        self.ui.idnSupply.setStyleSheet(style_sheets[8])
                        ic()
                        self.message.emit(f'Неверный идентификатор для {self.ui.portSupply.text()}', 'Warning')
                        self.current_supply.close()
                        self.ui.connectSupply.setEnabled(True)
                        return
                except errors.VisaIOError:
                    self.close_current_supply()
            ic()
            self.close_current_supply()
            self.ui.connectSupply.setStyleSheet(style_sheets[2])
            self.message.emit(f'Не удалось найти источник тока', 'Critical')
            self.ui.connectSupply.setEnabled(True)
        else:
            sleep(2)
            self.connection_current_supply()

    def close_current_supply(self):
        """Закрытие подключения к источнику тока"""
        try:
            self.current_supply.close()
        except AttributeError:
            pass

    @start_thread
    @try_visa
    def current_supply_setting(self):
        """
        Установка режима стабилизации тока
        """
        self.ui.CCSupply.setEnabled(False)
        if not int(self.query(Variables.SCPI.state)):
            # ограничиваем напряжение для перехода в режим
            self.set_voltage(0.01)
            self.set_current(0)
            self.write(Variables.SCPI.out_on)
            sleep(2)
            self.write(Variables.SCPI.volt_max)
            self.unblock_for_supply()
            self.ui.CCSupply.setStyleSheet(style_sheets[1])
        self.ui.CCSupply.setEnabled(True)

    def query(self, command: str):
        """
        Отправка команды query прибору и возврат ответа
        :param command: Сама команда
        :return: Ответ прибора
        """
        try:
            self.write(command)
            return self.current_supply.read()
        except errors.VisaIOError:
            raise errors.VisaIOError(-1073807339)

    def write(self, command: str):
        """
        Отправка команды write прибору
        :param command: Сама команда
        """
        self.current_supply.write(command)

    def set_current(self, value: float):
        """
        Установка тока
        :param value: Значение тока
        """
        self.write(f'{Variables.SCPI.set_current[0]}{value}{Variables.SCPI.set_current[1]}')

    def set_voltage(self, value: float):
        """
        Установка напряжения
        :param value: Напряжение
        """
        self.write(f'{Variables.SCPI.set_voltage[0]}{value}{Variables.SCPI.set_voltage[1]}')

    @start_thread
    def stab_current(self, value: float):
        """
        Установка тока от пользователя
        :param value: Ток от пользователя
        """
        self.set_current(value)
        sleep(1)
        if abs(self.query(Variables.SCPI.current_meas) - value) > 0.1:
            self.ui.current.setStyleSheet(style_sheets[8])
            self.message.emit(f'Не удалось установить ток {value}', 'Warning')
        else:
            self.ui.current.setStyleSheet(style_sheets[7])

    @start_thread
    def stop_visa(self):
        """
        Остановка тока
        """
        try:
            self.set_current(0)
            sleep(0.5)
            self.write(Variables.SCPI.out_off)
            self.ui.current.setStyleSheet(style_sheets[6])
            self.ui.current.setValue(0)
            try:
                self.query('IDN?')
                self.message.emit('Ток выведен из цепи', 'Information')
            except errors.VisaIOError:
                self.block_for_supply()
                self.ui.connectSupply.setStyleSheet(style_sheets[2])
                self.message.emit('Потеряна связь с источником тока', 'Critical')
                self.stop_arduino()
        except AttributeError:
            pass


class ArduinoControl:
    arduino: Serial
    """Открытый порт Arduino"""
    ui: QMainWindow
    """Дизайн главного окна"""
    message = pyqtSignal(str, str)
    """Сигнал для отправки сообщений"""
    voltages: list = []
    """Список напряжений"""
    stop_flag: bool = False
    """Флаг остановки цикла"""

    def block_for_arduino(self):
        """Блокировка элементов управления Arduino"""
        for i in [self.ui.startSide, self.ui.motion, self.ui.StartArduino, self.ui.LoadArduino]:
            i.setEnabled(False)

    def unblock_for_arduino(self):
        """Разблокировка элементов управления Arduino"""
        for i in [self.ui.startSide, self.ui.motion, self.ui.StartArduino, self.ui.LoadArduino]:
            i.setEnabled(True)

    def type_connect_arduino(self, index):
        """
        Выбор типа подключения к Arduino
        :param index: Номер выбранного типа
        """
        self.ui.connectArduino.setStyleSheet(style_sheets[0])
        self.ui.portArduino.clear()
        if index:
            self.ui.portArduino.setEnabled(True)
            self.ui.portArduino.addItems([i.description for i in comports()])
        else:
            self.ui.portArduino.setEnabled(False)

    @start_thread
    def connection_arduino(self):
        """
        Подключение к Arduino
        """
        self.block_for_arduino()
        if len(comports()) == 0:
            self.message.emit('Не найдено ни одного COM порта', 'Warning')
            self.ui.connectArduino.setEnabled(True)
            self.ui.connectArduino.setEnabled(True)
            return
        if self.ui.connectSupply.isEnabled():
            ic()
            if self.ui.typeConnectArduino.currentText() == 'Вручную':
                for i in comports():
                    d = i.description
                    ic(d)
                    if d == self.ui.portArduino.currentText():
                        if self.arduino_setting(i.device):
                            return
                        break
                self.message.emit(f'Не удалось подключиться к {self.ui.portArduino.currentText()}', 'Critical')
            else:
                list_ports = comports()
                for i in list_ports:
                    d = str(i.description)
                    ic(d)
                    if self.arduino_setting(i.device):
                        return
                ic()
                self.message.emit(f'Не удалось подключиться ни к одному порту', 'Critical')
                sleep(0.5)
            ic()
            try:
                self.arduino.close()
            except AttributeError:
                pass
            self.ui.connectArduino.setStyleSheet(style_sheets[2])
            self.ui.connectArduino.setEnabled(True)
        else:
            sleep(2)
            self.connection_arduino()

    def arduino_setting(self, port: str):
        try:
            self.arduino = Serial(port, 9600, write_timeout=1, timeout=1)
            ic()
            idn = self.query_arduino('IDN?')
            ic(idn)
            print(self.query_arduino('1'))
            if idn == 'Let\'s work!':
                ic()
                self.ui.connectArduino.setStyleSheet(style_sheets[1])
                self.unblock_for_arduino()
                return True
            else:
                ic()
                self.arduino.close()
        except SerialTimeoutException:
            self.arduino.close()
        except SerialException:
            pass

    @try_serial
    def load_script(self):
        """Загрузка скрипта на Arduino"""
        self.ui.LoadArduino.setEnabled(False)
        self.ui.StartArduino.setEnabled(False)
        Variables.setup_arduino = (f'{self.ui.motion.currentText()};'
                                   f'{0 if self.ui.startSide.isChecked() else 1};'
                                   f'{self.ui.hallCount.value()}')
        Variables.compiled_hex_path = make_sequence(*Variables.setup_arduino.split(';'))
        if not Variables.arduino_cli_path:
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            file_name, _ = QFileDialog.getOpenFileName(self, 'Выберите путь к исполняемому файлу arduino-cli',
                                                       'arduino-cli.exe', '(*.exe)', options=options)
            if file_name:
                Variables.arduino_cli_path = file_name
            else:
                self.ui.LoadArduino.setEnabled(True)
                return

        port = self.arduino.port
        board_id = self.ui.IDboard.text()
        compile_command = f"{Variables.arduino_cli_path} compile --fqbn {board_id} {Variables.compiled_hex_path}"
        result = subprocess.run(compile_command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            upload_command = (f"{Variables.arduino_cli_path} upload -p {port} --fqbn {board_id} "
                              f"{Variables.compiled_hex_path}")

            self.arduino.close()
            result = subprocess.run(upload_command, shell=True, capture_output=True, text=True)
            self.arduino = Serial(port, 9600, write_timeout=1)

            if result.returncode == 0 and self.query_arduino('Setup?') == Variables.setup_arduino:
                self.ui.StartArduino.setEnabled(True)
                self.ui.motion.setStyleSheet(style_sheets[4])
            else:
                self.ui.LoadArduino.setEnabled(True)
                self.ui.motion.setStyleSheet(style_sheets[5])
                self.message.emit('Не удалось загрузить скрипт', 'Warning')
        else:
            self.ui.LoadArduino.setEnabled(True)
            self.ui.motion.setStyleSheet(style_sheets[5])
            self.message.emit('Не удалось скомпилировать скрипт', 'Warning')

    @try_serial
    def start_sequence(self):
        """
        Запуск сценария на Arduino
        """
        self.ui.StartArduino.setEnabled(False)
        if self.ui.StartArduino.text() == 'Запустить':
            if self.ui.LoadArduino.isEnabled():
                self.load_script()
            if self.query_arduino('Start') and (self.query_arduino('Setup?') == Variables.setup_arduino):
                self.ui.StartArduino.setText('Остановить')
                self.control_sequence(*Variables.setup_arduino.split(';'))
            else:
                self.ui.LoadArduino.setEnabled(True)
                self.ui.motion.setStyleSheet(style_sheets[5])
                self.message.emit('Не удалось запустить скрипт', 'Warning')
                return
        else:
            self.stop_arduino()
            self.ui.StartArduino.setText('Запустить')
        self.ui.StartArduino.setEnabled(True)

    def write_arduino(self, command: str):
        """
        Отправка команды на Arduino
        :param command: Сама команда
        """
        try:
            self.arduino.write(command.encode('utf-8'))
        except AttributeError:
            raise SerialException()

    def query_arduino(self, command: str):
        """
        Запрос данных с Arduino
        :param command: Команда
        :return: Строка с результатом
        """
        self.write_arduino(command)
        answer = self.arduino.readline().decode('utf-8').strip()
        return answer if answer != 'Unknown command' else ''

    def get_hall_voltage(self) -> list[float]:
        """
        Получение напряжения с датчиков
        :return: Список напряжений
        """
        try:
            return list(map(float, self.query_arduino('Measure?').split(';')))
        except TypeError:
            self.message.emit('В ходе работы возникла ошибка', 'Critical')
            self.stop_arduino()

    @start_thread
    def save_voltage(self):
        """Сохранение напряжения с датчиков"""
        while not self.stop_flag:
            check = [[] for _ in range(self.ui.hallCount.value())]
            for _ in range(5):
                self.voltages = self.get_hall_voltage()
                [check[i].append(j) for i, j in enumerate(self.voltages)]
                sleep(0.025)
            for i in check:
                if max(i) - min(i) <= 10:
                    self.stop_arduino()
                    self.message.emit('Тележка остановилась', 'Warning')
                    break
        self.stop_arduino()

    @start_thread
    def control_sequence(self, mode: str, side: str | int, count: int | str):
        """
        Исполнение сценария на Arduino
        :param mode: Режим работы
        :param side: Сторона: 0 - сначала, 1 - с конца
        :param count: Число датчиков
        """
        count, side = int(count), int(side)
        self.save_voltage()
        sleep(0.1)
        mode = 1 if mode == 'Ускорение' else -1 if mode == 'Торможение' else 0
        current_coil = count * side + 1
        self.write_arduino(f'Coil:ON {current_coil-1} {mode}')
        while not self.stop_flag:
            if current_coil > self.ui.hallCount.value():
                self.stop_arduino()
                break
            current_coil += pow(-1, side)
            # Отслеживаем приближение к следующему датчику
            while abs(self.voltages[current_coil-1] - Variables.halls_zeros[current_coil-1]) < 100:
                if self.stop_flag:
                    return
                sleep(0.025)
            self.write_arduino(f'Coil:ON {current_coil-1} {mode}')
            self.write_arduino(f'Coil:OFF {current_coil-1}')

    @start_thread
    def stop_arduino(self):
        """Остановка работы с Arduino"""
        try:
            self.stop_flag = True
            if self.query_arduino('Stop') and self.arduino:
                self.message.emit('Arduino завершил работу', 'Information')
                return
        except SerialTimeoutException:
            self.message.emit('Потеряна связь с Arduino', 'Critical')
            self.arduino.close()
        except SerialException:
            pass
        finally:
            self.block_for_arduino()
            self.ui.connectArduino.setStyleSheet(style_sheets[2])
            self.stop_visa()


class ArduinoMain(QMainWindow, ArduinoControl, CurrentSupplyControl):
    ui = Ui_MainWindow()

    def __init__(self):
        super().__init__()
        # self.ui = loadUi('Arduino.ui', self)
        self.ui.setupUi(self)
        Variables.ui = self.ui
        self.create_message()
        self.setWindowIcon(QIcon('1699267514690.ico'))
        self.setWindowTitle('Управление магнитолевитационным транспортом')
        self.ui.connectArduino.clicked.connect(lambda: self.connection_arduino())
        self.ui.typeConnectArduino.currentIndexChanged.connect(self.type_connect_arduino)
        self.ui.portArduino.currentIndexChanged.connect(lambda: self.ui.connectArduino.setStyleSheet(
            style_sheets[0]))
        self.ui.motion.currentIndexChanged.connect(lambda: self.ui.LoadArduino.setEnabled(True))
        self.ui.startSide.toggled.connect(lambda: self.ui.LoadArduino.setEnabled(True))
        self.ui.motion.currentIndexChanged.connect(lambda: self.ui.motion.setStyleSheet(style_sheets[3]))
        self.ui.startSide.toggled.connect(lambda: self.ui.motion.setStyleSheet(style_sheets[3]))
        self.ui.LoadArduino.clicked.connect(lambda: self.load_script())
        self.ui.StartArduino.clicked.connect(lambda: self.start_sequence())

        self.ui.connectSupply.clicked.connect(lambda: self.connection_current_supply())
        self.ui.typeConnectSupply.currentIndexChanged.connect(self.type_connect_supply)
        self.type_connect_supply(0)
        self.ui.portSupply.currentIndexChanged.connect(lambda: self.ui.connectArduino.setStyleSheet(
            style_sheets[0]))
        self.ui.CCSupply.clicked.connect(self.current_supply_setting)
        self.ui.setCurrent.clicked.connect(lambda: self.stab_current(self.ui.current.value()))
        self.ui.current.valueChanged.connect(lambda: self.ui.current.setStyleSheet(style_sheets[6]))
        self.ui.offCurrent.clicked.connect(lambda: self.stop_visa())
        self.ui.idnSupply.textChanged.connect(lambda: self.ui.idnSupply.setStyleSheet(style_sheets[6]))

    @pyqtSlot()
    def create_message(self):
        """Формирование сигнала сообщений"""
        self.message.connect(message_for_user)

    def closeEvent(self, event: QCloseEvent):
        """
        Закрытие окна
        """
        reply = QMessageBox.question(self, 'Закрытие программы', 'Вы уверены, что хотите закрыть программу?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.stop_visa()
            sleep(0.5)
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':
    app = QApplication(argv)
    window = ArduinoMain()
    window.show()
    exit(app.exec_())
