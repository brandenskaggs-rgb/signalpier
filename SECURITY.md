# Security

SignalPier is early alpha software intended for local use. It binds to localhost and checks host/origin and a per-process request token for state-changing API calls. Use an SSH tunnel for remote access; do not directly expose the Python HTTP server to the internet.

Report security issues through the repository's private vulnerability reporting feature when available. Otherwise, open an issue requesting a private reporting channel without publishing exploit details or credentials.

The encryption lab uses browser-native AES-GCM but is an experiment, not a complete secure messaging protocol. It has no identity verification, key exchange or replay protection. It must not be described as an encrypted-radio system.
