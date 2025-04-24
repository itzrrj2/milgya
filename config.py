import os

DB_URI = os.environ.get("DATABASE_URL", "mongodb+srv://alex:alexuser@gpt.9do2y0m.mongodb.net/?retryWrites=true&w=majority&appName=gpt")
DB_NAME = os.environ.get("DATABASE_NAME", "cphdlust")

SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "api.gplinks.com")
SHORTLINK_API = os.environ.get("SHORTLINK_API", "45634dcb66385b9f434fb108d8f2cf54cf64e2ab")
VERIFY_EXPIRE = int(os.environ.get('VERIFY_EXPIRE', 43200)) # Add time in seconds
IS_VERIFY = os.environ.get("IS_VERIFY", "True")
TUT_VID = os.environ.get("TUT_VID", "https://telegram.me/AR_FileStreamBot?start=Njc5MTQzMjg3Njg1MTY2MjAwMDAvMzc4MTEyOTI1MzQ") # shareus ka tut_vid he 

# New configuration settings
PREMIUM_URL = os.environ.get("PREMIUM_URL", "https://t.me/igrisGPTBOT/?start=purchase")
FREE_DOWNLOADS = int(os.environ.get("FREE_DOWNLOADS", 3))  # Allow 3 free downloads
SHORTLINK_HOURS = int(os.environ.get("SHORTLINK_HOURS", 12))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Teraboxlink2VideoDownBot")

# Required channel details
REQUIRED_CHANNELS = {
    "Ashlynn_Repository": {
        "id": os.environ.get("CHANNEL_1", "@Ashlynn_Repository"),
        "invite_link": os.environ.get("CHANNEL_1_LINK", "https://t.me/Ashlynn_Repository")
    },
    "Ashlynn_RepositoryBot": {
        "id": os.environ.get("CHANNEL_2", "@Ashlynn_RepositoryBot"),
        "invite_link": os.environ.get("CHANNEL_2_LINK", "https://t.me/Ashlynn_RepositoryBot")
    }
}

# Version info
BOT_VERSION = "2.0.0"
