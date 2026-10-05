# Contributing to ScanSocial

Thank you for your interest in contributing to **ScanSocial**! We hold our codebase to senior engineering and production-grade standards.

## Code Standards

### Python Engine
- Formatted with `black` and `ruff`.
- Strict typing with type annotations on all domain entities and service methods.
- Minimum unit and domain logic test coverage of **80%**.
- All PRs must pass the 10-Criteria Benchmark suite (`pytest tests/test_benchmark_score.py`).

### Frontend & Tauri Shell
- TypeScript strict mode enabled (`noImplicitAny: true`).
- Clean separation between presentation components and Zustand state stores.
- Tailwind CSS with semantic tokens and dark/light mode compatibility.

## Commit Guidelines
We follow Conventional Commits:
- `feat: <feature description>`
- `fix: <bug fix description>`
- `docs: <documentation updates>`
- `test: <test suite additions>`
- `refactor: <code refactoring without functional changes>`

## Privacy & Safety Regulations
Contributions that introduce any of the following will be **immediately rejected**:
1. Fingerprint spoofing or proxy rotation designed to evade anti-abuse.
2. Circumvention of platform rate limits or CAPTCHA solvers.
3. Speculation of hidden phone numbers without legitimate provenance.
4. Bulk unsolicited messaging tools targeting personal messaging accounts.
