# skills/roles/ — AI Development Team Role Guides

This directory defines the AI development team for this repository.

Each file is a behaviour guide for a coding agent acting in that role. These roles exist to make AI-assisted development safer, more consistent, and more product-ready.

---

## Purpose

AI coding agents such as Claude Code, Codex, GitHub Copilot, Antigravity, or similar tools must know which role they are acting in for each task.

These role files prevent:

- unclear ownership
- scope creep
- duplicated effort
- hidden architecture changes
- unreviewed implementation
- stale documentation
- unsafe assumptions
- hallucinated APIs or fake test results

The goal is not bureaucracy. The goal is controlled, evidence-based development.

---

## Core Rule

No role may claim certainty without evidence.

If something was not checked, the role must say:

```txt
[NOT VERIFIED]