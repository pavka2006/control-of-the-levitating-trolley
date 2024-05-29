from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QCloseEvent
from threading import Thread, current_thread
from functools import wraps
from icecream import ic
from pyvisa import ResourceManager, errors
from serial import Serial, SerialException, SerialTimeoutException
from os.path import abspath
from os import curdir, walk, mkdir

ic.configureOutput(includeContext=True)


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
        text = '\n'.join([arduino_base_script[0].replace('<number>', str(i)) for i in range(count)]) + '\n'
        text += '\n'.join([arduino_base_script[1].replace('<number>', str(i)) for i in range(2*count+2)]) + '\n'
        text += (arduino_base_script[2].replace('<amount>', str(count)) +
                 ', '.join([f'Hall_Sensor_Pin{i}' for i in range(count)]) + '};\n')
        text += (arduino_base_script[3].replace('<amount>', str(count+1)) +
                 ', '.join([f'Coil{i}' for i in range(count*2+2)]) + '};\n')
        text += arduino_base_script[4].replace('<setup>', f'{mode};{side};{count}').replace(
            '<amount>', str(count)) + '\n'
        with open(file_path, 'w') as file:
            file.write(text)
    return file_path


style_sheets = ["""QPushButton {
                    background-color: #CEFDF2;
                    border: 0.5px solid #a9bdc9;
                    padding: 3px;
                }
                QPushButton:hover {
                    background-color: #daf2e7;
                    border-color: #a9bdc9;
                }
                QPushButton:pressed {
                    background-color: #88b8b4;
                    border-color: #a9bdc9;
                    color: #e6fff5;
                }
                QPushButton:disabled {
                    color: #e6fff5;
                }""",
                """QPushButton {
                    background-color: #56f3ba;
                    border: 0.5px solid #a9bdc9;
                    padding: 3px;
                }
                QPushButton:hover {
                    background-color: #daf2e7;
                    border-color: #a9bdc9;
                }
                QPushButton:pressed {
                    background-color: #88b8b4;
                    border-color: #a9bdc9;
                    color: #e6fff5;
                }
                QPushButton:disabled {
                    color: #e6fff5;
                }""",
                """QPushButton {
                    background-color: #f35656;
                    border: 0.5px solid #a9bdc9;
                    padding: 3px;
                }
                QPushButton:hover {
                    background-color: #daf2e7;
                    border-color: #a9bdc9;
                }
                QPushButton:pressed {
                    background-color: #88b8b4;
                    border-color: #a9bdc9;
                    color: #e6fff5;
                }
                QPushButton:disabled {
                    color: #e6fff5;
                }""",
                """
                QComboBox {
                    background-color: #CEFDF2;
                    border: 0.5 px solid #a9bdc9;
                    color: #185f9e;
                    padding: 1px 2px 1px 3px;
                }
                QComboBox::item:selected {
                    background: #88b8b4;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    border-left: 1px solid #a9bdc9;
                }
                QComboBox::down-arrow {
                    border: 2px solid #a9bdc9;
                    width: 6px;
                    height: 6px;
                    background: #e6e6e6;
                }""",
                """
                QComboBox {
                    background-color: #56f3ba;
                    border: 0.5 px solid #a9bdc9;
                    color: #185f9e;
                    padding: 1px 2px 1px 3px;
                }
                QComboBox::item:selected {
                    background: #88b8b4;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    border-left: 1px solid #a9bdc9;
                }
                QComboBox::down-arrow {
                    border: 2px solid #a9bdc9;
                    width: 6px;
                    height: 6px;
                    background: #e6e6e6;
                }""",
                """
                QComboBox {
                    background-color: #f35656;
                    border: 0.5 px solid #a9bdc9;
                    color: #185f9e;
                    padding: 1px 2px 1px 3px;
                }
                QComboBox::item:selected {
                    background: #88b8b4;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    border-left: 1px solid #a9bdc9;
                }
                QComboBox::down-arrow {
                    border: 2px solid #a9bdc9;
                    width: 6px;
                    height: 6px;
                    background: #e6e6e6;
                }""",
                """
                QLineEdit, QListView, QTreeView, QTableView, QAbstractSpinBox, QSpinBox {
                    background-color: #CEFDF2;
                    color: #185f9e;
                    border: 1px solid #a9bdc9;
                }""",
                """
                QLineEdit, QListView, QTreeView, QTableView, QAbstractSpinBox, QSpinBox {
                    background-color: #56f3ba;
                    color: #185f9e;
                    border: 1px solid #a9bdc9;
                }""",
                """
                QLineEdit, QListView, QTreeView, QTableView, QAbstractSpinBox, QSpinBox {
                    background-color: #f35656;
                    color: #185f9e;
                    border: 1px solid #a9bdc9;
                }"""]


arduino_base_script = [
                        "#define Hall_Sensor_Pin<number> A<number>;"  # number - номер датчика от 0
                        "int Coil<number>=<number>;",  # number - номер транзистора от 1
                        "Halls[<amount>]={",  # amount - количество датчиков
                        "Coils[<amount>]={",  # amount - количество транзисторов
                        """
                        int state = 0;
                        int count = <amount>;
                        String receivedData;
                        
                        void setup() {
                          bool stop_flag = false;
                          Serial.begin(9600);
                        }\n
                        
                        void loop() {
                          if (Serial.available() > 0) {

                            receivedData = Serial.readString();
                            if (receivedData == "*IDN?") {
                              Serial.println("Let's work!");
                        
                            } else if (receivedData == "Start") {
                              state = 1;
                              Serial.println("Start");
                        
                            } else if (receivedData == "State?") {
                              Serial.println(String(state));
                        
                            } else if (receivedData == "MEAS?") {
                              String volt = "";
                              for(int i = 0; i < count; i++) {
                                volt += String(analogRead(Halls[i])) + " ";
                              Serial.println(volt);
                              
                            } else if (receivedData == "Setup?") {
                              Serial.println("<setup>");
                        
                            } else if (receivedData == "Stop") {
                              state = 0;
                              Serial.println("Stop");
                        
                            } else if (receivedData.indexOf("Coil:") != -1) {
                              if (receivedData.indexOf("Coil:ON") != -1) {
                                int index1 = receivedData.indexOf("ON ") + 3;
                          
                                // Извлечь первое число после "ON"
                                String strNum1 = receivedData.substring(index1, receivedData.indexOf(" ", index1));
                                int num1 = strNum1.toInt();
                                // Извлечь второе число после первого числа
                                int index2 = receivedData.indexOf(" ", index1) + 1;
                                String strNum2 = receivedData.substring(index2);
                                int num2 = strNum2.toInt();
                                digitalWrite(Coils[num1*2+num2], HIGH);
                                Serial.println(String(num1) + " " + String(num2));
                        
                              } else {
                                int index = receivedData.indexOf("OFF ") + 4;
                                // Извлечь число после "OFF"
                                String strNum = receivedData.substring(index);
                                int num = strNum.toInt();
                                digitalWrite(Coils[num1], LOW);
                                Serial.println(num);
                              }
                              
                            } else {
                              Serial.println("Unknown command");
                            }
                          }
                        }"""
                        ]
