# Security

## Reporting a vulnerability

Report suspected vulnerabilities privately to Swayam Debata at swayamdebata2003@gmail.com.

You can also open a private GitHub security advisory at https://github.com/SwayamDebata/orqmesh/security/advisories/new. Do not post exploit details, credentials, or customer data in public issues or pull requests.

The supported line is the latest published release. Fixes are shipped in a new version.

## Scope

Orqmesh is an early prototype and has not undergone a production security review. Do not process sensitive information or use it for production side effects without an independent security assessment and appropriate application controls.

Local JSON checkpoints are unencrypted and have no cross-process concurrency controls. Tool allowlists do not sandbox code or authorize human reviewers. The consuming application must provide authentication, authorization, data protection, audit, and side-effect idempotency.
