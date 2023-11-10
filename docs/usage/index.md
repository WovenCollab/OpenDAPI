---
layout: page
title: Quickstart
permalink: /usage/
---

# Quickstart

In this guide, we will help you get started with OpenDAPI. We will cover how to
- use the Python client library to create and maintain OpenDAPI files in your repository.
- use the Github Action workflow to interact with a DAPI server (such as Woven) as part of your CI/CD pipeline.

_The library currently supports Python, with deep integrations for Pynamodb and SqlAlchemy. Other languages and ORMs are in the works but the implementation will be similar. Reach out to us if you would like to see a specific language or ORM supported._

## Create and maintain OpenDAPI files
In these steps, we will bootstrap your repository with OpenDAPI files (DAPIs and supporting teams, datastores and purposes), and show you how to maintain them as your codebase evolves. After this integration, the DAPI files will autoupdate and will always be in sync with the data model schema.

### Step 1: Add OpenDAPI as a Dev Dependency

Add the library as a dependency, however you manage your dependencies. The library is not yet published to PyPI, so you will have to install it from the git repo for now.

#### requirements.txt
If you use `requirements.txt`, add the following to your `requirements-dev.txt` file
```bash
opendapi @ git+https://github.com/WovenCollab/OpenDAPI.git@main#subdirectory=client/python
```

#### setuptools
If you use setuptools, add the following to your `setup.py` file
```python
setup(
    ...
    extras_require={
        "dev": [
            ...
            "opendapi @ git+https://github.com/WovenCollab/OpenDAPI.git@main#subdirectory=client/python",
        ]
    },
    ...
)
```

#### poetry
If you use `poetry`, add the following to your `pyproject.toml` file
```
[tool.poetry.dev-dependencies]
...
opendapi = { git = "https://github.com/WovenCollab/OpenDAPI.git", subdirectory = "client/python" }
```

#### pip
If you just want to install in your virtual environment, you can use `pip` directly
```bash
pip install git+https://github.com/WovenCollab/OpenDAPI.git@main#subdirectory=client/python
```

### Step 2: Setup Validators and add to your testing suite

The library consists of validators that validate the OpenDAPI files against the specifications, and autoupdate them as your codebase and data models evolve.

For a simple integration, you can leverage the pre-defined validators via the configurable `opendapi.validators.runner.Runner` classes. These validate teams (TeamsValidator), datstores (DatastoresValidator), purposes (PurposesValidator), DAPIs (DapiValidator), with special provisions for Pynamodb models (PynamodbValidator), and SqlAlchemy models (SqlAlchemyValidator). The `Runner` classes are designed to be [extensible](./advanced.md) to support custom requirements and validators.

The following is all you need to enable OpenDAPI for your repository. Add this to your testings suite, and run it as part of your CI/CD pipeline.


```python
# /my_repo/tests/test_opendapi.py

"""Test and auto-update opendapis"""
import os

from opendapi.validators.runner import Runner

from opendapi.utils import get_root_dir_fullpath

from my_repo.pynamodb.models.base import BasePynamoDBModel
from my_repo.sqlalchemy.metadata import BaseSqlAlchemyMetadata

class AcmeDapiRunner(Runner):
    """Orchestrates validations and auto-updates of OpenDAPIs"""

    # Full Path of the repo root directory. `get_root_dir_fullpath` is a helper to get the full path of a directory relative to this file in all environments.
    REPO_ROOT_DIR_PATH = get_root_dir_fullpath(
        __file__, 'my_repo'
    )

    # Full path of the directory where the OpenDAPI files would go
    DAPIS_DIR_PATH = os.path.join(REPO_ROOT_DIR_PATH, 'dapis')

    # What is your Organization's name?
    ORG_NAME = 'Acme'

    # What is your Organization's email domain?
    ORG_EMAIL_DOMAIN = 'acme.com'

    # What is your Organization's Slack Team ID?
    # Find this in your Slack URL or run `boot_data.team_id` in your browser console.
    ORG_SLACK_TEAM = 'T12345678'

    # Seed list of team names.
    # This is just a seed list and you can always add more teams directly to the company.teams.yaml file.
    SEED_TEAMS_NAMES = ['Ecommerce', 'Fraud', 'Marketing']

    # Seed list of datastore names mapped to the types.
    # This is just a seed list and you can always add more datastores directly to the company.datastores.yaml file.
    SEED_DATASTORES_NAMES_WITH_TYPES = {
        'my_mysql': 'mysql',
        'my_dynamo': 'dynamodb',
        'my_snow': 'snowflake'
    }

    # Seed list of purpose names.
    # This is just a seed list and you can always add more purposes directly to the company.purposes.yaml file.
    SEED_PURPOSES_NAMES = ['fraud_analytics', 'marketing']

    # The Base class that all your PynamoDB models inherit from.
    # This is used to auto-discover your PynamoDB models.
    PYNAMODB_TABLES_BASE_CLS = BasePynamoDBModel

    # Alternatively, you can specify the list of PynamoDB models directly. PYNAMODB_TABLES_BASE_CLS will be ignored if this is specified.
    PYNAMO_TABLES = []

    # The name of the datastore that is used to produce data to the DAPIs.
    # This must be present in your SEED_DATASTORES_NAMES_WITH_TYPES.
    PYNAMODB_PRODUCER_DATASTORE_NAME = 'my_dynamo'

    # The name of the Snowflake datastore where this data is shared and consumed from.
    # This must be present in your SEED_DATASTORES_NAMES_WITH_TYPES.
    PYNAMODB_CONSUMER_SNOWFLAKE_DATASTORE_NAME = 'my_snow'

    # A function that maps the PynamoDB table name to the Snowflake table name.
    PYNAMODB_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER = (
        lambda self, table_name: (
            'db.schema', f'production_{table_name}'
        )
    )

    # The Metadata object classes that are used to auto-discover your SqlAlchemy models.
    SQLALCHEMY_TABLES_METADATA_OBJECTS = [BaseSqlAlchemyMetadata]

    # Alternatively, you can specify the list of SqlAlchemy models directly. SQLALCHEMY_TABLES_METADATA_OBJECTS will be ignored if this is specified.
    SQLALCHEMY_TABLES = []

    # The name of the datastore that is used to produce data to the DAPIs.
    # This must be present in your SEED_DATASTORES_NAMES_WITH_TYPES.
    SQLALCHEMY_PRODUCER_DATASTORE_NAME = 'my_mysql'

    # The name of the Snowflake datastore where this data is shared and consumed from.
    # This must be present in your SEED_DATASTORES_NAMES_WITH_TYPES.
    SQLALCHEMY_CONSUMER_SNOWFLAKE_DATASTORE_NAME = 'my_snow'

    # A function that maps the SqlAlchemy table name to the Snowflake table name.
    SQLALCHEMY_CONSUMER_SNOWFLAKE_IDENTIFIER_MAPPER = (
        lambda self, table_name: (
            'db.schema', f'production_{table_name}'
        )
    )
    )
    # Advanced Configuration, if you want to override or add more validators.
    OVERRIDE_TEAMS_VALIDATOR = None
    OVERRIDE_DATASTORES_VALIDATOR = None
    OVERRIDE_PURPOSES_VALIDATOR = None
    ADDITIONAL_DAPI_VALIDATORS = []


def test_and_autoupdate_dapis():
    """Execute the Runner as a test case"""
    runner = AcmeDapiRunner()
    runner.run()

```

If you'd like to customize the validators, you can do so by extending the `Runner` class and overriding the validators, or adding additional DAPI Validators for unsupported ORMs. See [advanced](./advanced.md) for more details.


## Connect to a DAPI server
### Step 3: Integrate with a DAPI server via Github Actions
The final step is to connect your Github repo(s) to a DAPI server via Github Actions. The OpenDAPI repo has a reusable action to validate, register and perform impact analysis (if datastore credentials are shared via .datastores.yaml opendapi file) with a DAPI server.

Check out [Woven](https://wovencollab.com) for a hosted DAPI server. Sign up to get your API key for this Github Action. Woven provides AI-powered suggestions for your DAPIs at development time, and helps document and classify your datasets.

To use this action,
1. In your Github settings, allow GitHub Actions to create pull requests. This setting can be found in a repository's settings under Actions > General > Workflow permissions. For repositories belonging to an organization, this setting can be managed by admins in organization settings under Actions > General > Workflow permissions.
2. Then, add the following to your repo's `.github/workflows/opendapi_ci.yml` file:


```yaml
name: OpenDAPI CI
# Invoke for every Pull Request and push to main branch
on:
  pull_request:
  push:
    branches:
      - 'main'

# Allows this action to create PRs to suggest DAPI improvements
permissions:
  contents: write
  pull-requests: write
  issues: write

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
    - name: DAPI CI Action
      uses: WovenCollab/OpenDAPI/actions/dapi_ci@main
      with:
        # Store credentials in Github Repo secrets
        DAPI_SERVER_HOST: https://api.wovencollab.com
        DAPI_SERVER_API_KEY: ${{ secrets.DAPI_SERVER_API_KEY }}
        # Configure when DAPIs should be registered.
        # PRs do not register but only validate and provide suggestions
        MAINLINE_BRANCH_NAME: "main"
        REGISTER_ON_MERGE_TO_MAINLINE: True
```
