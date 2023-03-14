::: eventiq.service.Service
    handler: python
    options:
      members:
        - subscribe
      show_root_heading: true
      show_source: false

## Service Runner

Service runner class is a service container, responsible to run one or more services, as a standalone
program. If you want to run only one service, the `ServiceRunner` instance will be created under the hood.

::: eventiq.runner.ServiceRunner
    handler: python
    options:
      members:
        - __init__
        - run
      show_root_heading: true
      show_source: false