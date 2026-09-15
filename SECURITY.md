# Security Policy

## Credential safety

Never include a real email address, password, cookie, server UUID, server address, or workflow log containing personal data in an issue or pull request.

If a credential was committed or printed publicly:

1. Change the Lunes Host password immediately.
2. Delete and recreate the affected GitHub Actions secret.
3. Remove the exposed value from Git history; deleting only the latest file is not sufficient.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting feature when it is enabled. Do not publish credential-handling vulnerabilities in a public issue before a fix is available.
