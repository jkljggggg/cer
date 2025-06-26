# यह एक Python-आधारित Telegram बॉट का आधारभूत ढाँचा है।
# इसे चलाने के लिए आपको 'python-telegram-bot' लाइब्रेरी की आवश्यकता होगी।
# pip install python-telegram-bot Pillow qrcode

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# ContextTypes को इम्पोर्ट करें
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging
from PIL import Image, ImageDraw, ImageFont # इमेज पर टेक्स्ट जोड़ने के लिए
import io
import qrcode # QR कोड जनरेट करने के लिए (सिर्फ उदाहरण, असली पेमेंट QR नहीं)
import random

# लॉगिंग सेट अप करें ताकि आप देख सकें कि आपका बॉट क्या कर रहा है
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# आपका Telegram बॉट टोकन यहाँ डालें।
# BotFather से एक नया बॉट बनाकर यह टोकन प्राप्त करें।
TELEGRAM_BOT_TOKEN = "7862061815:AAFc-spL0dNrwHunPlyfAcEX_Rq5cl523OI" # यह आपके अपलोड किए गए app.py से लिया गया है
# वास्तविक उपयोग के लिए, इस टोकन को सीधे कोड में न डालें,
# बल्कि पर्यावरण चर (environment variables) का उपयोग करें।

# एडमिन यूजर ID यहाँ डालें (ये आपके Telegram यूजर ID होने चाहिए)
# आप @userinfobot पर अपनी ID प्राप्त कर सकते हैं।
ADMIN_IDS = [5464427719, 7681062358] # यह आपके अपलोड किए गए app.py से लिया गया है

# यूसी पैकेज की जानकारी
UC_PACKAGES = {
    "60_uc": {"uc": 60, "price": 100},
    "300_uc": {"uc": 300, "price": 400},
    "600_uc": {"uc": 600, "price": 750},
    "1200_uc": {"uc": 1200, "price": 1500},
}

# उपयोगकर्ता स्थिति को ट्रैक करने के लिए एक साधारण डिक्शनरी
# एक वास्तविक बॉट में, आप इसके लिए एक डेटाबेस का उपयोग करेंगे।
user_states = {} # {user_id: {"state": "current_state", "selected_uc": None, "selected_price": None}}

# --- कमांड हैंडलर ---

# /start कमांड
# ContextTypes.DEFAULT_TYPE का उपयोग करके context पैरामीटर के टाइप को सही करें
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """यूजर के /start कमांड पर वेलकम मैसेज भेजता है।"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    # वेलकम इमेज जनरेट करें (एक उदाहरण प्लेसहोल्डर इमेज)
    try:
        # इमेज डाउनलोड करने की बजाय, हम सीधे एक नई इमेज बनाएंगे
        img = Image.new('RGB', (600, 400), color = '#4CAF50')
        d = ImageDraw.Draw(img)
        
        # इंटर फ़ॉन्ट के लिए एक अनुमानित पथ या सामान्य फ़ॉन्ट
        try:
            # यह आपके सिस्टम पर Inter.ttf फ़ाइल के पथ पर निर्भर करेगा
            font_path = "/usr/share/fonts/truetype/inter/Inter-Regular.ttf" # Linux उदाहरण
            font = ImageFont.truetype(font_path, 40)
            small_font = ImageFont.truetype(font_path, 25)
        except IOError:
            # अगर फ़ॉन्ट नहीं मिला, तो डिफ़ॉल्ट फ़ॉन्ट का उपयोग करें
            logger.warning("Inter font not found, using default. Please install it or provide correct path.")
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        d.text((50, 100), f"नमस्ते, {user_name}!", fill=(255,255,255), font=font)
        d.text((50, 200), "यूसी बॉट में आपका स्वागत है!", fill=(255,255,255), font=small_font)
        d.text((50, 250), "आपके पसंदीदा गेम के लिए यूसी खरीदें।", fill=(255,255,255), font=small_font)
        
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        await update.message.reply_photo(photo=bio, caption="आपका स्वागत है! यूसी खरीदने के लिए तैयार हैं?")
    except Exception as e:
        logger.error(f"Error generating welcome image: {e}")
        await update.message.reply_text(f"नमस्ते, {user_name}! यूसी बॉट में आपका स्वागत है!\nआपके पसंदीदा गेम के लिए यूसी खरीदें।")

    keyboard = [
        [InlineKeyboardButton("यूसी खरीदें", callback_data="buy_uc")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("क्या आप आगे बढ़ना चाहेंगे?", reply_markup=reply_markup)
    user_states[user_id] = {"state": "main_menu", "selected_uc": None, "selected_price": None}

# --- कॉल बैक क्वेरी हैंडलर (इनलाइन बटन क्लिक्स के लिए) ---

# ContextTypes.DEFAULT_TYPE का उपयोग करके context पैरामीटर के टाइप को सही करें
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """इनलाइन बटन क्लिक्स को संभालता है।"""
    query = update.callback_query
    await query.answer() # कॉल बैक क्वेरी को तुरंत जवाब दें ताकि बटन "लोडिंग" न दिखे
    user_id = update.effective_user.id
    data = query.data

    if data == "buy_uc":
        await show_uc_packages(query)
        user_states[user_id]["state"] = "selecting_uc"
    elif data.startswith("select_uc_"):
        uc_key = data.replace("select_uc_", "")
        if uc_key in UC_PACKAGES:
            user_states[user_id]["selected_uc"] = UC_PACKAGES[uc_key]["uc"]
            user_states[user_id]["selected_price"] = UC_PACKAGES[uc_key]["price"]
            await show_payment_qr(query)
            user_states[user_id]["state"] = "awaiting_screenshot"
        else:
            await query.edit_message_text("अमान्य यूसी पैकेज चुना गया। कृपया पुनः प्रयास करें।")
            await show_uc_packages(query) # पैकेज दोबारा दिखाएं
    elif data == "back_to_main":
        await query.edit_message_text("मुख्य मेनू पर वापस।")
        keyboard = [
            [InlineKeyboardButton("यूसी खरीदें", callback_data="buy_uc")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("क्या आप आगे बढ़ना चाहेंगे?", reply_markup=reply_markup)
        user_states[user_id]["state"] = "main_menu"
    elif data == "back_to_buy_uc":
        await show_uc_packages(query)
        user_states[user_id]["state"] = "selecting_uc"
    elif data.startswith("admin_action_"):
        await handle_admin_action(update, context, data)

# --- सहायक फ़ंक्शन ---

async def show_uc_packages(query_or_message):
    """यूसी पैकेज के विकल्प दिखाता है।"""
    keyboard = []
    for key, pkg in UC_PACKAGES.items():
        keyboard.append(
            [InlineKeyboardButton(f"{pkg['uc']} यूसी - ₹{pkg['price']}", callback_data=f"select_uc_{key}")]
        )
    keyboard.append([InlineKeyboardButton("वापस जाएं", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(query_or_message, 'edit_message_text'):
        await query_or_message.edit_message_text(
            "कृपया एक यूसी पैकेज चुनें:", reply_markup=reply_markup
        )
    else: # If it's a message, not a callback query
        await query_or_message.reply_text(
            "कृपया एक यूसी पैकेज चुनें:", reply_markup=reply_markup
        )

async def show_payment_qr(query):
    """भुगतान QR कोड दिखाता है (सिर्फ डेमो)।"""
    user_id = query.from_user.id
    selected_price = user_states[user_id]["selected_price"]
    selected_uc = user_states[user_id]["selected_uc"]

    # एक डमी QR कोड जनरेट करें। वास्तविक एप्लिकेशन में, यह पेमेंट गेटवे से आएगा।
    qr_data = f"DEMO_QR_CODE_FOR_UC_{selected_uc}_PRICE_{selected_price}_USER_{user_id}_" + \
              f"RANDOM_{random.randint(1000, 9999)}"
    
    qr_img = qrcode.make(qr_data)
    bio = io.BytesIO()
    qr_img.save(bio, 'PNG')
    bio.seek(0)

    caption = (
        f"भुगतान राशि: ₹{selected_price}\n\n"
        f"भुगतान करने के लिए इस QR कोड को स्कैन करें।\n"
        f"(यह सिर्फ एक डेमो QR कोड है और वास्तविक भुगतान प्रक्रिया को ट्रिगर नहीं करेगा।)\n\n"
        f"भुगतान करने के बाद, कृपया भुगतान का स्क्रीनशॉट भेजें।"
    )
    
    keyboard = [
        [InlineKeyboardButton("वापस जाएं", callback_data="back_to_buy_uc")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_photo(photo=bio, caption=caption, reply_markup=reply_markup)
    await query.delete_message() # पिछले मैसेज को डिलीट कर दें ताकि QR कोड सीधे दिखे

# --- मैसेज हैंडलर ---

# ContextTypes.DEFAULT_TYPE का उपयोग करके context पैरामीटर के टाइप को सही करें
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """स्क्रीनशॉट प्राप्त होने पर उसे संभालता है और एडमिन को फॉरवर्ड करता है।"""
    user_id = update.effective_user.id
    
    if user_states.get(user_id, {}).get("state") != "awaiting_screenshot":
        await update.message.reply_text("मुझे अभी एक स्क्रीनशॉट की उम्मीद नहीं थी। कृपया /start से शुरू करें या 'यूसी खरीदें' बटन का उपयोग करें।")
        return

    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id # सबसे बड़ी फोटो प्राप्त करें
        selected_uc = user_states[user_id]["selected_uc"]
        selected_price = user_states[user_id]["selected_price"]

        await update.message.reply_text("आपका स्क्रीनशॉट सफलतापूर्वक अपलोड कर दिया गया है। यह अब एडमिन को भेजा गया है। कृपया उनकी स्वीकृति की प्रतीक्षा करें।")
        user_states[user_id]["state"] = "awaiting_admin_approval"

        # एडमिन को स्क्रीनशॉट और जानकारी फॉरवर्ड करें
        for admin_id in ADMIN_IDS:
            try:
                caption = (
                    f"**नया भुगतान प्राप्त हुआ!**\n\n"
                    f"यूज़र ID: `{user_id}`\n"
                    f"यूज़र नाम: @{update.effective_user.username or 'N/A'}\n"
                    f"चयनित यूसी: {selected_uc}\n"
                    f"भुगतान राशि: ₹{selected_price}\n\n"
                    f"कृपया समीक्षा करें और अनुमोदित/अस्वीकृत करें।"
                )
                keyboard = [
                    [
                        InlineKeyboardButton("✅ अनुमोदित करें", callback_data=f"admin_action_approve_{user_id}"),
                        InlineKeyboardButton("❌ अस्वीकृत करें", callback_data=f"admin_action_reject_{user_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_file_id,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                logger.info(f"Screenshot from {user_id} forwarded to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to forward screenshot to admin {admin_id}: {e}")
                await update.message.reply_text("एडमिन को स्क्रीनशॉट भेजने में त्रुटि हुई। कृपया बाद में पुनः प्रयास करें।")
    else:
        await update.message.reply_text("कृपया भुगतान का स्क्रीनशॉट भेजें। यह एक इमेज फ़ाइल होनी चाहिए।")

# --- एडमिन एक्शन हैंडलर ---
# ContextTypes.DEFAULT_TYPE का उपयोग करके context पैरामीटर के टाइप को सही करें
async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """एडमिन द्वारा अनुमोदन/अस्वीकृति को संभालता है।"""
    query = update.callback_query
    admin_id = update.effective_user.id

    if admin_id not in ADMIN_IDS:
        await query.answer("आप इस कार्रवाई को करने के लिए अधिकृत नहीं हैं।")
        return

    parts = data.split('_')
    action = parts[2] # 'approve' or 'reject'
    user_to_affect_id = int(parts[3]) # उस उपयोगकर्ता की ID जिसे प्रभावित करना है

    # यहाँ आप डेटाबेस अपडेट करेंगे
    # फिलहाल, हम सिर्फ उपयोगकर्ता को सूचित करेंगे

    if action == "approve":
        status_message = "आपका भुगतान अनुमोदित कर दिया गया है! यूसी जल्द ही आपके खाते में जोड़ दी जाएगी।"
        log_message = f"Admin {admin_id} approved payment for user {user_to_affect_id}"
        color_emoji = "✅"
    else: # reject
        status_message = "आपका भुगतान अस्वीकृत कर दिया गया है। कृपया सुनिश्चित करें कि आपने सही राशि और क्यूआर कोड का उपयोग किया है और एक स्पष्ट स्क्रीनशॉट अपलोड किया है। कृपया दोबारा प्रयास करें।"
        log_message = f"Admin {admin_id} rejected payment for user {user_to_affect_id}"
        color_emoji = "❌"

    logger.info(log_message)

    # उपयोगकर्ता को सूचित करें
    try:
        await context.bot.send_message(
            chat_id=user_to_affect_id,
            text=f"{color_emoji} {status_message}"
        )
        # एडमिन के मैसेज को एडिट करें ताकि पता चले कि कार्रवाई हो गई है
        # सुनिश्चित करें कि caption_html मौजूद है, अन्यथा raw_text का उपयोग करें
        message_text_to_edit = query.message.caption_html if query.message.caption_html else query.message.text
        await query.edit_message_text(
            text=f"{message_text_to_edit}\n\n**कार्यवाही: {color_emoji} {action.capitalize()}**",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Failed to send status to user {user_to_affect_id} or edit admin message: {e}")
        await query.answer("उपयोगकर्ता को सूचित करने या संदेश संपादित करने में त्रुटि हुई।")

    await query.answer(f"भुगतान {action} कर दिया गया है।")
    user_states[user_to_affect_id]["state"] = "completed" # या कोई और उपयुक्त स्थिति

# --- मुख्य फ़ंक्शन ---

def main():
    """बॉट को चलाता है।"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # कमांड हैंडलर
    application.add_handler(CommandHandler("start", start))

    # बटन हैंडलर
    application.add_handler(CallbackQueryHandler(button_handler))

    # इमेज (स्क्रीनशॉट) मैसेज हैंडलर
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_screenshot))

    # बॉट शुरू करें
    logger.info("Starting polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
