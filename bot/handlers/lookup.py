"""
Handler untuk pencarian nomor telepon
"""

import re
import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.services.phone_utils import normalize_phone, format_display_number
from bot.services.datapublik import DataPublikClient, MultiSourceResponse, SourceResult
from bot.services.cache import SearchCache
from bot.services.utils import escape_markdown as _escape_md

logger = logging.getLogger(__name__)


def _format_result(result: MultiSourceResponse, from_cache: bool = False, total_balance: int = None) -> str:
    """Format MultiSource result into a nice Telegram message with separators."""
    if result.error or not result.success:
        return (
            f"❌ *Pencarian Gagal*\n\n"
            f"Nomor: `{_escape_md(result.phone_number)}`\n"
            f"Error: {_escape_md(result.error or result.message)}"
        )

    display_num = format_display_number(result.phone_number)
    lines = [
        "✅ *Hasil Pencarian Multi\\-Source*",
        f"📱 *Nomor:* `{_escape_md(display_num)}`",
        "",
    ]

    for source_res in result.sources:
        if source_res.source.lower() == "whatsapp":
            continue
            
        source_name = source_res.source.upper()
        lines.append(f"\\=\\=\\=\\=\\= *{_escape_md(source_name)}* \\=\\=\\=\\=\\=")
        
        has_data = False
        
        if source_res.status_code == 200:
            if source_res.name:
                lines.append(f"📛 *Nama:* {_escape_md(source_res.name)}")
                has_data = True
                
            # Get extra fields from results if any (e.g. carrier for Truecaller)
            res_data = source_res.raw_data or {}
            if isinstance(res_data, dict):
                carrier = res_data.get("carrier")
                if carrier:
                    lines.append(f"📡 *Provider:* {_escape_md(carrier)}")
                    has_data = True

            # Source-specific data
            if source_res.source == "getcontact" and source_res.tags:
                lines.append(f"🏷️ *Tag \\({source_res.tag_count} total\\):*")
                for i, tag_obj in enumerate(source_res.tags, 1):
                    tag_name = tag_obj.get("tag", "")
                    tag_count = tag_obj.get("count", 0)
                    lines.append(f"  {i}\\. {_escape_md(tag_name)} \\({tag_count}\\)")
                has_data = True
            
            elif source_res.source == "eyecon" and "contacts" in res_data:
                contacts = res_data.get("contacts", [])
                if contacts:
                    lines.append(f"👥 *Kontak Terdeteksi:*")
                    for i, c in enumerate(contacts, 1):
                        c_name = c.get("name", "")
                        lines.append(f"  {i}\\. {_escape_md(c_name)}")
                    has_data = True
        
        if not has_data:
            lines.append("_\\-kosong\\-_")
            
        lines.append("") # Spacer between sources

    # Token info - Only show if NOT from cache to avoid confusion
    if not from_cache:
        # Show total balance if provided and if user has a pool (more than 1 voucher)
        # We check total_balance is not None and either it's higher than current or we know user has more vouchers
        if total_balance is not None:
            lines.append(f"🪙 *Sisa Token:* `{result.remaining_tokens}` \\(Total Pool: `{total_balance}`\\)")
        else:
            lines.append(f"🪙 *Sisa Token:* `{result.remaining_tokens}`")
    
    # Cache indicator
    if from_cache:
        lines.append("💾 _Hasil diambil dari cache \\(Hemat Token\\)_")

    return "\n".join(lines)




async def _send_long_message(update: Update, text: str, status_msg: Update.message = None) -> None:
    """Split and send long messages to avoid Telegram limit."""
    # Split into chunks of ~4000 chars, preferably at newline
    max_len = 4000
    chunks = []
    
    while len(text) > 0:
        if len(text) <= max_len:
            chunks.append(text)
            break
            
        # Find best place to split (newline)
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1: # No newline found, just cut at max_len
            split_at = max_len
            
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    # Send first chunk
    first_chunk = chunks[0]
    if status_msg:
        try:
            await status_msg.edit_text(first_chunk, parse_mode="MarkdownV2")
        except Exception as e:
            logger.error(f"MDv2 Error in chunk 1: {e}")
            # Fallback for Markdown error
            plain = first_chunk.replace("\\", "").replace("*", "").replace("_", "").replace("`", "")
            await status_msg.edit_text(f"⚠️ \\(Part 1 \\- Format error\\)\n\n{plain}", parse_mode="MarkdownV2")
    else:
        try:
            await update.message.reply_text(first_chunk, parse_mode="MarkdownV2")
        except Exception as e:
            logger.error(f"MDv2 Error in chunk 1: {e}")
            plain = first_chunk.replace("\\", "").replace("*", "").replace("_", "").replace("`", "")
            await update.message.reply_text(f"⚠️ \\(Part 1 \\- Format error\\)\n\n{plain}", parse_mode="MarkdownV2")

    # Send remaining chunks
    for i, chunk in enumerate(chunks[1:], 2):
        try:
            await update.message.reply_text(f"*Lanjutan \\(Bagian {i}\\):*\n\n{chunk}", parse_mode="MarkdownV2")
        except Exception as e:
            logger.error(f"MDv2 Error in chunk {i}: {e}")
            plain = chunk.replace("\\", "").replace("*", "").replace("_", "").replace("`", "")
            await update.message.reply_text(f"⚠️ \\(Part {i} \\- Format error\\)\n\n{plain}", parse_mode="MarkdownV2")


async def lookup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages (JSON payloads or phone numbers)."""
    raw_text = update.message.text.strip()
    user_id = update.effective_user.id
    dynamic_config = context.bot_data.get("dynamic_config")
    
    # 1. Try to parse as JSON first
    payload = None
    try:
        if raw_text.startswith('{') and raw_text.endswith('}'):
            import json
            payload = json.loads(raw_text)
    except Exception:
        payload = None

    # Handle JSON Payload
    if payload:
        # Payload: {phoneNumber: "+62...", key: "..."}
        if "phoneNumber" in payload:
            phone = payload.get("phoneNumber")
            key = payload.get("key") or dynamic_config.get_voucher()
            await _handle_phone_lookup(phone, update, context, key)
            return

    # 2. Fallback to existing phone number detection
    if re.match(r"^[\d\+\s\-\(\)]+$", raw_text):
        digits_only = re.sub(r"\D", "", raw_text)
        if len(digits_only) >= 8:
            await _handle_phone_lookup(raw_text, update, context)
            return

    # If no match, just ignore or log
    logger.info(f"Ignored message from {user_id}: {raw_text[:50]}")


async def _handle_phone_lookup(raw_phone: str, update: Update, context: ContextTypes.DEFAULT_TYPE, override_key: str = None) -> None:
    """Consolidated phone lookup logic."""
    user_id = update.effective_user.id
    normalized = normalize_phone(raw_phone)
    dynamic_config = context.bot_data.get("dynamic_config")
    
    if not normalized:
        await update.message.reply_text(
            "❌ *Format nomor tidak valid*\n\n"
            "Pastikan Anda mengirim nomor telepon yang benar\\.",
            parse_mode="MarkdownV2",
        )
        return

    active_user_voucher = dynamic_config.get_active_user_voucher(user_id)
    
    # --- Calculate Total Balance for display ---
    total_balance = None
    if active_user_voucher:
        total_balance = dynamic_config.get_total_balance(user_id)

    # --- Check cache ---
    cache: SearchCache = context.bot_data.get("cache")
    if cache:
        cached_data = cache.get(normalized)
        if cached_data:
            logger.info(f"✅ Cache HIT for: {normalized}")
            # Re-parse the cached dict into the object
            result = dp_client._parse_multisource_response(normalized, cached_data)
            cache.log_search(normalized, user_id, update.effective_user.username, from_cache=True)
            
            formatted_text = _format_result(result, from_cache=True, total_balance=total_balance)
            await _send_long_message(update, formatted_text)
            return
        else:
            logger.info(f"❌ Cache MISS for: {normalized}")

    # --- Search ---
    status_msg = await update.message.reply_text(
        f"🔍 Mencari `{_escape_md(format_display_number(normalized))}`\\.\\.\\.",
        parse_mode="MarkdownV2",
    )

    dp_client: DataPublikClient = context.bot_data.get("dp_client")
    if not dp_client:
        await status_msg.edit_text("❌ API client tidak tersedia\\.", parse_mode="MarkdownV2")
        return

    # DYNAMIC KEY INJECTION:
    # Priority: Override (JSON) > User specific pool > Global Dynamic > Default Hardcoded
    active_user_voucher = dynamic_config.get_active_user_voucher(user_id)
    active_key = override_key or active_user_voucher or dynamic_config.get_voucher() or dp_client.default_key
    
    # Perform search
    # We need to get the raw data to store in cache
    result, raw_data = await dp_client.search_multisource(normalized, active_key)
    
    # Save to cache if successful
    if cache and result.success:
        cache.put(normalized, raw_data)
        cache.log_search(normalized, user_id, update.effective_user.username, from_cache=False)

    # TRACKING & AUTO-SWITCH: Update balance in pool
    if result.success:
        # If using a user voucher, update its balance in the pool
        if active_user_voucher and active_key == active_user_voucher:
            dynamic_config.update_voucher_balance(user_id, active_key, result.remaining_tokens)
            # Recalculate total balance after update
            total_balance = dynamic_config.get_total_balance(user_id)
            
            # If tokens are 0, move to next voucher in pool
            if result.remaining_tokens == 0:
                dynamic_config.remove_first_user_voucher(user_id)
                logger.info(f"Voucher empty for user {user_id}, automatically removed.")

    # Robust multi-part message delivery
    formatted_text = _format_result(result, total_balance=total_balance)
    await _send_long_message(update, formatted_text, status_msg)
