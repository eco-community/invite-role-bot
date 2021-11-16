# InviteRoleBot

A bot that can automatically assign roles based on what invite URL was used

# Bot can:
* Detect which user joined via which invite link
* Log messages when users join channel
* Assign roles when user joined
* Show stats for invite links

# Installation
1. [Install Docker](https://docs.docker.com/engine/install/ubuntu/)
2. Execute `docker-compose up -d`
2. Install requirements from `requirements.txt` for `Python 3`
3. Copy and update settings in `config.example.py`
4. Add `LOG_CHANNEL_ID` to `config.py`, to this channel will be posted users when bot is unsure about their invite link, they won't be assigned any roles, you need to handle them manually
5. Add `TOKEN` bot token into `config.py`, bot requires at least `268745824` [permissions](https://discord.com/developers/docs/topics/permissions)
4. Start bot via `python bot.py` or [via supervisord](http://supervisord.org/) or [systemd](https://es.wikipedia.org/wiki/Systemd)

# Available commands
* `$invites.stats_all` Displays a list of all invite URLs
* `$invites.stats_used` Lists invite URLs which were used at least once
* `$invites.list` Lists all connected invite URLs and roles
* `$invites.connect` Connects an invite URL to roles, assigning roles to whoever joins using the given invite URL
* `$invites.disconnect` Disconnects the given invite URL from roles it is connected to
