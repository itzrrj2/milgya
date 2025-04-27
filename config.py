import os

DB_URI = os.environ.get("DATABASE_URL", "mongodb+srv://shresthforyt:NY9pM7Yp70RndD9w@terab.v3zltm8.mongodb.net/?retryWrites=true&w=majority&appName=Terab")
DB_NAME = os.environ.get("DATABASE_NAME", "Terab")

SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "bharatlinks.com")
SHORTLINK_API = os.environ.get("SHORTLINK_API", "442622b64c0c0829663e547bd8c5d685b9c3773c")
VERIFY_EXPIRE = int(os.environ.get('VERIFY_EXPIRE', 43200)) # Add time in seconds
IS_VERIFY = os.environ.get("IS_VERIFY", "True")
TUT_VID = os.environ.get("TUT_VID", "https://t.me/sr_trbx_tutorial") # shareus ka tut_vid he 

# New configuration settings
PREMIUM_URL = os.environ.get("PREMIUM_URL", "https://t.me/srxpremiumBOT/?start=purchase")
FREE_DOWNLOADS = int(os.environ.get("FREE_DOWNLOADS", 1))  # Allow 3 free downloads
SHORTLINK_HOURS = int(os.environ.get("SHORTLINK_HOURS", 12))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Mill_Gyabot")

# Required channel details
REQUIRED_CHANNELS = {
    "Sr_Robots": {
        "id": os.environ.get("CHANNEL_1", "@sr_robots"),
        "invite_link": os.environ.get("CHANNEL_1_LINK", "https://t.me/sr_robots")
    },
    "Xstream_Links2": {
        "id": os.environ.get("CHANNEL_2", "@xstream_links2"),
        "invite_link": os.environ.get("CHANNEL_2_LINK", "https://t.me/xstream_links2")
    }
}

# Version info
BOT_VERSION = "2.0.0"
