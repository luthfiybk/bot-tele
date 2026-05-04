from telegram import Update
from telegram.ext import ContextTypes
import logging
from bot.services.utils import escape_markdown

logger = logging.getLogger(__name__)

async def set_my_voucher_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command for a user to add a voucher to their personal pool."""
    user_id = update.effective_user.id
    dynamic_config = context.bot_data.get("dynamic_config")
    
    if not context.args:
        vouchers = dynamic_config.get_user_vouchers(user_id)
        count = len(vouchers)
        active = vouchers[0]["key"] if vouchers else 'Belum ada'
        total = dynamic_config.get_total_balance(user_id)
        
        msg = (
            f"🎫 *Voucher Pool Anda*\n\n"
            f"• Jumlah Voucher: `{count}`\n"
            f"• Total Token Pool: `{total}`\n"
            f"• Voucher Aktif: `{active}`\n\n"
            f"Gunakan: `/set_voucher <kode_baru>`\n"
            f"_Voucher baru akan ditambahkan ke antrian (akumulasi)._"
        )
        await update.message.reply_text(escape_markdown(msg), parse_mode="MarkdownV2")
        return

    new_voucher = context.args[0].strip()
    
    # Check for "clear" command
    if new_voucher.lower() == "clear":
        dynamic_config.clear_user_vouchers(user_id)
        await update.message.reply_text("🗑️ Semua voucher Anda telah dihapus.")
        return

    dynamic_config.add_user_voucher(user_id, new_voucher)
    
    vouchers = dynamic_config.get_user_vouchers(user_id)
    await update.message.reply_text(
        f"✅ Voucher berhasil ditambahkan\\!\n"
        f"Sekarang Anda memiliki `{len(vouchers)}` voucher dalam antrian\\.", 
        parse_mode="MarkdownV2"
    )

async def my_voucher_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check current user voucher pool."""
    user_id = update.effective_user.id
    dynamic_config = context.bot_data.get("dynamic_config")
    vouchers = dynamic_config.get_user_vouchers(user_id)
    
    if vouchers:
        msg = f"🎫 *Antrian Voucher Anda ({len(vouchers)}):*\n\n"
        for i, v in enumerate(vouchers, 1):
            status = " (Aktif)" if i == 1 else ""
            key = escape_markdown(v["key"])
            balance = v.get("balance", 0)
            msg += f"{i}\\. `{key}` \\(Sisa: `{balance}`\\){status}\n"
        
        total = dynamic_config.get_total_balance(user_id)
        msg += f"\n💰 *Total Saldo Pool:* `{total}`"
        msg += "\n\n_Bot akan otomatis pindah ke voucher berikutnya jika voucher aktif sudah habis._"
        await update.message.reply_text(msg, parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("❌ Anda belum memiliki voucher pribadi. Menggunakan voucher default bot.")
