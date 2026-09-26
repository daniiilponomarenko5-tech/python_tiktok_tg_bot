import logging
import os
import re
import subprocess
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("8856778762:AAG849g2fecPoTVLEFa1TzgQe0dkmiSsDCw")

def is_tiktok_url(url: str) -> bool:
    tiktok_patterns = [
        r'tiktok\.com',
        r'vm\.tiktok\.com',
        r'vt\.tiktok\.com',
    ]
    return any(re.search(pattern, url) for pattern in tiktok_patterns)

async def download_tiktok_video(url: str) -> str | None:
    try:
        output_path = Path("downloads")
        output_path.mkdir(exist_ok=True)

        output_template = str(output_path / "%(id)s.mp4")

        command = [
            "yt-dlp",
            "-f", "best",
            "-o", output_template,
            url
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            timeout=60,
            text=True
        )

        if result.returncode == 0:
            files = list(output_path.glob("*.mp4"))
            if files:
                return str(files[-1])
        else:
            logger.error(f"Ошибка yt-dlp: {result.stderr}")

    except subprocess.TimeoutExpired:
        logger.error("Timeout при скачивании видео")
    except Exception as e:
        logger.error(f"Ошибка при скачивании: {e}")

    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Привет! Я бот для скачивания TikTok видео.\n\n"
        "Просто отправь мне ссылку на TikTok видео, и я скачаю его в хорошем качестве и пришлю тебе!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text

    if not is_tiktok_url(message_text):
        await update.message.reply_text(
            "❌ Это не похоже на TikTok ссылку.\n"
            "Пожалуйста, отправь правильную ссылку (например: https://vm.tiktok.com/...)"
        )
        return

    status_message = await update.message.reply_text("⏳ Загружаю видео...")

    try:
        video_path = await download_tiktok_video(message_text)

        if not video_path:
            await status_message.edit_text("❌ Не удалось скачать видео. Попробуй другую ссылку.")
            return

        file_size = os.path.getsize(video_path)

        if file_size > 2 * 1024 * 1024 * 1024:
            await status_message.edit_text("❌ Видео слишком большое (более 2GB)")
            os.remove(video_path)
            return

        await status_message.edit_text("📤 Отправляю видео...")

        with open(video_path, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file,
                caption="✅ Вот твое видео!"
            )

        os.remove(video_path)
        await status_message.delete()

    except Exception as e:
        logger.error(f"Ошибка при обработке: {e}")
        await status_message.edit_text(
            f"❌ Произошла ошибка: {str(e)[:100]}\n"
            "Попробуй позже или напиши @support"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    urls = re.findall(r'https?://\S+', update.message.text)

    if urls:
        await handle_message(update, context)

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
