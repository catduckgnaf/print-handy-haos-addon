<p align="center"><img src="print_handy/logo.png" alt="Print Handy" width="250"></p>

# Print Handy for Home Assistant OS

A Home Assistant app repository for [Print Handy](https://github.com/catduckgnaf/print-handy): Bambu Handy for every printer, as a one-click install on Home Assistant OS and Supervised installs.

[![Add the repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fcatduckgnaf%2Fprint-handy-haos-addon)

## Install

1. Select the button above, or open **Settings > Apps > App store > ⋮ > Repositories** and add `https://github.com/catduckgnaf/print-handy-haos-addon`.
2. Install **Print Handy**, start it, and select **Open Web UI**.
3. Add the [Print Handy integration](https://github.com/catduckgnaf/ha-print-handy) from HACS to get every printer as a Home Assistant device.

Full instructions are in the app's [documentation](print_handy/DOCS.md).

## Other ways to run Print Handy

Docker Compose, Unraid and a plain Linux install are covered in the [Print Handy docs](https://github.com/catduckgnaf/print-handy-docs). All of them run the same image.

## How updates work

There is nothing to do by hand. The **Upstream** workflow checks for a new Print Handy release every 30 minutes:

1. It pins the release's tag and multi-arch image digest in `print_handy/Dockerfile` and the matching `version` in `print_handy/config.yaml`, on a branch.
2. It builds the app image for `amd64` and `aarch64` with Home Assistant's builder actions. It smoke-tests the result the way the Supervisor runs it (root-owned `/data` and `/config`, an `options.json`, a `/healthz` check, Print Handy running unprivileged), then publishes `ghcr.io/catduckgnaf/print-handy-haos-addon:<version>`.
3. Only after the image is live does it fast-forward `main` and cut a release, so Home Assistant never offers an update it cannot pull.

A packaging fix on the same Print Handy release gets a fourth version number (`2.3.2.1`) and is published by the **Builder** workflow when it merges to `main`. A version that is already published is never pushed again.

## Layout

| Path | What it is |
| --- | --- |
| `print_handy/config.yaml` | The app definition: version, image, ports, options |
| `print_handy/Dockerfile` | A thin layer over `ghcr.io/catduckgnaf/print-handy` (pinned by tag and digest) |
| `print_handy/rootfs/usr/local/bin/print-handy-app` | Entry script: prepares `/data` and `/config`, maps options, drops to `handy` |
| `scripts/upstream.py` | Finds the newest Print Handy release and pins it |
| `scripts/smoke.sh` | Starts the image like the Supervisor and checks it |

## License

AGPL-3.0-only, the same as Print Handy.
