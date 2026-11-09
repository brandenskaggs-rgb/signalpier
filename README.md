# SignalPier

**A small radio workbench app for Windows 10/11 and Raspberry Pi 3.** Spectrum surveys, supported sensor decoding, a station clock, and a local encryption lab in one clean browser dashboard.

[Download the app](https://brandenskaggs-rgb.github.io/signalpier/downloads.html) · [Website](https://brandenskaggs-rgb.github.io/signalpier/) · [Setup guide](https://brandenskaggs-rgb.github.io/signalpier/guide.html)

SignalPier installs on your existing Windows or 64-bit Raspberry Pi OS system.

## Install on Windows 10/11

Download **SignalPier-0.1.0-alpha.4-windows-x64-Setup.exe**, run setup, and launch SignalPier from the Start menu. Python and receiver tools are bundled. Windows x64 is supported; the build is tested on Windows 11, with separate Windows 10 testing pending. This alpha installer is unsigned.

If your RTL-SDR needs a USB driver, follow the website's Windows USB setup guide to install WinUSB for the SDR's Bulk-In Interface 0. The application does not automatically replace device drivers. Uninstall through Windows Settings → Apps.

On both platforms, a newer release triggers an **Update available** pop-up with **Install update** and **Later**. Settings → **Check for updates** checks immediately. The Windows updater verifies the setup download, closes the current app, installs into the same folder, and reopens SignalPier. Updates are never installed automatically.

## Install on Raspberry Pi 3

Requires **64-bit Raspberry Pi OS Bookworm or newer**, with its system Python 3.10+. Primary hardware target: Pi 3 Model B/B+ with 1 GB RAM. A desktop browser displays the dashboard.

1. Open the website on your Pi and click **Download AppImage for Pi 3**.
2. Right-click the downloaded file → Properties → Permissions → allow execution as a program.
3. Double-click it. SignalPier opens its dashboard and adds an application-menu shortcut.

Terminal equivalent:

```bash
chmod +x SignalPier-0.1.0-alpha.4-aarch64.AppImage
./SignalPier-0.1.0-alpha.4-aarch64.AppImage
```

The AppImage includes `rtl_power`, `rtl_433` and their receiver libraries. First launch copies the app to `~/.local/share/signalpier/SignalPier.AppImage`; subsequent launches use the menu shortcut. It runs as your user. Choose **Quit SignalPier** in the dashboard to stop it. If receiver access is denied, **Settings → Enable USB receiver access** requests administrator permission to add the bundled RTL-SDR USB rules; reconnect the dongle afterward.

If FUSE is unavailable, launch with `--appimage-extract-and-run`. The AppImage handles extraction internally. To remove SignalPier, quit it and delete `~/.local/share/signalpier` and `~/.local/share/applications/signalpier.desktop`. The `.deb` remains an optional alternative for service-based installations.

### Using your laptop's screen

On the laptop:

```bash
ssh -N -L 8765:127.0.0.1:8765 YOUR_USER@YOUR_PI
```

Start the AppImage on the Pi with `--no-browser`. Keep the tunnel open and browse to http://127.0.0.1:8765. The Pi handles reception; your laptop renders the interface. If the Pi's port is occupied, SignalPier prints its chosen port; adjust the tunnel accordingly.

## What works in this alpha

- **Receiver setup:** automatic RTL-SDR inventory, name/serial selection, and an explicit connection test. Permission, busy, disconnected, missing-driver and timeout states explain the next step. Tests are excluded while a capture is running; discovery does not claim a receiver is ready.
- **Startup help:** launcher exceptions are saved locally and displayed in a browser error page.

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
- The optional Debian service has a 160 MB memory-pressure threshold and 256 MB hard memory limit. These systemd limits do not apply to the user-run AppImage.

These are configured constraints, not a guarantee of particular RF throughput. The AppImage bundles the Bookworm RTL-SDR driver for standard RTL2832U receivers including Blog V3; Blog V4 is not supported by this build. Do not assume that every SDR, protocol, or frequency is supported.

## Validation

See [the validation report](docs/validation.json). The ARM64 AppImage was launched under QEMU with extract-and-run. User-owned installation, menu shortcut, bundled receiver-tool availability, demo capture, update support and Quit passed. Unit and browser tests also cover AppImage update replacement and its user interface. The actual ARM64 `rtl_433` binary decoded a pinned recorded Acurite IQ sample, and the unprivileged ARM64 server/capture pipeline passed.

**Physical Pi 3 boot, USB reception, thermal behavior, power stability, and sustained RF performance remain unverified.** This release is explicitly an alpha. The desktop installer integration also needs a physical Pi desktop check.

## Run from source

```bash
python3 app.py
```

Open http://127.0.0.1:8765. The clock, encryption lab and demo work without receiver executables. Linux users can alternatively install from source with `sudo bash scripts/install.sh`.

Both the AppImage and optional `.deb` support online update notices. In the AppImage, **Install update** downloads and verifies the new ARM64 AppImage, then atomically replaces the user-owned installed copy. Quit and reopen from the menu after installation. No update runs until you click. Source installations are updated manually; the `.deb` updater uses APT.

## Develop and package

```bash
python3 -m unittest discover -s tests -v
node --test tests/crypto.test.cjs tests/solar.test.cjs
python3 scripts/build_site.py
python3 scripts/package.py
bash scripts/build-deb.sh
# Linux build with a prepared Bookworm ARM64 sysroot:
python3 scripts/build-appimage.py /path/to/arm64-sysroot
```

Node/Playwright are development-only dependencies. `npm ci` prepares browser checks; install a Playwright browser or set `BROWSER_CHANNEL=msedge`. Start the app on port 8766 and the static site on 8780 before `npm run test:browser`.

Troubleshooting: `systemctl status signalpier` and `journalctl -u signalpier -n 50 --no-pager`. Default binding is localhost; use SSH for remote access. This small HTTP service is not designed for public internet exposure.

## License

MIT for SignalPier's own code. Natural Earth map data is public domain. Receiver tools are separately licensed OS dependencies. See [NOTICE.md](NOTICE.md).
