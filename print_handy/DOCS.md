# Print Handy

Print Handy is Bambu Handy for every printer. Drop a model link in Discord, Telegram or Matrix, approve it, and walk away. It slices, prints, watches for spaghetti and makes fun of your bad print choices. This app runs the same image as the Docker and Unraid installs, inside Home Assistant OS.

## Installation

1. Open **Settings > Apps > App store**, then the menu in the top right, then **Repositories**.
2. Add `https://github.com/catduckgnaf/print-handy-haos-addon`.
3. Install **Print Handy** and start it.
4. Select **Open Web UI**. On the first start the Web UI has no login and offers its setup walkthrough: add your printers there, then finish the **Login** step (set a password, or record that you mean to leave it open on a trusted network).

The app runs on 64-bit hardware only (`amd64` and `aarch64`), like Print Handy itself. A Raspberry Pi 4 or 5 running the 64-bit Home Assistant OS works; slicing large models is faster on an x86 machine.

## Connect Home Assistant

Install the [Print Handy integration](https://github.com/catduckgnaf/ha-print-handy) from HACS, then add it under **Settings > Devices & services**. Use `http://<your Home Assistant IP>:8088` as the URL, and the Web UI password or access token if you set one.

## Configuration

Most settings live in Print Handy's own settings file, which the Web UI's configuration page edits:

```
/addon_configs/<id>_print_handy/print-handy.yaml
```

It is created on the first start from the image's Docker defaults and never overwritten afterwards. You can also edit it with the File editor or Studio Code Server apps, or over Samba. Settings are read once at start, so restart the app after editing the file by hand.

App options:

| Option | What it does |
| --- | --- |
| Web UI access token | Optional. Claims the Web UI before anyone else can reach it (`WEBUI_ACCESS_TOKEN`). |
| Serve the bundled Spoolman on the network | Lets Moonraker reach the bundled Spoolman. Also set a host port for `8000/tcp` under **Network**. |
| Extra environment variables | Any Print Handy environment variable as a name and value: chat bot tokens (`DISCORD_BOT_TOKEN`, `TELEGRAM_BOT_TOKEN`), printer secrets (`BAMBU_LAN_PASSWORD`, `AD5X_CHECK_CODE`, `MOONRAKER_API_KEY`) or any `PRINT_HANDY__SECTION__KEY` override. Every variable from Print Handy's `.env.example` works here. |

The timezone comes from Home Assistant.

## Data and backups

Everything Print Handy keeps (state, print archive, records, the bundled Spoolman database and account tokens under `.config`) lives in the app's data folder and is part of Home Assistant backups. The download cache is left out of backups.

## Updates

Each app version runs the Print Handy release with the same number. When Print Handy publishes a release, this repository picks it up automatically, usually within minutes, publishes the app image, and Home Assistant offers the update under **Settings > Apps**. Print Handy's release notes say what changed.

## Network

The app uses the normal app network, not the host network. Printers are reached by the addresses in your Print Handy settings. Automatic discovery that relies on LAN broadcasts (for example, finding Elegoo printers) does not see through this network, so enter those printers' IP addresses yourself.

## Support

- Print Handy itself: [Print Handy issues](https://github.com/catduckgnaf/print-handy/issues) and the [Print Handy docs](https://github.com/catduckgnaf/print-handy-docs)
- This app's packaging: [app issues](https://github.com/catduckgnaf/print-handy-haos-addon/issues)
- Chat: the [Print Handy Discord server](https://discord.gg/mT2Ht3nqZu)
