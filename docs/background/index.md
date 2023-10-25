# Background

OpenDAPI strives to shift-left the Data Governance and Data Collaboration concerns, and make them first-class concerns of the Modern Data Stack. We believe that it is possible to create self-discoverable and self-governed datasets.

## Problem

_Data Governance is about protecting customer data while maximizing business value_. Organizations struggle getting this prioritized or done right, because they tend to be added as a concern after-the-fact, and the implementations tend to feel more like process than a delightful experience.

In most organizations, significant resources are spent to reactively make sense of and govern data that was created and shared (read: _thrown over the wall_) through replication, bespoke APIs and ETLs. This creates a handful of problems - popular of them are:
- Data consumers have **little confidence in the quality of data** as the data producers seldom know how their data is being used.
- Crucial information such as **semantics, data classification (PII, Personal data, etc.)** are often inferred from the schema - the only thing data producers typically guarantee.
- Data Governance becomes nearly impractical **putting the data privacy and security obligations at risk** which inturn demands a costly centralized governance initiative.
- Data Producers, typically Software Engineers, just **don't have the right tools to participate** in the Modern Data Stack and intentionally drive business value of their data.

## DAPIs to the rescue

We can do better, and when done right, it's a win-win for both customer rights and the organization.

OpenDAPI files can be used to power many Data Governance and Data Collaboration use-cases, and makes them first-class concerns of the Data Stack. Here are some example capabilities that can be powered by DAPIs and the OpenDAPI ecosystem:

- **Data Catalog and Semantic layer** - DAPIs can be used to power data catalogs, and provide a rich set of metadata to data consumers, powered by AI/ML.
- **Purpose Driven Data Sharing** - DAPIs can be used to codify data sharing intent, and enable data consumers to discover and request access to datasets for specific business purposes, which the data producer can approve or deny.
- **Data Privacy rights** - The data classification and business purposes can help power a ROPA, and make it easy to fulfill data privacy requests such as Right to Access, Right to be Forgotten, etc.
- **Data Quality** - DAPIs can be used to power data quality checks, perform downstream impact analysis, and enable data producers to proactively identify, and often prevent, data quality issues.
