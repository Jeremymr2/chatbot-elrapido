import telebot
from telebot.types import ForceReply
from datetime import datetime, timedelta
from dateutil import parser
import os
import re
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN_BOT")
TOKEN_CONSULTA = os.getenv("TOKEN_API")

BASE_URL = os.getenv("BASE_URL")

headers = {
    "Authorization": TOKEN_CONSULTA
    }


dir_path = os.path.dirname(os.path.realpath(__file__))
logs_dir = os.path.join(dir_path, "logs")
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)
log_filename = os.path.join(logs_dir, f"{datetime.today().date()}_pedidos.txt")
logging.basicConfig(filename=log_filename, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(TOKEN)

# Fecha
now = datetime.now()
date = now
date_one = now + timedelta(days=1)
date_two = now + timedelta(days=2)
date_three = now + timedelta(days=3)
date_four = now + timedelta(days=4)
date_five = now + timedelta(days=5)
array_dates = [date.date(), date_one.date(), date_two.date(), date_three.date(), date_four.date()]

# Hora
# Hora de inicio
hora_inicio = datetime.strptime("05:00", "%H:%M")

# Lista para almacenar las horas
horas = []

boleta = {}
_dnis = 1

# Agregar las horas al arreglo hasta las 10:00 pm
while hora_inicio.time() <= datetime.strptime("22:00", "%H:%M").time():
    horas.append(hora_inicio.strftime("%H:%M"))
    hora_inicio += timedelta(minutes=45)

hora = now.hour
saludo = "Hola, soy ElRapido_bot, un servicio de atención al cliente. Puedo ayudarte a resolver dudas y realizar reserva de pasajes.\n"

asientos = 0

@bot.message_handler(commands=['start', 'ayuda', 'Ayuda', 'Start'])
def send_welcome(message):
    bot.reply_to(
        message, saludo + "\n" +
        "Estos son algunos comandos que puedes usar\n"
        "/informacion - Información\n"
        "/reserva - Reserva\n"
    )


@bot.message_handler(commands=['informacion','información','Informacion','Información','INFORMACION','INFORMACIÓN'])
def informacion(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    bot.send_message(message.chat.id, "¿Qué desea saber?", reply_markup=markup)


@bot.message_handler(commands=['reserva','Reserva','RESERVA','reservar','Reservar','RESERVAR'])
def reserva(message):
    # markup = ForceReply()
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for date in array_dates:
        markup.add(telebot.types.KeyboardButton(f"{date}"))
    msg = bot.send_message(message.chat.id, "¿En qué fecha va a reservar?", reply_markup=markup)
    bot.register_next_step_handler(msg, definir_hora)

def definir_hora(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)

    if is_date(message.text) and is_valid_date(message.text):
        if datetime.strptime(message.text, "%Y-%m-%d").date() in array_dates:
            boleta[message.chat.id] = {}
            boleta[message.chat.id]["dni_pasajeros"] = []
            boleta[message.chat.id]["nombre_pasajeros"] = []
            # Almacenando fecha en la boleta
            boleta[message.chat.id]["fecha"] = message.text
            # print("Fecha: ",boleta[message.chat.id]["fecha"])
            # Agregando horas al markup
            for hora in horas:
                markup.add(telebot.types.KeyboardButton(f"{hora}"))
            
            msg = bot.send_message(message.chat.id, f"¿En qué horario desea reservar?", reply_markup=markup)
            bot.register_next_step_handler(msg,definir_numAsientos)
        else:
            for date in array_dates:
                markup.add(telebot.types.KeyboardButton(f"{date}"))
            msg = bot.send_message(message.chat.id, "La fecha es incorrecta. \n¿Qué fecha va a reservar?", reply_markup=markup)
            bot.register_next_step_handler(msg,definir_hora)

def definir_numAsientos(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    if validar_formato_hora(message.text):
        if message.text in horas:
            # Almacenando hora en la boleta
            boleta[message.chat.id]["hora"] = message.text
            msg = bot.send_message(message.chat.id, f"¿Cuántos asientos desea reservar?")
            bot.register_next_step_handler(msg,definir_dni)
            # print("Hora: ",boleta[message.chat.id]["hora"])
        else:
            for hora in horas:
                markup.add(telebot.types.KeyboardButton(f"{hora}"))
            msg = bot.send_message(message.chat.id, f"Ese horario no está disponible. \n¿En qué horario desea reservar?", reply_markup=markup)
            bot.register_next_step_handler(msg,definir_numAsientos)
    else:
        for hora in horas:
                markup.add(telebot.types.KeyboardButton(f"{hora}"))
        msg = bot.send_message(message.chat.id, "La hora seleccionada es incorrecta. \n¿En qué horario desea reservar?", reply_markup=markup)
        bot.register_next_step_handler(msg,definir_numAsientos)


def definir_dni(message):
    global _dnis, asientos
    if not message.text.isdigit():
        markup = ForceReply()
        msg = bot.send_message(message.chat.id, "Error: Debes indicar un número. \n¿Cuántos asientos desea reservar?")
        bot.register_next_step_handler(msg,definir_dni)
    else:
        if validar_dni_pasajeros(message.text):
                asientos = int(message.text)
                #print("Asientos: ", asientos)
                _dnis = 1
                msg = bot.send_message(message.chat.id, f"Digite el DNI del pasajero {_dnis}")
                bot.register_next_step_handler(msg,definir_contacto)
        else:
            msg = bot.send_message(message.chat.id, "Error: La cantidad de asientos es superior a la capacidad máxima. \n¿Cuántos asientos desea reservar?")
            bot.register_next_step_handler(msg,definir_dni)


def definir_contacto(message):
    global _dnis, asientos
    if validar_dni(message.text):
        boleta[message.chat.id]["dni_pasajeros"].append(message.text)
        pasajero = consulta_dni(message.text)
        if pasajero:
            boleta[message.chat.id]["nombre_pasajeros"].append(pasajero)
            _dnis += 1
            if len(boleta[message.chat.id]["dni_pasajeros"]) < asientos :
                msg = bot.send_message(message.chat.id, f"Digite el DNI del pasajero {_dnis}")
                bot.register_next_step_handler(msg,definir_contacto)
            else:
                bot.send_message(message.chat.id, f"Dni de todos los pasajeros registrados.")
                boleta[message.chat.id]["precio"] = len(boleta[message.chat.id]["dni_pasajeros"])*20
                msg = bot.send_message(message.chat.id, f"Digite su correo de contacto")
                bot.register_next_step_handler(msg,guardar_datos)
        else:
            msg = bot.send_message(message.chat.id, f"Error: El DNI no existe. \nDigite el DNI del pasajero {_dnis}")
            bot.register_next_step_handler(msg,definir_contacto)
    else:
        msg = bot.send_message(message.chat.id, f"Error: El formato del DNI ingresado es incorrecto. \nDigite el DNI del pasajero {_dnis}")
        bot.register_next_step_handler(msg,definir_contacto)

def guardar_datos(message):
    if es_email(message.text):
        boleta[message.chat.id]["correo"] = message.text
        texto = 'Datos introducidos\n'
        texto += f'<code>FECHA....:</code> {boleta[message.chat.id]["fecha"]}\n'
        texto += f'<code>HORA.....:</code> {boleta[message.chat.id]["hora"]}\n'
        texto += f'<code>PASAJEROS:</code> \n'
        for i, (nombre,dni) in enumerate(zip(boleta[message.chat.id]["nombre_pasajeros"],boleta[message.chat.id]["dni_pasajeros"]), start=1):
            texto += f'<code> •</code> Pasajero {i}: {nombre}({dni})\n'
        texto += f'<code>PRECIO...:</code> {boleta[message.chat.id]["precio"]}\n'
        bot.send_message(message.chat.id,texto,parse_mode='html')
        print(boleta)
    else:
        msg = bot.send_message(message.chat.id, f"Error: El formato de correo ingresado es incorrecto. \nDigite su correo de contacto")
        bot.register_next_step_handler(msg,guardar_datos)

def consulta_dni(text):
    params = {"numero":int(text)}
    response = requests.get(BASE_URL, headers=headers, params=params)
    data = response.json()
    try:
        pasajero = data.get("nombres")+' '+data.get("apellidoPaterno")+' '+data.get("apellidoMaterno")
        return pasajero
    except TypeError:
        if data["message"] == "dni no valido":
            return '_'
        else:
            return None
        
def es_email(correo):
    # Expresión regular para verificar el formato de un correo electrónico
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(patron, correo) is not None

def validar_dni(dni):
    try:
        return dni.isdigit() and contar_digitos(dni) == 8
    except ValueError:
        return False
    
def contar_digitos(numero):
    digitos = 0
    for n in numero :
        digitos += 1
    return digitos

def validar_natural(texto):
    print('validando natural')
    try:
        numero = int(texto)
        return numero
    except ValueError:
        return False

def validar_dni_pasajeros(texto):
    dni_pasajeros_maximo = 10
    try:
        numero = int(texto)
        return numero < dni_pasajeros_maximo
    except ValueError:
        return False

def validar_formato_hora(texto):
    # El patrón de expresión regular para hh:mm
    patron = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
    return re.match(patron, texto) is not None

def is_date(text):
    try:
        parser.parse(text)
        return True
    except ValueError:
        return False

def is_valid_date(text):
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False    

def validar_formato_fecha(texto):
    # El patrón de expresión regular para yyyy:mm:dd
    patron = r'^\d{4}:\d{2}:\d{2}$'
    return re.match(patron, texto) is not None

if __name__ == '__main__':
    print('[',date.time(),'] Compilando chatbot...')
    bot.infinity_polling()