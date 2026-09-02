# Security

## Sensitive data boundary

This repository and its release archives must never contain proxy subscription
URLs, node definitions, server addresses, UUIDs, passwords, Google tokens,
cookies, Antigravity conversations, account databases, generated Mihomo
configuration, or unredacted runtime logs.

The application discovers supported local proxy-client caches at runtime and
writes generated state only under `%LOCALAPPDATA%\Antigravity\private-proxy`.
That directory is not part of the source tree or release archive.

## Reporting

Open a GitHub security advisory for vulnerabilities. Do not paste credentials,
subscription links, account data, or raw logs into a public issue.
