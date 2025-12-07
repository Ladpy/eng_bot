import os

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv, find_dotenv

import random

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from models import User, Word, UserActiveWord

load_dotenv(find_dotenv())
db_host = os.getenv("DB_HOST", default="localhost")
db_port = os.getenv("DB_PORT", default="5432")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER", default="postgres")
db_password = os.getenv("DB_PASSWORD")

DSN = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
engine = create_engine(DSN)
Session = sessionmaker(bind=engine)

bot_token = os.getenv("BOT_TOKEN")

print('Start telegram bot...')

state_storage = StateMemoryStorage()
bot = TeleBot(bot_token, state_storage=state_storage)

buttons = []


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


def is_known_user(uid):
    with Session() as session:
        users_count = session.query(User).filter(User.user_id == uid).count()
    return users_count == 1


def is_enough_words(uid):
    with Session() as session:
        words_count = session.query(UserActiveWord).filter(UserActiveWord.user_id == uid).count()
    return words_count >= 4


def is_active_word(uid, word):
    with Session() as session:
        count = session.query(UserActiveWord).filter(UserActiveWord.user_id == uid).join(Word).filter(Word.english == word).count()
        return count == 1


def add_user(uid):
    with Session() as session:
        user = User(user_id=uid)
        session.add(user)

        common_words = session.query(Word).filter(Word.owner_id.is_(None)).all()
        for word in common_words:
            active_word = UserActiveWord(user_id=uid, word_id=word.word_id)
            session.add(active_word)

        session.commit()


def get_random_words(uid):
    if not is_enough_words(uid):
        return None
    with Session() as session:
        all_words = session.query(UserActiveWord).filter(UserActiveWord.user_id == uid).all()

        word = random.choice(all_words)
        all_words.remove(word)
        target_word = word.word.english
        translate = word.word.russian

        other_words = []

        for _ in range(3):
            word = random.choice(all_words)
            all_words.remove(word)
            other_words.append(word.word.english)

    return target_word, translate, other_words


def add_word(uid, english, russian):
    with Session() as session:
        word = Word(english=english, russian=russian, owner_id=uid)
        session.add(word)
        session.commit()

        active_word = UserActiveWord(user_id=uid, word_id=word.word_id)
        session.add(active_word)
        session.commit()


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    uid = message.from_user.id
    if not is_known_user(uid):
        add_user(uid)
        bot.send_message(cid, "Hello, stranger, let study English...")

    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []
    words = get_random_words(uid)
    if not words:
        bot.send_message(cid, "Недостаточно слов! Добавьте новые слова, чтобы продолжить.")
        return
    target_word, translate, others = words
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    uid = message.from_user.id
    cid = message.chat.id
    with bot.retrieve_data(uid, cid) as data:
        with Session() as session:
            session.query(Word).filter(and_(Word.english == data['target_word'],
                                                    Word.owner_id == uid)).delete()
            word = session.query(Word.word_id) \
                .filter(Word.english == data['target_word']) \
                .filter(Word.owner_id.is_(None)) \
                .first()

            if word:
                deleted_count = session.query(UserActiveWord) \
                    .filter(UserActiveWord.word_id == word.word_id) \
                    .delete(synchronize_session=False)

            session.commit()
    bot.send_message(cid, "Слово успешно удалено!")


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def new_word(message):
    cid = message.chat.id
    msg = bot.send_message(cid,"Введите новое слово на английском:")
    bot.register_next_step_handler(msg, enter_eng_word)


def enter_eng_word(message):
    cid = message.chat.id
    uid = message.from_user.id
    if not is_active_word(uid, message.text):
        with bot.retrieve_data(uid, cid) as data:
            data['new_eng_word'] = message.text
        msg = bot.send_message(cid, "Введите перевод нового слова:")
        bot.register_next_step_handler(msg, enter_ru_word)
    else:
        msg = bot.send_message(cid, "Такое слово уже существует! Выберите другое:")
        bot.register_next_step_handler(msg, enter_eng_word)

def enter_ru_word(message):
    cid = message.chat.id
    uid = message.from_user.id
    with bot.retrieve_data(uid, cid) as data:
        add_word(uid, data['new_eng_word'], message.text)
    bot.send_message(cid, "Новое слово успешно добавлено!")


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)
