import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

TOKEN = "9092555570:AAEqYgy-Lwx46Z386aSgHc6PVpEqaFvsmPY"
ADMIN_ID = 8657503976  # O'z Telegram ID raqamingiz

bot = telebot.TeleBot(TOKEN)

# Bazani yaratish
def init_db():
    conn = sqlite3.connect("movies.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            file_id TEXT,
            caption TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Asosiy pastki menyu (Reply Keyboard) - Rasmda pastda turgan tugmalar
def main_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🎦 Medialarni boshqarish")
    btn2 = types.KeyboardButton("📊 Statistika")
    btn3 = types.KeyboardButton("✉️ Xabar yuborish")
    btn4 = types.KeyboardButton("⚙️ Tizim sozlamalari")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# Medialarni boshqarish ichidagi Inline tugmalar (Rasmda chiqadigan menyu)
def media_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("🎬 Soddalashtirilgan yuklash (Video + Kod)", callback_data="sodda_yuklash")
    btn2 = types.InlineKeyboardButton("📋 Barcha medialar ro'yxati", callback_data="barcha_medialar")
    btn3 = types.InlineKeyboardButton("⬅️ Orqaga", callback_data="orqaga")
    markup.add(btn1, btn2, btn3)
    return markup

# /start komandasi
@bot.message_handler(commands=['start', 'admin'])
def send_welcome(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(
            message.chat.id,
            "🎦 **BOSHQARUV PANELIGA XUSH KELIBSIZ**\n\nKerakli bo'limni tanlang:",
            parse_mode="Markdown",
            reply_markup=main_admin_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            "Assalomu alaykum! Menga kino kodini yuboring (masalan: 2), men sizga kinoni topib beraman.",
            reply_markup=types.ReplyKeyboardRemove()
        )

# Pastki menyu tugmalari bosilganda
@bot.message_handler(content_types=['text'])
def handle_text_menu(message):
    if message.from_user.id != ADMIN_ID:
        # Oddiy foydalanuvchi kino kodi yuborganda
        if not message.text.startswith('/'):
            code = message.text.strip()
            conn = sqlite3.connect("movies.db")
            cursor = conn.cursor()
            cursor.execute("SELECT file_id, caption FROM movies WHERE code = ?", (code,))
            movie = cursor.fetchone()
            conn.close()
            if movie:
                bot.send_video(message.chat.id, movie[0], caption=movie[1])
            else:
                bot.send_message(message.chat.id, f"Siz yuborgan kod: {code} bo'yicha kino topilmadi.")
        return

    text = message.text

    if text == "🎦 Medialarni boshqarish":
        bot.send_message(
            message.chat.id,
            "🎬 **MEDIA BOSHQARUV MARKAZI**\n\nKontent yuklash yoki boshqarish usulini tanlang:",
            parse_mode="Markdown",
            reply_markup=media_inline_keyboard()
        )
    elif text == "📊 Statistika":
        conn = sqlite3.connect("movies.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM movies")
        count = cursor.fetchone()[0]
        conn.close()
        bot.send_message(message.chat.id, f"📊 **Statistika:**\n\n🎦 Bazadagi jami kinolar soni: {count} ta", parse_mode="Markdown")
    elif text == "✉️ Xabar yuborish":
        bot.send_message(message.chat.id, "📢 Hozircha bu funksiya qo'shilmagan.")
    elif text == "⚙️ Tizim sozlamalari":
        bot.send_message(message.chat.id, "⚙️ Bot holati: **Barqaror ishlayapti** (Render)", parse_mode="Markdown")
    else:
        # Agar admin shunchaki matn yuborsa (kino kodi sifatida tekshiramiz)
        code = text.strip()
        conn = sqlite3.connect("movies.db")
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, caption FROM movies WHERE code = ?", (code,))
        movie = cursor.fetchone()
        conn.close()
        if movie:
            bot.send_video(message.chat.id, movie[0], caption=movie[1])
        else:
            bot.send_message(message.chat.id, f"Siz yuborgan kod: {code} bo'yicha kino topilmadi.")

# Inline tugmalar bosilganda ishlaydigan qism
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.from_user.id != ADMIN_ID:
        return

    if call.data == "sodda_yuklash":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "📥 **Kino yuklash uchun tayyorlaning:**\nMenga kino videosini yuboring va ostiga uning **kodini** yozib yuboring (masalan: `2`).",
            parse_mode="Markdown"
        )
    elif call.data == "barcha_medialar":
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect("movies.db")
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM movies")
        movies = cursor.fetchall()
        conn.close()
        
        if movies:
            codes = ", ".join([row[0] for row in movies])
            bot.send_message(call.message.chat.id, f"📋 **Bazadagi mavjud kino kodlari:**\n\n{codes}", parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, "📋 Hozircha bazada kinolar yo'q.")
    elif call.data == "orqaga":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            "Bosh menyuga qaytdingiz.",
            call.message.chat.id,
            call.message.message_id
        )

# Admin video yuborganda bazaga saqlash
@bot.message_handler(content_types=['video', 'document'])
def save_movie_file(message):
    if message.from_user.id != ADMIN_ID:
        return

    file_id = message.video.file_id if message.video else message.document.file_id
    code = message.caption or message.text

    if not code:
        bot.reply_to(message, "⚠️ Iltimos, video bilan birga uning **kodini** ham yozib yuboring!")
        return

    clean_code = code.strip()
    conn = sqlite3.connect("movies.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO movies (code, file_id, caption)
        VALUES (?, ?, ?)
    """, (clean_code, file_id, f"Kino kodi: {clean_code}"))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"✅ **{clean_code}**-kodli kino bazaga muvaffaqiyatli saqlandi!", parse_mode="Markdown")

# Render uchun veb-server
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

bot.infinity_polling()
