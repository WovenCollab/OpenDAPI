## OpenDAPI

OpenDAPI is an open protocol for describing Data APIs, aka. DAPIs.

Data Producers create DAPIs alongside their schema to describe their datasets and fields, with semantic descriptions, data classifications, shareability status, and ownership information. They can codify their intent to explicitly share their datasets with their consumers in certain replication destinations with defined SLAs, and business purposes.

It's best to think of **DAPI as an evolution of data schema - schema++**, if you will. DAPI enables a federated Data Governance model where Data producers take ownership of their high-quality datasets being used in an organization, and play an active role in upkeeping their consumers' data privacy rights and organization's data security posture.

_Already familiar with OpenDAPI? [Skip to Getting Started section](#getting-started)_

### Background
#### Problem

_Data Governance is about protecting customer data while maximizing business value_. Organizations struggle getting this prioritized or done right, because they tend to be added as a concern after-the-fact, and the implementations tend to feel more like process than a delightful experience. We can do better, and when done right, it's a win-win for both customer rights and the organization.

In most organizations, significant resources are spent to reactively make sense of and govern data that was created and shared (read: _thrown over the wall_) through replication, bespoke APIs and ETLs. This creates a handful of problems - popular of them are:
- Data consumers have **little confidence in the quality of data** as the data producers seldom know how their data is being used.
- Crucial information such as **semantics, data classification (PII, Personal data, etc.)** are often inferred from the schema - the only thing data producers typically guarantee.
- Data Governance becomes nearly impractical **putting the data privacy and security obligations at risk** which inturn demands a costly centralized governance initiative.
- Data Producers, typically Software Engineers, just **don't have the right tools to participate** in the Modern Data Stack and intentionally drive business value of their data.

#### Purpose of OpenDAPI

OpenDAPI's core hypothesis is that data documentation, classification and codifying of sharing intent **at schema-time** is the most effective way to federate Data Governance and foster Data Collaboration in an organization.

This OpenDAPI repo is a collection of tools, clients and specifications to create DAPIs, and define associated entities such as teams, datastores and business purposes. This library also provides useful tooling for validating and auto-updating OpenDAPI files in any repository.

The library helps with the goal to create a `DAPI` file for every dataset (e.g. `user.dapi.yaml`). DAPI files reference information from `teams`, `datastores` and `purposes` (e.g. `company.teams.yaml`), which are defined in their own files. A dataset can have only one DAPI file, but there can be many teams, datastores and purposes, and the tooling can help you manage them. The Specification for all these protocols can be found as JSONSchema in the [spec](https://github.com/WovenCollab/OpenDAPI/tree/main/spec) directory.


#### What can DAPIs power?

OpenDAPI files can be used to power many Data Governance and Data Collaboration use-cases, and makes them first-class concerns of the Data Stack. Here are some example capabilities that can be powered by DAPIs and the OpenDAPI ecosystem:

- **Data Catalog and Semantic layer** - DAPIs can be used to power data catalogs, and provide a rich set of metadata to data consumers, powered by AI/ML.
- **Purpose Driven Data Sharing** - DAPIs can be used to codify data sharing intent, and enable data consumers to discover and request access to datasets for specific business purposes, which the data producer can approve or deny.
- **Data Privacy rights** - The data classification and business purposes can help power a ROPA, and make it easy to fulfill data privacy requests such as Right to Access, Right to be Forgotten, etc.
- **Data Quality** - DAPIs can be used to power data quality checks, perform downstream impact analysis, and enable data producers to proactively identify, and often prevent, data quality issues.


#### DAPI servers can take OpenDAPI to the next level

This OpenDAPI repo is certainly a self-sufficient system with specifications and language-specific clients to annotate, validate and auto-update DAPI files. However, the true power of OpenDAPI is realized when it is used in conjunction with a DAPI server.

A DAPI server can be built by the organizations glueing together existing solutions on top of the foundation provided by OpenDAPI or, better, leverage a commercial product that extends the power of OpenDAPI, such as the AI-native [Woven](https://wovencollab.com).

Because we capture the semantics in the DAPI files, [Woven](https://wovencollab.com) and other DAPI servers can harness the power of Gen-AI to power these workflows:

- **AI-powered suggestions** - DAPI servers can power AI/ML models to suggest data classifications, business purposes, and even data sharing intent at development time - in the IDE or the CI/CD pipeline (e.g. Github Actions)
- **Downstream impact analysis** - DAPI servers can parse the changes made to the DAPI files, and perform downstream impact analysis to identify and notify the affected consumers, or surface those at development time.
- **AI-enabled discovery** - The DAPIs, when registered with a DAPI server, can be used to power a data catalog and AI-driven BI interfaces for data consumers to get to their business metrics faster
- **Access control management** - DAPI servers can be used to power access control management workflows, and enable data consumers to request access to datasets for specific business purposes, which the data producer can approve or deny. DAPI servers can creates business purpose based roles in the storage systems that are then assigned to users and systems, to enforce access control policies.
- **Streamline Customer privacy rights** - With a powerful semantic catalog and control plane for datasets, DAPI servers can be used to streamline customer privacy rights fulfillment workflows such as Right to Access, Right to be Forgotten, etc.
- **Data management control plane** - DAPI servers can use the replication destinations, SLAs, and other information in the DAPI files to power a control plane for data management workflows such as replication, retention, etc.


#### OpenDAPI Fundamentals

Every dataset needs a DAPI file. Dataset is loosely defined and can be anything - entity, event or other package of information accessible in a storage system.

DAPI files are language-agnostic and are usually named `<dataset>.dapi.yaml` or `<dataset>.dapi.json`. DAPI files are written in YAML or JSON, and are validated against the JSONSchema specification identified in the `schema` attribute. The Specifications are hosted on [opendapi.org](https://opendapi.org/spec/0-0-1/dapi.json) and available in [this repo](https://github.com/WovenCollab/OpenDAPI/blob/main/spec/dapi.json)

Here's an example DAPI file:

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
- `owner_team_urn` - The team that owns this dataset and maps to a `company.teams.yaml` or `company.teams.json` file and adheres to the [teams specification](https://opendapi.org/spec/0-0-1/teams.json)
- `datastores URN` - The datastore where this dataset is created and consumed from, and maps to a `company.datastores.yaml` file, adhering to the [datastores specification](https://opendapi.org/spec/0-0-1/datastores.json)
- `business_purposes URN` - The business purposes for which this dataset is used, and maps to a `company.purposes.yaml` file, adhering to the [purposes specification](https://opendapi.org/spec/0-0-1/purposes.json)

All these specifications can also be found in this repo under the `spec` folder.

Here is a sample `company.teams.yaml`,

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
      username: aws_secretsmanager:arn:aws:secretsmanager:us-east-1:1234567:secret:prod/dynamodb/pw-123
    env_dev:
      location: arn:aws:dynamodb:us-east-1:972019825782
      username: aws_secretsmanager:arn:aws:secretsmanager:us-east-1:1234567:secret:prod/dynamodb/username-123
      username: aws_secretsmanager:arn:aws:secretsmanager:us-east-1:1234567:secret:prod/dynamodb/pw-123

- urn: company.datastores.snowflake
  type: snowflake
  host:
    env_prod:
      location: org-account.us-east-1.snowflakecomputing.com
      username: aws_secretsmanager:arn:aws:secretsmanager:us-east-1:1234567:secret:prod/dynamodb/username-123
      username: aws_secretsmanager:arn:aws:secretsmanager:us-east-1:1234567:secret:prod/dynamodb/pw-123
```

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

#### Putting DAPIs to use
There must be exactly one DAPI file per dataset. However, it is okay to have multiple files for teams, datastores and purposes. This ecosystem is fully extensible to support and enforce data policies as well.

As evident, OpenDAPI files are merely representation of information. The real value comes from the tooling
- by this package to generate, validate and autoupdate these files at development time
- by the DAPI server to build workflows on top of these DAPI files with intelligence

Imagine these scenarios:
1. An engineer adds or updates a dataset. Their local development environment auto generates and validates the OpenDAPI files. They push the changes to Github and the Github Actions interacts with the DAPI server to provide helpful AI-powered suggestions to improve the dataset's DAPI - semantics, data classification, etc. It also identifies potential downstream impact the changes may have and flags that in the same PR.

2. A data consumer wants access to a Snowflake dataset for their business purpose. They make their request in the DAPI server, which inturn creates a PR against the appropriate DAPI file for the data owner's approval. Upon approval, the snowflake role for the business purpose will be granted access to the dataset.

3. Want to create a ROPA? The DAPI server can parse the DAPIs and extract a fully-compliant ROPA for you to review and sign.


### Getting started

The specfications are defined in JSONSchema, and hence are language-agnostic. However, it is recommended to use the python client library to generate, validate and autoupdate these files for a streamlined developer experience. Other language clients are in the works, but the implementation will be similar. This package also includes a Github Action workflow to interact with a DAPI server as part of your CI/CD pipeline.

##### Step 1: Install the package
It is sufficient to install as a dev dependency, as the package is only used at development time.

```bash
pip install git+https://github.com/WovenCollab/OpenDAPI.git@main#subdirectory=client/python
# `pip install opendapi` will work once the package is published to PyPI
```

##### Step 2: Define validators
The python client has a few validators to validate the DAPI, teams, datastores and purposes files. These validators are designed to
- validate the file against the JSONSchema specification
- autoupdate the files based on your base template. Any changes to the OpenDAPI files will be applied on top of your base template before  validation.
- enforce that the files are created and updated automatically in a consistent manner - for e.g. you can configure the validator to create a DAPI file for every SqlAlchemy model in your codebase, and also enforce that the DAPI file is updated whenever the model is updated, such as adding or removing a new column.

There are `TeamsValidator`, `PurposesValidator`, `DatastoresValidator`, and a generic `DapiValidator`. There are also specific custom validators for `Pynamodb` and `SqlAlchemy` models that subclass the `DapiValidator`

Let us look at an example in action

```python
# /path/to/opendapi.py

import glob
import importlib
import inspect
import os

from opendapi.defs import OPENDAPI_SPEC_URL
from opendapi.validators.dapi import PynamodbDapiValidator
from opendapi.validators.datastores import DatastoresValidator
from opendapi.validators.teams import TeamsValidator

from opendapi.utils import get_root_dir_fullpath, find_subclasses_in_directory

from pynamodb.models import Model

"""
Find the root directory in the repo under which all the OpenDAPI files will be managed.
Works with /Users/username/Projects/dir/my-repo locally or /home/runner/work/my-repo/my-repo on GitHub Actions
"""
ROOT_DIR = get_root_dir_fullpath(__file__, 'my-repo')

# we choose to place all the DAPIs in the same directory, but this is not a requirement as long as they are under the ROOT_DIR
DAPIS_DIR = os.path.join(ROOT_DIR, "dapis")


class MyTeamsValidator(TeamsValidator):
    """
    An example validator for `my_company.teams.yaml` where we want to enforce that the teams file always has an Engineering team.
    Any changes made to the `my_company.teams.yaml` file will be applied on top of the output of this autoupdate base template.
    """

    REQUIRED_TEAM_NAMES = {"Engineering"}

    def base_template_for_autoupdate(self) -> dict[str, dict]:
        teams = [
            {
                "urn": f"my_company.teams.{team_name.lower()}",
                "name": team_name,
                "domain": "Engineering",
                "email": "grp.engineering@company.com",
            }
            for team_name in self.REQUIRED_TEAM_NAMES
        ]
        return {
            f"{DAPIS_DIR}/my_company.teams.yaml": {
                "schema": OPENDAPI_SPEC_URL.format(version="0-0-1", entity="teams"),
                "organization": {"name": "Company", "slack_teams": ["T123456789"]},
                "teams": teams,
            }
        }


class MyCompanyDatastoresValidator(DatastoresValidator):
    """
    MyCompany's datastores.dapi.yaml
    Checkout the [DatastoresValidator class](https://github.com/WovenCollab/OpenDAPI/blob/732fb2dccc5786aa97ac8d63c57e76c0267f1968/client/python/opendapi/validators/datastores.py#L6) for more details on how to use this validator.
    """

    def base_template_for_autoupdate(self) -> dict[str, dict]:
        return {
            f"{DAPIS_DIR}/my_company.datastores.yaml": {
                "schema": OPENDAPI_SPEC_URL.format(
                    version="0-0-1", entity="datastores"
                ),
                "datastores": [
                    {
                        "urn": "my_company.datastores.dynamodb",
                        "type": "dynamodb",
                        "host": {
                            "env_prod": {
                                "location": "arn:aws:dynamodb:us-east-1:12345678",
                            },
                            "env_dev": {
                                "location": "arn:aws:dynamodb:us-east-1:12345678",
                            },
                        },
                    }
                ],
            }
        }


class MyCompanyPynamodbDapiValidator(PynamodbDapiValidator):
    """
    MyCompany pynamodb tables dapi validator
    Check out the [PynamodbDapiValidator class](https://github.com/WovenCollab/OpenDAPI/blob/732fb2dccc5786aa97ac8d63c57e76c0267f1968/client/python/opendapi/validators/dapi.py#L88) for more details

    """

    def get_pynamo_tables(self):
        """return a list of Pynamo table classes here"""
        # Define the directory containing your modules and the base class
        directory = ROOT_DIR
        base_class = Model

        # Find subclasses of the base class in the modules in the directory
        models = find_subclasses_in_directory(
            directory, base_class, exclude_dirs=["tests", "node_modules"]
        )
        return models

    def build_datastores_for_table(self, table) -> dict:
        return {
            "producers": [
                {
                    "urn": "my_company.datastores.dynamodb",
                    "data": {
                        "identifier": table.Meta.table_name,
                        "namespace": "",
                    },
                },
            ],
            "consumers": [],
        }

    def build_owner_team_urn_for_table(self, table):
        return "my_company.teams.engineering"

    def build_urn_for_table(self, table):
        return f"my_company.dapis.{table.Meta.table_name}"

    def build_dapi_location_for_table(self, table) -> str:
        return f"{DAPIS_DIR}/pynamodb/{table.Meta.table_name}.dapi.yaml"


def test_and_autoupdate_opendapis():
    """Test and auto-update opendapis"""
    errors = []
    validator_clss = [
        MyCompanyTeamsValidator,
        MyCompanyDatastoresValidator,
        MyCompanyPynamodbDapiValidator,
    ]
    for val_cls in validator_clss:
        inst = val_cls(
            root_dir=ROOT_DIR, enforce_existence=True, should_autoupdate=True
        )
        try:
            inst.run()
        except Exception as exc:
            errors.append(exc)

    # Display errors however preferred
    if errors:
        raise Exception(errors)

```

##### Step 3: Add the validators to local testing
It's preferable to run the validator as part of your testing suite for faster dev cycles. To do so, add the validator script from the previous step to your tests - e.g. add to `repo/tests/test_opendapi.py` for python - which gets picked up by most testing frameworks. Since your CI/CD pipelines will also run the same tests, you can be sure that your opendapis are always up to date. It is also recommended that you run your tests as part of `pre-commit` hooks (e.g. [pre-commit](https://pre-commit.com/))

At this point, any changes made to the data models will autoupdate the DAPI files, locally, at development time.


##### Step 4: Connect with a DAPI server via Github Actions
The final step is to connect your Github repo(s) to a DAPI server. This is typically done via Github Actions. The OpenDAPI repo comes with an Action to validate, register and perform impact analysis (if datastore credentials are shared via .datastores.yaml opendapi file) with a DAPI server. To use this action, add the following to your repo's `.github/workflows/opendapi_ci.yml` file:

Check out [Woven](https://wovencollab.com) for a hosted DAPI server. Sign up to get your API key for this Github Action. Woven provides AI-powered suggestions for your DAPIs at development time, and helps document and classify your datasets.

```yaml
name: OpenDAPI CI
# Invoke for every Pull Request and push to main branch
on:
  pull_request:
  push:
    branches:
      - 'main'

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
    - name: DAPI CI Action
      # TODO: add versioning to the action
      uses: WovenCollab/OpenDAPI/actions/dapi_ci@main
      with:
        # Store credentials in Github Repo secrets
        DAPI_SERVER_HOST: https://api.wovencollab.com
        DAPI_SERVER_API_KEY: ${{ secrets.DAPI_SERVER_API_KEY }}

        # Configure when DAPIs should be registered. PRs only validate the OpenDAPI files
        MAINLINE_BRANCH_NAME: "main"
        REGISTER_ON_MERGE_TO_MAINLINE: True
```

##### Step 5: That's it!

Leverage your DAPIs in your DAPI server. Go check out what your DAPI server can do for you, powered by OpenDAPI. For e.g. [Woven](https://wovencollab.com) provides AI-powered suggestions for data documentation, data discovery on Slack, and more.
