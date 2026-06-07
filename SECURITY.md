# Security Policy

## Reporting a vulnerability

If you believe you have found a security vulnerability, please **do not** open a public GitHub issue with exploit details.

Instead, report it privately to the repository maintainers through GitHub Security Advisories or by contacting the project owners directly. Include:

- A description of the issue and potential impact
- Steps to reproduce (if applicable)
- Affected components (files, endpoints, configuration)
- Any suggested mitigation

We will acknowledge receipt and work with you on a reasonable timeline to investigate and address valid reports.

## Secrets and credentials

**Never commit secrets to this repository.**

This includes:

- API keys (OpenAI, Azure OpenAI, DeepSeek, Gemini, Tavily, etc.)
- AWS access keys, session tokens, or IAM credentials
- Database connection strings with passwords
- Private endpoints or deployment-specific URLs that should not be public

Use environment variables loaded from `app/.env.local` (gitignored). See `app/.env.local.example` for the variable names only — not real values.

Before opening a PR:

- Confirm `.env`, `.env.local`, and `app/.env.local` are not staged
- Do not paste secrets into issues, PR descriptions, logs, or test fixtures
- Use mock providers and offline tests by default (`ENABLE_REAL_LLM=false`)

## Application security expectations

Contributors should follow practices documented in `skills/core/security-and-privacy.md`:

- Treat retrieved context (knowledge base, web search, records) as **untrusted input** until validated
- Validate external LLM output with schemas and quality checks where implemented
- Fail safely on configuration errors (e.g., placeholder deployment names in production mode)
- Avoid logging PII, full student queries, or complete model responses in production logs

## Responsible AI and data privacy

This toolkit is designed for **education-focused workflows**, not unconstrained general chat.

Expectations for deployments and contributions:

- **Accuracy** — AI-generated explanations may be incorrect. Downstream products should display disclaimers and encourage verification.
- **Not a substitute for educators** — Human review remains important for high-stakes learning, assessment, and grading decisions.
- **Student data** — Minimize collection, avoid logging identifiable student content unnecessarily, and follow applicable privacy laws and institutional policies in production deployments.
- **Provider data handling** — When `ENABLE_REAL_LLM=true`, queries are sent to configured third-party model providers. Operators are responsible for provider terms, data retention, and regional compliance.

## Supported versions

Security fixes are applied on the active development branch. There is no long-term support guarantee for early-stage releases.

## Disclosure

We aim to coordinate disclosure with reporters before publishing details of confirmed vulnerabilities.
