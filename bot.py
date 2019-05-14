#!python3.6
"""
bot.py

Runs continuously until stopped manually or disconnected from WebSocket for any reason.
Also fails loudly on any exceptions or throwables.
Requires python 3.6+

https://discordapp.com/oauth2/authorize?scope=bot&permissions=88128&client_id=577679744460652544
"""

import asyncio
import json
import os
import random
import re

import aiohttp

TOKEN = os.getenv("TOKEN")
URL = "https://discordapp.com/api"
COMMAND_PREFIX = "!rune"

async def api_call(path, method="GET", **kwargs):
    """Return the JSON body of a call to Discord REST API."""
    defaults = {"headers": {"Authorization": f"Bot {TOKEN}"}}
    kwargs = dict(defaults, **kwargs)
    async with aiohttp.ClientSession() as session:
        async with session.request(method, f"{URL}{path}", **kwargs) as response:
            assert 200 <= response.status <= 299, response.reason
            if "json" in response.headers["Content-Type"]:
                return await response.json()
            else:
                return await response.text()


async def add_reaction(channel_id, message_id, reaction_emoji):
    print(
        f"About to reaction to message ID ({message_id}) in channel ({channel_id}) using emoji ({reaction_emoji})."
    )
    return await api_call(
        f"/channels/{channel_id}/messages/{message_id}/reactions/{reaction_emoji}/@me",
        "PUT",
    )


async def send_message(channel_id, content):
    """Send a message with content to the channel_id."""
    print(f"About to send message: {content}")
    return await api_call(
        f"/channels/{channel_id}/messages", "POST", json={"content": content}
    )

async def send_embed_message(channel_id, content, embed):
    """ Send a message with content and embed to the given channel ID. """
    print(f"About to send message with embed: {content}")
    return await api_call(
        f"/channels/{channel_id}/messages", "POST", json={"content": content, "embed": embed}
    )

async def show_help(user_id, channel_id):
    content = f'''<@{user_id}>, here's how you use this bot!

Prepend all commands with `!rune`; valid commands:

- `help`             // Displays this help message.
- `choices`           // Display valid champion choices.
- `{{champion-name}}` // Returns the most used rune page for the given champion.
'''
    return await send_message(channel_id, content)


async def heartbeat(ws, interval, last_sequence):
    """Send every interval ms the heatbeat message."""
    while True:
        await asyncio.sleep(interval / 1000)  # seconds
        await ws.send_json({"op": 1, "d": last_sequence})  # Heartbeat


async def start(url):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"{url}?v=6&encoding=json") as ws:
            async for msg in ws:
                data = json.loads(msg.data)
                if data["op"] == 10:  # Hello
                    # Send identification response
                    await ws.send_json(
                        {
                            "op": 2,  # Identify
                            "d": {
                                "token": TOKEN,
                                "properties": {},
                                "compress": False,
                                "large_threshold": 250,
                            },
                        }
                    )
                    last_sequence = data["s"]
                    print(json.dumps(data, indent=2))
                    # Set up async task for responding to heartbeat within interval
                    asyncio.ensure_future(
                        heartbeat(ws, data["d"]["heartbeat_interval"], last_sequence)
                    )
                elif data["op"] == 11:  # Heartbeat ACK
                    pass
                elif data["op"] == 0:  # Dispatch
                    if data["t"] == "MESSAGE_CREATE":
                        print("DATA: " + json.dumps(data["d"], indent=2))
                        new_message = data["d"]["content"].lower()
                        channel_id = data["d"]["channel_id"]
                        author = data["d"]["author"]["username"]
                        author_id = data["d"]["author"]["id"]
                        message_id = data["d"]["id"]
                        # Don't fall over ourselves; let's not react to ourselves.
                        if author == "LeagueRuneBot":
                            continue

                        if new_message.startswith(COMMAND_PREFIX):
                            message_parts = new_message.split(" ")
                            command = message_parts[1]
                            if command == "help":
                                await show_help(author_id, channel_id)
                            elif command == "choices":

                else:
                    pass


async def main():
    """Main program."""
    response = await api_call("/gateway")
    await start(response["url"])


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
