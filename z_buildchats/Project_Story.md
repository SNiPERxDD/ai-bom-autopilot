
# ML-BOM Autopilot: The Story

## Inspiration

Our inspiration for ML-BOM Autopilot came from the growing need for robust AI governance and the increasing complexity of managing AI/ML components in modern software development. With regulations like the EU AI Act on the horizon, we saw a critical gap in tooling for creating verifiable, end-to-end audit trails for AI systems. We were particularly inspired by the idea of going beyond static analysis of code repositories and capturing the *actual* runtime usage of AI components. This led us to explore the novel approach of using eBPF for live, kernel-level tracing of ML artifacts, providing a true "source-of-truth" for what's running in production.

## What it does

ML-BOM Autopilot is a tactical AI governance system designed to provide complete transparency into your AI supply chain. It automatically:
*   **Discovers AI/ML Assets:** It scans Git repositories and Hugging Face spaces to find models, datasets, prompts, and tools.
*   **Captures Runtime Usage:** Using eBPF, it traces syscalls to see which AI components are actually being used by your applications in real-time.
*   **Generates ML-BOMs:** It creates standards-compliant CycloneDX Machine Learning Bill of Materials (ML-BOMs) for your AI stack.
*   **Versions and Diffs:** It stores versioned BOMs in a database and can automatically generate a "diff" to show you exactly what has changed between scans.
*   **Enforces Policies:** It runs checks against your AI inventory for things like license compliance, model drift, or use of unapproved components.
*   **Alerts and Notifies:** When a policy is violated, it can automatically send alerts to Slack or create tickets in Jira.
*   **Provides Hybrid Search:** It allows you to perform both semantic and keyword searches across all the evidence it has collected.

## How we built it

We built ML-BOM Autopilot with a modular and scalable architecture:
*   **Backend:** A Python-based backend using **FastAPI** for the API and **LangGraph** to orchestrate the complex, multi-step workflow of scanning, normalizing, embedding, generating BOMs, and checking policies.
*   **Database:** We used **TiDB Serverless** as our core database, leveraging its powerful hybrid capabilities. We used its vector search for semantic similarity on artifact metadata and its full-text search (with a fallback to an in-app BM25 implementation) for keyword-based queries.
*   **Runtime Tracing:** We used **eBPF** (via `py-bpfcc`) to create a lightweight, kernel-level tracer that could monitor file access and network calls to identify runtime usage of ML components with minimal overhead.
*   **Frontend:** A simple and intuitive user interface built with **Streamlit** provides a single-page dashboard to run scans and review the results (BOMs, Diffs, Policy Events).
*   **Integrations:** The system is designed to be extensible, with initial integrations for sending notifications to **Slack** and **Jira**.

## Challenges we ran into

*   **eBPF Noise Filtering:** The eBPF tracer initially generated a lot of noise from irrelevant system events. We had to develop a sophisticated filtering system based on file extensions, paths, and process names to isolate the events related to ML artifacts.
*   **Database Feature Variability:** We discovered that TiDB's FULLTEXT search feature wasn't available in all serverless regions. We overcame this by implementing a fallback mechanism that uses an in-application BM25 library for keyword search, ensuring our hybrid search would work for all users.
*   **License Complexity:** Dealing with software licenses is always a challenge. We integrated `scancode-toolkit` to help normalize found licenses to SPDX identifiers, but we also had to build a flexible policy system to handle "unknown" or unapproved licenses and allow for operator overrides.

## Accomplishments that we're proud of

*   **Runtime AI-BOM Generation:** We are incredibly proud of the eBPF-based runtime tracing. It's a novel approach that provides a much more accurate picture of an AI system's dependencies than static analysis alone.
*   **Standards-Compliant ML-BOMs:** We successfully implemented the generation of CycloneDX v1.6 ML-BOMs, ensuring our output is compatible with a growing ecosystem of security and compliance tools.
*   **Hybrid Search Implementation:** The successful implementation of a hybrid search system using both vector and full-text search (with a fallback) on TiDB is a significant technical achievement. The Reciprocal Rank Fusion (RRF) algorithm for combining the search results provides a superior retrieval experience.

## What we learned

Throughout this project, we learned a great deal about the intricacies of AI governance and the challenges of building a system that can provide a verifiable audit trail. We gained deep insights into:
*   The practical application of eBPF for system observability.
*   The power and flexibility of hybrid transactional/analytical processing (HTAP) databases like TiDB.
*   The importance of standards like CycloneDX for interoperability in the software supply chain.
*   The need for a flexible and user-friendly policy engine to handle the nuances of real-world compliance.

## What's next for ML-BOM Autopilot

We see a bright future for ML-BOM Autopilot. Our roadmap includes:
*   **Expanding Runtime Tracing:** Adding support for more syscalls and network protocols to capture an even wider range of runtime events.
*   **More Integrations:** Adding more notification channels and integrating with CI/CD systems to block builds that violate policy.
*   **Advanced Policy Rules:** Developing more sophisticated policy rules, including those based on model performance metrics or ethical AI guidelines.
*   **Cloud-Native Deployment:** Packaging the application for easy deployment on Kubernetes and other cloud-native platforms.

## Built with

*   **Languages:** Python
*   **Frameworks:** FastAPI, LangGraph, Streamlit
*   **Databases:** TiDB Serverless (with Vector Search and Full-Text Search)
*   **Platforms:** Docker
*   **Key Libraries:** `py-bpfcc` (for eBPF), `cyclonedx-python-lib`, `gitpython`, `rank-bm25`
*   **APIs & Services:** Hugging Face API, Slack API, Jira API
