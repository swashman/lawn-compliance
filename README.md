# Lawn Compliance

Lawn Compliance cogs and tasks

[![license](https://img.shields.io/badge/license-MIT-green)](https://github.com/swashman/lawn-compliance/blob/master/LICENSE)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Installing into production AA

To install your plugin into a production AA run this command within the virtual Python environment of your AA installation:

```bash
pip install git+https://github.com/swashman/lawn-compliance
```

- Add `'lawn_compliance',` to `INSTALLED_APPS` in `settings/local.py`
- add the following settings to `settings/local.py`

```python
## LAWN COMPLIANCE SETTINGS
LAWN_COMPLIANCE_CHANNELS = [
    1243724889731502191
]  # list of channels that allow alliance and any corp commands
```

- run migrations
- restart your allianceserver.

## Permissions

| Name                     | Description                                                |
| ------------------------ | ---------------------------------------------------------- |
| `lawn_compliance.alliance` | Can view all compliance levels. |
| `lawn_compliance.any_corp` | Can view any corp and own corp compliance data.    |
| `lawn_compliance.own_corp` | Can view own corp compliance data.  |

## Bot slash Commands

all commands begin with /compliance

|Command |  Description |
|--- | --- |
|`alliance` | returns basic data of all corps|
|`corp` | returns corp specific data for selected corp|
|`mycorp` | returns corp specific data for own corp|
