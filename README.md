# agily

![Python Compatibility](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg) ![Django Compatibility](https://img.shields.io/badge/django-4.0%20%7C%204.1%20%7C%204.2%20%7C%205.0-green.svg)

## Overview

A very simple project managent tool built with Django & Bulma.io.

Here are some screenshots:

![](https://github.com/matagus/agily/raw/main/agily/static/screenshots/stories-1.png)

![](https://github.com/matagus/agily/raw/main/agily/static/screenshots/stories-2.png)

![](https://github.com/matagus/agily/raw/main/agily/static/screenshots/stories-4.png)

![](https://github.com/matagus/agily/raw/main/agily/static/screenshots/epics-1.png)

![](https://github.com/matagus/agily/raw/main/agily/static/screenshots/sprints-1.png)


## Features

- Create, edit, delete and list (with pagination) and search Stories, Epics and Sprints
- Stories have assignee, status, priority, points and optionally belong to an Epic and Sprint
- Epics have the same fields and they track progress
- Sprints have start and end dates, and also track progress
- Workspaces to separate stories, epics and sprints
- Login / logout


## Roadmap

- ~~Migrate from Turbolinks to HTMX <3~~
- Enhance test coverage
- ~~Run using docker~~
- Upgrade to Bulma 1.0
- Dark mode
- Support for multiple themes
- Realtime updates
- Milestones
- Subtasks
- Projects
- Multiple assigness
- Kanban view
- History
- Comments everywhere
- Attachments for Stories, Epics and Milestones
- Import data from Jira, Github, Asana, etc


## Quick Start

There are 2 ways to run the project: using Docker or installing it locally (using `hatch`).

### Run using Docker

1. Clone the repository:

```bash
git clone git@github.com:agily-project/agily.git
cd agily
```

2. Create the .env file (and customize it if you want):
```bash
cp config/env.example config/.env
```

3. Run the following command:

```bash
docker-compose up -d
```

4. Create a superuser:

```bash
docker-compose run --rm web sh -c "hatch run prod:python manage.py createsuperuser"
```

You will be asked a username, email and password for the superuser at the end of the process.

4. Open your browser at [http://localhost:8000](http://localhost:8000) and login using the user credentials you created
in step 3.


### Install and run locally

1. Clone the repository:

```bash
git clone git@github.com:agily-project/agily.git
cd agily
```

2. Install [hatch](https://hatch.pypa.io/latest/) using `pip`:

```
pip install hatch
```

or see [instructions for alternative methods](https://hatch.pypa.io/latest/install/).

3. Run the install command:

```
hatch run local:install
```

This will create the database, run the migrations, setup the `config/.env` configuration file and create a superuser/.
You will be asked a username, email and password for the superuser at the end of the process.

4. Run the web server:

```
hatch run local:server
```

5. Open your browser at [http://localhost:8000](http://localhost:8000) and login using the user credentials you created in step 3.


### Run Tests

`hatch run test:test` will run the tests in every Python + Django versions combination.

`hatch run test.py3.11-4.2:test will run them for python 3.11 and Django 4.2. Please see possible combinations using
`hatch env show` ("test" matrix).


## Contributing

Contributions are welcome! ❤️


## License

[MPL](https://www.mozilla.org/en-US/MPL/)
