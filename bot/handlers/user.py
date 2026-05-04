from telegram import Update
from telegram.ext import ContextTypes
import logging
from bot.services.utils import escape_markdown

logger = logging.getLogger(__name__)

async def set_my_voucher_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command for a user to set their own personal voucher."""
    user_id = update.effective_user.id
    
    if not context.args:
        dynamic_config = context.bot_data.get("dynamic_config")
        current_voucher = dynamic_config.get_user_voucher(user_id)
        
        msg = (
            f"ℹ️ *Voucher Pribadi Anda*\n\n"
            f"Voucher saat ini: `{current_voucher or 'Belum diatur'}`\n\n"
            f"Gunakan: `/set_voucher <kode_baru>`\n"
            f"_Voucher ini akan digunakan khusus untuk pencarian Anda._"
        )
        await update.message.reply_text(escape_markdown(msg), parse_mode="MarkdownV2")
        return

    new_voucher = context.args[0]
    dynamic_config = context.bot_data.get("dynamic_config")
    dynamic_config.set_user_voucher(user_id, new_voucher)
    
    await update.message.reply_text(
        f"✅ Voucher pribadi berhasil diperbarui menjadi: `{escape_markdown(new_voucher)}`", 
        parse_mode="MarkdownV2"
    )

async def my_voucher_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check current user voucher."""
    user_id = update.effective_user.id
    dynamic_config = context.bot_data.get("dynamic_config")
    voucher = dynamic_config.get_user_voucher(user_id)
    
    if voucher:
        await update.message.reply_text(f"🎫 Voucher Anda: `{escape_markdown(voucher)}`", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("❌ Anda belum mengatur voucher pribadi. Menggunakan voucher default bot.")
