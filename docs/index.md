<p align="left">
    <a href="https://github.com/WovenCollab/OpenDAPI"  alt="GitHub">
        <img src="https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white" />
    </a>
    <a href="https://wovencollab.com" alt="Woven" >
        <img src="https://woven-public.s3.amazonaws.com/static/img/logo.png" width="30" />
    </a>
</p>

[OpenDAPI](https://opendapi.org) is an open protocol for creating _self-discoverable_ and _self-governed_ datasets.

Like a thoughtfully created API, a Data API (or DAPI) enables data collaboration in an organization. DAPI as an evolution of the data schema (Schema++). It enables a federated Data Governance model where Data producers take ownership of their high-quality datasets, embrace its use in their organization, and play an active role in upkeeping their consumers' data privacy rights and organization's data security posture.

Data producers use DAPIs to describe their datasets and fields, with semantic descriptions, data classifications, shareability status, and ownership information. They can codify their intent to explicitly share their datasets with their consumers in certain replication destinations with defined SLAs, and business purposes.

## Purposes of OpenDAPI

OpenDAPI's core hypothesis is that data documentation, classification and codifying of sharing intent **at schema-time** is the most effective way to federate Data Governance and foster Data Collaboration in an organization.

To that end, the OpenDAPI library powers two main purposes:

### 1. Create and maintian DAPI files

The repo contains a collection of tools, clients and specifications to create DAPIs, and define associated entities such as teams, datastores and business purposes. This library also provides useful tooling for validating and auto-updating OpenDAPI files in any repository.

The library helps with the goal to create a `DAPI` file for every dataset (e.g. `user.dapi.yaml`). DAPI files reference information from `teams`, `datastores` and `purposes` (e.g. `company.teams.yaml`), which are defined in their own files. A dataset can have only one DAPI file, but there can be many teams, datastores and purposes, and the tooling can help you manage them.

The protocols for these DAPI, teams, datastores and purposes entities are available as [versioned JSONSchema specifications](./spec/index.md).


### 2. Connect to a DAPI server

This OpenDAPI repo is certainly a self-sufficient system with specifications and language-specific clients to annotate, validate and auto-update DAPI files. However, the true power of OpenDAPI is realized when it is used in conjunction with a DAPI server.

The OpenDAPI library also provides clients, such as a Github Action, to connect to a DAPI server to power Data Governance and Data Collaboration workflows.

A DAPI server can be built by the organizations glueing together existing solutions on top of the foundation provided by OpenDAPI or, better, leverage a commercial product that extends the power of OpenDAPI, such as the **AI-native [Woven](https://wovencollab.com)**.

## Curious to learn more?
- [Why DAPIs?](./background/index.md)
- [What can DAPI Servers do?](./background/dapi-servers.md)
    - [What can Woven do for you?](https://wovencollab.com)
- [OpenDAPI Specification](./spec/index.md)


## Getting Started
- [OpenDAPI Fundamentals](./usage/fundamentals.md)
- [Quickstart](./usage/index.md)
- [Advanced Usage](./usage/advanced.md)
