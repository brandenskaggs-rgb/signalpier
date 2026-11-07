# Third-party notices

SignalPier's own application, packaging, documentation, and website are MIT-licensed.

The bundled `static/world.json` is Natural Earth 1:110m land geometry, public domain:
https://www.naturalearthdata.com/about/terms-of-use/
Source: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson

The installer declares dependencies on separately distributed Raspberry Pi OS/Debian packages: Python 3, RTL-SDR utilities and rtl_433. These are not re-licensed under SignalPier's MIT license. Their licenses and copyright notices are supplied by those packages in `/usr/share/doc/`. Their corresponding source is available from the configured distribution source repositories.

- RTL-SDR: https://github.com/osmocom/rtl-sdr
- rtl_433: https://github.com/merbanan/rtl_433
- NOAA space weather: https://services.swpc.noaa.gov/

An upstream IQ sample from `merbanan/rtl_433_tests` was used during development to test the actual ARM64 decoder. The sample is not bundled or redistributed with SignalPier. Its pinned source and hash are recorded in the validation report.

SignalPier is an independent project. It is not affiliated with Raspberry Pi, NOAA, SDR++, Pocket25, or the HamClock project.
