---
layout: page
title: Fundamentals
permalink: /usage/fundamentals/
---

# OpenDAPI Fundamentals

Every dataset needs a DAPI file. Dataset is loosely defined and can be anything - entity, event or other package of information accessible in a storage system.

DAPI files are language-agnostic and are usually named `<dataset>.dapi.yaml` or `<dataset>.dapi.json`. DAPI files are written in YAML or JSON, and are validated against the JSONSchema specification identified in the `schema` attribute. The specifications are available on [opendapi.org](../spec/index.md).

## Examples
### DAPI
Let us take a look at a DAPI file for a dataset called `user`:

```yaml
# /path/to/user.dapi.yaml
schema: https://opendapi.org/spec/0-0-1/dapi.json

# Identifier that is unique across the organization
urn: company.membership.user
type: entity
description: This dataset contains information about our users and are stored when they signup

# The team that owns this dataset
owner_team_urn: my_company.teams.engineering.accounts

datastores:
  # The datastore where this dataset is created
  producers:
  - urn: my_company.datastores.dynamodb
    # what is this dataset called in the datastore
    data:
      identifier: User
      namespace: ''
    # approved business purposes for which this dataset is used in this datastore
    business_purposes: ['servicing', 'fraud_prevention']
    # infinite retention
    retention_days: ~
    # source datastore
    freshness_sla_minutes: 0

  # The datastore where this dataset is replicated to and consumed from
  consumers:
  - urn: my_company.datastores.snowflake
    data:
      identifier: user
      namespace: prod.accounts
    business_purposes: ['product_analytics', 'direct_marketing']
    # These business purposes require a 365 day retention
    retention_days: 365
    # SLA to replicate to this datastore
    freshness_sla_minutes: 60

fields:
- name: email
  data_type: string
  description: The email of the user that is verified via OTP
  is_nullable: false
  is_pii: true
  # Does the producer guarantee the field's stability
  share_status: stable

- name: name
  data_type: string
  description: The full legal name of the user
  is_nullable: false
  is_pii: true
  # the producer may change the field's semantics at some point
  share_status: unstable

- name: created_at
  data_type: datetime
  description: Timestamp when they created an account
  is_nullable: false
  is_pii: false
  share_status: stable

# unique key, often useful to manage data
primary_key:
- email
```

Every DAPI has its `URN` to uniquely identify within an organization, and it also references three other URNs:
- `owner_team_urn` - The team that owns this dataset and maps to a `company.teams.yaml` or `company.teams.json` file and adheres to the [teams specification](../spec/0-0-1/teams.json)
- `datastores URN` - The datastore where this dataset is created and consumed from, and maps to a `company.datastores.yaml` file, adhering to the [datastores specification](../spec/0-0-1/datastores.json)
- `business_purposes URN` - The business purposes for which this dataset is used, and maps to a `company.purposes.yaml` file, adhering to the [purposes specification](../spec/0-0-1/purposes.json)


### Teams
Let us review the `company.teams.yaml` file.

```yaml
# /path/to/company.teams.yaml
schema: https://opendapi.org/spec/0-0-1/teams.json
organization:
  name: Acme Company
  # Slack integration
  slack_teams:
  - T1234567890
teams:
- urn: my_company.teams.engineering
  name: Engineering
  domain: Engineering
  email: lead@company.com
- urn: my_company.teams.engineering.accounts
  name: Accounts Engineering
  domain: User Growth
  email: accounts@company.com
  manager_email: mgr@company.com
  slack_channel_id: C1234567890
  github_team: org/accounts
  # org hierarchy
  parent_team_urn: my_company.teams.engineering
```

### Datastores

Here is a sample `company.datastores.yaml`. Adding datastore credentials is optional, but recommended to enable DAPI servers to connect to the datastores and provide impact analysis as part of every change.

```yaml
# /path/to/company.datastores.yaml
schema: https://opendapi.org/spec/0-0-1/datastores.json
datastores:
- urn: company.datastores.dynamodb
  type: dynamodb
  host:
    # Supports multiple environments, but env_prod is required
    env_prod:
      location: arn:aws:dynamodb:us-east-1:12345567
      # Credentials must be shared with your DAPI server AWS accounts
      username: aws_secretsmanager:arn:aws:secretsmanager:us-east-1:1234567:secret:prod/dynamodb/username-123
      password: aws_secretsmanager:arn:aws:secretsmanager:us-east-1:1234567:secret:prod/dynamodb/pw-123
    env_dev:
      location: arn:aws:dynamodb:us-east-1:972019825782
      username: aws_secretsmanager:arn:aws:secretsmanager:us-east-1:1234567:secret:prod/dynamodb/username-123
      password: aws_secretsmanager:arn:aws:secretsmanager:us-east-1:1234567:secret:prod/dynamodb/pw-123

- urn: company.datastores.snowflake
  type: snowflake
  host:
    env_prod:
      location: org-account.us-east-1.snowflakecomputing.com
      username: aws_secretsmanager:arn:aws:secretsmanager:us-east-1:1234567:secret:prod/dynamodb/username-123
      password: aws_secretsmanager:arn:aws:secretsmanager:us-east-1:1234567:secret:prod/dynamodb/pw-123
```

### Purposes
and a sample `company.purposes.yaml`,

```yaml
# /path/to/company.purposes.yaml
schema: https://opendapi.org/spec/0-0-1/purposes.json
purposes:
- urn: company.purposes.servicing
  description: Servicing our customers
- urn: company.purposes.fraud_prevention
  description: Preventing fraud
```

## Putting DAPIs to use

There must be exactly one DAPI file per dataset. However, it is okay to have multiple files for teams, datastores and purposes. This ecosystem is fully extensible to support and enforce data policies as well.

As evident, OpenDAPI files are merely representation of information. The real value comes from the tooling to create & maintain DAPIs and power workflows using the DAPI server.

Here are some example scenarios:
1. An engineer adds or updates a dataset. Their local development environment auto generates and validates the OpenDAPI files. They push the changes to Github and the Github Actions interacts with the DAPI server to provide helpful AI-powered suggestions to improve the dataset's DAPI - semantics, data classification, etc. It also identifies potential downstream impact the changes may have and flags that in the same PR.

2. A data consumer wants access to a Snowflake dataset for their business purpose. They make their request in the DAPI server, which inturn creates a PR against the appropriate DAPI file for the data owner's approval. Upon approval, the snowflake role for the business purpose will be granted access to the dataset.

3. Want to create a ROPA? The DAPI server can parse the DAPIs and extract a fully-compliant ROPA for you to review and sign.
