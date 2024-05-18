import time
import logging
import paramiko
import re, os
import psycopg2
from dotenv import load_dotenv
from telegram import Update, ForceReply, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from psycopg2 import Error
from pathlib import Path

load_dotenv()

TOKEN = os.getenv('TOKEN')

RM_HOST = os.getenv('RM_HOST')
RM_PORT = os.getenv('RM_PORT')
RM_USER = os.getenv('RM_USER')
RM_PASSWORD = os.getenv('RM_PASSWORD')

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_DATABASE = os.getenv('DB_DATABASE')



client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())


# Подключаем логирование
logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def db_request(req):
    connection = None
    res = None

    try:
        connection = psycopg2.connect(user=DB_USER,
                                      password=DB_PASSWORD,
                                      host=DB_HOST,
                                      port=DB_PORT,
                                      database=DB_DATABASE)

        cursor = connection.cursor()
        cursor.execute(req)
        res = cursor.fetchall()

    except (Exception, Error) as error:
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()
            return res
        return False


def db_insert(req):
    connection = None
    res = None

    try:
        connection = psycopg2.connect(user=DB_USER,
                                      password=DB_PASSWORD,
                                      host=DB_HOST,
                                      port=DB_PORT,
                                      database=DB_DATABASE)

        cursor = connection.cursor()
        cursor.execute(req)
        connection.commit()

    except (Exception, Error) as error:
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()
            return True



def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name}!')

def helpCommand(update: Update, context):
    update.message.reply_text('Help!')

#Находим
def find_phone_numbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')

    return 'find_phone_numbers'

def find_phone_numbers(update: Update, context):
    global foundedPhones
    user_input = update.message.text

    phoneNumRegexs = [
        re.compile(r'8 \(\d{3}\) \d{3}-\d{2}-\d{2}'),    # формат 8 (000) 000-00-00
        re.compile(r'\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}'),  # формат +7 (000) 000-00-00
        re.compile(r'8\d{10}'),                          # формат 80000000000
        re.compile(r'\+7\d{10}'),                        # формат +70000000000
        re.compile(r'8\(\d{3}\)\d{7}'),                  # формат 8(000)0000000
        re.compile(r'\+7\(\d{3}\)\d{7}'),                # формат +7(000)0000000
        re.compile(r'8 \d{3} \d{3} \d{2} \d{2}'),        # формат 8 000 000 00 00
        re.compile(r'\+7 \d{3} \d{3} \d{2} \d{2}'),      # формат +7 000 000 00 00
        re.compile(r'8 \(\d{3}\) \d{3} \d{2} \d{2}'),    # формат 8 (000) 000 00 00
        re.compile(r'\+7 \(\d{3}\) \d{3} \d{2} \d{2}'),  # формат +7 (000) 000 00 00
        re.compile(r'8-\d{3}-\d{3}-\d{2}-\d{2}'),        # формат 8-000-000-00-00
        re.compile(r'\+7-\d{3}-\d{3}-\d{2}-\d{2}')       # формат +7-000-000-00-00
    ]

    phone_numbersList = [] # Ищем номера телефонов
    for i in phoneNumRegexs:
        phone_numbersList.extend(i.findall(user_input))
    if not phone_numbersList:
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END

    phone_numberss = ''
    for i in range(len(phone_numbersList)):
        phone_numberss += f'{i+1}. {phone_numbersList[i]}\n'

    update.message.reply_text(phone_numberss)
    foundedPhones = phone_numbersList
    update.message.reply_text("Вы хотите сохранить найденные номера в базу? Напишите <yes> или <y>, для сохранения")

    return 'add_phone_number'

def add_phone_number(update: Update, context):
    user_input = update.message.text
    if user_input == 'yes' or user_input == 'y':
        res = ''
        for i in foundedPhones:
            res += "('" + i + "')" + ','
        res = res[:-1:]

        if db_insert('INSERT INTO phone_numbers (phone_number) values ' + res + ';'):
            update.message.reply_text("Номера телефонов успешно сохранены!")
        else: update.message.reply_text("ERROR Номера телефонов  НЕ сохранены!")
    else:
        update.message.reply_text("Данные не сохранены")

    return ConversationHandler.END

def find_emailCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска адреса почты: ')

    return 'find_email'

def find_email(update: Update, context):
    global foundedEmails

    user_input = update.message.text

    emailRegex = re.compile(r'\b[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+)*' \
                            r'@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b')

    emailList = emailRegex.findall(user_input)
    if not emailList:
        update.message.reply_text('Email-адреса не найдены')
        return ConversationHandler.END

    email = ''
    for i in range(len(emailList)):
        email += f'{i+1}. {emailList[i]}\n'

    update.message.reply_text(email)
    foundedEmails = emailList
    update.message.reply_text("Вы хотите сохранить найденные адреса в базу? Напишите <yes> или <y>, для сохранения")

    return 'add_Email'

def add_Email(update: Update, context):
    user_input = update.message.text
    if user_input == 'yes' or user_input == 'y':
        res = ''
        for i in foundedEmails:
            res += "('" + i +"')" + ','
        res = res[:-1:]

        if db_insert('insert into emails (email) values ' + res + ';'):
            update.message.reply_text("Email-адреса успешно сохранены!")
        else: update.message.reply_text("ERROR Email-адреса не сохранены!")
    else:
        update.message.reply_text("Email-адреса не сохранены")

    return ConversationHandler.END

def get_emails(update: Update, context):
    res = db_request("SELECT * FROM emails;")
    for row in res:
        update.message.reply_text(row)

def get_phone_numbers(update: Update, context):
    res = db_request("SELECT * FROM phone_numbers;")
    for row in res:
        update.message.reply_text(row)

#Проверяющие
def verify_password_command(update: Update, context):
    update.message.reply_text('Введите текст проверки пароля: ')

    return 'verify_password'

def verify_password(update: Update, context):
    user_input = update.message.text

    regExps = [
        re.compile(r'\S{8,}'),
        re.compile(r'[A-Z]'),
        re.compile(r'[a-z]'),
        re.compile(r'\d'),
        re.compile(r'[\!\@\#\$\%\^\&\*\(\)\.]')
    ]
    for i in regExps:
        if not i.search(user_input):
            update.message.reply_text('Пароль простой')
            return ConversationHandler.END
    update.message.reply_text('Пароль сложный')
    return ConversationHandler.END



#Повторитель
def echo(update: Update, context):
    update.message.reply_text(update.message.text)

#Антиспам
def bigsms(update: Update, text: str, max_length=4096, delay=0.5):
    parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    for part in parts:
        update.message.reply_text(part)
        time.sleep(delay)

# Блоки создаем TODO
def get_release(update: Update, context):
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command('lsb_release -a')
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    update.message.reply_text(data)
    return ConversationHandler.END

def get_uname(update: Update, context):
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command('uname -a')
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    update.message.reply_text(data)
    return ConversationHandler.END

def get_uptime(update: Update, context):
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command('uptime')
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    update.message.reply_text(data)
    return ConversationHandler.END

def get_df(update: Update, context):
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command('df -h')
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    update.message.reply_text(data)
    return ConversationHandler.END

def get_free(update: Update, context):
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command('free -m')
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    update.message.reply_text(data)
    return ConversationHandler.END

def get_mpstat(update: Update, context):
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command('mpstat')
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    update.message.reply_text(data)
    return ConversationHandler.END

def get_w(update: Update, context):
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command('w')
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    update.message.reply_text(data)
    return ConversationHandler.END

def get_auths(update: Update, context):
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command('last -10')
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    update.message.reply_text(data)
    return ConversationHandler.END

def get_critical(update: Update, context):
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command('journalctl -p err -b -n 5')
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    update.message.reply_text(data)
    return ConversationHandler.END

def get_ps(update: Update, context):
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command('ps aux | head -n 10')
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    update.message.reply_text(data)
    return ConversationHandler.END

def get_ss(update: Update, context):
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command('ss -tuln')
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    update.message.reply_text(data)
    return ConversationHandler.END

def get_apt(update, context):
    reply_markup = ReplyKeyboardMarkup([['Все пакеты', 'Один пакет']], one_time_keyboard=True)
    update.message.reply_text('Выберите, какую информацию вы хотите получить:', reply_markup=reply_markup)
    return 'choose_option'

def choose_option(update, context):
    option = update.message.text
    if option == 'Все пакеты':
        command = 'dpkg -l | head -n 10'
        client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
        stdin, stdout, stderr = client.exec_command(command)
        data = stdout.read().decode('utf-8')
        client.close()
        update.message.reply_text(data, reply_markup=ReplyKeyboardRemove())
    elif option == 'Один пакет':
        update.message.reply_text('Введите название пакета:')
        return 'get_specific_package'
    else:
        update.message.reply('Пожалуйста, выберите один из вариантов: "Все пакеты" или "Один пакет"')
    return ConversationHandler.END

def get_specific_package(update, context):
    package_name = update.message.text
    command = f'dpkg -l | grep {package_name}'
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command(command)
    data = stdout.read().decode('utf-8')
    client.close()
    update.message.reply_text(data, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def get_services(update: Update, context):
    client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)
    stdin, stdout, stderr = client.exec_command('systemctl list-units --type=service | head -n 10')
    
    data = stdout.read() + stderr.read()
    client.close()
    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]
    update.message.reply_text(data)
    return ConversationHandler.END

#Логи репла
def get_repl_logs(update: Update, context):
    log_file_path = Path('/var/log/postgresql/postgresql.log')

    try:
        if log_file_path.exists():
            res = ""
            line_count = 0  # Счетчик строк
            with open(log_file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    lowerLine = line.casefold()
                    if ('repl' in lowerLine) or ('репл' in lowerLine):
                        res += line.rstrip() + "\n"
                        line_count += 1  # Увеличиваем счетчик на каждой итерации
                        if line_count >= 10:  # Проверяем, достигли ли мы лимита в 10 строк
                            break  # Если да, выходим из цикла

            if res:
                bigsms(update, res)
            else:
                update.message.reply_text("Нет логов")
                logging.info("Нет логов")
        else:
            update.message.reply_text("Файла с логами не найден")
            logging.error("Файла с логами не найден")
    except Exception as e:
        update.message.reply_text(f"Ошибка при выводе логов: {str(e)}")
        logging.error(f"Ошибка при выводе логов: {str(e)}")



def main():
    updater = Updater(TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher


    # Обработчик диалога
    convHa_pdler_n= ConversationHandler(
        entry_points=[CommandHandler('find_phone_numbers', find_phone_numbersCommand)],
        states={
            'find_phone_numbers': [MessageHandler(Filters.text & ~Filters.command, find_phone_numbers)],
            'add_phone_number': [MessageHandler(Filters.text & ~Filters.command, add_phone_number)],
        },
        fallbacks=[]
    )
    convHandlerFind_email = ConversationHandler(
        entry_points=[CommandHandler('find_email', find_emailCommand)],
        states={
            'find_email': [MessageHandler(Filters.text & ~Filters.command, find_email)],
            'add_Email': [MessageHandler(Filters.text & ~Filters.command, add_Email)],
        },
        fallbacks=[]
    )
    convHandlerCheckPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verify_password_command)],
        states={
            'verify_password': [MessageHandler(Filters.text & ~Filters.command, verify_password)],
        },
        fallbacks=[]
    )
    conv_handler_get_apt = ConversationHandler(
    entry_points=[CommandHandler('get_apt_list', get_apt)],
    states={
        'choose_option': [MessageHandler(Filters.regex('^(Все пакеты|Один пакет)$'), choose_option)],
        'get_specific_package': [MessageHandler(Filters.text & ~Filters.command, get_specific_package)],
    },
    fallbacks=[]
)

    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))
    
    #Monitoring
    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_services", get_services))
    #ДАТА БЕЙЗ
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))
    dp.add_handler(CommandHandler("get_emails", get_emails))
  
    dp.add_handler(convHa_pdler_n)
    dp.add_handler(convHandlerFind_email)
    dp.add_handler(convHandlerCheckPassword)
    dp.add_handler(conv_handler_get_apt)

    # Регистрируем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Запускаем бота
    updater.start_polling()

    # Останавливаем бота при нажатии Ctrl+C
    updater.idle()


if __name__ == '__main__':
    main()
