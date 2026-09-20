<div align="center">
  <img src="icons/icon.png" alt="icon" width="160"><br>
  <h1>ok-nte</h1>
  <p>An image-recognition-based automation tool for <em>Neverness To Everness</em>, with background operation support, developed based on the <a href="https://github.com/ok-oldking/ok-script">ok-script</a> framework.</p>

English | [简体中文](README_cn.md)

  <p>
    <img src="https://img.shields.io/badge/platform-Windows-blue" alt="Platform">
    <img src="https://img.shields.io/badge/python-3.12-skyblue" alt="Python Version">
    <a href="https://github.com/BnanZ0/ok-nte/releases"><img src="https://img.shields.io/github/downloads/BnanZ0/ok-nte/total" alt="Total Downloads"></a>
    <a href="https://github.com/BnanZ0/ok-nte/releases"><img src="https://img.shields.io/github/v/release/BnanZ0/ok-nte" alt="Latest Release"></a>
    <a href="https://discord.gg/vVyCatEBgA"><img alt="Discord" src="https://img.shields.io/discord/296598043787132928?color=5865f2&label=%20Discord"></a>
  </p>

  <p>
    <a href="docs/en/getting-started/installation.md">📥 Latest release</a> ·
    <a href="docs/en/index.md">📖 Documentation</a> ·
    <a href="docs/en/guides/quick-start.md">🚀 Quick start</a> ·
    <a href="docs/en/guides/troubleshooting.md">🛠️ FAQ and feedback</a>
  </p>

  <p>
    <a href="https://github.com/BnanZ0/ok-nte">Lighten the star⭐</a> &nbsp;|&nbsp; <a href="./SPONSOR.md">Sponsor the developer☕</a>
  </p>
</div>

<p align="center">
  <img width="950" alt="ok-nte-gif-en" src="./assets/gif/ok-nte-gif-en.gif" />
</p>

## 🔧 Fork Additions

Changes in this fork that are not in upstream [BnanZ0/ok-nte](https://github.com/BnanZ0/ok-nte). Newest first.

### Character Builder groundwork (scanners)

Two read-only scan tasks that read progression data out of the game. They are the data
layer for a planned Character Builder tab; that tab does not exist yet, so for now they
report to the log and to `configs/`.

**Character Ascend Scan** reads the ascension requirements for the character currently
open in the `C` menu: the target level, the stat gains, and each required material with
its owned/needed counts. It then opens each material to read its name and its in-game
**Source**, for example `Anomaly Hunt "Serenetti"`. That gives the full chain of
character to material to the activity that drops it, without relying on external guides.

**Anomaly Material Scan** reads the four Anomaly Zone tabs on the `F1` page and records
the domains each one offers, so a material's source can later be resolved to a task
configuration.

**How to use them**

1. From the open world, select the character you want to read in the `C` menu.
2. Run **Character Ascend Scan**. Results appear in the log.
3. Run **Anomaly Material Scan** from the open world. It writes
   `configs/AnomalyMaterialMap.json`.

Both are strictly read-only. Neither spends City Stamina, materials or currency. The
Ascend screen carries a confirm button and a Material Conversion button that would spend
resources; the scanner derives its click points from each material's own count box, so a
click can only land on the icon row, and tests assert it stays clear of both controls.

### City Delivery with Hathor

Finds the highest-paying daily delivery and hands it in using Hathor's once-a-day auto
delivery, so the job is completed without driving the minigame.

Daily deliveries vary a lot in value. A recent day ranged from 8,000 to 32,000 Fons, and the
biggest payout was a plain "Shop Restock" rather than the one labelled Urgent, so the reward
is read from each job rather than guessed from its cargo type. Ranking uses the
`Professional Rating: (90+)` tier, because Hathor always claims at the top tier.

Hathor only needs to be owned; she does not have to be in your active party.

**How to use it**

1. From the open world, run **City Delivery** with **Track Highest Reward** enabled. It opens
   the map, reads every daily delivery, ranks them, and tracks the best one. The job then
   appears on your compass and minimap.
2. Fast travel to a nearby point and make your way to the delivery NPC yourself.
3. Run the task again with **Complete with Hathor** enabled, or let it run as the last step of
   your daily routine. It waits up to **Arrival Wait (seconds)** for you to reach the NPC,
   then completes the delivery and closes the reward screen.

Both options are off by default. The task also appears at the end of the **Daily Tasks** list,
disabled, so you can opt in per profile; it is placed last because it is the only routine task
that waits on you.

**Safety**

The dialogue also offers **Accept Order**, which would start a real timed delivery and spend
City Stamina. The task only ever clicks the option whose text names Hathor, never a position
or the highlighted default. If that option is missing, usually because the daily use is
already spent, it closes the dialogue and stops rather than choosing something else. The
reward screen is dismissed with **Complete**, matched by text, never the adjacent **Again!**.

Travel is still manual. Automating it needs a detection template for the delivery marker.

### Daily Routine Profiles and per-weekday scheduling

Run a different set of daily tasks on each day of the week.

Previously a schedule entry ran one task, and Daily Tasks stored a single selection, so every scheduled run did the same thing. There are now **7 routine profiles**, each with its own task selection and ordering. Profile 1 is the original Daily Tasks, so existing configs keep working.

Sub-task settings (Cafe, Anomaly, and so on) remain **shared** across profiles — configure them once. Only the selection and ordering are per-profile.

**How to use it**

1. Open the **Daily Tasks** tab. Pick a profile from the **Profile** dropdown at the top.
2. Enable the tasks you want for that profile and drag them into the order you want.
3. Optionally rename the profile using the **Profile Name** field in the settings card at the top — call it `Monday`, `Tuesday`, and so on. The name updates in the dropdown as you type, and is what the Schedule tab shows.
4. Repeat for each profile you need.
5. Open the **Schedule** tab and click **Create**. Your profiles appear in **Select Task** under their names.
6. Set **Trigger Type** to `Weekly`, then pick a **Day of Week** and a start time.
7. Create one entry per weekday, each pointing at its own profile.

Weekly schedule entries previously always fired on Monday regardless of when they were created; the **Day of Week** control fixes that and applies to both new and existing entries.

## What is ok-nte?

ok-nte is a Windows automation tool for <em>Neverness To Everness</em>. It interacts through screen recognition, OCR, system audio feedback, and ordinary keyboard and mouse input; it does not read game memory or modify game files.

## ✨ Main Features

- **Automated Tasks**: Dailies, weeklies, fishing, rhythm games, anomalies, and other instances.
- **Auto Combat**: Computer vision-based combat, Character Center, custom combo lists, and feature management.
- **Constant Triggers**: Audio-driven dodge and counter, dialog skipping, and fast travel.
- **Utilities**: MIDI-based auto piano and other auxiliary features.
- **Background Operation**: Automate game actions while in the background.

See the [feature overview](docs/en/features/overview.md) for the complete list.

## ⚠️ Disclaimer

> [!CAUTION]
> **This software is an open-source, free external tool intended for learning and exchange purposes only. It is designed to automate the gameplay of *Neverness To Everness* by interacting with the game solely through the existing user interface and in compliance with relevant laws and regulations.**
>
> - **Mechanism**: The package is intended to provide a simplified way for users to interact with the game. This package does not modify any game files or game code in any way.
> - **Purpose**: It is not meant to disrupt the game balance or provide any unfair advantage.
> - **Liability**: All issues and consequences arising from the use of this software are not related to this project or its development team. The development team reserves the final right of interpretation for this project.
> - **Commercialization**: If you encounter vendors using this software for services and charging a fee, this may cover their costs for equipment and time; any resulting problems or consequences are not associated with this software.

> [!WARNING]
> **Please Note: According to the [*Neverness To Everness* Fair Play Declaration](https://nte.perfectworld.com/en/article/news/gamebroad/20260206/260828.html):**
>
> The use of any third-party tools that undermine fair gameplay is strictly prohibited. We will take strong action against violations involving illegal tools such as cheats, speed hacks, macro scripts, and similar software.
>
> Prohibited behaviors include, but are not limited to: auto-farming, skill acceleration, god mode, teleportation, and game data manipulation. Any account found to be involved in such activities will be banned upon verification.
>
> **You should fully understand and voluntarily assume all potential risks associated with using this tool.**

## 🚀 Download & Installation

The installer is recommended for most users and supports automatic updates:

1. Go to the [**Releases**](https://github.com/BnanZ0/ok-nte/releases) page.
2. Download the latest `ok-nte-win32-Global-setup.exe` file.
3. Double-click the installer and follow the prompts.

For source setup and detailed installation steps, see the [installation guide](docs/en/getting-started/installation.md).

## 🖥️ System Requirements

- **Operating System**: Windows.
- **Game Resolution**: 1920x1080 or higher (**16:9 aspect ratio only**).
- **Game Language**: Simplified Chinese / English.

## 📚 Documentation

| What you want to do | Recommended entry |
| --- | --- |
| Use ok-nte for the first time | [Installation](docs/en/getting-started/installation.md) → [Before you start](docs/en/getting-started/configuration.md) → [Quick start](docs/en/guides/quick-start.md) |
| Learn what the project supports | [Feature overview](docs/en/features/overview.md) |
| The update is stuck or a task has problems | [FAQ and feedback](docs/en/guides/troubleshooting.md) |
| Run from source or contribute | [Development documentation](docs/en/development/running-from-source.md) |
| Read the complete documentation | [Documentation site](https://ok-script.com/ok-nte/en/docs/) |

## 💬 Community

- **Discord**: [https://discord.gg/vVyCatEBgA](https://discord.gg/vVyCatEBgA)

## 🔗 Projects developed using [ok-script](https://github.com/ok-oldking/ok-script)

- Wuthering Waves [https://github.com/ok-oldking/ok-wuthering-waves](https://github.com/ok-oldking/ok-wuthering-waves)
- End Field [https://github.com/AliceJump/ok-end-field](https://github.com/AliceJump/ok-end-field)
- Genshin Impact (discontinued, but background story progression is still usable) [https://github.com/ok-oldking/ok-genshin-impact](https://github.com/ok-oldking/ok-genshin-impact)
- Girls' Frontline 2 [https://github.com/ok-oldking/ok-gf2](https://github.com/ok-oldking/ok-gf2)
- Honkai: Star Rail [https://github.com/Shasnow/ok-starrailassistant](https://github.com/Shasnow/ok-starrailassistant)
- Star-Resonance [https://github.com/Sanheiii/ok-star-resonance](https://github.com/Sanheiii/ok-star-resonance)
- Duet Night Abyss [https://github.com/BnanZ0/ok-duet-night-abyss](https://github.com/BnanZ0/ok-duet-night-abyss)
- Ash Echoes (discontinued) [https://github.com/ok-oldking/ok-baijing](https://github.com/ok-oldking/ok-baijing)

## ❤️ Support & Acknowledgments

### Contributors

<a href="https://github.com/BnanZ0/ok-nte/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=BnanZ0/ok-nte" />
</a>

### Sponsors

- **EXE Signing**: Free code signing provided by [SignPath.io](https://signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

### Acknowledgments

- [ok-oldking/OnnxOCR](https://github.com/ok-oldking/OnnxOCR)
- [zhiyiYo/PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)
- [Toufool/AutoSplit](https://github.com/Toufool/AutoSplit)
- [ImLaoBJie/ZZZSoundTrigger](https://github.com/ImLaoBJie/ZZZSoundTrigger)
