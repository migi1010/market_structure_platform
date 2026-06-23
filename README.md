# MIJI Research OS

## AI-Assisted Industrial Intelligence Platform

A full-stack AI-assisted industrial intelligence platform that integrates theme discovery, industrial dependency mapping, dynamic ranking, evidence lineage, and company-level research workflows into a unified decision-support system.

## Why This Project Matters

MIJI Research OS is designed as a research and decision-support prototype for complex industrial domains. Although the current demo uses financial-market and industrial-theme data, the core engineering value is not stock picking. The system demonstrates how heterogeneous data can be organized into themes, bottlenecks, dependency paths, entity roles, evidence lineage, dynamic rankings, and research workflows.

This architecture is relevant to industrial decision environments where teams need to understand what is changing, why it matters, which dependencies are affected, and what evidence supports each conclusion.

## Smart Manufacturing Relevance

The same architecture can generalize to smart manufacturing scenarios such as:

- Process bottleneck analysis
- Equipment constraint tracking
- Material and supplier dependency mapping
- Yield-loss root-cause investigation
- Production risk monitoring
- Cross-functional decision support
- Manufacturing knowledge management

For a manufacturing organization, the workflow can be reframed as:

```text
Factory signals
-> issue / opportunity discovery
-> process-theme analysis
-> equipment / material / supplier dependency map
-> affected tool / line / supplier research
```

## System Workflow

The current demo workflow is:

```text
Rotation -> Scout -> Theme -> Supply Chain -> Stock Research
```

For industrial decision support, the same workflow maps to:

```text
Signal Detection
-> Theme Discovery
-> Industrial Analysis
-> Dependency Mapping
-> Company / Entity Research
```

Each workspace has a distinct responsibility:

| Workspace | Research Question | Industrial Analogy |
| --- | --- | --- |
| Rotation | Where are signals moving? | Factory / market signal detection |
| Scout | What deserves research next? | Issue or opportunity discovery |
| Theme | Why does this theme matter? | Process-theme analysis |
| Supply Chain | How does this industry work? | Equipment, material, supplier dependency mapping |
| Stock Research | Which company or entity benefits and why? | Affected tool, line, vendor, or supplier research |

## Core Modules

### 1. Dynamic Theme Registry

A projection-only registry that consolidates themes from graph, Scout, and research sources. The registry answers: what themes exist? It does not replace source-of-truth systems.

### 2. Dynamic Theme Ranking

A deterministic ranking layer that identifies which industrial themes matter now. Ranking augments the registry and supports workspace ordering without creating buy/sell recommendations.

### 3. Theme Scout

An LLM-ready proposal provider with strict validation, evidence manifests, and a human-review boundary. Scout candidates are research candidates only. They do not create graph nodes, graph edges, companies, recommendations, or downstream analytical records without validation.

### 4. Supply Chain Intelligence

Graph-backed bottleneck, controller, beneficiary, and dependency-path analysis. The workspace is designed to answer where the industrial constraint is and which entities are connected through persisted evidence-backed relationships.

### 5. Stock / Company Research Workspace

A company-level research memo showing theme exposure, supply-chain role, evidence chain, research completeness, related entities, and decision-support context. It is positioned as entity research, not as a quote dashboard.

### 6. Evidence Lineage

Every research output is traceable to source evidence and persisted relationships. Unknown information remains explicit rather than being treated as favorable or complete.

### 7. Full-Stack Research OS

The platform combines a FastAPI backend, deterministic projection engines, SQLite persistence, a Next.js / React / TypeScript frontend, and automated validation across backend tests, frontend type checks, production builds, and browser workflows.

## Architecture Overview

MIJI Research OS uses a projection-first architecture:

```text
Persisted Evidence + Industrial Graph
        |
        v
Deterministic Projection Engines
        |
        v
Theme Registry / Ranking / Scout / Supply Chain / Stock Research
        |
        v
Research OS Workspaces
```

Key architecture principles:

- Source-of-truth boundaries are explicit.
- Read models are projection layers, not hidden mutation systems.
- Evidence lineage is preserved across research outputs.
- Ranking and scoring are deterministic and reproducible.
- Frontend workspaces have separated responsibilities.
- Missing evidence remains unknown rather than being fabricated.

## Tech Stack

### Backend

- Python
- FastAPI
- SQLite
- Deterministic projection engines
- NetworkX for graph preparation/export
- pytest

### Frontend

- Next.js
- React
- TypeScript
- CSS modules / global design system
- Browser workflow validation

### Architecture

- Projection-first read models
- Source-of-truth boundaries
- Evidence lineage
- Deterministic ranking
- Frontend workspace responsibility separation

## Testing and Validation

Latest local validation:

- Backend pytest: 442 passed
- Frontend `npm test`: passed
- Frontend `npx tsc --noEmit`: passed
- Frontend `npm run build`: passed

The system has been validated locally with automated backend tests, frontend tests, TypeScript checks, production build checks, and browser workflow validation.

This is a prototype and local research system, not a production-certified manufacturing deployment.

## Demo Workflow

Suggested GitHub or interview demo path:

1. Open the Research OS and start at Rotation.
2. Show how high-level signals are ranked and organized.
3. Move to Scout to show research candidate intake and validation boundaries.
4. Open Theme to explain why a theme matters and what evidence supports it.
5. Open Supply Chain to show bottleneck-centered dependency mapping.
6. Open Stock Research to show company/entity exposure, role, evidence chain, and research completeness.
7. Emphasize that all major outputs are projections from persisted evidence and deterministic engines.

Manufacturing framing for the same demo:

1. Detect signal changes from factory or operational data.
2. Identify a process issue, constraint, or opportunity worth research.
3. Map the issue to process, material, equipment, supplier, and constraint dependencies.
4. Trace which entity, tool, line, or vendor is affected.
5. Use evidence lineage to support cross-functional decisions.

## Interview Talking Points

### How I would explain this project in a TSMC interview

Chinese version:

> 這個專案雖然目前使用金融與產業主題資料作為示範，但我真正想呈現的是一套智慧決策平台的工程能力。它可以把不同來源的資料整理成主題、瓶頸、關聯路徑與公司角色，並透過前後端系統讓使用者追蹤研究流程。這種架構可以對應到智慧製造中的製程瓶頸分析、設備異常追蹤、供應鏈風險、良率改善決策與跨部門決策支援。

English version:

> Although the current demo uses market and industrial-theme data, the core system is an AI-assisted industrial intelligence platform. It integrates heterogeneous data into themes, bottlenecks, dependency paths, entity roles, evidence lineage, and research workflows. The same architecture can be applied to smart manufacturing problems such as process bottleneck analysis, equipment constraint tracking, supplier dependency mapping, yield-loss investigation, and operational decision support.

### Resume Bullet Examples

- Built a full-stack AI-assisted industrial intelligence platform using FastAPI, Next.js, SQLite, and TypeScript, integrating dynamic theme ranking, supply-chain dependency mapping, evidence lineage, and company-level research workflows.
- Designed a Research OS workflow from signal detection to theme discovery, industrial dependency analysis, and entity-level research, enabling structured analysis of bottlenecks, controllers, beneficiaries, and supporting evidence.
- Implemented deterministic projection engines for theme registry, theme ranking, supply-chain intelligence, and stock/company research, with 400+ backend tests and frontend type/build validation.
- Applied AI-assisted development workflow to rapidly prototype, test, and validate complex research modules while maintaining strict source-of-truth boundaries and reproducible validation.

## Future Extensions

Potential manufacturing-oriented extensions:

- Connect machine, process, recipe, metrology, and yield data sources.
- Replace demo market signals with factory event streams or MES/SPC indicators.
- Extend the industrial graph with material, equipment, chamber, recipe, and process-step entities.
- Add reviewed evidence pipelines for engineering reports, logs, quality events, and supplier records.
- Build role-specific workspaces for process engineers, equipment engineers, manufacturing data engineers, and operations managers.

## Disclaimer

This project is a research and decision-support system prototype. It does not provide investment advice, buy/sell recommendations, target prices, or automated trading actions.
