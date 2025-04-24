# TeraBox Downloader Bot

A Telegram bot for downloading videos and files from TeraBox.

## Features

- ⚡ Fast downloads from TeraBox
- 📥 3 free downloads for all users
- 🔄 Shortlink verification for additional downloads
- 💎 Premium membership support
- 🔐 Required channel membership checks
- 📊 Admin dashboard with detailed statistics
- 🎛️ User-friendly interface

## Setup and Installation

### Prerequisites

- Python 3.10+
- MongoDB database
- Telegram Bot Token
- Aria2 (for downloading)

### Environment Variables

Create a `config.env` file with the following variables:

```
# Bot Configuration
BOT_TOKEN=your_bot_token
TELEGRAM_API=your_telegram_api_id
TELEGRAM_HASH=your_telegram_api_hash
BOT_USERNAME=your_bot_username
ADMINS=comma_separated_admin_ids

# Database
MONGO_URL=your_mongodb_url
DATABASE_NAME=your_db_name

# Channel Settings
FSUB_ID=your_forcesub_channel_id
DUMP_CHAT_ID=your_dump_chat_id
CHANNEL_1=@your_channel_1_id
CHANNEL_1_LINK=https://t.me/your_channel_1
CHANNEL_2=@your_channel_2_id
CHANNEL_2_LINK=https://t.me/your_channel_2

# Shortlink Configuration
SHORTLINK_URL=your_shortlink_url
SHORTLINK_API=your_shortlink_api
SHORTLINK_HOURS=12
FREE_DOWNLOADS=3  # Number of free downloads allowed
TUT_VID=your_tutorial_video_url
```

### Docker Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/yourbot.git
   cd yourbot
   ```

2. Build the Docker image:
   ```bash
   docker build -t terabox-bot .
   ```

3. Run the container:
   ```bash
   docker run -d --env-file config.env terabox-bot
   ```

### Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/yourbot.git
   cd yourbot
   ```

2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Aria2:
   ```bash
   # On Ubuntu/Debian
   sudo apt-get install aria2
   ```

4. Run Aria2 with RPC enabled:
   ```bash
   aria2c --enable-rpc --rpc-listen-all=false --rpc-listen-port=6800 --rpc-allow-origin-all --daemon
   ```

5. Start the bot:
   ```bash
   python terabox.py
   ```

## User Guide

### Basic Usage

1. Start the bot by sending `/start`
2. Send a TeraBox link to download the file
3. The bot will process the link and send the file to you

### Commands

- `/start` - Start the bot
- `/profile` - View your profile and download count
- `/check` - Check verification status
- `/help` - Show help message (admin only)

### Admin Commands

- `/stats` - Show bot statistics
- `/addpremium <user_id> <months>` - Add premium to a user
- `/removepremium <user_id>` - Remove premium from a user
- `/premiumlist` - List all premium users
- `/broadcast` - Send message to all users (Reply to a message)

## Technical Details

- Built with Pyrogram and Motor for asynchronous operation
- Uses Aria2 for efficient downloading
- MongoDB for user data storage
- Flask web server for keep-alive functionality

## Contribution

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This bot is for educational purposes only. Always respect the terms of service of TeraBox.

## 🌟 Features

- **Modern UI/UX**: Clean, professional interface with intuitive navigation
- **Force Channel Join**: Users must join specified channels before using the bot
- **Free Downloads**: Users get 3 free downloads before requiring verification
- **Premium System**: Premium users get unlimited downloads without ads
- **Admin Controls**: Comprehensive admin commands for user management
- **Shortlink Verification**: Access for 12 hours after completing verification
- **Profile System**: Users can check their status, downloads, and remaining limits
- **Admin Default Premium**: Admins automatically get unlimited access
- **Support for Private Channels**: Can configure private channel join links
- **Customizable Bot Username**: Change bot username through configuration

## 🔧 Configuration (config.env)

- `BOT_TOKEN`: The Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- `TELEGRAM_API`: API ID from <https://my.telegram.org>
- `TELEGRAM_HASH`: API Hash from <https://my.telegram.org>
- `FSUB_ID`: Force Subscribe Channel ID (starting with -100)
- `DUMP_CHAT_ID`: Dump Channel ID for storing downloaded videos (starting with -100)
- `MONGO_URL`: MongoDB connection string
- `ADMINS`: Admin user IDs (comma separated for multiple admins)

### New Configuration Options
- `CHANNEL_1`: First required channel username/ID
- `CHANNEL_2`: Second required channel username/ID
- `CHANNEL_1_LINK`: Invite link for first channel (for private channels)
- `CHANNEL_2_LINK`: Invite link for second channel (for private channels)
- `PREMIUM_URL`: URL for premium purchase
- `FREE_DOWNLOADS`: Number of free downloads allowed (default: 3)
- `SHORTLINK_HOURS`: Hours of access after shortlink verification (default: 12)
- `BOT_USERNAME`: Your bot's username (without @)

## 💼 Admin Commands

- `/addpremium <user_id> <months>` - Add premium to a user (also supports `/addpremium_user_id_months` format)
- `/removepremium <user_id>` - Remove premium from a user (also supports `/removepremium_user_id` format)
- `/premiumlist` - List all premium users
- `/stats` - Show bot statistics
- `/broadcast` - Send message to all users (Reply to a message to broadcast it)

## 👤 User Commands

- `/start` - Start the bot and view welcome message
- `/profile` - View your profile including status, downloads, and time remaining
- `/check` - Check token verification status

## 🚀 Deployment

### Prerequisites

1. Python 3.8 or higher
2. Docker (optional)

### Setup

1. Clone this repository:
```
git clone https://github.com/yourusername/yourbot.git && cd yourbot-bot
```

2. Install requirements:
```
pip install -r requirements.txt
```

3. Configure your `config.env` file with your settings

4. Start the bot:
```
bash start.sh
```

### Docker Deployment

1. Build Docker image:
```
sudo docker build . -t terabox-bot
```

2. Run the image:
```
sudo docker run terabox-bot
```

Alternatively, use docker-compose:
```
sudo docker-compose up --build
```

## 📱 Usage

1. Start the bot on Telegram
2. Join the required channels
3. Send a TeraBox link to download
4. After 3 free downloads, verify through shortlink or purchase premium

## 🔒 Privacy & Security

- The bot only stores necessary user information for functionality
- Premium user management is admin-controlled
- Verification tokens are randomly generated and expire after set time

## 🔰 Credits

- TeraBox-DL API
- PyroGram
- All relevant libraries and contributors

## 😵‍💫 Feature : 

- Public usage & Pvt usage 
- Save all videos into Database Channel 
- Broadcast 
- Total user count
- Admin can download 500MB+
- Force sub | Channel & Group 
- Token verification Feature 
- check token timeout 
- 🆕 check STATUS how many users are verified via token ( current status )
- 🆕 Working on Groups & in PM

## Command:
```
/start - alive or not !
/check - token timeout (user)
/broadcast - media/txt support (a)
/Stats - verified user status (a)
---
## Deploy on VPS
---
## Prerequisites

### 1. Installing requirements

- Clone this repo:

```
git clone / && cd terabox
```

- For Debian based distros

```
sudo apt install python3 python3-pip
```

Install Docker by following the [Official docker docs](https://docs.docker.com/engine/install/#server).
Or you can use the convenience script: `curl -fsSL https://get.docker.com |  bash`


- For Arch and it's derivatives:

```
sudo pacman -S docker python
```

------

### 2. Build And Run the Docker Image

Make sure you still mount the app folder and installed the docker from official documentation.

- There are two methods to build and run the docker:
  1. Using official docker commands.
  2. Using docker-compose.

------

#### Build And Run The Docker Image Using Official Docker Commands

- Start Docker daemon (SKIP if already running, mostly you don't need to do this):

```
sudo dockerd
```

- Build Docker image:

```
sudo docker build . -t phdlust
```

- Run the image:

```
sudo docker run -p 80:80 -p 8080:8080 phdlust
```

- To stop the running image:

```
sudo docker ps
```

```
sudo docker stop id
```

----

#### Build And Run The Docker Image Using docker-compose

**NOTE**: If you want to use ports other than 80 and 8080 change it in [docker-compose.yml](docker-compose.yml).

- Install docker compose

```
sudo apt install docker-compose
```

- Build and run Docker image:

```
sudo docker-compose up --build
```

- To stop the running image:

```
sudo docker-compose stop
```

- To run the image:

```
sudo docker-compose start
```

- To get latest log from already running image (after mounting the folder):

```
sudo docker-compose up
```

--

Cmd to start the Bot: bash start.sh
