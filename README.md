# SWGOH Helper

SWGOH Helper is a Discord bot for the Star Wars: Galaxy of Heroes mobile game. It provides various functionalities related to the game, such as providing information about units and events, account linkage, and more. It uses the discord.py library for Discord API interaction, along with the self-hosted [swgoh-comlink](https://github.com/swgoh-utils/swgoh-comlink/) service to fetch game data and a Postgres database to store data for the bot. It can be deployed together with the provided Docker Compose file, or run manually with external Comlink and Postgres servers.

This bot leverages a custom-built asynchronous API wrapper, [async-comlink](https://github.com/bnziv/async-comlink), to efficiently interact with the service. This wrapper simplifies API requests, ensuring smooth and non-blocking communication between the bot and the game APIs.

## Features

#### Command Groups

The bot has the following command groups:

- `/unit`: Commands related to units, such as getting unit information, abilities, and tags
- `/allycode`: Commands related to linking your Discord account to a SWGOH account
- `/events`: Commands related to events, such as getting upcoming and current events
- `/fleet`: Commands related to fleet shard functionality

#### Notifications

The bot can send the following notifications to your Discord account via DMs:

* Live updates on your fleet arena payout
  * 1 hour prior to your payout and whenever your next battle is available on rank increase
* Notable roster updates such as character upgrades and ability unlocks
* Daily reset and bonus energy availability and a reminder if notification is not acknowledged
* When new events start

## Setup

There are two main setup methods:

#### Docker Compose

Prerequisites:
* Python 3.10
* Docker with Docker Compose

1. Clone the repository
   ```
   git clone https://github.com/bnziv/swgoh-helper.git
   cd swgoh-helper
   ```
2. Create a `.env` file in the root directory with the following variables:
   ```
   DB_USERNAME=username_for_local_db
   DB_PASSWORD=password_for_local_db
   BOT_TOKEN=your_bot_token
   ```
3. Build the Docker images and start the Docker Compose file
   ```
   docker compose build
   docker compose up
   ```

#### Manual Setup

Prerequisites:
* Python 3.10
* Hosted Comlink and Postgres servers

1. Clone the repository
   ```
   git clone https://github.com/bnziv/swgoh-helper.git
   cd swgoh-helper
   ```
2. Install Python dependencies
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory with the following variables:
   ```
   DB_URL=connection_string_for_postgres_db
   COMLINK_URL=url_for_comlink_service
   BOT_TOKEN=your_bot_token
   ```
4. Run the bot
   ```
   python src/bot.py
   ```

## License

This project is released under the [MIT License](https://opensource.org/license/MIT).
