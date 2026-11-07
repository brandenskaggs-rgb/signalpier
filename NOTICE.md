# Third-party notices

SignalPier's own application, packaging, documentation, and website are MIT-licensed.

The bundled `static/world.json` is Natural Earth 1:110m land geometry, public domain:
https://www.naturalearthdata.com/about/terms-of-use/
Source: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson

The AppImage bundles Debian Bookworm ARM64 receiver tools and libraries: rtl-sdr 0.6.0-4 (GPL-2.0+), rtl_433 22.11-1 (GPL-2.0+), libusb 1.0.26-1 (LGPL-2.1+), and SoapySDR 0.8.1-3 (Boost Software License). Their original copyright files and license texts are included under the AppImage's `usr/share/doc`. Corresponding source archives and Debian packaging are provided in the same GitHub release as `SignalPier-0.1.0-alpha.2-third-party-sources.tar.gz`. These components are not relicensed under SignalPier's MIT license.

The type-2 AppImage runtime comes from AppImage/type2-runtime tag 20251108. Its MIT license and linked-library notices are included in the AppImage. Runtime source, build scripts, the patched libfuse source dependency, and squashfuse source are included in the third-party source archive. The runtime links musl, libfuse, squashfuse, zstd and zlib; their original licenses apply.

Python 3.10+ and base system libraries are supplied by the supported Raspberry Pi OS host. The optional Debian installer uses OS packages for its receiver tools.

- RTL-SDR: https://github.com/osmocom/rtl-sdr
- rtl_433: https://github.com/merbanan/rtl_433
- NOAA space weather: https://services.swpc.noaa.gov/

An upstream IQ sample from `merbanan/rtl_433_tests` was used during development to test the actual ARM64 decoder. The sample is not bundled or redistributed with SignalPier. Its pinned source and hash are recorded in the validation report.

SignalPier is an independent project. It is not affiliated with Raspberry Pi, NOAA, SDR++, Pocket25, or the HamClock project.
