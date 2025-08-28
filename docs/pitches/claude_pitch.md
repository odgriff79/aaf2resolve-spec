# [Tool/Model] Pitch
Date: 2025-08-28
Source: Conversation with claude

## Overview
(then paste the full pitch text exactly as written)

Request for Input (No Code Yet)
I’ve prepared a full specification repository for a project called aaf2resolve-spec: 👉 https://github.com/odgriff79/aaf2resolve-spec
This repo defines a spec-first, JSON-first pipeline for converting Avid AAF sequences into FCPXML 1.13 compatible with DaVinci Resolve.
Key points you need to know from the repo:
* Canonical JSON schema in /docs/data_model_json.md is the single source of truth.
* Traversal, UMID resolution, and effect extraction rules are defined in /docs/inspector_rule_pack.md.
* Authoritative-first UMID resolution is required: SourceClip → MasterMob → SourceMob → ImportDescriptor → Locator(URLString).
* Path fidelity: preserve UNC, percent-encoding, and drive letters exactly (no normalization).
* No filtering: all OperationGroups (AVX/AFX/DVE) must be captured, including filler effects, with parameters, keyframes, and external references.
* Legacy compressed JSON rules are included for traceability, not as the main implementation path.
* Writers must only consume canonical JSON — never AAF or DB directly.
* /src is scaffolding only, implementation must strictly follow /docs.
⚠️ Note: The repo itself may contain errors, gaps, or incorrect assumptions. At this stage, all ideas, critiques, and observations are welcome, even if they challenge or contradict parts of the repo.
What I’d like from you now:
* A pitch or proposal describing how you would proceed from here.
* Suggestions, ideas, or architectural strategies to move the project toward a working prototype.
* Inspirations you see from other open-source projects, industry standards, or commercial tools that might influence direction.
* Creative thoughts about workflow, UX, or validation/testing approaches.
* Absolutely no code at this stage — just reasoning, planning, and conceptual guidance.
The goal is to gather diverse perspectives from different AIs, then compare their proposals before we move forward with actual implementation.Edit🎯 Proposal: Strategic Path to Working AAF→Resolve Pipeline
After thoroughly reviewing your aaf2resolve-spec repository, I'm impressed by the rigorous specification-driven approach. Here's my strategic proposal for moving toward a working prototype:
🧭 Core Assessment: What's Right
Your repository demonstrates excellent architectural discipline:

Specification-first design prevents scope creep and implementation drift
Authoritative-first UMID resolution correctly addresses the core complexity of AAF parsing
Path fidelity mandates acknowledge the fragile nature of media workflows
Effect completeness (no filtering) ensures professional-grade conversion
Canonical JSON boundary creates a clean testing and validation surface

The docs/welcome_for_llms.md is particularly brilliant—it prevents the repetitive context-building cycle that typically plagues LLM collaborations on complex projects.
🚀 Proposed Implementation Strategy
Phase 1: Validation-Driven Prototyping (2-3 weeks)
1.1 Golden Sample Creation

Source 2-3 representative AAF files from different editorial contexts:

Simple cut sequence (baseline)
Complex timeline with AVX effects + Pan&Zoom stills
Timeline with nested sequences and broken UMID chains


Manually create expected canonical JSON for each using AAF Inspector
This becomes your ground truth for all subsequent validation

1.2 Minimal Viable Parser (MVP)

Implement build_canonical_from_aaf() with maximum logging/debugging
Focus on correctness over performance initially
Create extensive intermediate state dumps at each traversal step
Build comparison utilities to diff actual vs. expected canonical JSON

1.3 Contract Testing Framework
bash# Validation pipeline
tests/run_golden_tests.py 
  ├── Schema validation (required keys, types, nullability)
  ├── UMID chain integrity checks  
  ├── Timeline math verification (frame arithmetic)
  └── Path preservation audits (byte-for-byte comparison)
Phase 2: Real-World Robustness (3-4 weeks)
2.1 Edge Case Catalog
Based on industry experience, prioritize these failure modes:

Broken UMID chains (missing mobs, orphaned references)
UTF-16LE path corruption (Pan&Zoom stills with unusual encoding)
Mixed frame rates (source vs. timeline rate mismatches)
Drop-frame edge cases (29.97/59.94 with non-integer timecode)
Nested sequence recursion (deeply nested compositions)

2.2 Incremental FCPXML Development

Start with minimal valid FCPXML (clips only, no effects)
Add basic asset management (path preservation, de-duplication)
Progressively add effect parameter mapping (conservative, no guessing)
Validate each increment against DaVinci Resolve import

Phase 3: Professional Polish (2-3 weeks)
3.1 Enhanced AAF Inspector Integration
Your vision of right-click debugging hooks is excellent:

"Preview Canonical Fragment" for any AAF node
"Resolve Source Chain" with visual UMID traversal
"Build Canonical Timeline" with real-time JSON preview
This creates an interactive specification validator

3.2 Production Workflow Integration

Batch processing capabilities for editorial handoffs
Validation reports highlighting conversion warnings/losses
Asset relinking suggestions for broken media paths

🔍 Risk Mitigation Strategies
Technical Risks

pyaaf2 API limitations: Create abstraction layer for potential SDK changes
UMID resolution complexity: Implement extensive logging for chain traversal debugging
Resolve FCPXML quirks: Build round-trip validation (FCPXML → re-import → compare)

Scope Management

Effect parameter explosion: Use conservative whitelist approach—only map parameters with proven FCPXML equivalents
Format variations: Focus on broadcast-standard AAFs initially, not experimental formats
Performance optimization: Profile after correctness is established

💡 Architectural Inspirations
From FFmpeg Ecosystem

Extensive format validation with detailed error reporting
Probing utilities that expose internal structure without conversion
Conservative parameter handling (preserve unknown, don't guess)

From OTIO (OpenTimelineIO)

Adapter pattern for different editorial formats
Schema-driven validation with rich error messages
Timeline mathematics as first-class concern

From Professional Color Grading

Media conforming workflows with detailed reports
Asset relinking strategies for broken paths
Metadata preservation as non-negotiable requirement

🧪 Testing Philosophy
Contract-Driven Development
Every function should have paired specification tests:
pythondef test_resolve_sourceclip_authoritative_first():
    # Given: AAF with complete UMID chain
    # When: resolve_sourceclip() called
    # Then: path from Locator(URLString), not comp-level mirror
    
def test_path_preservation_byte_for_byte():
    # Given: UNC path with percent-encoding
    # When: canonical JSON generated  
    # Then: exact string match (no normalization)
Real-World Validation

Professional editor feedback loops with working colorists/editors
Production timeline stress tests (hundreds of cuts, dozens of effects)
Cross-platform path handling (Windows UNC, macOS volumes, Linux mounts)

🎨 Creative Workflow Ideas
Interactive Development

Live canonical JSON preview while editing specifications
Visual UMID chain explorer showing mob relationships
Timeline visualization overlaying canonical events on pyaaf2 structure

Collaborative Validation

Community AAF sample library with diverse editorial contexts
Crowdsourced edge case collection from professional workflows
Public validation dashboard showing conversion success rates

🎯 Success Metrics
Technical Milestones

 100% schema compliance on golden samples
 Zero path alterations in round-trip tests
 Complete effect capture (no OperationGroup losses)
 Sub-second conversion for typical timelines

Professional Adoption

 Working colorist endorsement ("This actually works!")
 Complex timeline survival (broadcast-grade sequences)
 Cross-platform reliability (Windows/macOS/Linux parity)

🔮 Future Vision
This project could become the reference implementation for AAF→NLE interchange, potentially inspiring:

Industry standardization around canonical JSON schema
Vendor-neutral editorial workflows
Open-source alternative to expensive proprietary conversion tools

The specification-driven approach you've established provides a solid foundation for building something that could genuinely serve professional post-production workflows.
Next Step Recommendation: Start with Phase 1.1 (golden sample creation) to establish your validation baseline, then implement the MVP parser with extensive debugging output. The specification quality you've established deserves an equally rigorous implementation approach.
