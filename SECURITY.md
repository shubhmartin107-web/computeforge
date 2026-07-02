# Security Policy

## Supported Versions

| Version | Supported          |
|---------|-------------------|
| 0.1.x   | ✅ Active         |

## Reporting a Vulnerability

ComputeForge takes security seriously. If you discover a security vulnerability,
please do NOT open a public issue. Instead, report it privately to the maintainers.

**Contact**: security@computeforge.ai

We will acknowledge receipt within 48 hours and provide a timeline for a fix.

## Security Considerations

When using ComputeForge:

1. **API Keys**: Never commit API keys. Use environment variables.
2. **Browser Safety**: The default policy blocks dangerous JavaScript execution.
   Review policies before enabling `browser.evaluate`.
3. **Network Access**: ComputeForge can navigate to any URL. Review the
   `blocklist_domains` policy configuration for your use case.
4. **Desktop Control**: Desktop actions (click, type) are blocked by default
   and require explicit policy changes to enable.
5. **Docker**: When using Docker, ensure the container has appropriate
   network restrictions.
