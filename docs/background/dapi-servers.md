---
layout: page
title: DAPI server
permalink: /background/dapi-servers/
---

# DAPI Servers

**DAPI servers can take OpenDAPI to the next level** by providing a control plane for data management workflows, and enabling AI-powered data management.

This OpenDAPI library is certainly a self-sufficient system with specifications and language-specific clients to annotate, validate and auto-update DAPI files. However, the true power of OpenDAPI is realized when it is used in conjunction with a DAPI server.

A DAPI server can be built by the organizations glueing together existing solutions on top of the foundation provided by OpenDAPI or, better, leverage a commercial product that extends the power of OpenDAPI, such as the AI-native [Woven](https://wovencollab.com).

Because we capture the semantics in the DAPI files, [Woven](https://wovencollab.com) and other DAPI servers can harness the power of Gen-AI to power these workflows:

- **AI-powered suggestions** - DAPI servers can power AI/ML models to suggest data classifications, business purposes, and even data sharing intent at development time - in the IDE or the CI/CD pipeline (e.g. Github Actions)
- **Downstream impact analysis** - DAPI servers can parse the changes made to the DAPI files, and perform downstream impact analysis to identify and notify the affected consumers, or surface those at development time.
- **AI-enabled discovery** - The DAPIs, when registered with a DAPI server, can be used to power a data catalog and AI-driven BI interfaces for data consumers to get to their business metrics faster
- **Access control management** - DAPI servers can be used to power access control management workflows, and enable data consumers to request access to datasets for specific business purposes, which the data producer can approve or deny. DAPI servers can creates business purpose based roles in the storage systems that are then assigned to users and systems, to enforce access control policies.
- **Streamline Customer privacy rights** - With a powerful semantic catalog and control plane for datasets, DAPI servers can be used to streamline customer privacy rights fulfillment workflows such as Right to Access, Right to be Forgotten, etc.
- **Data management control plane** - DAPI servers can use the replication destinations, SLAs, and other information in the DAPI files to power a control plane for data management workflows such as replication, retention, etc.
