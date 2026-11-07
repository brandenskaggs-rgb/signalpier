#!/usr/bin/env bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python3 "$source_dir/scripts/build_deb.py"
build_dir=$(mktemp -d /var/tmp/signalpier-deb.XXXXXX)
trap 'rm -rf -- "$build_dir"' EXIT
cp -R "$source_dir/dist/deb-stage/." "$build_dir/"
find "$build_dir" -type d -exec chmod 755 {} +
find "$build_dir" -type f -exec chmod 644 {} +
chmod 755 "$build_dir/DEBIAN/"{postinst,prerm,postrm} "$build_dir/usr/bin/signalpier"
version=$(tr -d '\r\n' < "$source_dir/VERSION")
deb_version=${version/-alpha./~alpha}
dpkg-deb --root-owner-group --build "$build_dir" "$source_dir/dist/signalpier_${deb_version}_arm64.deb"
