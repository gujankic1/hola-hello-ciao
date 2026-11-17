# 1. Introduction and goals

## Purpose

A service that receives weather readings from sensors (temperature, humidity, wind speed, ...) and answers aggregate queries over them. It is a proof of concept for a take-home challenge, built in a few hours; documented gaps are acceptable.

## Requirements

Source: the "Weather Sensor Metrics API - Take-home brief" (Claude Doc owned by the project owner).

| # | Requirement | Status |
|---|---|---|
| F1 | Receive new metric values for a sensor through an API call (sensors must be registered first) | slice 1 |
| F2 | Answer queries: one/many/all sensors, one or more metrics, a statistic per metric (min, max, sum, avg), date range 1 day to 1 month (default: last 24 h) | slice 2 |
| T1 | REST API (UI optional), Python | slice 1 |
| T2 | Data persisted in a database | slice 1 |
| T3 | Input validation and exception handling | slice 1 (ingest), slice 2 (query) |
| T4 | README with run instructions and approach notes | slice 1 |
| T5 | Tests where useful (full coverage not expected) | slice 1 |
| T6 | Public source repository | open |

Example query: average temperature and humidity for sensor 1 in the last week.

## Quality goals

| Priority | Goal | Meaning |
|---|---|---|
| 1 | Simplicity | Few moving parts; easy to run, understand and change |
| 2 | Maintainability | Typed, tested, documented; every dependency and decision explainable |
| 3 | Low operating cost | One process, one file database, no external services |

## Stakeholders

| Role | Expectation |
|---|---|
| Owner / developer | A lean codebase that is quick to extend and that they can fully explain |
| Reviewers | Readable code, clear README, justified trade-offs |
| AI agents | Clear conventions and docs ([AGENTS.md](../../AGENTS.md)) |
