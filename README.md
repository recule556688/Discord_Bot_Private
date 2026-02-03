# TessBot — Discord Bot

A modular Discord bot built with Python, discord.py, and PostgreSQL. Features moderation, message logging, birthdays, image transformations, and more.

---

## Features

| Category | Commands | Description |
|----------|----------|-------------|
| **Admin** | `/addrole`, `/ping`, `/owner`, `/clear`, `/force_unban_all`, `/check_stored_roles` | Role management, moderation, server owner tools |
| **Info** | `/server_stats`, `/avatar`, `/user_info`, `/uptime` | Server and user statistics |
| **Fun** | `/joke`, `/cat`, `/weather` | Jokes, cat images, weather (OpenWeatherMap) |
| **Birthday** | `/birthday` | Add, delete, display birthdays; countdown to next |
| **DM** | `/dm`, `/cancel_dm` | Send DMs; schedule delayed messages |
| **Logging** | `/manage_logging_channels`, `/read_logs`, `/delete_all_logs` | Exclude channels from logging; view/delete logs |
| **Moderation** | Auto | Banned-word filter with temporary suspension; role restore on rejoin |

**Context menus** (right-click message):

- **Gay to Gay**, **Ratio to Ratio**, **Féminisme to Féminisme** — Add text overlay to images/GIFs
- **Image to emoji** — Resize and upload as server emoji
- **Image to Sticker** — Resize image for sticker use

---

## Prerequisites

- Python 3.10+
- PostgreSQL 13+
- [Discord Bot Token](https://discord.com/developers/applications)
- [OpenWeatherMap API Key](https://openweathermap.org/api) (for `/weather`)

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/recule556688/Discord_Bot_Private.git
cd Discord_Bot_Private
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in the project root:

```env
# Required
BOT_TOKEN=your_discord_bot_token
OPENWEATHERMAP_API_KEY=your_openweathermap_key

# Database (PostgreSQL)
POSTGRES_DB=discord_bot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

```

### 3. Run the bot

```bash
# Won't start without a postgres db
cd app
python bot.py
```

---

## Docker

### With Docker Compose (recommended)

```bash
docker compose up -d
```

This starts the bot and PostgreSQL. The `app/` folder is mounted into the container, so code changes apply after a restart.

### Build image manually

```bash
docker build -t tessbot .
docker run --env-file .env tessbot
```

---

## Project Structure

```
app/
├── bot.py              # Entry point
├── config.py           # Constants, env, API keys
├── database.py         # PostgreSQL connection and helpers
├── state.py            # Shared state (temp bans, stored roles)
├── crafty_auth.py      # Crafty API (disabled)
├── cogs/
│   ├── admin.py        # Admin commands
│   ├── dm.py           # DM and scheduled messages
│   ├── info.py         # Server/user info
│   ├── fun.py          # Joke, cat, weather
│   ├── birthday.py     # Birthday management
│   ├── logging_cog.py  # Message logging
│   ├── images.py       # Image context menus
│   └── moderation.py   # Banned words, temp bans
├── utils/
│   └── checks.py       # is_owner decorator
└── data/
    ├── bot.log         # Log file
    └── Roboto-Bold.ttf # Font for image overlays
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Discord bot token |
| `OPENWEATHERMAP_API_KEY` | Yes | OpenWeatherMap API key |
| `POSTGRES_DB` | Yes | PostgreSQL database name |
| `POSTGRES_USER` | Yes | PostgreSQL user |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `POSTGRES_HOST` | Yes | PostgreSQL host |
| `POSTGRES_PORT` | Yes | PostgreSQL port (default: 5432) |

---

## Discord Setup

1. Create an application at [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a bot and copy the token.
3. Enable **Privileged Gateway Intents**: Server Members, Message Content.
4. Invite the bot with scopes: `bot`, `applications.commands`.

---

## License

See [LICENSE](LICENSE).
