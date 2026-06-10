import asyncio
import base64
import logging
import os
import random

from aiogram import Bot, Dispatcher, types
from aiohttp import ClientSession, web
from dotenv import load_dotenv

from database_manager import (
    award_referral_credit,
    get_user_data,
    set_referrer,
    set_user_premium,
    update_user_data,
    use_free_credit,
    user_agreed_to_terms,
)

load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
PLAN_ID = os.getenv("PAYPAL_PLAN_ID", "P-39U78069VC411525WNF64WEA")
PAYPAL_URL = f"https://www.paypal.com/webapps/billing/plans/subscribe?plan_id={PLAN_ID}"
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "live").lower()
PAYPAL_API_URL = "https://api-m.sandbox.paypal.com" if PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", API_TOKEN[-16:] if API_TOKEN else "telegram")
USE_TELEGRAM_WEBHOOK = os.getenv("USE_TELEGRAM_WEBHOOK", "auto").lower()
ADMIN_IDS = {
    admin_id.strip()
    for admin_id in os.getenv("ADMIN_IDS", "").split(",")
    if admin_id.strip()
}
PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
polling_task = None

DISCLAIMER_TEXT = (
    "⚠️ **כתב ויתור אחריות ותנאי שימוש** ⚠️\n\n"
    "1. השימוש בבוט ובמידע המופק ממנו הוא על אחריות המשתמש בלבד.\n"
    "2. המידע הוא המלצה סטטיסטית בלבד ואינו מבטיח זכייה.\n"
    "3. הבוט ומפתחיו אינם נושאים באחריות לנזק כספי.\n"
    "**המשך השימוש מהווה הסכמה לתנאים אלו.**"
)

MARKETING_STORY = (
    "🔬 **הטכנולוגיה שמאחורי המזל**\n\n"
    "מערכת **LottoAI** פותחה על ידי צוות מומחי דאטה.\n"
    "האלגוריתם סורק אלפי הגרלות עבר ומזהה דפוסים סטטיסטיים\n"
    "כדי לזקק את הצירופים בעלי הפוטנציאל הגבוה ביותר."
)


def generate_numbers():
    lines = []
    for _ in range(10):
        nums = sorted(random.sample(range(1, 38), 6))
        strong = random.randint(1, 7)
        lines.append(nums + [strong])
    return lines


def is_admin(user_id):
    return str(user_id) in ADMIN_IDS


def is_premium_active(user):
    return bool(user.get("is_premium", False))


async def get_paypal_access_token():
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        return None

    auth_raw = f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode("utf-8")
    headers = {
        "Authorization": f"Basic {base64.b64encode(auth_raw).decode('ascii')}",
        "Accept": "application/json",
        "Accept-Language": "en_US",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    async with ClientSession() as session:
        async with session.post(
            f"{PAYPAL_API_URL}/v1/oauth2/token",
            headers=headers,
            data="grant_type=client_credentials",
        ) as response:
            if response.status != 200:
                logging.error("PayPal token request failed: %s %s", response.status, await response.text())
                return None
            data = await response.json()
            return data.get("access_token")


async def create_paypal_subscription(user_id):
    token = await get_paypal_access_token()
    if not token:
        logging.warning("Missing PayPal credentials; using fallback plan URL.")
        return f"{PAYPAL_URL}&custom={user_id}"

    payload = {
        "plan_id": PLAN_ID,
        "custom_id": str(user_id),
        "application_context": {
            "brand_name": "LottoAI",
            "locale": "he-IL",
            "shipping_preference": "NO_SHIPPING",
            "user_action": "SUBSCRIBE_NOW",
        },
    }

    if PUBLIC_BASE_URL:
        payload["application_context"]["return_url"] = f"{PUBLIC_BASE_URL}/paypal/success?user_id={user_id}"
        payload["application_context"]["cancel_url"] = f"{PUBLIC_BASE_URL}/paypal/cancel?user_id={user_id}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Prefer": "return=representation",
    }

    async with ClientSession() as session:
        async with session.post(
            f"{PAYPAL_API_URL}/v1/billing/subscriptions",
            headers=headers,
            json=payload,
        ) as response:
            data = await response.json(content_type=None)
            if response.status not in (200, 201):
                logging.error("PayPal subscription create failed: %s %s", response.status, data)
                return f"{PAYPAL_URL}&custom={user_id}"

    for link in data.get("links", []):
        if link.get("rel") == "approve":
            return link.get("href")

    logging.error("PayPal subscription response did not include approve link: %s", data)
    return f"{PAYPAL_URL}&custom={user_id}"


async def send_share_prompt(user_id):
    bot_username = BOT_USERNAME
    if not bot_username:
        me = await bot.get_me()
        bot_username = me.username

    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    text = (
        "🎁 רוצה עוד הגרלה חינמית?\n\n"
        "שתף את הקישור עם חבר. כשהוא יצטרף ויאשר את התנאים, "
        "תקבל קרדיט חינמי נוסף להרצה אחת."
    )
    keyboard = types.InlineKeyboardMarkup(row_width=1).add(
        types.InlineKeyboardButton("📤 שתף חבר", url=f"https://t.me/share/url?url={referral_link}"),
        types.InlineKeyboardButton("🔗 פתח קישור הזמנה", url=referral_link),
    )
    await bot.send_message(user_id, text, reply_markup=keyboard)


@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    user_id = str(message.from_user.id)
    args = message.get_args()
    if args.startswith("ref_"):
        await set_referrer(user_id, args.replace("ref_", "", 1))

    user = await get_user_data(user_id)
    welcome_img = "https://images.unsplash.com/photo-1518133835878-5a93cc3f89e5?q=80&w=1000"

    if not user.get("agreed_to_terms", False):
        keyboard = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("✅ אני מאשר את התנאים", callback_data="agree_terms")
        )
        await bot.send_photo(
            message.chat.id,
            welcome_img,
            caption=DISCLAIMER_TEXT,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        await show_main_menu(message.chat.id, message.from_user.first_name)


@dp.message_handler(commands=["whoami"])
async def show_whoami(message: types.Message):
    user_id = str(message.from_user.id)
    admin_status = "כן" if is_admin(user_id) else "לא"
    await bot.send_message(
        message.chat.id,
        f"Telegram ID שלך: <code>{user_id}</code>\nמזוהה כאדמין: <b>{admin_status}</b>",
        parse_mode="HTML",
    )


@dp.message_handler(commands=["grantvip"])
async def grant_vip(message: types.Message):
    if not is_admin(message.from_user.id):
        await bot.send_message(message.chat.id, "אין לך הרשאה לבצע פעולה זו.")
        return

    target_user_id = message.get_args().strip()
    if not target_user_id.isdigit():
        await bot.send_message(message.chat.id, "שימוש נכון: /grantvip 123456789")
        return

    expiry = await set_user_premium(target_user_id, "manual_admin_grant")
    await bot.send_message(
        message.chat.id,
        f"VIP נפתח למשתמש <code>{target_user_id}</code>\nתוקף עד: <b>{expiry}</b>",
        parse_mode="HTML",
    )

    try:
        await bot.send_message(
            target_user_id,
            f"🎊 מנוי VIP הופעל עבורך!\nתוקף: {expiry}\nאפשר להפיק הגרלות ללא הגבלה.",
        )
    except Exception as e:
        logging.warning("Could not notify manually granted VIP user %s: %s", target_user_id, e)


@dp.message_handler(commands=["revokevip"])
async def revoke_vip(message: types.Message):
    if not is_admin(message.from_user.id):
        await bot.send_message(message.chat.id, "אין לך הרשאה לבצע פעולה זו.")
        return

    target_user_id = message.get_args().strip()
    if not target_user_id.isdigit():
        await bot.send_message(message.chat.id, "שימוש נכון: /revokevip 123456789")
        return

    await update_user_data(target_user_id, {"is_premium": False})
    await bot.send_message(
        message.chat.id,
        f"VIP בוטל למשתמש <code>{target_user_id}</code>",
        parse_mode="HTML",
    )


@dp.message_handler(commands=["userstatus"])
async def user_status(message: types.Message):
    if not is_admin(message.from_user.id):
        await bot.send_message(message.chat.id, "אין לך הרשאה לבצע פעולה זו.")
        return

    target_user_id = message.get_args().strip()
    if not target_user_id.isdigit():
        await bot.send_message(message.chat.id, "שימוש נכון: /userstatus 123456789")
        return

    user = await get_user_data(target_user_id)
    premium_status = "כן" if user.get("is_premium", False) else "לא"
    await bot.send_message(
        message.chat.id,
        (
            f"משתמש: <code>{target_user_id}</code>\n"
            f"VIP פעיל: <b>{premium_status}</b>\n"
            f"תוקף: <b>{user.get('expiry_date') or 'אין'}</b>\n"
            f"ניצל חינם: <b>{'כן' if user.get('has_used_free') else 'לא'}</b>\n"
            f"קרדיטים חינמיים: <b>{user.get('free_credits', 0)}</b>"
        ),
        parse_mode="HTML",
    )


async def show_main_menu(chat_id, name):
    text = f"שלום {name}! 🎰\n\n{MARKETING_STORY}\n\nהאלגוריתם מוכן. מה תרצה לעשות?"
    keyboard = types.InlineKeyboardMarkup(row_width=1).add(
        types.InlineKeyboardButton("🎰 הפק 10 שורות VIP", callback_data="get_lotto"),
        types.InlineKeyboardButton("💳 הצטרף למנוי VIP", callback_data="show_pay"),
        types.InlineKeyboardButton("🎁 הזמן חבר וקבל הגרלה חינמית", callback_data="share_friend"),
    )
    await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == "agree_terms")
async def process_agree(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    await user_agreed_to_terms(user_id)
    referrer_id = await award_referral_credit(user_id)
    await bot.answer_callback_query(callback_query.id, "התנאים אושרו!")
    if referrer_id:
        await bot.send_message(referrer_id, "🎁 חבר שהזמנת הצטרף! נוסף לך קרדיט חינמי להרצה אחת.")
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await show_main_menu(callback_query.message.chat.id, callback_query.from_user.first_name)


@dp.callback_query_handler(lambda c: c.data == "get_lotto")
async def process_lotto(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    user = await get_user_data(user_id)
    unlimited_allowed = is_admin(user_id) or is_premium_active(user)
    has_extra_credit = int(user.get("free_credits", 0) or 0) > 0

    if unlimited_allowed or not user.get("has_used_free", False) or has_extra_credit:
        results = generate_numbers()
        if not unlimited_allowed:
            if user.get("has_used_free", False):
                await use_free_credit(user_id)
            else:
                await update_user_data(user_id, {"has_used_free": True})

        text = "🎰 **התחזית האלגוריתמית עבורך:**\n\n"
        for i, row in enumerate(results, 1):
            nums = "  ".join([f"<b>{n}</b>" for n in row[:-1]])
            text += f"{i}. {nums} | ⭐ <b>{row[-1]}</b>\n"

        await bot.send_message(user_id, text, parse_mode="HTML")

        if not unlimited_allowed:
            await asyncio.sleep(2)
            promo = '🧐 רוצה תחזיות ללא הגבלה? הצטרף ל-VIP ב-10 ש"ח בלבד!'
            keyboard = types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("💳 למנוי VIP", callback_data="show_pay")
            )
            await bot.send_message(user_id, promo, reply_markup=keyboard)
            await send_share_prompt(user_id)
    else:
        await show_payment_options(user_id)


async def show_payment_options(user_id):
    url = await create_paypal_subscription(user_id)
    text = (
        "🛑 **מגבלת שימוש חינמי**\n\n"
        "כבר ניצלת את התחזית החינמית. הצטרף ל-VIP כדי להמשיך ללא הגבלה."
    )
    keyboard = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton('💳 מנוי VIP ב-10 ש"ח', url=url)
    )
    await bot.send_message(user_id, text, reply_markup=keyboard, parse_mode="Markdown")


@dp.callback_query_handler(lambda c: c.data == "show_pay")
async def callback_pay(callback_query: types.CallbackQuery):
    await show_payment_options(callback_query.from_user.id)


@dp.callback_query_handler(lambda c: c.data == "share_friend")
async def callback_share(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await send_share_prompt(callback_query.from_user.id)


async def handle_home(request):
    return web.Response(text="LottoAI Server is Running!")


async def handle_paypal_success(request):
    return web.Response(text="Payment approved. VIP access will be activated by the PayPal webhook.")


async def handle_paypal_cancel(request):
    return web.Response(text="Payment cancelled. You can return to Telegram.")


async def handle_telegram_webhook(request):
    update = types.Update(**await request.json())
    await dp.process_update(update)
    return web.Response(text="OK")


async def handle_paypal_webhook(request):
    try:
        data = await request.json()
        event_type = data.get("event_type")
        resource = data.get("resource", {})

        user_id = resource.get("custom_id") or resource.get("custom")
        if not user_id and "subscriber" in resource:
            user_id = resource["subscriber"].get("custom_id")

        logging.info("Webhook: %s | User: %s", event_type, user_id)

        if user_id and event_type in [
            "PAYMENT.SALE.COMPLETED",
            "BILLING.SUBSCRIPTION.ACTIVATED",
            "BILLING.SUBSCRIPTION.RE-ACTIVATED",
        ]:
            expiry = await set_user_premium(user_id, resource.get("id"))
            await bot.send_message(
                user_id,
                f"🎊 **מנוי VIP הופעל!**\nתוקף: {expiry}\nבהצלחה! 🍀",
                parse_mode="Markdown",
            )
        elif user_id and event_type in [
            "BILLING.SUBSCRIPTION.CANCELLED",
            "BILLING.SUBSCRIPTION.EXPIRED",
            "BILLING.SUBSCRIPTION.SUSPENDED",
        ]:
            await update_user_data(user_id, {"is_premium": False})

        return web.Response(text="OK", status=200)
    except Exception as e:
        logging.error("Webhook Error: %s", e)
        return web.Response(text="Error", status=400)


async def on_startup(app):
    global polling_task
    should_use_webhook = USE_TELEGRAM_WEBHOOK == "true" or (
        USE_TELEGRAM_WEBHOOK == "auto" and bool(PUBLIC_BASE_URL)
    )

    if should_use_webhook:
        telegram_webhook_url = f"{PUBLIC_BASE_URL}/webhook/telegram/{TELEGRAM_WEBHOOK_SECRET}"
        logging.info("Starting Telegram webhook: %s", telegram_webhook_url)
        logging.info("Configured admin IDs: %s", ", ".join(sorted(ADMIN_IDS)) or "none")
        await bot.set_webhook(telegram_webhook_url, drop_pending_updates=True)
        return

    logging.info("Starting Telegram Bot Polling...")
    logging.info("Configured admin IDs: %s", ", ".join(sorted(ADMIN_IDS)) or "none")
    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dp.start_polling())


async def on_shutdown(app):
    global polling_task
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    await bot.session.close()


if __name__ == "__main__":
    app = web.Application()
    app.router.add_get("/", handle_home)
    app.router.add_get("/paypal/success", handle_paypal_success)
    app.router.add_get("/paypal/cancel", handle_paypal_cancel)
    app.router.add_post("/webhook/paypal", handle_paypal_webhook)
    app.router.add_post(f"/webhook/telegram/{TELEGRAM_WEBHOOK_SECRET}", handle_telegram_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=PORT)
