# EVALS.md

## Purpose

Define how the system evaluates agent performance and detects regressions.

## Intent

Evals keep the system honest. The goal is to measure outcomes:
- single-pass success
- verification friction normalized by complexity
- QA defect pressure
- reopen rate
- expert effectiveness by context key

## Where eval data comes from

- Signal Stream events
- Outcome Ingestor aggregates
- Provenance links from the Assembler

## What to add first

- intent correctness checks (does intent match issue)
- routing correctness checks (did we consult required expert classes)
- verification friction checks (iterations, time-to-green)
- QA checks (defects mapped to acceptance criteria)
