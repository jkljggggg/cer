# -*- coding: utf-8 -*-
# This is a foundational structure for a Python-based Telegram bot.
# To run this, you will need the 'python-telegram-bot' library.
# pip install python-telegram-bot Pillow

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging
from PIL import Image, ImageDraw, ImageFont # For adding text to images
import io
# qrcode library is no longer needed as we're using a static image
# import qrcode 
import random

# Set up logging to see what your bot is doing
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your Telegram Bot Token goes here.
# Get this token by creating a new bot with BotFather.
TELEGRAM_BOT_TOKEN = "7862061815:AAFc-spL0dNrwHunPlyfAcEX_Rq5cl523OI" 
# For actual use, do not hardcode this token. Use environment variables.

# Admin User IDs go here (these should be your Telegram User IDs)
# You can get your ID from @userinfobot.
ADMIN_IDS = [5464427719, 7681062358] 

# UC package information
UC_PACKAGES = {
    "300_uc": {"uc": 300, "price": 180},
    "600_uc": {"uc": 600, "price": 400},
    "1500_uc": {"uc": 1500, "price": 1250},
    "3000_uc": {"uc": 3000, "price": 2800},
    "6000_uc": {"uc": 6000, "price": 5200},
}

# --- STATIC QR CODE IMAGE URL ---
# IMPORTANT: Replace this with the actual URL of your QR code image.
# You can upload your QR code image to an image hosting service (like Imgur, GitHub Gist with raw link, etc.)
# and paste the direct link here. Make sure it's publicly accessible.
STATIC_QR_CODE_IMAGE_URL = "https://files.catbox.moe/3yvk5a.jpg"
# Example if you have a real QR image hosted: "https://example.com/my_qr_code.png"


# Simple dictionary to track user states
# In a real bot, you would use a database for this.
user_states = {} # {user_id: {"state": "current_state", "selected_uc": None, "selected_price": None, "game_id": None}}

# --- Command Handlers ---

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message and prompts for UC package selection."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    # Generate a welcome image with dynamic text
    try:
        img = Image.new('RGB', (700, 450), color='#2A9D8F') # Vibrant background color
        d = ImageDraw.Draw(img)
        
        # Try to load a nicer font, fallback to default
        try:
            # Adjust this path based on your system's font location for Inter font
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # A common fallback font on Linux
            title_font = ImageFont.truetype(font_path, 55)
            text_font = ImageFont.truetype(font_path, 30)
            small_text_font = ImageFont.truetype(font_path, 20)
        except IOError:
            logger.warning("Custom font not found, using default. Please install it or provide correct path.")
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            small_text_font = ImageFont.load_default()

        # Add dynamic text to the image
        d.text((50, 80), f"👋 Hello, {user_name}!", fill=(255,255,255), font=title_font)
        d.text((50, 180), "Welcome to the CARDING UC Bot!", fill=(255,255,255), font=text_font)
        d.text((50, 250), "Get your favorite game's UC here.", fill=(255,255,255), font=small_text_font)
        d.text((50, 320), "✨ Fast, Secure & Easy! ✨", fill=(255,255,255), font=text_font)
        
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        
        await update.message.reply_photo(
            photo=bio, 
            caption=f"Hey *{user_name}*! Welcome to the CARDING UC Bot! 🎉\n\n"
                    "We're thrilled to have you here. Let's get you started. "
                    "Please select your desired UC package below."
        )
    except Exception as e:
        logger.error(f"Error generating welcome image: {e}")
        await update.message.reply_text(
            f"Hello, *{user_name}*! Welcome to the UC Bot! 🎉\n\n"
            "Get your favorite game's UC here. Please select your desired UC package below."
        )

    # Immediately show UC packages after welcome
    await show_uc_packages(update.message) # Pass update.message to send a new message
    user_states[user_id] = {"state": "selecting_uc", "selected_uc": None, "selected_price": None, "game_id": None}

# --- Callback Query Handler (for inline button clicks) ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles inline button clicks."""
    query = update.callback_query
    await query.answer() # Acknowledge the callback query immediately to stop the button "loading"
    user_id = update.effective_user.id
    data = query.data

    if data.startswith("select_uc_"):
        uc_key = data.replace("select_uc_", "")
        if uc_key in UC_PACKAGES:
            user_states[user_id]["selected_uc"] = UC_PACKAGES[uc_key]["uc"]
            user_states[user_id]["selected_price"] = UC_PACKAGES[uc_key]["price"]
            
            await query.edit_message_text(
                f"You selected *{user_states[user_id]['selected_uc']} UC* for *₹{user_states[user_id]['selected_price']}*.\n\n"
                "Now, please send me your *Game User ID* (Player ID) in the next message. 🎮"
            )
            user_states[user_id]["state"] = "awaiting_game_id"
        else:
            await query.edit_message_text(
                "❌ Invalid UC package selected. Please try again."
            )
            await show_uc_packages(query) # Show packages again
    elif data == "confirm_payment":
        await show_payment_qr(query, context) # Pass context to show_payment_qr
        user_states[user_id]["state"] = "awaiting_screenshot"
    elif data == "cancel_payment":
        await query.edit_message_text(
            "🚫 Payment cancelled. Returning to main menu. If you wish to buy again, use /start."
        )
        user_states[user_id]["state"] = "main_menu" # Reset state
    elif data == "back_to_main":
        await query.edit_message_text("Returning to the *Main Menu*. 🚀", parse_mode='Markdown')
        keyboard = [
            [InlineKeyboardButton("🛒 Buy UC", callback_data="buy_uc")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "*What would you like to do?*", 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
        user_states[user_id]["state"] = "main_menu"
    elif data == "back_to_buy_uc": # This is "Back to Packages" button
        await show_uc_packages(query)
        user_states[user_id]["state"] = "selecting_uc"
    elif data.startswith("admin_action_"):
        await handle_admin_action(update, context, data)

# --- Helper Functions ---

async def show_uc_packages(query_or_message):
    """Displays UC package options."""
    keyboard = []
    for key, pkg in UC_PACKAGES.items():
        keyboard.append(
            [InlineKeyboardButton(f"✨ {pkg['uc']} UC - ₹{pkg['price']}", callback_data=f"select_uc_{key}")]
        )
    # The "Go Back" button leads to a simplified main menu in this flow
    keyboard.append([InlineKeyboardButton("🔙 Go Back", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    message_text = "*Please select a UC package:*"
    if hasattr(query_or_message, 'edit_message_text'):
        await query_or_message.edit_message_text(
            message_text, reply_markup=reply_markup, parse_mode='Markdown'
        )
    else: # If it's a message, not a callback query (like from /start)
        await query_or_message.reply_text(
            message_text, reply_markup=reply_markup, parse_mode='Markdown'
        )

async def show_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays payment details and asks for confirmation before showing QR."""
    user_id = update.effective_user.id
    current_state = user_states.get(user_id, {})
    selected_uc = current_state.get("selected_uc")
    selected_price = current_state.get("selected_price")
    game_id = current_state.get("game_id")

    if not all([selected_uc, selected_price, game_id]):
        await update.message.reply_text("Something went wrong. Please start again with /start.")
        user_states[user_id]["state"] = "main_menu" # Reset state
        return

    message_text = (
        f"✅ *Order Summary:*\n\n"
        f"📦 *UC Package:* {selected_uc} UC\n"
        f"💸 *Amount:* ₹{selected_price}\n"
        f"🎮 *Your Game ID:* `{game_id}`\n\n"
        f"Please *confirm* these details before proceeding to payment. "
        f"Make sure your Game ID is correct!"
    )

    keyboard = [
        [
            InlineKeyboardButton("👍 Confirm & Proceed to Payment", callback_data="confirm_payment"),
        ],
        [
            InlineKeyboardButton("❌ Cancel Order", callback_data="cancel_payment")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    user_states[user_id]["state"] = "awaiting_payment_confirmation"


async def show_payment_qr(query, context): # context added as parameter
    """Displays the payment QR code image (static image)."""
    user_id = query.from_user.id
    current_state = user_states.get(user_id, {})
    selected_price = current_state.get("selected_price")
    selected_uc = current_state.get("selected_uc")
    game_id = current_state.get("game_id")

    caption = (
        f"💰 *Payment Details:*\n\n"
        f"📦 *UC Package:* {selected_uc} UC\n"
        f"💸 *Amount to Pay:* ₹{selected_price}\n"
        f"🎮 *Your Game ID:* `{game_id}`\n\n"
        f"Scan this QR code to make your payment.\n"
        f"_(This is very fast and secure payment gateway.)_\n\n"
        f"*IMPORTANT:* After making the payment, please send the "
        f"*screenshot of the payment confirmation* here. We will verify it."
    )
    
    keyboard = [
        [InlineKeyboardButton("↩️ Back to Packages", callback_data="back_to_buy_uc")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Delete the previous confirmation message if it exists
    if query.message:
        await query.message.delete()
    
    # Send the static QR code image
    await context.bot.send_photo( # Use context.bot.send_photo for sending URL
        chat_id=user_id,
        photo=STATIC_QR_CODE_IMAGE_URL, # Use the static URL here
        caption=caption, 
        reply_markup=reply_markup, 
        parse_mode='Markdown'
    )

# --- Message Handler for Game ID ---
# --- Message Handler for Game ID ---
async def handle_game_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles receiving the Game User ID."""
    user_id = update.effective_user.id
    
    if user_states.get(user_id, {}).get("state") == "awaiting_game_id":
        game_id_input = update.message.text.strip()
        
        # Check if the input consists only of digits
        if game_id_input.isdigit():
            user_states[user_id]["game_id"] = game_id_input
            await show_payment_confirmation(update, context) # Proceed to confirmation
        else:
            await update.message.reply_text(
                "🔢 *Invalid Game ID format!* 🚫\n\n"
                "Please enter your *Game User ID* using*. "
                "For example: `5444954540`\n\n"
                "Double-check your ID to ensure a smooth transaction! ✨"
            )
    else:
        # If text is received when not expecting Game ID, revert to main menu or inform
        await update.message.reply_text(
            "I wasn't expecting text input right now. Please use the buttons provided or /start to begin. 🔄"
        )
        user_states[user_id]["state"] = "main_menu" # Reset state to avoid confusion

# --- Message Handler for Screenshot ---
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles receiving a screenshot and forwards it to admins."""
    user_id = update.effective_user.id
    
    if user_states.get(user_id, {}).get("state") != "awaiting_screenshot":
        await update.message.reply_text(
            "I wasn't expecting a screenshot right now. Please start with /start or select a package."
        )
        return

    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id # Get the largest photo
        current_state = user_states.get(user_id, {})
        selected_uc = current_state.get("selected_uc")
        selected_price = current_state.get("selected_price")
        game_id = current_state.get("game_id")

        await update.message.reply_text(
            "✅ Your screenshot has been successfully uploaded and sent to the admin for review. "
            "Please await their approval. Thank you for your patience! 🙏"
        )
        user_states[user_id]["state"] = "awaiting_admin_approval"

        # Forward screenshot and info to admins
        for admin_id in ADMIN_IDS:
            try:
                caption = (
                    f"🚨 *NEW PAYMENT RECEIVED!* 🚨\n\n"
                    f"User ID: `{user_id}`\n"
                    f"User Name: @{update.effective_user.username or 'N/A'}\n"
                    f"Selected UC: *{selected_uc}*\n"
                    f"Payment Amount: *₹{selected_price}*\n"
                    f"Game ID: *`{game_id}`*\n\n" # Included Game ID
                    f"Please review the screenshot and approve/reject."
                )
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"admin_action_approve_{user_id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"admin_action_reject_{user_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_file_id,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode='Markdown' # Use Markdown for bold/italic in caption
                )
                logger.info(f"Screenshot from {user_id} (Game ID: {game_id}) forwarded to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to forward screenshot to admin {admin_id}: {e}")
                await update.message.reply_text(
                    "❗️ An error occurred while sending the screenshot to the admin. "
                    "Please try again later."
                )
    else:
        await update.message.reply_text(
            "Please send a screenshot of your payment confirmation. It should be an image file."
        )

# --- Admin Action Handler ---
async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handles approval/rejection by an admin."""
    query = update.callback_query
    admin_id = update.effective_user.id

    if admin_id not in ADMIN_IDS:
        await query.answer("🚫 You are not authorized to perform this action.")
        return

    parts = data.split('_')
    action = parts[2] # 'approve' or 'reject'
    user_to_affect_id = int(parts[3]) # ID of the user to affect

    # In a real application, you would update a database here.
    # For now, we'll just notify the user.

    current_state = user_states.get(user_to_affect_id, {})
    selected_uc_admin = current_state.get("selected_uc", "N/A")
    game_id_admin = current_state.get("game_id", "N/A")


    if action == "approve":
        status_message = (
            f"✅ Your payment for *{selected_uc_admin} UC* has been *approved*! "
            f"Your UC will be added to your Game ID (`{game_id_admin}`) soon. Enjoy! 🎉"
        )
        log_message = f"Admin {admin_id} approved payment for user {user_to_affect_id} (Game ID: {game_id_admin})"
        color_emoji = "✅"
    else: # reject
        status_message = (
            f"❌ Your payment for *{selected_uc_admin} UC* (Game ID: `{game_id_admin}`) has been *rejected*! "
            "Please ensure you used the correct amount and QR code, and uploaded a clear screenshot. "
            "Please try again or contact support for assistance."
        )
        log_message = f"Admin {admin_id} rejected payment for user {user_to_affect_id} (Game ID: {game_id_admin})"
        color_emoji = "❌"

    logger.info(log_message)

    # Notify the user
    try:
        await context.bot.send_message(
            chat_id=user_to_affect_id,
            text=status_message,
            parse_mode='Markdown' # Use Markdown for bold/italic in status message
        )
        # Edit the admin's message to indicate that action has been taken
        # Ensure caption_html exists, otherwise use raw_text
        message_text_to_edit = query.message.caption_html if query.message.caption_html else query.message.text
        await query.edit_message_text(
            text=f"{message_text_to_edit}\n\n*Action: {color_emoji} {action.capitalize()}*",
            parse_mode='Markdown' # Use Markdown for the edited admin message
        )
    except Exception as e:
        logger.error(f"Failed to send status to user {user_to_affect_id} or edit admin message: {e}")
        await query.answer("An error occurred while notifying the user or editing the message.")

    await query.answer(f"Payment {action}ed for user {user_to_affect_id}.")
    user_states[user_to_affect_id]["state"] = "completed" # Or another appropriate state

# --- Main Function ---

def main():
    """Runs the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))

    # Button handlers
    application.add_handler(CallbackQueryHandler(button_handler))

    # Message handlers
    # Handle text messages for Game ID input when in awaiting_game_id state
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_game_id))
    # Handle photo messages for screenshots
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_screenshot))

    # Start the bot
    logger.info("Starting polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
