#!/bin/sh
if command -v xdg-open >/dev/null 2>&1 && { [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; }; then
  exec xdg-open http://127.0.0.1:8765
fi
printf '%s\n' 'SignalPier: http://127.0.0.1:8765' 'From another computer: ssh -N -L 8765:127.0.0.1:8765 YOUR_USER@YOUR_PI'
