| yml file                 | Triggers                                | Description                                                |
|--------------------------|-----------------------------------------|------------------------------------------------------------|
| `unit_tests_reduced.yml` | Push to any branch except fix/*         | Execute reduced matrix of unit tests                       |
| `unit_tests_full.yml`    | Pull requests or push to fix/* / manual | Execute full matrix of unit tests                          |
| `deploy_dev.yml`         | Manual                                  | Run full test matrix + deploy dev package to test.pypi.org |
| `deploy_prod.yml`        | Push to `main`                          | Run full test matrix + deploy dev package to pypi.org      |
| `update_badges.yml`      | Pull request to `main` / manual         | Update coverage & test badges & upload to github pages     |