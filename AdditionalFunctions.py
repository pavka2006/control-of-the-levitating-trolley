from PyQt5.QtWidgets import *
from threading import Thread, current_thread
from functools import wraps
from icecream import ic
from pyvisa import ResourceManager, errors
from serial import Serial, SerialException, SerialTimeoutException
from os.path import abspath
from os import curdir, walk, mkdir

ic.configureOutput(prefix="", outputFunction=print)


class Variables:
    ui: QMainWindow
    """Дизайн приложения"""
    setup_arduino = f';;'
    """Параметры загруженного скрипта Arduino"""
    arduino_cli_path: str = ''
    """Путь к исполняемому файлу arduino-cli"""
    compiled_hex_path: str
    """Путь к скомпилированному файлу .hex"""
    halls_zeros: list = [512, 512, 512, 512]

    class SCPI(object):
        """Класс для работы с SCPI"""
        idn = '*IDN?'
        reset = "*RST"
        volt_max = 'VOLT MAX'
        out_on = 'OUTPUT:STATE ON'
        out_off = 'OUTPUT:STATE OFF'
        current_meas = 'MEAS:CURR?'
        volt_meas = 'MEAS:VOLT?'
        volt_cond = 'VOLT?'
        curr_cond = 'CURR?'
        state = "OUTPut:STATe?"
        set_current = ("CURR ", " A")
        set_voltage = ("VOLT ", " V")


def start_thread(func):
    """
    Декоратор запуска функции в отдельном потоке
    :param func: Декорируемая функция
    :return: Запущенный поток
    """
    @wraps(func)
    def wrapped(*args, **kwargs):
        return Thread(target=func, args=args, kwargs=kwargs, daemon=True).start()
    return wrapped


def try_visa(func):
    """
    Декоратор для обработки ошибок при работе с VISA
    :param func: Декорируемая функция
    :return: Результат выполнения функции
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except errors.VisaIOError:
            self.stop_visa()
    return wrapper


def try_serial(func):
    """
    Декоратор для обработки ошибок при работе с Serial
    :param func: Декорируемая функция
    :return: Результат выполнения функции
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(args)
        try:
            return func(*args, **kwargs)
        except SerialTimeoutException:
            args[0].stop_arduino()
        except SerialException:
            pass
    return wrapper


def message_for_user(text: str, type_mes='Information'):
    """
    Сообщение пользователю
    :param text: Текст сообщения
    :param type_mes: Тип сообщения: Critical, Question, Warning, Information.
    """
    print(text, type_mes)
    if 'MainThread' in str(current_thread()):
        match type_mes:
            case 'Critical':
                QMessageBox.critical(Variables.ui, 'Critical', text, QMessageBox.Ok)
            case 'Question':
                QMessageBox.question(Variables.ui, 'Question', text, QMessageBox.Ok)
            case 'Warning':
                QMessageBox.warning(Variables.ui, 'Warning', text, QMessageBox.Ok)
            case 'Information':
                QMessageBox.information(Variables.ui, 'Information', text, QMessageBox.Ok)
    else:
        ic(f'Вызов дизайна из доп потока: {text}')


# ToDo
def make_sequence(mode: str, side: str | int, count: int | str):
    """
    Создание hex-файла для работы Arduino
    :param mode: Выбранный режим работы
    :param side: Сторона запуска
    :param count: Количество датчиков Холла
    :return: Путь к созданному hex-файлу
    """
    try:
        mkdir(abspath(curdir).replace('\\', '/') + '/Scripts')
    except FileExistsError:
        pass
    file_path = abspath(curdir).replace('\\', '/') + f'/Scripts/Arduino_{mode}_{side}_{count}.hex'
    if f'Arduino_{mode}_{side}_{count}.hex' not in list(walk(abspath(curdir).replace('\\', '/') + '/Scripts')):
        ...
    return file_path
