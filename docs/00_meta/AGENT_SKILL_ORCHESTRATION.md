# Agent Skill — Documentation Orchestration

> **Status:** Active | **Last updated:** 2026-09-18

## Purpose

Treat documentation as operational memory.

## Canonical files

- Product truth: `01_definition/`
- Execution truth: `02_execution/07_progress.md`
- Decisions: `02_execution/08_decisions_log.md`
- Backlog: `02_execution/09_backlog.md`
- Technical truth: `04_technical/`

## Required workflow

**Read → Plan → Change → Validate → Document**

An agent must identify whether a request changes implemented code, target architecture,
backlog, deployment behavior, database schema, authorization, or RTL/i18n behavior.

Do not duplicate the same progress/backlog state across multiple files.
