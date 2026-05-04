"""
Handler untuk command /start, /help, dan /status
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.services.utils import escape_markdown

def clean(text: any) -> str:
    return escape_markdown(str(text))


WELCOME_MESSAGE = """
🔍 *Multi\\-Source OSINT Bot*

Selamat datang\\! Bot ini dapat mencari informasi dari nomor telepon menggunakan berbagai sumber \\(GetContact, Truecaller, CallApp, dll\\)\\.

*Cara Penggunaan:*
Kirim nomor telepon dalam format apapun:

• `08123456789`
• `\\+628123456789`  
• `628123456789`

*Commands:*
/start \\- Tampilkan pesan ini
/help  \\- Panduan penggunaan
/status \\- Cek status konfigurasi bot
/myid  \\- Lihat Telegram User ID Anda

⚠️ _Bot ini hanya untuk keperluan pribadi\\. Gunakan dengan bijak\\._
"""

HELP_MESSAGE = """
📖 *Panduan Penggunaan*

*1\\. Kirim Nomor Telepon*
Cukup ketik atau tempel nomor telepon yang ingin dicari\\. Bot akan otomatis mendeteksi dan memformat nomor\\.

*Format yang didukung:*
• `08123456789` \\(lokal\\)
• `\\+628123456789` \\(internasional\\)
• `62 812 345 6789` \\(dengan spasi\\)

*2\\. Tunggu Hasil*
Bot akan mencari nomor tersebut di berbagai database:
• 📛 Nama yang tersimpan
• 🏷️ Daftar tag \\(GetContact\\)
• 📱 Status dari sumber lain

*3\\. Batasan*
• API memiliki limit token harian
• Tidak semua nomor tersedia di database
• Hasil bergantung pada data yang tersedia di tiap sumber

*4\\. Perintah Admin \\(Khusus Admin\\)*
• `/set_voucher <key>` \\- Memperbarui API Key tanpa restart bot
• `/status` \\- Melihat sisa token dan statistik cache
"""


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode="MarkdownV2",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode="MarkdownV2",
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - check bot configuration & stats."""
    dp_client = context.bot_data.get("dp_client")
    cache = context.bot_data.get("cache")

    api_status = "✅ Aktif" if dp_client else "❌ Tidak aktif"

    lines = [
        "📊 *Status Bot*",
        "",
        f"• Telegram Bot: ✅ Aktif",
        f"• OSINT API: {api_status}",
    ]

    # Cache stats
    if cache:
        stats = cache.get_stats()
        lines.append(f"• Cache: ✅ Aktif")
        lines.append("")
        lines.append("📈 *Statistik:*")
        lines.append(f"  • Nomor di\\-cache: {clean(stats.get('cached_numbers', 0))}")
        lines.append(f"  • Total pencarian: {clean(stats.get('total_searches', 0))}")
        lines.append(f"  • Cache hits: {clean(stats.get('cache_hits', 0))}")
        lines.append(f"  • API calls: {clean(stats.get('cache_miss', 0))}")
    else:
        lines.append(f"• Cache: ❌ Tidak aktif")

    await update.message.reply_text(
        "\n".join(lines), parse_mode="MarkdownV2"
    )


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /myid command - show user's Telegram ID for whitelist setup."""
    user = update.effective_user
    
    # Escape dynamic values
    uid = clean(user.id)
    username = clean(user.username or 'tidak ada')
    full_name = clean(user.full_name)

    info = (
        f"👤 *Info Anda:*\n\n"
        f"• User ID: `{uid}`\n"
        f"• Username: @{username}\n"
        f"• Nama: {full_name}\n\n"
        f"_Berikan User ID ini ke admin untuk ditambahkan ke whitelist_"
    )
    await update.message.reply_text(
        info,
        parse_mode="MarkdownV2",
    )
