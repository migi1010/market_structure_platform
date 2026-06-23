# AGENTS.md

# MIJI Quant Terminal + SEREnity Intelligence Platform

This document is the highest-priority project rulebook.

All architecture decisions, implementations, reviews, refactors, UI work, graph work, and investment systems must follow these rules.

---

# Project Mission

Build a professional market operating system.

Not:

* a dashboard
* a collection of pages
* a chatbot
* a stock screener
* a graph demo

The platform should feel closer to:

* Bloomberg Terminal
* TradingView
* Koyfin
* Finviz Elite

than a traditional SaaS dashboard.

---

# North Star

The platform should eventually answer:

What is the true bottleneck?

Who controls it?

Who supplies it?

Who enables it?

Who benefits first?

What is the risk?

What is the evidence?

Every feature must move the platform closer to answering those questions.

---

# Product Philosophy

SEREnity is an Industrial Intelligence Platform.

Core flow:

Theme
→ Technology
→ Process
→ Material
→ Equipment
→ Constraint
→ Controller
→ Hidden Opportunity

The system exists to discover:

* bottlenecks
* controllers
* monopoly suppliers
* hidden opportunities

before the market fully prices them.

---

# Truth First

Never fabricate:

* financial data
* market data
* company relationships
* supply-chain relationships
* graph edges
* catalysts
* bottlenecks
* investment conclusions
* portfolio allocations
* risk metrics

If evidence is missing:

Return explicit empty state.

Never invent data.

---

# Provenance First

Every graph relationship must have provenance.

Allowed:

* curated seed evidence
* approved research evidence
* deterministic system-generated relationships

Forbidden:

* LLM-generated graph edges
* guessed supplier relationships
* guessed company relationships
* generated market facts

Every relationship must be:

* explainable
* auditable
* traceable

---

# Architecture Rules

Backend owns:

* normalization
* validation
* graph construction
* cache policy
* scoring
* intelligence generation

Frontend owns:

* rendering
* navigation
* interaction
* visualization

Frontend must never invent business logic.

---

# Industrial Graph Rules

Industrial Graph is the source of truth.

Graph structure:

Theme
→ Technology
→ Process
→ Material
→ Equipment
→ Constraint
→ Company

Future:

Theme
→ Technology
→ Process
→ Material
→ Equipment
→ Constraint
→ Controller
→ Hidden Opportunity

Do not bypass graph layers.

No shortcut relationships.

---

# Phase 12 Rules

Industrial Graph must remain:

* deterministic
* evidence-backed
* reproducible

Use:

* SQLite
* NetworkX analytics

Do not use:

* GraphRAG runtime
* vector-generated relationships
* LLM-generated edges
* graph databases unless approved

NetworkX may only be used for:

* traversal
* dependency analysis
* centrality analysis
* path analysis

SQLite remains source of truth.

---

# Supply Chain Rules

Never infer:

* suppliers
* customers
* controllers

without explicit evidence.

Unknown relationships remain unknown.

Supply-chain relationships require provenance.

---

# Data Freshness Rules

Never represent stale data as live.

Allowed quote states:

* live
* cached
* stale
* fallback
* unavailable

Status must remain truthful end-to-end.

Frontend may not upgrade statuses.

---

# API Contract Rules

Backend contracts are authoritative.

Frontend may not:

* rename fields
* reinterpret statuses
* invent defaults
* fabricate fallback values

If backend returns null:

Render explicit empty state.

---

# TypeScript Rules

Strict typing required.

Forbidden:

any

unknown as any

@ts-ignore

non-null assertions without justification

Prefer:

explicit interfaces

discriminated unions

typed API contracts

exhaustive switch handling

---

# React Rules

Prefer:

server-safe rendering

stable keys

memoized expensive calculations

abortable fetches

shared hooks

Avoid:

hydration mismatches

duplicate state

duplicate requests

waterfall fetching

---

# Performance Rules

Prefer:

persisted intelligence

snapshot activation

generation-based cache invalidation

bounded traversal

incremental builds

Avoid:

N+1 queries

full graph rebuilds per request

frontend recomputation

duplicate aggregate fetches

---

# Testing Rules

Every phase requires:

pytest

TypeScript validation

production build

contract validation

No phase is complete without verification.

---

# Universal Search

Search must support:

* stocks
* themes
* sectors
* industries
* supply chains
* graph entities
* ETFs
* risk overlays

Search is navigation.

Not a ticker lookup box.

---

# Core Navigation

Market
→ Rotation
→ Theme
→ Supply Chain
→ Stock
→ Risk Overlay

Rotation is a primary destination.

Do not hide Rotation.

Risk is an overlay.

Not a standalone workspace.

---

# Theme Intelligence Rules

Theme pages must preserve:

Theme Summary
→ Why Now
→ Lifecycle
→ Catalysts
→ Bottlenecks
→ Beneficiaries
→ Supply Chain
→ Relationship Intelligence
→ Portfolio Context

Do not duplicate intelligence across cards.

---

# ContextDock Rules

ContextDock is the primary intelligence layer.

Single click:
Open ContextDock.

Double click:
Drilldown.

Hover:
Preview only.

Hover must never trigger heavy intelligence fetches.

ContextDock must eventually support:

* stocks
* themes
* sectors
* supply chains
* graph entities
* risks

---

# Stock Workspace

Final drilldown destination.

Target:

70% chart

30% contextual intelligence

Modules:

* Smart Money
* Bubble
* Theme Exposure
* Supply Chain Exposure
* Risk Overlay

should behave as overlays or dock panels.

---

# Alpha Pages

Behave like institutional screeners.

Prefer:

* dense tables
* rankings
* factor exposure

Avoid:

* dashboard cards
* oversized summary widgets

---

# Design Principles

Terminal First

Dark professional workspace.

Chart First

Charts are primary.

Tables support charts.

Dense Information

Scanability over card count.

Context First

Intelligence should be one click away.

Chinese First

Chinese labels first.

English secondary.

---

# UX Review Process

Before major UI implementation:

1. Architecture Review
2. Product Review
3. Workflow Review
4. Browser Inspection
5. Visual Audit
6. Mockup Approval

before coding.

Visual quality has higher priority than feature quantity.

Always review:

* hierarchy
* typography
* density
* treemap quality
* heatmap quality
* hover states
* selection states

before implementation.

---

# Phase 11 Rules

Investment Committee consumes evidence.

Agents do not create facts.

Agents evaluate facts.

Evidence always wins over opinion.

Committee decisions must be traceable.

---

# Investment Rules

The platform does not generate buy recommendations from LLM opinion.

Investment conclusions must be supported by:

Theme

Technology

Process

Material

Equipment

Constraint

Controller

Valuation

Risk

Evidence Coverage

Every recommendation must be explainable.

---

# Final Rule

If a proposed feature improves visual complexity but does not improve:

* bottleneck discovery
* controller discovery
* supply-chain understanding
* hidden opportunity detection
* investment decision quality

it should be reconsidered.
