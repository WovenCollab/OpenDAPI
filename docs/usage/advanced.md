# Advanced Usage

If the [simple use case](./index.md) does not meet your needs, you can create custom validators and use them in your runners.

All Validators essentially have a `base_template_for_autoupdate` method that returns a dictionary of OpenDAPI files and their contents. The OpenDAPI files can be modified directly as well. Every time the validators are run, the current state of the file is merged on top of the base template. This preserves the manual updates while ensuring a consistent structure, format and keeps the files up to date with the latest codebase and data models.


## Custom Teams Validator

Subclass the `TeamsValidator` class and update the `base_template_for_autoupdate` method.

```python
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

```

## Custom Datastores Validator

Subclass the `DatastoresValidator` class and update the `base_template_for_autoupdate` method.

```python
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

```

## Custom DAPI Validator

DAPI Validators behave the same way as well but they need to fulfill a few more requirements such as returning a list of relevant model classes and extracting the column information from them. Check out the [PynamodbDapiValidator class](https://github.com/WovenCollab/OpenDAPI/blob/main/client/python/opendapi/validators/dapi.py) for inspiration on how to create custom DAPI validators for any ORM.

Here is an example of a custom PynamoDb validator. Subclass the `PynamodbDapiValidator` class and fill in the methods to help build the base template for autoupdate.

```python
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

```
