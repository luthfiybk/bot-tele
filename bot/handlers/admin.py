from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

# List of admin IDs (you can move this to .env later)
ADMIN_IDS = [12345678, 87654321] # Ganti dengan ID telegram Anda

async def set_voucher_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to update the global voucher value."""
    user_id = update.effective_user.id
    
    # Check if user is admin (optional, depends on security needs)
    # if user_id not in ADMIN_IDS:
    #     await update.message.reply_text("❌ Anda tidak memiliki izin untuk perintah ini.")
    #     return

    if not context.args:
        current_voucher = context.bot_data.get("dynamic_config").get_voucher()
        await update.message.reply_text(
            f"ℹ️ Voucher saat ini: `{current_voucher or 'Belum diatur'}`\n\n"
            "Gunakan: `/set_voucher <kode_baru>`",
            parse_mode="Markdown"
        )
        return

    new_voucher = context.args[0]
    dynamic_config = context.bot_data.get("dynamic_config")
    dynamic_config.set_voucher(new_voucher)
    
    await update.message.reply_text(f"✅ Voucher berhasil diperbarui menjadi: `{new_voucher}`", parse_mode="Markdown")
