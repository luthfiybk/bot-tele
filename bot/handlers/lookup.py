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

logger = logging.getLogger(__name__)


def _format_result(result: MultiSourceResponse, from_cache: bool = False) -> str:
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

    # Token info
    lines.append(f"🪙 *Sisa Token:* `{result.remaining_tokens}`")
    
    # Cache indicator
    if from_cache:
        lines.append("💾 _Hasil dari cache_")

    return "\n".join(lines)


def _escape_md(text: str) -> str:
    """Escape special characters for MarkdownV2."""
    if not text:
        return ""
    special_chars = r"_*[]()~`>#+-=|{}.!\\"
    escaped = ""
    for char in text:
        if char in special_chars:
            escaped += f"\\{char}"
        else:
            escaped += char
    return escaped


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

    # --- Check cache ---
    cache: SearchCache = context.bot_data.get("cache")
    if cache:
        logger.info(f"🔎 Checking cache for: {normalized}")
        cached_data = cache.get(normalized)
        if cached_data:
            logger.info(f"🎯 Cache HIT for: {normalized}")
            dp_client: DataPublikClient = context.bot_data.get("dp_client")
            # Re-parse the cached dict into the object
            result = dp_client._parse_multisource_response(normalized, cached_data)
            cache.log_search(normalized, user_id, update.effective_user.username, from_cache=True)
            await update.message.reply_text(_format_result(result, from_cache=True), parse_mode="MarkdownV2")
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
    active_key = override_key or dynamic_config.get_voucher() or dp_client.default_key
    
    # Perform search
    # We need to get the raw data to store in cache
    result, raw_data = await dp_client.search_multisource(normalized, active_key)
    
    # Save to cache if successful
    if cache and result.success:
        cache.put(normalized, raw_data)
        cache.log_search(normalized, user_id, update.effective_user.username, from_cache=False)

    await status_msg.edit_text(_format_result(result), parse_mode="MarkdownV2")
