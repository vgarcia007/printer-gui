# Security policy

Print & Scan Hub has no authentication and is intended only for a trusted private network. Access to the web port grants the ability to submit print jobs, start scans, download scans, rename files, and permanently delete scan files.

Do not expose port 8081 directly to the internet. Use an authenticated HTTPS reverse proxy or a VPN for remote access. CUPS, scanner, and OCR ports must remain unpublished.

Report vulnerabilities through a private security advisory in the project's GitHub repository. Never include credentials, private addresses, document contents, or scanned files in a public issue.

Keep .env and config/printers.local.json out of Git. If migrating from BrotherScannerDocker, revoke any Telegram bot token that ever appeared in its Compose file. Print & Scan Hub does not use Telegram.
