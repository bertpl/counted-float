| yml file                 | Triggers               | Description                                                |
|--------------------------|------------------------|------------------------------------------------------------|
| `unit_tests_reduced.yml` | Push to any branch     | Execute reduced matrix of unit tests                       |
| `unit_tests_full.yml`    | Pull requests / manual | Execute full matrix of unit tests                          |
| `deploy_dev.yml`         | Manual                 | Run full test matrix + deploy dev package to test.pypi.org |
| `deploy_prod.yml`        | Push to `main`         | Run full test matrix + deploy dev package to pypi.org      |