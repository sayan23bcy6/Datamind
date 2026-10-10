# Security

The old local development credentials were committed in an earlier commit and must be treated as compromised. The project history was not rewritten, and the values should not be reused in any environment.

Any environment that used the previous credential set must have its Postgres password rotated manually by the project owner. This is out of scope for the code change and must be handled outside of this repository.

Production deployments must use a secret manager such as Azure Key Vault, GitHub Actions secrets, or an equivalent platform-managed secret store. Local development values must never be reused in production, and production credentials must never read from the local `.env` files used for development.
