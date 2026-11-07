# SignalPier

**A small radio workbench app for Raspberry Pi 3.** Spectrum surveys, supported sensor decoding, a station clock, and a local encryption lab in one clean browser dashboard.

[Download the app](https://brandenskaggs-rgb.github.io/signalpier/downloads.html) · [Website](https://brandenskaggs-rgb.github.io/signalpier/) · [Setup guide](https://brandenskaggs-rgb.github.io/signalpier/guide.html)

SignalPier is **an application, not an operating system**. Install it on your existing Raspberry Pi OS. No reflashing is required.

## Install on Raspberry Pi 3

Requires **64-bit Raspberry Pi OS**, Python 3.10+, and an internet connection for missing system dependencies. Primary hardware target: Pi 3 Model B/B+ with 1 GB RAM.

1. Open the website on your Pi and click **Download for Raspberry Pi 3**.
2. Open the `.deb` with the system's software installer. If no graphical installer is available, open a terminal in Downloads and run:

```bash
sudo apt install ./signalpier_0.1.0-alpha.1_arm64.deb
```

3. Launch **SignalPier** from the application menu or open **http://127.0.0.1:8765** on the Pi.

The installer starts an unprivileged background service and installs the receiver utilities through your OS package manager. It does not change your Wi-Fi or replace your OS. Uninstall with `sudo apt remove signalpier`.

### Using your laptop's screen

On the laptop:

```bash
ssh -N -L 8765:127.0.0.1:8765 YOUR_USER@YOUR_PI
```

Keep the tunnel open and browse to http://127.0.0.1:8765. The Pi handles reception; your laptop renders the interface. A local server must not already occupy that port.

## What works in this alpha

- **Spectrum:** real `rtl_power` receiver adapter, waterfall, peak candidates, cancellation, JSON export.
- **Packets:** real `rtl_433` adapter for supported sensor/device protocols.
- **Station clock:** UTC/local clocks, callsign, Maidenhead locators, world sunlight map, approximate sunrise/sunset, DX short-path distance/bearing, optional NOAA Kp and solar flux.
- **Encryption lab:** native browser AES-256-GCM encryption and authenticated decryption of your own text.
- **Settings:** browser-local capture defaults.
- **Demo:** labeled synthetic captures for trying the UI without a receiver.
- **Updates:** online update notices with an Install update button in the packaged app. Installation starts only after clicking; reception, the clock, and the encryption lab work offline after setup. NOAA readings and update checks require internet.

Live reception needs a supported USB RTL-SDR and antenna. Only one program can own a receiver at a time. Installed tools are not proof that a receiver is connected. Hardware mode never silently substitutes simulated data.

This release does not implement P25 voice, automatic SDR++/Pocket25 integration, general encrypted-radio decryption, or over-the-air encrypted messaging. The local encryption lab is not a P25/DMR format and has no recipient identity, key exchange, or replay protection. Reticulum/LXMF is a future integration, not a bundled feature.

RTL-SDR Blog V3 is receive-only. Transmitting and programming handheld/mobile radios are not included in this alpha; they require separate hardware and model-specific integrations.

## Pi 3 performance design

- Python standard library server; no pip, containers, or Node.js runtime on the Pi.
- One receiver job at a time, 2–60 second captures, bounded process output.
- Plots capped at 30 sweeps and 1,024 peak-preserving bins per sweep. Export contains this reduced plot data; it is not a raw IQ recording.
- Status polling returns a small response when data hasn't changed.
- Charts, map shading and encryption run in the browser.
- The service has a 160 MB memory-pressure threshold and 256 MB hard memory limit.

These are configured constraints, not a guarantee of particular RF throughput. Raspberry Pi OS's packaged receiver drivers determine model support; older `librtlsdr` packages may need replacement for RTL-SDR Blog V4. Do not assume that every SDR, protocol, or frequency is supported.

## Validation

See [the validation report](docs/validation.json). Tests were run on Windows and inside an ARM64 Raspberry Pi OS userspace under QEMU. The actual ARM64 `rtl_433` binary decoded a pinned recorded Acurite IQ sample, and the unprivileged ARM64 server/capture pipeline passed.

**Physical Pi 3 boot, USB reception, thermal behavior, power stability, and sustained RF performance remain unverified.** This release is explicitly an alpha. The desktop installer integration also needs a physical Pi desktop check.

## Run from source

```bash
python3 app.py
```

Open http://127.0.0.1:8765. The clock, encryption lab and demo work without receiver executables. Linux users can alternatively install from source with `sudo bash scripts/install.sh`.

The automatic installer is included only in the `.deb` package. Source installations must be updated manually. The packaged updater downloads only this project's release, verifies its checksum and package identity, and installs it through APT.

## Develop and package

```bash
python3 -m unittest discover -s tests -v
node --test tests/crypto.test.cjs tests/solar.test.cjs
python3 scripts/build_site.py
python3 scripts/package.py
bash scripts/build-deb.sh
```

Node/Playwright are development-only dependencies. `npm ci` prepares browser checks; install a Playwright browser or set `BROWSER_CHANNEL=msedge`. Start the app on port 8766 and the static site on 8780 before `npm run test:browser`.

Troubleshooting: `systemctl status signalpier` and `journalctl -u signalpier -n 50 --no-pager`. Default binding is localhost; use SSH for remote access. This small HTTP service is not designed for public internet exposure.

## License

MIT for SignalPier's own code. Natural Earth map data is public domain. Receiver tools are separately licensed OS dependencies. See [NOTICE.md](NOTICE.md).
