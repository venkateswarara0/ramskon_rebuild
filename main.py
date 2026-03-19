import os
import re
import json
import requests
import urllib.parse
from uuid import uuid4
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

from db import get_connection

try:
    from groq import Groq
except ImportError:
    Groq = None

load_dotenv()

app = Flask(__name__, template_folder="app/templates", static_folder="app/static")
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret-key")
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "app/static/uploads")
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "pdf", "jpg", "jpeg", "png", "mp4", "mp3",
    "doc", "docx", "txt", "zip"
}

COURSES_DATA = [
    ("Video Editing", "Learn editing fundamentals, storytelling, pacing, transitions, audio cleanup, reels workflow, client edits, and delivery.", "Creative & Agency Skills"),
    ("Graphic Designing", "Learn design principles, layout, typography, color, branding, social media creatives, and practical design workflow.", "Creative & Agency Skills"),
    ("Motion Graphics", "Learn animation basics, motion principles, title animation, transitions, promo videos, and content motion design.", "Creative & Agency Skills"),
    ("UI/UX Design", "Learn design thinking, wireframes, user flows, prototypes, research, UI systems, and practical product design.", "Creative & Agency Skills"),
    ("Thumbnail Designing", "Learn thumbnail psychology, CTR design, composition, contrast, visual hooks, and practical channel work.", "Creative & Agency Skills"),
    ("Social Media Content Creation", "Learn content ideas, scripting, hooks, content pillars, platform adaptation, and content planning.", "Creative & Agency Skills"),
    ("Generative AI", "Learn generative AI concepts, tools, prompt usage, image/text generation, and business use cases.", "AI & Tech Skills"),
    ("AI & Machine Learning Basics", "Learn ML foundations, supervised learning, models, data basics, training ideas, and beginner workflows.", "AI & Tech Skills"),
    ("AI Automation", "Learn automation with no-code tools like Zapier and Make, workflow logic, integrations, and business automation.", "AI & Tech Skills"),
    ("Prompt Engineering", "Learn structured prompts, context handling, system prompts, role prompting, chain prompting, and practical results.", "AI & Tech Skills"),
    ("ChatGPT & AI Tools Mastery", "Learn AI workflows, productivity systems, research usage, automation ideas, and client-facing use cases.", "AI & Tech Skills"),
    ("Web Development", "Learn frontend, backend, databases, APIs, auth, deployment, and real website building.", "Development Skills"),
    ("Python Programming", "Learn Python syntax, logic, loops, functions, files, OOP, APIs, and practical mini projects.", "Development Skills"),
    ("Full Stack Development", "Learn frontend, backend, database design, authentication, APIs, deployment, and full product workflow.", "Development Skills"),
    ("App Development", "Learn app basics, UI flow, backend integration, APIs, user experience, and deployment foundations.", "Development Skills"),
    ("Digital Marketing", "Learn funnels, offers, content, ads, branding, customer journey, analytics, and agency-oriented marketing.", "Marketing & Business Skills"),
    ("SEO", "Learn keyword research, on-page SEO, technical SEO, backlinks, content SEO, and ranking systems.", "Marketing & Business Skills"),
    ("Social Media Marketing", "Learn platform growth, strategy, brand content, ad basics, lead generation, and campaign planning.", "Marketing & Business Skills"),
    ("Freelancing & Personal Branding", "Learn client outreach, proposals, pricing, positioning, social proof, and personal brand building.", "Marketing & Business Skills"),
    ("Agency Building & Client Acquisition", "Learn service packaging, niche selection, lead generation, sales systems, onboarding, and delivery.", "Marketing & Business Skills"),
]

SPINE_SOURCES_TEXT = r"""
Video Editing — spine sources used for coverage and ordering.
T01 Foundations: editing goals, story intent, basic terminology (shots, sequences, continuity). Time=low | Prereq=none
T02 Tooling landscape: NLE concepts, project setup, sequence settings, shortcuts. Time=medium | Tools=NLEs | Output=setup checklist
T03 Media fundamentals: codecs/containers, frame rate, resolution, audio sample rate, proxies. Time=medium | Workflow=ingest→organize→edit→finish→deliver
T04 Ingest & organization: folder hygiene, bin structure, naming, backups, relinking. Time=medium | Output=project template
T05 Timeline essentials: trims (ripple/roll/slip/slide), cut types, pacing basics. Time=medium | Prereq=T01–T04
T06 Story craft in edit: continuity, J/L cuts, b-roll, visual grammar, montage logic. Time=medium
T07 Audio for editors: dialogue cleanup, music beds, SFX, basic mixing, loudness targets. Time=high | Prereq=T05
T08 Color correction basics: exposure/white balance, matching shots, scopes-first mindset. Time=high | Prereq=T05
T09 Titles & captions: lower thirds, typography rules, subtitles/captions workflow. Time=medium | Output=brand title pack
T10 Motion + effects basics: keying, masking, motion tracking (intro), stabilization. Time=high | Prereq=T05
T11 Time manipulation: speed changes, time remapping, speed ramps, optical flow caveats. Time=medium | Pitfall=artifacting
T12 Multicam editing: sync strategies, angle switching, audio-first decisions. Time=high | Prereq=T05
T13 Performance workflow: caches, proxies, storage throughput, GPU settings, troubleshooting. Time=medium
T14 Collaboration basics: handoffs, sharing projects, archiving, deliverable packaging. Time=medium | Output=handoff checklist
T15 Export & delivery: masters vs publish exports, QC pass, platform-safe presets. Time=high | Prereq=T05–T10
T16 Accessibility & compliance: captions quality, flash/epilepsy considerations, privacy basics. Time=medium
T17 Best practices: consistent project templates, incremental saves, color/audio checkpoints. Time=low
T18 Portfolio Project A: 60–90s story edit (audio mix + basic grade + titles). Time=high | Output=case study
T19 Portfolio Project B: multi-format repurpose pack (16:9 + 9:16 + 1:1 exports). Time=high | Prereq=T15
T20 Common pitfalls: mixed frame rates, clipping audio, over-grading, no backups, ignoring QC. Time=low | Output=pitfall checklist

Graphic Designing — spine sources used for coverage and ordering.
T01 Foundations: elements/principles, hierarchy, balance, whitespace, critique vocabulary. Time=medium | Prereq=none
T02 Raster vs vector: resolution, DPI/PPI, file formats, color modes (RGB/CMYK). Time=medium
T03 Tool setup: workspaces, non-destructive mindset (layers, masks, versions). Time=medium | Tools=common design suites
T04 Typography essentials: font pairing, hierarchy, readability, alignment, spacing. Time=high | Output=type system mini-guide
T05 Color theory + accessibility: harmonies, contrast, color-blind safety, palette creation. Time=high | Output=palette set
T06 Layout systems: grids, modular scales, spacing rules, responsive layouts vs print pages. Time=high
T07 Image editing basics: crop, levels, selection tools, retouch, compositing principles. Time=high | Prereq=T02–T03
T08 Vector drawing: paths, pen tool logic, booleans, icon sets, logo construction. Time=high
T09 Branding fundamentals: identity components, tone, usage rules, brand kit concept. Time=high | Output=style guide outline
T10 Social/web assets: export settings, safe margins, template systems, batch exports. Time=medium
T11 Print production basics: bleeds, preflight, PDF export, typography for print. Time=medium
T12 Asset management: libraries, components, shared folders, naming conventions. Time=medium
T13 Collaboration workflow: feedback loops, annotations, version control for design files. Time=medium
T14 Design QA: consistency checks (type, color, spacing), accessibility checks, proofing. Time=medium
T15 Best practices: design brief → moodboard → iterations → final specs; document decisions. Time=low
T16 Legal basics: licensing fonts/images, usage rights, attribution norms. Time=medium
T17 Portfolio Project A: logo + mini identity kit (palette, type, usage, mockups). Time=high | Output=case study
T18 Portfolio Project B: campaign set (poster/flyer + 6 social creatives + variants). Time=high
T19 Assessment: critique rubric + before/after iterations + export spec sheet. Time=medium
T20 Common pitfalls: random fonts, low contrast, inconsistent spacing, destructive edits, no brief. Time=low

Motion Graphics — spine sources used for coverage and ordering.
T01 Foundations: motion principles (timing, spacing, easing), storyboards/animatics. Time=medium | Prereq=basic design
T02 Tool chain overview: compositing app, 3D tool (optional), asset pipeline. Time=medium | Tools=AE/C4D/Blender/Lottie
T03 Project setup: frame rates, comp sizes, safe areas, naming/versioning standards. Time=medium
T04 Shape/vector workflows: importing vectors, shape layers, boolean ops, trim paths. Time=high
T05 Keyframes & easing: graph editor concepts, motion blur, natural motion patterns. Time=high | Prereq=T01
T06 Kinetic typography: readable type motion, hierarchy in time, subtitle animation. Time=high
T07 Masks & mattes: alpha/luma mattes, roto basics, edge artifacts management. Time=high
T08 2.5D/3D basics: cameras, lights, parallax, depth cues, DOF tradeoffs. Time=high
T09 Tracking basics: attach graphics to footage, stabilize, manual vs assisted tracking. Time=high
T10 Compositing fundamentals: blending modes, color correction, grain, matching plates. Time=high
T11 Expressions intro: linking properties, loops, basic math, debugging errors. Time=high | Prereq=T05
T12 Template thinking: reusable rigging (controllers), modular precomps, naming discipline. Time=medium
T13 3D integration (optional): C4D/Blender scene basics, render passes, compositing. Time=high | Prereq=T10
T14 Delivery formats: video exports, transparency/alpha workflows, GIF pitfalls, web formats. Time=medium
T15 Lottie pipeline: constraints, export considerations, testing on target runtime. Time=high | Prereq=T04
T16 Best practices: keep comps clean, precomp rules, performance-friendly effects. Time=low
T17 Portfolio Project A: 8–12s logo sting + lower-third pack (3 styles). Time=high | Output=brand motion kit
T18 Portfolio Project B: 20–30s micro-explainer with sound + captions. Time=high
T19 Portfolio Project C: Lottie animation shipped + “limits learned” write-up. Time=high | Prereq=T15
T20 Common pitfalls: messy timelines, overuse of effects, unreadable type, untested exports. Time=low

UI/UX Design — spine sources used for coverage and ordering.
T01 Foundations: UX vs UI vs product design, deliverables, success metrics. Time=low | Prereq=none
T02 Human-centred process: plan research, design, evaluate iteratively across lifecycle. Time=medium | Prereq=none
T03 Discovery research: stakeholder interviews, user interviews, surveys, desk research. Time=high | Output=research plan
T04 Synthesis: personas, JTBD/hypotheses, problem statements, opportunity mapping. Time=high | Prereq=T03
T05 Information architecture: content inventory, sitemaps, navigation models, card sorting. Time=high
T06 Interaction design: user flows, task flows, edge cases, error states, microinteractions. Time=high
T07 Wireframing: low-fi layouts, responsive patterns, prioritization, annotation. Time=medium
T08 UI foundations: typography, spacing systems, color/contrast, consistency patterns. Time=high | Prereq=T07
T09 Platform guidance: designing within ecosystem conventions (Apple-style + Material-style). Time=medium | Prereq=T08
T10 Design systems: components, variants, tokens, naming, documentation, governance. Time=high
T11 Prototyping: interactive flows, transitions, stateful components, accessible prototypes. Time=high | Prereq=T06
T12 Heuristic evaluation: apply usability heuristics; write actionable findings. Time=medium | Output=heuristic report
T13 Usability testing: test plan, scripts, moderation, analysis, prioritization. Time=high | Prereq=T11
T14 Accessibility: WCAG principles, touch targets, keyboard flow, contrast, content. Time=high | Prereq=T08
T15 Handoff: specs, redlines, assets, design tokens, dev Q&A workflow. Time=medium
T16 Product analytics thinking: event taxonomy, funnels, iteration loops (non-tool-specific). Time=medium
T17 Best practices: design with states (loading/empty/error), edge cases, hierarchy clarity. Time=low
T18 Portfolio Project A: end-to-end redesign case study (research → prototype → test). Time=high | Output=portfolio case
T19 Portfolio Project B: mini design system + documentation + sample screens. Time=high | Prereq=T10
T20 Common pitfalls: skipping research, weak IA, inconsistent components, ignoring accessibility. Time=low

Thumbnail Designing — spine sources used for coverage and ordering.
T01 Foundations: thumbnail purpose, attention economics, “small-size readability” constraints. Time=low | Prereq=basic design
T02 Research workflow: audience intent, competitor scan, style patterns, brand constraints. Time=medium | Output=swipe file
T03 Composition basics: hierarchy, subject isolation, rule of thirds, negative space. Time=medium
T04 Typography for thumbnails: minimal words, thick strokes, mobile legibility tests. Time=high
T05 Color & contrast: high-contrast palettes, consistent grading, color-blind checks. Time=high
T06 Image sourcing: frame selection, staged shots, emotion clarity, story-in-one-frame. Time=medium
T07 Cutouts/masking: clean edges, hair detail strategies, shadow/outline consistency. Time=high
T08 Depth & separation: background blur, rim light, gradients, focus funnel. Time=medium
T09 Consistency system: templates, safe zones, repeated motifs, “series” branding. Time=medium | Output=template kit
T10 Metadata alignment: title–thumbnail promise match; avoid deceptive framing. Time=medium
T11 Compliance basics: prohibited imagery, community/policy alignment, risk flags. Time=medium
T12 Export discipline: file formats, file size constraints, compression without artifacts. Time=medium
T13 Workflow: brief → draft 3 concepts → pick winner → finalize → export → upload. Time=medium
T14 Iteration loop: refresh old thumbnails; log changes; compare performance over time. Time=medium | Output=iteration log
T15 Best practices: one focal point, 1–3 colors, consistent type, test at 10% zoom. Time=low
T16 Portfolio Project A: 10-thumbnail set for one niche + rationale per design. Time=high | Output=case study
T17 Portfolio Project B: “thumbnail style guide” (rules + templates + do/don’t). Time=high
T18 Assessment: blind review rubric + legibility test + policy checklist. Time=medium
T19 Advanced: scalable production (batching, reusable assets), speed vs quality tradeoffs. Time=medium
T20 Common pitfalls: clutter, tiny text, misleading visuals, inconsistent branding, no testing. Time=low

Social Media Content Creation — spine sources used for coverage and ordering.
T01 Foundations: objectives (awareness/leads/sales), platform format landscape, audience fit. Time=low | Prereq=none
T02 Content strategy: niche, pillars, messaging, brand voice, creative constraints. Time=medium | Output=content pillars doc
T03 Planning: ideation, scripting, storyboarding, shot lists, production calendar. Time=medium
T04 Capture basics: lighting, audio, framing, b-roll, vertical vs horizontal decisions. Time=medium
T05 Editing for social: hooks, pacing, captions, safe zones, repurposing strategy. Time=high | Prereq=T04
T06 Trend intelligence: hashtags/sounds/creator patterns and when to use/avoid. Time=medium
T07 Publishing workflow: scheduling, metadata, thumbnails/covers, CTA placement. Time=medium
T08 Community ops: comment moderation, DM handling, escalation rules, tone consistency. Time=medium
T09 Analytics basics: retention, CTR, watch time, engagement, cohort comparisons. Time=high | Output=metrics dashboard spec
T10 Iteration loop: hypothesis → variant → measure → learn → standardize. Time=high
T11 Collaboration with clients/brands: approvals, briefs, deliverables, revision limits. Time=medium
T12 Legal & compliance: music rights, disclosure (ads/affiliates), privacy/consent. Time=medium
T13 Content accessibility: captions, readable overlays, contrast, pacing for comprehension. Time=medium
T14 Paid vs organic thinking: when to boost, creative-as-test, messaging experiments. Time=medium
T15 Best practices: batch production, templating, consistent naming, weekly review cadence. Time=low
T16 AI assist (optional): ideation, scripting, hooks, captions—plus verification discipline. Time=medium
T17 Portfolio Project A: 30-day calendar + 10 shipped assets across 3 formats. Time=high | Output=case study
T18 Portfolio Project B: 3-ad creative set (3 hooks × 2 edits each) + analytics plan. Time=high
T19 Assessment: rubric (hook clarity, brand fit, accessibility, metrics plan) + peer review. Time=medium
T20 Common pitfalls: inconsistent posting, ignoring analytics, weak hooks, copyright strikes, no process. Time=low

Generative AI — spine sources used for coverage and ordering.
T01 Foundations: what “generative” means (text/image/audio), typical capabilities/limits. Time=low | Prereq=none
T02 Core concepts: tokens, context window, embeddings, training vs inference basics. Time=medium
T03 Model selection factors: cost/latency/quality tradeoffs; constraints-first mindset. Time=medium
T04 Risk & responsibility: AI risk framing, trustworthiness, governance basics. Time=medium
T05 Data privacy & compliance: sensitive data handling, retention assumptions, red lines. Time=medium
T06 Core use cases: drafting, summarization, extraction, classification, ideation, code assist. Time=medium
T07 Grounding & RAG: retrieval concepts, citations, source-of-truth patterns. Time=high | Prereq=T02
T08 Evaluation basics: gold sets, rubrics, human review, regression tests. Time=high
T09 Prompting as control: instruction hierarchy, constraints, formatting, examples. Time=medium
T10 Structured outputs: schemas, validators, parsing errors, fallback strategies. Time=high
T11 Tool use & agents: tool calling, orchestration, guardrails, approvals. Time=high | Prereq=T09–T10
T12 Security: prompt injection, data exfiltration scenarios, safe input handling. Time=high
T13 Monitoring: logs, quality metrics, drift awareness, incident playbooks. Time=medium
T14 Cost optimization: caching, batching, truncation, retrieval sizing. Time=high
T15 Multimodal basics: image+text analysis workflows, limitations, red-team cases. Time=medium
T16 “Build vs buy” thinking: when to use hosted tools vs API integration. Time=medium
T17 Best practices: cite sources, constrain inputs/outputs, test adversarially, keep humans in loop. Time=low
T18 Portfolio Project A: mini RAG assistant on a small corpus + eval report. Time=high | Output=repo + write-up
T19 Portfolio Project B: content variant generator + A/B plan + safety checklist. Time=high
T20 Common pitfalls: hallucinated facts, no eval set, leaking secrets, brittle parsing. Time=low

AI & Machine Learning Basics — spine sources used for coverage and ordering.
T01 Prereqs: basic Python, algebra, descriptive stats, spreadsheet-level data comfort. Time=medium
T02 ML workflow overview: define task → collect data → train → evaluate → iterate. Time=medium
T03 Data splitting: train/validation/test, leakage, stratification, baselines. Time=high
T04 Feature basics: scaling, encoding categories, missing values, pipelines. Time=high
T05 Supervised learning: regression vs classification; when to use each. Time=medium
T06 Metrics & scoring: accuracy vs precision/recall, ROC-AUC, MAE/MSE, calibration. Time=high
T07 Cross-validation & tuning: validation strategy, grid/random search, overfitting control. Time=high
T08 Unsupervised learning: clustering, dimensionality reduction, anomaly detection (overview). Time=medium
T09 Bias–variance + regularization: under/overfitting, model complexity intuition. Time=high
T10 Neural nets intro: layers/activations, loss functions, basic training loop concepts. Time=high
T11 Deep learning overview: CNN/RNN/transformers concepts and where they fit. Time=medium
T12 Data pipelines: batching, shuffling, dataset building, reproducibility. Time=medium
T13 Practical experimentation: notebooks, random seeds, tracking changes, learning curves. Time=medium
T14 Error analysis: confusion matrix reviews, slice analysis, “where it fails” thinking. Time=high
T15 Ethics & risk: fairness, privacy, and practical risk framing in ML projects. Time=medium
T16 Best practices: start simple, baseline first, validate data, document assumptions. Time=low
T17 Project A: supervised model + metric report + error analysis notebook. Time=high | Output=report
T18 Project B: simple neural net classification + training curves + evaluation. Time=high
T19 Portfolio: “model card” + reproducible pipeline + README with metrics. Time=high
T20 Common pitfalls: leakage, wrong metric, overfitting, no baseline, irreproducible runs. Time=low

AI Automation — spine sources used for coverage and ordering.
T01 Foundations: automation mindset, process mapping, triggers/actions mental model. Time=low | Prereq=basic spreadsheets
T02 Scoping automations: define inputs/outputs, success criteria, failure modes. Time=medium
T03 Build-first automation: single trigger → single action; validate end-to-end. Time=medium | Output=working “hello automation”
T04 Multi-step flows: multiple actions, data mapping, field hygiene, normalization. Time=high
T05 Conditional logic: filters, if/else branches, routing rules, guard conditions. Time=high | Prereq=T03–T04
T06 Data transformation: formatters, parsing JSON/text, dedupe, enrichment. Time=high
T07 Webhooks: inbound/outbound webhooks, payload design, testing with sample requests. Time=high
T08 Auth & access: OAuth, API keys, least-privilege connections, secret storage basics. Time=medium
T09 Reliability: retries, idempotency, rate limits, scheduling vs instant triggers. Time=high
T10 Error handling: alerts, dead-letter queues (concept), manual review steps. Time=high
T11 Logging & monitoring: execution logs, dashboards, SLA thinking. Time=medium
T12 Human-in-the-loop: approval steps, exception handling, audit trails. Time=medium
T13 AI-augmented automations: call AI endpoints, parse outputs, validate structured results. Time=high | Prereq=T06
T14 Security & privacy: PII handling, access rotation, vendor risk awareness. Time=medium
T15 Documentation: SOPs, runbooks, change management, client handoff pack. Time=medium | Output=automation playbook
T16 Best practices: start small, name steps, store raw inputs, add validation early. Time=low
T17 Project A: lead intake → CRM → notification → follow-up sequence automation. Time=high | Output=demo + SOP
T18 Project B: content pipeline: intake → summarize → tag → publish queue. Time=high
T19 Assessment: reliability checklist + monitoring plan + test cases for edge inputs. Time=medium
T20 Common pitfalls: brittle parsing, silent failures, scope creep, permission sprawl, no logs. Time=low

Prompt Engineering — spine sources used for coverage and ordering.
T01 Foundations: why prompts matter; nondeterminism; controllable vs uncontrollable factors. Time=low | Prereq=none
T02 Prompt anatomy: roles/instructions/context/examples/output specification. Time=medium
T03 Clarity techniques: explicit constraints, delimiters, “do/don’t”, success criteria. Time=high
T04 Few-shot prompting: choosing examples, coverage of edge cases, avoiding leakage. Time=high
T05 Structured outputs: JSON schemas, validation rules, re-ask loops, error recovery. Time=high
T06 Iteration loop: draft → test → analyze failures → refine; prompt versioning. Time=medium
T07 Context management: summarization, chunking, retrieval, “what to include” heuristics. Time=high
T08 Tool calling patterns: function schemas, tool selection gates, safe argument shaping. Time=high
T09 Evaluation: test sets, rubrics, regression checks, “prompt unit tests”. Time=high
T10 Safety: prompt injection attacks, untrusted inputs, output constraints. Time=high
T11 Domain grounding: requiring citations, extracting facts from provided sources only. Time=medium
T12 Parameter awareness: temperature/top-p/max tokens; when to control for determinism. Time=medium
T13 Prompt libraries: reusable templates, style guides, team conventions. Time=medium | Output=prompt catalog
T14 Troubleshooting: hallucinations, verbosity, refusal patterns, format drift. Time=medium
T15 Advanced patterns: self-checks, multi-pass extraction, critique/repair loops. Time=high
T16 Best practices: measure improvements, keep prompts short but specific, validate outputs. Time=low
T17 Project A: build 5 prompts (summarize/extract/classify/draft/QA) + eval report. Time=high
T18 Project B: extraction pipeline producing strict JSON + validator + fallback. Time=high
T19 Assessment: red-team prompts + security checklist + failure-mode write-up. Time=medium
T20 Common pitfalls: vague asks, no examples, no validation, trusting tool outputs blindly. Time=low

ChatGPT & AI Tools Mastery — spine sources used for coverage and ordering.
T01 Foundations: capability overview, when to use chat vs API vs automations. Time=low | Prereq=none
T02 Privacy & workspace basics: data handling norms, team/workspace concepts (high-level). Time=medium
T03 Prompting essentials: structuring requests, context, constraints, explicit outputs. Time=medium
T04 Custom Instructions: consistent preferences, style rules, reusable constraints. Time=medium | Output=personal instruction doc
T05 Creating GPTs: defining purpose, instructions, knowledge sources, tool permissions. Time=high
T06 Publishing & governance: testing, versioning, distribution decisions, maintenance plan. Time=high
T07 Tool use patterns: browsing/file analysis/actions—choosing the safest minimal toolset. Time=medium
T08 Safety & policy: prohibited uses, safe deployment practices, moderation concepts. Time=high
T09 Agent risks: prompt injection and untrusted inputs; mitigation patterns. Time=high
T10 Prompt libraries: reusable templates, checklists, evaluation prompts. Time=medium
T11 Structured outputs: JSON-first workflows, validators, retry rules. Time=high
T12 Integrations: connect ChatGPT to external services via actions/APIs (concept + governance). Time=high
T13 Operational basics: logging outputs, error triage, user feedback loops. Time=medium
T14 Cost/latency awareness (conceptual): scope outputs; avoid unnecessary calls. Time=medium
T15 API intro: keys, quickstart patterns, separating dev/prod, environment variables. Time=high
T16 Best practices: do not paste secrets, keep scope narrow, cite sources, test edge cases. Time=low
T17 Project A: build a “knowledge GPT” (FAQ assistant) + test suite + safety checklist. Time=high | Output=demo
T18 Project B: build a “content ops GPT” (scripts, captions, variants) + workflow SOP. Time=high
T19 Assessment: rubric-based evaluation of outputs + failure-mode report. Time=medium
T20 Common pitfalls: leaking private data, weak instructions, no tests, over-trusting outputs. Time=low

Web Development — spine sources used for coverage and ordering.
T01 Foundations: how the web works; client/server; basic dev environment setup. Time=medium | Prereq=none
T02 HTML semantics: structure, forms, accessibility roles, document outlines. Time=high
T03 CSS fundamentals: layout (flex/grid), responsive design, typography basics. Time=high
T04 JavaScript fundamentals: syntax, DOM, events, async basics. Time=high
T05 Tooling: package managers, bundlers, dev server, environment variables. Time=medium
T06 HTTP basics: methods, status codes, headers, caching concepts, CORS overview. Time=high
T07 Frontend architecture: component thinking, state, routing (framework-agnostic). Time=medium
T08 Accessibility & UX: keyboard navigation, ARIA basics, responsive constraints. Time=high
T09 Performance basics: image optimization, minimizing render-blocking, caching. Time=medium
T10 Backend fundamentals: routing/controllers, templates vs APIs, middleware thinking. Time=high
T11 Databases: SQL concepts, schema design, migrations (high-level). Time=high
T12 API design: REST patterns, pagination, errors, versioning, documentation. Time=high
T13 Auth basics: sessions/cookies, JWT concepts, password hashing principles. Time=high
T14 Security basics: input validation, least privilege, secure headers, dependency hygiene. Time=high
T15 Testing: unit tests, integration tests, API tests; testable architecture. Time=high
T16 Deployment: hosting, domains/TLS basics, CI/CD concepts. Time=medium
T17 Best practices: consistent code style, docs-first APIs, incremental refactors, logs. Time=low
T18 Project A: CRUD web app (frontend + backend + DB) with auth + tests. Time=high | Output=deployed app
T19 Project B: third-party API integration + caching + monitoring checklist. Time=high
T20 Common pitfalls: tangled state, no validation, poor error handling, insecure auth, no tests. Time=low

Python Programming — spine sources used for coverage and ordering.
T01 Setup: interpreter, IDE, virtual environments concept, running scripts. Time=medium | Prereq=none
T02 Syntax basics: variables, types, operators, strings, f-strings. Time=medium
T03 Control flow: if/elif/else, loops, comprehensions, truthiness. Time=high
T04 Functions: parameters, return values, scope, docstrings. Time=high
T05 Data structures: list/dict/set/tuple patterns; common algorithms (search/sort basics). Time=high
T06 Files & data: reading/writing files, JSON, CSV patterns, encoding pitfalls. Time=high
T07 Errors & exceptions: try/except, custom exceptions, context managers. Time=high
T08 Modules/packages: imports, project structure, reusable modules. Time=medium
T09 OOP basics: classes, methods, dataclasses (conceptual), composition over inheritance. Time=high
T10 Testing with pytest: test structure, assertions, fixtures, parametrization basics. Time=high
T11 Code style: PEP 8 conventions, readability, naming, formatting discipline. Time=medium
T12 Dependency management: pip usage, requirements, installer basics. Time=medium
T13 Packaging basics: installable packages, entry points (concept), distribution overview. Time=medium
T14 Standard library leverage: pathlib, datetime, collections, itertools (survey). Time=high
T15 Automation scripting: CLI args, environment variables, logging basics. Time=high
T16 Concurrency overview: threads vs async (conceptual entry point). Time=medium
T17 Best practices: write tests early, type/edge-case thinking, isolate side effects. Time=low
T18 Project A: CLI utility (e.g., file organizer) + tests + packaging basics. Time=high | Output=repo
T19 Project B: data processing pipeline (CSV→report) + test suite + docs. Time=high
T20 Common pitfalls: global state, no tests, tangled dependencies, mixing envs, weak error handling. Time=low

Full Stack Development — spine sources used for coverage and ordering.
T01 Foundations: full-stack architecture; responsibilities across frontend/backend/DB. Time=medium | Prereq=web dev basics
T02 API contracts: design-first with OpenAPI; errors, versioning, docs generation. Time=high
T03 Database design: schemas, normalization, indexing fundamentals, migrations. Time=high | Prereq=T01
T04 Auth at scale: RBAC, permissions, session strategy, OAuth concepts. Time=high
T05 Frontend integration: API clients, state synchronization, caching, optimistic updates. Time=high
T06 Background jobs: queues, scheduled tasks, async processing patterns (conceptual). Time=medium
T07 Observability: structured logs, metrics, tracing basics, incident response thinking. Time=high
T08 CI/CD: automated tests, build steps, deployment pipelines, rollback plans. Time=high
T09 Containers: images, local dev parity, Compose stacks, health checks. Time=high
T10 Environment management: configs, secrets, dev/stage/prod separation. Time=high
T11 Performance: caching layers, DB query optimization, CDN basics, pagination. Time=high
T12 Security hardening: dependency scanning mindset, least privilege, secure defaults. Time=high
T13 Data management: backups, restores, retention policies (conceptual). Time=medium
T14 Documentation: runbooks, onboarding docs, API docs, architecture diagrams. Time=medium
T15 Collaboration: code reviews, branching strategy, issue tracking, release notes. Time=medium
T16 Best practices: treat API contract as product; automate checks; document assumptions. Time=low
T17 Capstone A: end-to-end app with API docs + DB + deployment + monitoring checklist. Time=high | Output=live demo
T18 Capstone B: add CI/CD + docker-compose local stack + backup/rollback plan. Time=high
T19 Portfolio: README + OpenAPI spec + architecture diagram + test coverage summary. Time=high
T20 Common pitfalls: unclear schemas, brittle migrations, secrets in repo, no monitoring, no rollback. Time=low

App Development — spine sources used for coverage and ordering.
T01 Platform choices: native vs cross-platform; constraints; “basic app” scope definition. Time=medium | Prereq=basic programming
T02 Environment setup: SDKs, emulators/simulators, project templates, debugging basics. Time=medium
T03 UI building blocks: layout primitives, components/widgets, adaptive UI principles. Time=high
T04 Navigation: screens, routes, tab stacks, deep links (conceptual). Time=high
T05 State management basics: local state vs app state; predictable data flow. Time=high
T06 Data storage: preferences, local DB concepts, caching; offline-first basics. Time=high
T07 Networking: REST requests, JSON parsing, error handling, loading states. Time=high
T08 Permissions/privacy: runtime permissions, data minimization, user consent patterns. Time=medium
T09 Accessibility: dynamic type/font scaling, contrast, semantics, touch targets. Time=medium
T10 Testing: basic unit tests + UI tests (conceptual intro + habit formation). Time=medium
T11 Debugging/profiling: logs, crash triage, performance hotspots. Time=medium
T12 Build & release: signing, build variants, store listing basics, versioning. Time=medium
T13 Notifications overview: push vs local notifications; user experience pitfalls. Time=medium
T14 Payments/ads basics: high-level monetization options and UX constraints. Time=low
T15 Security basics: secure storage patterns, network security, sensitive data handling. Time=high
T16 Best practices: keep screens small, handle offline/errors, document navigation flows. Time=low
T17 Project A: basic CRUD app (create/read/update/delete) with local storage. Time=high | Output=demo app
T18 Project B: API-integrated app with caching + robust error/loading states. Time=high
T19 Portfolio: screenshots + short demo video + “decisions” write-up. Time=medium
T20 Common pitfalls: messy state, no offline story, ignoring permissions, weak error handling. Time=low

Digital Marketing — spine sources used for coverage and ordering.
T01 Foundations: core channels, funnels, customer journey, outcomes vs vanity metrics. Time=medium | Prereq=none
T02 Strategy: goals, KPIs, audience/segments, positioning, messaging hierarchy. Time=high | Output=marketing brief
T03 Content marketing: value props, editorial planning, lead magnets, distribution. Time=high
T04 Website/landing pages: conversion basics, forms, CTA, trust signals. Time=high
T05 Search ads overview: intent match, keyword structure, ad relevance principles. Time=high
T06 Social ads overview: objectives, audiences, creatives, measurement loops. Time=high
T07 Email marketing: lists, segmentation, lifecycle automation (conceptual). Time=high
T08 Analytics fundamentals: GA4 structure, events, conversions, attribution basics. Time=high
T09 Measurement discipline: UTMs, naming conventions, dashboards, reporting cadence. Time=medium
T10 Budgeting: channel allocation, marginal ROI thinking, test budgets. Time=medium
T11 Creative strategy: hooks, storytelling, offer design; creative briefs. Time=high
T12 Experimentation: A/B testing basics, iteration cycles, learning agendas. Time=high
T13 Platform learning paths: certifications and structured practice routines. Time=medium
T14 Operations: SOPs, asset management, approvals, compliance checks. Time=medium
T15 Privacy/compliance basics: consent, cookies, data handling (high-level). Time=medium
T16 Best practices: start with clear KPIs; measure end-to-end; prioritize repeatable tests. Time=low
T17 Project A: full digital marketing plan (channels, KPIs, budgets, content calendar). Time=high | Output=plan doc
T18 Project B: campaign measurement framework (UTMs + GA4 events + report template). Time=high
T19 Portfolio: case study format + dashboard screenshots + “what I learned” section. Time=medium
T20 Common pitfalls: no tracking plan, random tactics, misaligned KPIs, poor creative testing. Time=low

SEO — spine sources used for coverage and ordering.
T01 Search fundamentals: crawling, indexing, ranking (conceptual), search intent. Time=medium | Prereq=basic web
T02 Search guidelines: what search engines expect; avoiding manipulative tactics. Time=medium
T03 Keyword research: topic clusters, intent mapping, avoiding “keyword stuffing”. Time=high
T04 On-page SEO: titles, headings, internal links, content structure, semantic HTML. Time=high
T05 Technical SEO: sitemaps, robots directives, canonicalization basics. Time=high
T06 Site architecture: IA for crawl + users; faceted navigation risks. Time=high
T07 Performance basics: page speed, image optimization, caching concepts. Time=high
T08 Structured data: schema vocabulary, eligibility concepts, validation mindset. Time=high
T09 Content strategy: topical coverage, editorial maintenance, content refresh cycles. Time=high
T10 International/mobile: mobile-first thinking, multilingual basics (conceptual). Time=medium
T11 Off-site factors: links as signals (high-level), digital PR mindset, risk awareness. Time=medium
T12 Tooling: Search Console workflow, query analysis, coverage issues, inspections. Time=high
T13 SEO audits: technical checklist, prioritization, fix validation, regression checks. Time=high
T14 Reporting: KPI selection (impressions/clicks/rankings/conversions), annotation discipline. Time=medium
T15 Best practices: build for users, validate with tools, document changes and outcomes. Time=low
T16 Project A: keyword map + on-page updates for 5 pages + expected impact notes. Time=high | Output=audit report
T17 Project B: technical audit (sitemap/robots/canonical/performance) + fix backlog. Time=high
T18 Portfolio: SEO case study with baseline→change→result narrative (with caveats). Time=medium
T19 Assessment: “find issues” test + propose fixes + communicate tradeoffs to stakeholders. Time=medium
T20 Common pitfalls: thin content, broken canonicals, ignoring indexing, poor internal linking. Time=low

Social Media Marketing — spine sources used for coverage and ordering.
T01 Foundations: choose platforms by audience + objective; define success metrics. Time=medium | Prereq=none
T02 Strategy: content pillars, brand voice, community plan, calendar system. Time=high
T03 Organic execution: posting cadence, storytelling formats, engagement routines. Time=high
T04 Creative production pipeline: briefs, scripting, filming, editing, approvals. Time=high
T05 Paid social basics: ad formats, objectives, creative specs, compliance. Time=high
T06 Targeting: core audiences, retargeting concepts, exclusions, geo/device basics. Time=high
T07 Tracking & measurement: pixels/events, UTMs, attribution caveats. Time=high
T08 Creative testing: A/B tests, controlled variables, learning agendas, iteration loops. Time=high
T09 Reporting: dashboards, weekly insights, decision-making from results. Time=medium
T10 Platform governance: access control, business managers, roles, audit trails. Time=medium
T11 Community + brand safety: moderation, replies, escalation, crisis basics. Time=medium
T12 Influencers/creators: briefs, deliverables, tracking, disclosure basics. Time=medium
T13 Social commerce overview: creators/shops/affiliate structures (high-level). Time=medium
T14 Best practices: refresh creatives regularly, track learnings, systemize approvals. Time=low
T15 Project A: 30-day content calendar + community SOP + KPI dashboard template. Time=high | Output=playbook
T16 Project B: paid campaign plan (3 creatives × 2 audiences × 1 objective) + measurement. Time=high
T17 Portfolio: case study with creative rationale, targeting, and results interpretation. Time=medium
T18 Assessment: ad creative checklist + policy check + reporting walkthrough. Time=medium
T19 Advanced: multi-platform repurposing strategy + difference in intent per platform. Time=medium
T20 Common pitfalls: chasing trends blindly, no tracking, inconsistent branding, no testing. Time=low

Freelancing & Personal Branding — spine sources used for coverage and ordering.
T01 Positioning: pick niche, define outcomes, craft service menu and differentiator. Time=high | Prereq=some skill to sell
T02 Personal brand basics: narrative, credibility signals, consistent messaging. Time=medium
T03 Portfolio building: case study structure (problem→process→result), proof artifacts. Time=high | Output=portfolio template
T04 Profile optimization: headline, about section, featured work, credibility-first profile. Time=medium | Output=profile checklist
T05 Lead generation (inbound): content, SEO, referrals, community presence. Time=high
T06 Lead generation (outbound): targeting list, outreach scripts, follow-up cadence. Time=high
T07 Sales process: discovery calls, qualification, scope clarification, next-step control. Time=high
T08 Pricing: hourly vs fixed vs retainer; rate setting frameworks; negotiation basics. Time=high
T09 Proposals: scope, deliverables, timeline, revision limits, assumptions, exclusions. Time=high | Output=proposal template
T10 Contracts: core clauses, IP terms, payment terms, change orders; contract tooling. Time=high
T11 Payments & invoicing: milestones, deposits, payment schedules, late fees (conceptual). Time=medium
T12 Client operations: kickoff, meeting cadence, status updates, stakeholder management. Time=medium
T13 Managing revisions: feedback collection, versioning, sign-offs, conflict prevention. Time=medium
T14 Project management: personal capacity planning, time tracking, handoff artifacts. Time=medium
T15 Quality & delivery: checklists, final QA, packaging deliverables, archiving. Time=medium
T16 Best practices: document everything; set boundaries; confirm scope in writing. Time=low
T17 Project A: full personal brand kit (portfolio site outline + profile revamp + media kit). Time=high | Output=kit
T18 Project B: 3 proposals + 2 contract templates + pricing sheet + onboarding checklist. Time=high
T19 Assessment: mock sales call + proposal review + contract risk review checklist. Time=medium
T20 Common pitfalls: vague scope, underpricing, no contract, unpaid revisions, poor follow-up. Time=low

Agency Building & Client Acquisition — spine sources used for coverage and ordering.
T01 Agency models: productized services, retainers, project work; selecting a focus. Time=medium | Prereq=deliverable skill
T02 Offer design: ICP, value proposition, guaranteed outcomes vs deliverables. Time=high
T03 Packaging services: scope boundaries, tiers, add-ons, SLAs, pricing logic. Time=high
T04 Operations: intake → kickoff → production → review → delivery → reporting workflow. Time=high | Output=process map
T05 Team & roles: account management, delivery, QA, creative, tech, sales ops. Time=medium
T06 Systems: SOPs, templates, brand kits, QA checklists, documentation culture. Time=high
T07 Sales pipeline: pipeline stages, qualification criteria, forecasting basics. Time=high
T08 Lead channels: outbound, inbound, referrals, partners, directories, events. Time=high
T09 Partnerships: platform partner programs (requirements, benefits, responsibilities). Time=medium
T10 Onboarding at scale: access requests, assets, measurement setup, expectations. Time=high
T11 Delivery quality control: review gates, escalation paths, scope change handling. Time=high
T12 Reporting: KPIs per client, cadence, QBR structure, “insights not charts” discipline. Time=high
T13 Financial basics: utilization, margins, cash flow buffer, churn risk awareness. Time=medium
T14 Client retention: renewals, expansion, satisfaction tracking, proactive comms. Time=high
T15 Governance: permissions, security, data access, ad/policy compliance. Time=medium
T16 Best practices: sell outcomes, not tasks; systemize delivery; protect capacity. Time=low
T17 Project A: agency playbook (SOPs + templates + checklists + onboarding pack). Time=high | Output=playbook
T18 Project B: acquisition system (ICP + outreach sequences + landing page + pipeline). Time=high
T19 Portfolio: 3 case studies + proof assets + partner badges plan (if applicable). Time=medium
T20 Common pitfalls: selling custom everything, weak scope control, no pipeline hygiene, undercharging. Time=low
"""


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def build_youtube_search_link(query):
    if not query:
        return ""
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)


def clean_topic_for_youtube(text):
    if not text:
        return ""
    text = re.sub(r"\s*\|\s*.*$", "", text).strip()
    text = re.sub(r"\bTime=.*$", "", text).strip()
    text = re.sub(r"\bPrereq=.*$", "", text).strip()
    text = re.sub(r"\bOutput=.*$", "", text).strip()
    text = re.sub(r"\bPitfall=.*$", "", text).strip()
    return text.strip()


def build_youtube_queries(course_title, topic_title, preferred_language="english"):
    cleaned = clean_topic_for_youtube(topic_title)

    english_queries = [
        f"{course_title} {cleaned} tutorial",
        f"{cleaned} tutorial",
        f"{course_title} {cleaned} explained",
        f"{cleaned} for beginners",
    ]

    telugu_queries = [
        f"{course_title} {cleaned} tutorial telugu",
        f"{cleaned} tutorial telugu",
        f"{course_title} {cleaned} explained telugu",
        f"{cleaned} for beginners telugu",
    ]

    return telugu_queries if preferred_language == "telugu" else english_queries


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Access denied.", "danger")
            return redirect(url_for("user_dashboard"))
        return f(*args, **kwargs)
    return decorated_function


def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "user":
            flash("Access denied.", "danger")
            return redirect(url_for("admin_dashboard"))
        return f(*args, **kwargs)
    return decorated_function


def create_admin_if_not_exists():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = ?", ("admin@ramskon.com",))
    admin = cursor.fetchone()

    if not admin:
        password_hash = generate_password_hash("admin123")
        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role, preferred_language)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("Admin", "admin@ramskon.com", password_hash, "admin", "english")
        )
        conn.commit()

    conn.close()


def seed_courses():
    conn = get_connection()
    cursor = conn.cursor()

    for title, description, category in COURSES_DATA:
        cursor.execute("SELECT id FROM courses WHERE title = ?", (title,))
        existing = cursor.fetchone()

        if not existing:
            cursor.execute(
                """
                INSERT INTO courses (title, description, duration_days, category)
                VALUES (?, ?, ?, ?)
                """,
                (title, description, 30, category)
            )

    conn.commit()
    conn.close()


def parse_spine_sources(raw_text):
    course_map = {}
    current_course = None

    for raw_line in raw_text.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue

        if "— spine sources used for coverage and ordering." in line:
            current_course = line.split("—")[0].strip()
            course_map[current_course] = []
            continue

        if current_course and re.match(r"^T\d{2}\b", line):
            code = line[:3]
            body = line[3:].strip()
            course_map[current_course].append({
                "code": code,
                "body": body
            })

    return course_map


SPINE_TOPICS = parse_spine_sources(SPINE_SOURCES_TEXT)


def get_spine_topics_for_course(course_title):
    return SPINE_TOPICS.get(course_title, [])


def fetch_youtube_videos(course_title, topic_title, preferred_language="english", max_results=3):
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        return []

    language_code = "te" if preferred_language == "telugu" else "en"
    queries = build_youtube_queries(course_title, topic_title, preferred_language=preferred_language)

    search_attempts = []

    for q in queries:
        search_attempts.append({
            "q": q,
            "relevanceLanguage": language_code,
            "videoEmbeddable": "true",
            "videoSyndicated": "true",
        })
        search_attempts.append({
            "q": q,
            "relevanceLanguage": language_code,
            "videoEmbeddable": "true",
        })
        search_attempts.append({
            "q": q,
            "videoEmbeddable": "true",
        })

    for params_extra in search_attempts:
        try:
            params = {
                "part": "snippet",
                "type": "video",
                "maxResults": max_results,
                "key": api_key,
            }
            params.update(params_extra)

            response = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            videos = []
            for item in data.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                snippet = item.get("snippet", {})
                if video_id:
                    videos.append({
                        "title": snippet.get("title", "Video"),
                        "channel": snippet.get("channelTitle", ""),
                        "watch_url": f"https://www.youtube.com/watch?v={video_id}",
                        "embed_url": f"https://www.youtube.com/embed/{video_id}",
                        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
                    })

            if videos:
                return videos

        except Exception as e:
            print("YouTube API error:", str(e))

    return []


def build_topic_title_from_spine(topic):
    body = topic["body"]
    title_part = body.split("|")[0].strip()
    return f"{topic['code']} {title_part}"


def build_deterministic_30_day_plan(course_title, course_description, spine_topics):
    plan = []

    for idx, topic in enumerate(spine_topics, start=1):
        topic_title = build_topic_title_from_spine(topic)
        plan.append({
            "day_number": idx,
            "topic_title": topic_title,
            "topic_content": (
                f"Study {topic_title}. Source guidance: {topic['body']}. "
                f"Focus on understanding this concept clearly, applying it in practical work, "
                f"and connecting it to the course goal: {course_description}"
            ),
            "assignment_text": (
                f"Complete a practical assignment for {topic_title}. "
                f"Create notes, a mini exercise, or a proof-of-work submission based on this topic."
            ),
            "youtube_query_en": f"{course_title} {topic_title} tutorial english",
            "youtube_query_te": f"{course_title} {topic_title} tutorial telugu"
        })

    revision_topics = [
        "Revision Sprint 1",
        "Revision Sprint 2",
        "Practice & Application",
        "Case Study Build 1",
        "Case Study Build 2",
        "Review & Optimization",
        "Portfolio Packaging",
        "Assessment & Gap Fixing",
        "Final Capstone",
        "Pitfalls Review & Final QA"
    ]

    start_day = len(plan) + 1
    for i, revision_title in enumerate(revision_topics, start=start_day):
        plan.append({
            "day_number": i,
            "topic_title": revision_title,
            "topic_content": (
                f"This day is used to reinforce the earlier spine topics of {course_title}. "
                f"Revise key concepts, strengthen weak areas, and convert what you learned into practical output."
            ),
            "assignment_text": (
                f"Submit a practical revision/capstone output for {revision_title} in {course_title}. "
                f"Show applied understanding, not only theory."
            ),
            "youtube_query_en": f"{course_title} {revision_title} tutorial english",
            "youtube_query_te": f"{course_title} {revision_title} tutorial telugu"
        })

    return plan[:30]


def generate_course_plan_with_groq(course_title, course_description):
    client = None
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if api_key and Groq is not None:
        client = Groq(api_key=api_key)

    spine_topics = get_spine_topics_for_course(course_title)

    if not spine_topics:
        return build_deterministic_30_day_plan(course_title, course_description, [
            {"code": "T01", "body": f"Foundations of {course_title}."},
            {"code": "T02", "body": f"Practical workflow of {course_title}."},
            {"code": "T03", "body": f"Core execution and applied learning in {course_title}."},
            {"code": "T04", "body": f"Advanced practice and delivery in {course_title}."},
            {"code": "T05", "body": f"Portfolio and project building in {course_title}."},
        ])

    if client is None:
        return build_deterministic_30_day_plan(course_title, course_description, spine_topics)

    ordered_spine = "\n".join(
        [f"{topic['code']}: {topic['body']}" for topic in spine_topics]
    )

    prompt = f"""
You are generating a premium 30-day roadmap from an exact source curriculum spine.

Course title: {course_title}
Course description: {course_description}

Use these source topics exactly as the syllabus spine and preserve their order:
{ordered_spine}

Return ONLY valid JSON array with exactly 30 objects.

Each object must contain:
day_number
topic_title
topic_content
assignment_text
youtube_query_en
youtube_query_te

Rules:
- exactly 30 days
- preserve the original source-topic order
- do NOT invent unrelated topics
- if a source topic is heavy, you may spread it across more than one day
- after the core topics are covered, use revision, project, assessment, portfolio, capstone, and pitfalls days based on the same syllabus
- topic_title must clearly reflect the actual syllabus topic
- topic_content must explain the topic in a useful practical flow
- assignment_text must be practical and based on that topic
- youtube_query_en and youtube_query_te must be good search queries for that topic
- no markdown
- no text outside JSON
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()
        plan = json.loads(content)

        normalized = []
        for item in plan:
            normalized.append({
                "day_number": int(item["day_number"]),
                "topic_title": item["topic_title"].strip(),
                "topic_content": item["topic_content"].strip(),
                "assignment_text": item["assignment_text"].strip(),
                "youtube_query_en": item["youtube_query_en"].strip(),
                "youtube_query_te": item["youtube_query_te"].strip()
            })

        if len(normalized) != 30:
            return build_deterministic_30_day_plan(course_title, course_description, spine_topics)

        return normalized
    except Exception as e:
        print("Groq generation error:", str(e))
        return build_deterministic_30_day_plan(course_title, course_description, spine_topics)


def user_has_approved_course(user_id, course_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id
        FROM course_requests
        WHERE user_id = ? AND course_id = ? AND status = 'approved'
        """,
        (user_id, course_id)
    )
    approved = cursor.fetchone()
    conn.close()
    return approved is not None


def get_unlocked_day(user_id, course_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS completed_days
        FROM assignment_submissions
        WHERE user_id = ? AND course_id = ?
        """,
        (user_id, course_id)
    )
    row = cursor.fetchone()
    conn.close()
    completed_days = row.completed_days if row else 0
    return completed_days + 1

@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not full_name or not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            flash("Email already registered.", "danger")
            return render_template("auth/register.html")

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role, preferred_language)
            VALUES (?, ?, ?, ?, ?)
            """,
            (full_name, email, password_hash, "user", "english")
        )
        conn.commit()
        conn.close()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("auth/login.html")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, full_name, email, password_hash, role, preferred_language
            FROM users
            WHERE email = ?
            """,
            (email,)
        )
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["full_name"] = user.full_name
            session["email"] = user.email
            session["role"] = user.role
            session["preferred_language"] = user.preferred_language

            flash("Login successful.", "success")

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("user_dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


@app.route("/user/set-language", methods=["POST"])
@user_required
def set_language():
    language = request.form.get("preferred_language", "english").strip().lower()
    if language not in ["english", "telugu"]:
        flash("Invalid language.", "danger")
        return redirect(url_for("user_dashboard"))

    user_id = session.get("user_id")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET preferred_language = ? WHERE id = ?",
        (language, user_id)
    )
    conn.commit()
    conn.close()

    session["preferred_language"] = language
    flash("Preferred language updated.", "success")
    return redirect(url_for("user_dashboard"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total_users FROM users WHERE role = 'user'")
    total_users = cursor.fetchone().total_users

    cursor.execute("SELECT COUNT(*) AS total_courses FROM courses")
    total_courses = cursor.fetchone().total_courses

    cursor.execute("SELECT COUNT(*) AS pending_requests FROM course_requests WHERE status = 'pending'")
    pending_requests = cursor.fetchone().pending_requests

    cursor.execute("SELECT COUNT(*) AS total_days FROM course_days")
    total_days = cursor.fetchone().total_days

    conn.close()

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_courses=total_courses,
        pending_requests=pending_requests,
        total_days=total_days
    )


@app.route("/admin/requests")
@admin_required
def admin_requests():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            cr.id,
            u.full_name,
            u.email,
            c.title,
            cr.status,
            cr.requested_at
        FROM course_requests cr
        INNER JOIN users u ON cr.user_id = u.id
        INNER JOIN courses c ON cr.course_id = c.id
        ORDER BY cr.id DESC
        """
    )
    requests_data = cursor.fetchall()
    conn.close()

    return render_template("admin/requests.html", requests_data=requests_data)


@app.route("/admin/requests/<int:request_id>/<action>", methods=["POST"])
@admin_required
def update_request_status(request_id, action):
    if action not in ["approve", "reject"]:
        flash("Invalid action.", "danger")
        return redirect(url_for("admin_requests"))

    new_status = "approved" if action == "approve" else "rejected"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE course_requests
        SET status = ?, reviewed_at = GETDATE()
        WHERE id = ?
        """,
        (new_status, request_id)
    )
    conn.commit()
    conn.close()

    flash(f"Request {new_status} successfully.", "success")
    return redirect(url_for("admin_requests"))


@app.route("/admin/generate-days", methods=["GET", "POST"])
@admin_required
def admin_generate_days():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, description FROM courses ORDER BY title ASC")
    courses = cursor.fetchall()

    if request.method == "POST":
        course_id = int(request.form.get("course_id"))

        cursor.execute("SELECT id, title, description FROM courses WHERE id = ?", (course_id,))
        course = cursor.fetchone()

        if not course:
            conn.close()
            flash("Course not found.", "danger")
            return redirect(url_for("admin_generate_days"))

        cursor.execute("DELETE FROM course_days WHERE course_id = ?", (course_id,))
        conn.commit()

        plan = generate_course_plan_with_groq(course.title, course.description)

        for item in plan:
            cursor.execute(
                """
                INSERT INTO course_days
                (course_id, day_number, topic_title, topic_content, assignment_text, youtube_query_en, youtube_query_te)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    course_id,
                    item["day_number"],
                    item["topic_title"],
                    item["topic_content"],
                    item["assignment_text"],
                    item["youtube_query_en"],
                    item["youtube_query_te"]
                )
            )

        conn.commit()
        conn.close()

        flash("30-day AI plan generated successfully using your exact syllabus topics.", "success")
        return redirect(url_for("admin_generate_days"))

    conn.close()
    return render_template("admin/generate_days.html", courses=courses)


@app.route("/admin/progress")
@admin_required
def admin_progress():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            u.full_name,
            u.email,
            c.title AS course_title,
            COUNT(s.id) AS completed_days
        FROM course_requests cr
        INNER JOIN users u ON cr.user_id = u.id
        INNER JOIN courses c ON cr.course_id = c.id
        LEFT JOIN assignment_submissions s
            ON s.user_id = u.id AND s.course_id = c.id
        WHERE cr.status = 'approved'
        GROUP BY u.full_name, u.email, c.title
        ORDER BY u.full_name, c.title
        """
    )
    rows = cursor.fetchall()
    conn.close()

    progress_rows = []
    for row in rows:
        progress_percent = int((row.completed_days / 30) * 100)
        progress_rows.append({
            "full_name": row.full_name,
            "email": row.email,
            "course_title": row.course_title,
            "completed_days": row.completed_days,
            "remaining_days": 30 - row.completed_days,
            "progress_percent": progress_percent
        })

    return render_template("admin/progress.html", progress_rows=progress_rows)


@app.route("/admin/submissions")
@admin_required
def admin_submissions():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            s.id,
            u.full_name,
            u.email,
            c.title AS course_title,
            s.day_number,
            s.submission_text,
            s.file_name,
            s.file_path,
            s.file_type,
            s.admin_review_status,
            s.admin_review_note,
            s.submitted_at
        FROM assignment_submissions s
        INNER JOIN users u ON s.user_id = u.id
        INNER JOIN courses c ON s.course_id = c.id
        ORDER BY s.submitted_at DESC
        """
    )
    submissions = cursor.fetchall()
    conn.close()

    return render_template("admin/submissions.html", submissions=submissions)


@app.route("/admin/submissions/<int:submission_id>/review", methods=["POST"])
@admin_required
def admin_review_submission(submission_id):
    review_status = request.form.get("admin_review_status", "pending").strip().lower()
    review_note = request.form.get("admin_review_note", "").strip()

    if review_status not in ["pending", "approved", "needs_changes"]:
        flash("Invalid review status.", "danger")
        return redirect(url_for("admin_submissions"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE assignment_submissions
        SET admin_review_status = ?, admin_review_note = ?
        WHERE id = ?
        """,
        (review_status, review_note or None, submission_id)
    )
    conn.commit()
    conn.close()

    flash("Submission review updated.", "success")
    return redirect(url_for("admin_submissions"))


@app.route("/user/dashboard")
@user_required
def user_dashboard():
    user_id = session.get("user_id")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            c.id,
            c.title,
            c.description,
            c.duration_days,
            c.category
        FROM course_requests cr
        INNER JOIN courses c ON cr.course_id = c.id
        WHERE cr.user_id = ? AND cr.status = 'approved'
        ORDER BY c.title ASC
        """,
        (user_id,)
    )
    approved_courses = cursor.fetchall()

    course_cards = []
    for course in approved_courses:
        unlocked_day = get_unlocked_day(user_id, course.id)

        cursor.execute(
            """
            SELECT COUNT(*) AS total_days
            FROM course_days
            WHERE course_id = ?
            """,
            (course.id,)
        )
        total_days_row = cursor.fetchone()
        total_days = total_days_row.total_days if total_days_row else 0

        completed_days = max(unlocked_day - 1, 0)
        progress_percent = int((completed_days / 30) * 100) if total_days else 0

        course_cards.append({
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "duration_days": course.duration_days,
            "category": course.category,
            "unlocked_day": unlocked_day if unlocked_day <= 30 else 30,
            "completed_days": completed_days,
            "progress_percent": progress_percent
        })

    conn.close()
    return render_template("user/dashboard.html", approved_courses=course_cards)


@app.route("/user/progress")
@user_required
def user_progress():
    user_id = session.get("user_id")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            c.id,
            c.title,
            c.category,
            COUNT(s.id) AS completed_days
        FROM course_requests cr
        INNER JOIN courses c ON cr.course_id = c.id
        LEFT JOIN assignment_submissions s
            ON s.course_id = c.id AND s.user_id = ?
        WHERE cr.user_id = ? AND cr.status = 'approved'
        GROUP BY c.id, c.title, c.category
        ORDER BY c.title
        """,
        (user_id, user_id)
    )
    rows = cursor.fetchall()
    conn.close()

    progress_rows = []
    for row in rows:
        progress_rows.append({
            "course_id": row.id,
            "course_title": row.title,
            "category": row.category,
            "completed_days": row.completed_days,
            "remaining_days": 30 - row.completed_days,
            "progress_percent": int((row.completed_days / 30) * 100)
        })

    return render_template("user/progress.html", progress_rows=progress_rows)


@app.route("/user/courses")
@user_required
def user_courses():
    user_id = session.get("user_id")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            c.id,
            c.title,
            c.description,
            c.duration_days,
            c.category,
            cr.status
        FROM courses c
        LEFT JOIN course_requests cr
            ON c.id = cr.course_id AND cr.user_id = ?
        ORDER BY c.title ASC
        """,
        (user_id,)
    )
    courses = cursor.fetchall()
    conn.close()

    return render_template("user/courses.html", courses=courses)


@app.route("/user/request-course/<int:course_id>", methods=["POST"])
@user_required
def request_course(course_id):
    user_id = session.get("user_id")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM course_requests
        WHERE user_id = ? AND course_id = ?
        """,
        (user_id, course_id)
    )
    existing = cursor.fetchone()

    if existing:
        conn.close()
        flash("You have already requested this course.", "warning")
        return redirect(url_for("user_courses"))

    cursor.execute(
        """
        INSERT INTO course_requests (user_id, course_id, status)
        VALUES (?, ?, 'pending')
        """,
        (user_id, course_id)
    )
    conn.commit()
    conn.close()

    flash("Course request sent to admin.", "success")
    return redirect(url_for("user_courses"))


@app.route("/user/course/<int:course_id>")
@user_required
def user_course_detail(course_id):
    user_id = session.get("user_id")
    preferred_language = session.get("preferred_language", "english")

    if not user_has_approved_course(user_id, course_id):
        flash("This course is not approved for you.", "danger")
        return redirect(url_for("user_dashboard"))

    unlocked_day = get_unlocked_day(user_id, course_id)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, description, duration_days, category
        FROM courses
        WHERE id = ?
        """,
        (course_id,)
    )
    course = cursor.fetchone()

    cursor.execute(
        """
        SELECT
            cd.day_number,
            cd.topic_title,
            cd.topic_content,
            cd.assignment_text,
            cd.youtube_query_en,
            cd.youtube_query_te,
            CASE
                WHEN s.id IS NOT NULL THEN 1
                ELSE 0
            END AS is_completed,
            s.file_name,
            s.file_path,
            s.submission_text,
            s.admin_review_status,
            s.admin_review_note
        FROM course_days cd
        LEFT JOIN assignment_submissions s
            ON cd.course_id = s.course_id
            AND cd.day_number = s.day_number
            AND s.user_id = ?
        WHERE cd.course_id = ?
        ORDER BY cd.day_number ASC
        """,
        (user_id, course_id)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        flash("This course has no generated 30-day plan yet. Ask admin to generate it in AI Planner.", "warning")
        return render_template(
            "user/course_detail.html",
            course=course,
            days=[],
            unlocked_day=1,
            preferred_language=preferred_language
        )

    days = []
    for row in rows:
        videos = []
        english_search_url = build_youtube_search_link(row.youtube_query_en or "")
        telugu_search_url = build_youtube_search_link(row.youtube_query_te or "")

        if row.day_number <= unlocked_day or row.is_completed == 1:
            if preferred_language == "telugu":
                videos = fetch_youtube_videos(course.title, row.topic_title, preferred_language="telugu", max_results=3)
                if not videos:
                    videos = fetch_youtube_videos(course.title, row.topic_title, preferred_language="english", max_results=3)
            else:
                videos = fetch_youtube_videos(course.title, row.topic_title, preferred_language="english", max_results=3)
                if not videos:
                    videos = fetch_youtube_videos(course.title, row.topic_title, preferred_language="telugu", max_results=3)

        days.append({
            "day_number": row.day_number,
            "topic_title": row.topic_title,
            "topic_content": row.topic_content,
            "assignment_text": row.assignment_text,
            "is_completed": row.is_completed,
            "file_name": row.file_name,
            "file_path": row.file_path,
            "submission_text": row.submission_text,
            "admin_review_status": row.admin_review_status,
            "admin_review_note": row.admin_review_note,
            "videos": videos,
            "english_search_url": english_search_url,
            "telugu_search_url": telugu_search_url
        })

    return render_template(
        "user/course_detail.html",
        course=course,
        days=days,
        unlocked_day=unlocked_day,
        preferred_language=preferred_language
    )


@app.route("/user/submit-assignment/<int:course_id>/<int:day_number>", methods=["POST"])
@user_required
def submit_assignment(course_id, day_number):
    user_id = session.get("user_id")

    if not user_has_approved_course(user_id, course_id):
        flash("This course is not approved for you.", "danger")
        return redirect(url_for("user_dashboard"))

    unlocked_day = get_unlocked_day(user_id, course_id)

    if day_number != unlocked_day:
        flash("You can only submit the currently unlocked day.", "danger")
        return redirect(url_for("user_course_detail", course_id=course_id))

    submission_text = request.form.get("submission_text", "").strip()
    uploaded_file = request.files.get("submission_file")

    if not submission_text and (not uploaded_file or uploaded_file.filename == ""):
        flash("Submit text or upload a file.", "danger")
        return redirect(url_for("user_course_detail", course_id=course_id))

    file_name = None
    file_path = None
    file_type = None

    if uploaded_file and uploaded_file.filename:
        if not allowed_file(uploaded_file.filename):
            flash("Unsupported file type.", "danger")
            return redirect(url_for("user_course_detail", course_id=course_id))

        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        safe_name = secure_filename(uploaded_file.filename)
        extension = safe_name.rsplit(".", 1)[1].lower()
        final_name = f"{uuid4().hex}.{extension}"
        absolute_path = os.path.join(app.config["UPLOAD_FOLDER"], final_name)
        uploaded_file.save(absolute_path)

        file_name = safe_name
        file_path = f"uploads/{final_name}"
        file_type = extension

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO assignment_submissions
        (user_id, course_id, day_number, submission_text, file_name, file_path, file_type, status, admin_review_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'submitted', 'pending')
        """,
        (user_id, course_id, day_number, submission_text or None, file_name, file_path, file_type)
    )
    conn.commit()
    conn.close()

    flash(f"Day {day_number} submitted successfully. Next day unlocked.", "success")
    return redirect(url_for("user_course_detail", course_id=course_id))


if __name__ == "__main__":
    create_admin_if_not_exists()
    seed_courses()
    app.run(debug=True)