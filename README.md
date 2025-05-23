# arXiv Paper Search

A web application to search for papers on arXiv, built with Python, Flask, and JavaScript.

## Description

This project provides a user-friendly interface to query the arXiv API, view research papers, and browse summaries. It features dynamic content loading, formatted results, and a clean user interface.

## Features

*   Search arXiv papers by keywords.
*   View paper details including title, authors, publication date, and summary.
*   Formatted author lists and publication dates.
*   Expandable paper summaries.
*   Client-side validation for search input.
*   AJAX-powered search and pagination for a smoother experience (no full page reloads).
*   Loading indicators during search.
*   Basic caching mechanism to reduce API calls for repeated searches (via Flask-Caching).

## Tech Stack

*   **Backend:** Python, Flask
*   **Frontend:** HTML, CSS, JavaScript (Vanilla JS)
*   **API:** arXiv API
*   **Caching:** Flask-Caching (SimpleCache - in-memory)
*   **Styling:** Bootstrap (primarily for layout and base components)

## Prerequisites

*   Python 3.8+ (or the version specified in your development environment)
*   pip (Python package installer)
*   A virtual environment tool (e.g., `venv`, `virtualenv`)

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment:**
    *   On macOS and Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a `.env` file in the project root directory. Add the following required variable:
    ```env
    SECRET_KEY='your_very_secret_and_unique_key_here'
    # FLASK_APP=run.py (Optional, usually auto-detected or set in run.py)
    # FLASK_ENV=development (Optional, for development mode features like debugger)
    ```
    Replace `'your_very_secret_and_unique_key_here'` with a strong, unique secret key.

5.  **Run the development server:**
    ```bash
    flask run
    ```
    Or, if you have a `run.py` configured to start the app:
    ```bash
    python run.py
    ```
    The application should typically be available at `http://127.0.0.1:5000/`.

## Usage

1.  Open your web browser and navigate to the application URL (e.g., `http://127.0.0.1:5000/`).
2.  Use the search bar to enter keywords for papers you are interested in.
3.  Browse the search results. Click on paper titles or PDF links to view more details.
4.  Use pagination controls to navigate through multiple pages of results.
5.  Click "Read more" or "Read less" to expand or collapse paper summaries.

## Running Tests

(Instructions for running automated tests will be added here once test suites are more formally structured, e.g., using PyTest discovery and a dedicated test command.)

Currently, testing involves manual verification of features and checking unit tests if run individually (e.g., `python -m unittest tests/test_template_filters.py`).

## Deployment

This section provides guidance on deploying the arXiv Paper Search application to various platforms.

### General Considerations

*   **WSGI Server:** For production, do not use the Flask development server (`flask run`). Instead, use a production-grade WSGI server like Gunicorn or uWSGI.
*   **Environment Variables:** Ensure `SECRET_KEY` is set securely in your production environment. Other configurations (like database URLs if you add a database) should also be managed via environment variables.
*   **Static Files:** Depending on the platform, you might need to configure how static files (CSS, JS) are served. Some platforms handle this automatically, while others might require a separate web server (like Nginx) or a CDN.
*   **Logging:** Implement robust logging to monitor application health and troubleshoot issues. Configure log levels and destinations appropriately for your environment.
*   **HTTPS:** Always serve your application over HTTPS in production. Most platforms offer easy ways to configure SSL/TLS certificates.

### Deploying with Docker

Docker allows you to package the application and its dependencies into a container, making it portable across different environments.

1.  **Create a `Dockerfile`:**
    ```Dockerfile
    # Use an official Python runtime as a parent image
    FROM python:3.9-slim

    # Set the working directory in the container
    WORKDIR /app

    # Copy the requirements file into the container
    COPY requirements.txt .

    # Install any needed packages specified in requirements.txt
    RUN pip install --no-cache-dir -r requirements.txt

    # Copy the rest of the application code into the container
    COPY . .

    # Make port 5000 available to the world outside this container
    EXPOSE 5000

    # Define environment variable
    ENV FLASK_APP=run.py
    ENV FLASK_RUN_HOST=0.0.0.0
    # Add your SECRET_KEY as an environment variable here or pass it during runtime
    # ENV SECRET_KEY='your_production_secret_key'

    # Run app.py when the container launches
    CMD ["gunicorn", "-b", "0.0.0.0:5000", "run:app"]
    ```
    *Note: You'll need to add `gunicorn` to your `requirements.txt`.*

2.  **Create a `.dockerignore` file:**
    ```
    venv
    __pycache__
    *.pyc
    *.pyo
    *.pyd
    .Python
    env
    .env
    .pytest_cache
    .DS_Store
    ```

3.  **Build the Docker image:**
    ```bash
    docker build -t arxiv-paper-search .
    ```

4.  **Run the Docker container:**
    ```bash
    docker run -p 5000:5000 -e SECRET_KEY='your_production_secret_key' arxiv-paper-search
    ```
    You can then access the application at `http://localhost:5000`.

*   **Resource Requirements:** Depends on traffic. Start with 1-2 vCPUs and 1-2 GB RAM and monitor.
*   **Security:** Keep the base Python image updated. Scan your Docker images for vulnerabilities. Manage secrets securely (e.g., using Docker secrets or environment variables injected at runtime).
*   **Scaling:** Use orchestration platforms like Docker Swarm or Kubernetes to manage and scale multiple containers.
*   **Monitoring:** Monitor container health, resource usage (CPU, memory), and application logs. Tools like Prometheus and Grafana can be integrated.

### Deploying to AWS

#### Using AWS Elastic Beanstalk

Elastic Beanstalk is a PaaS offering that simplifies deployment.

1.  **Prerequisites:** AWS Account, EB CLI installed and configured.
2.  **Ensure `gunicorn` is in `requirements.txt`.**
3.  **Initialize Elastic Beanstalk:**
    ```bash
    eb init -p python-3.9 arxiv-paper-search --region your-aws-region
    ```
4.  **Create an environment:**
    ```bash
    eb create arxiv-env
    ```
5.  **Configure Environment Variables:** In the Elastic Beanstalk console, navigate to your environment's "Configuration" > "Software" and add `SECRET_KEY`.
6.  **Deploy:**
    ```bash
    eb deploy
    ```
    Elastic Beanstalk will handle provisioning resources, deploying your code, and setting up load balancing.

*   **Resource Requirements:** EB manages this, but you can configure instance types. Start with `t3.micro` or `t3.small`.
*   **Security:** Use IAM roles for EC2 instances. Configure security groups to restrict traffic. Use AWS Certificate Manager for SSL.
*   **Scaling:** Configure auto-scaling rules in Elastic Beanstalk based on metrics like CPU utilization.
*   **Monitoring:** Use AWS CloudWatch for logs, metrics, and alarms.

### Deploying to Google Cloud Platform (GCP)

#### Using Google App Engine (Standard Environment)

App Engine is a serverless platform ideal for Python applications.

1.  **Prerequisites:** GCP Account, Google Cloud SDK installed and configured.
2.  **Create an `app.yaml` file:**
    ```yaml
    runtime: python39 # Or your Python version e.g., python310, python311
    entrypoint: gunicorn -b :$PORT run:app # Ensure gunicorn is in requirements.txt

    # instance_class: F1 # Optional: default is F1

    # automatic_scaling: # Optional: configure scaling
    #   min_instances: 1
    #   max_instances: 5
    #   target_cpu_utilization: 0.65

    env_variables:
      SECRET_KEY: 'your_production_secret_key' # Set this securely, consider Secret Manager
    ```
    *Note: For `SECRET_KEY`, it's better to use Google Secret Manager and grant your App Engine service account access.*

3.  **Deploy:**
    ```bash
    gcloud app deploy
    ```
    Select your region when prompted.

*   **Resource Requirements:** App Engine manages this based on your `app.yaml` scaling settings.
*   **Security:** App Engine provides a secure environment. Use Identity-Aware Proxy (IAP) for access control if needed. Manage secrets using Secret Manager.
*   **Scaling:** App Engine scales automatically. Configure scaling parameters in `app.yaml`.
*   **Monitoring:** Use Google Cloud Logging and Google Cloud Monitoring (Stackdriver).

### Deploying to Azure

#### Using Azure App Service

Azure App Service is a PaaS for web applications.

1.  **Prerequisites:** Azure Account, Azure CLI installed and configured.
2.  **Ensure `gunicorn` is in `requirements.txt`.**
3.  **Create an App Service Plan and Web App:**
    ```bash
    # Create a resource group
    az group create --name ArxivSearchResources --location "East US"

    # Create an App Service plan (Linux)
    az appservice plan create --name ArxivAppServicePlan --resource-group ArxivSearchResources --sku B1 --is-linux

    # Create the Web App
    az webapp create --resource-group ArxivSearchResources --plan ArxivAppServicePlan --name your-unique-arxiv-app-name --runtime "PYTHON|3.9" --startup-file "gunicorn -b 0.0.0.0:8000 run:app"
    ```
4.  **Configure Environment Variables:**
    ```bash
    az webapp config appsettings set --resource-group ArxivSearchResources --name your-unique-arxiv-app-name --settings SECRET_KEY="your_production_secret_key" FLASK_APP="run.py"
    ```
    *Azure App Service uses port 8000 by default for Python apps with Gunicorn if not specified otherwise in startup.*

5.  **Deploy using Git or Zip Deploy:**
    *   **Git:**
        ```bash
        az webapp deployment source config-local-git --name your-unique-arxiv-app-name --resource-group ArxivSearchResources
        # Add the Azure remote and push
        git remote add azure <azure-git-url>
        git push azure main # or your current branch
        ```
    *   **Zip Deploy:**
        ```bash
        # Create a zip file of your project (excluding venv, .git, etc.)
        zip -r ../arxiv-app.zip .
        az webapp deployment source config-zip --resource-group ArxivSearchResources --name your-unique-arxiv-app-name --src ../arxiv-app.zip
        ```

*   **Resource Requirements:** Depends on the App Service Plan SKU (e.g., B1, S1).
*   **Security:** Use Azure Key Vault for secrets. Configure custom domains and SSL bindings. Use Managed Identities.
*   **Scaling:** Scale up (change SKU) or scale out (increase instance count) in the App Service Plan settings.
*   **Monitoring:** Use Azure Monitor and Application Insights.

### Deploying On-Premises

Deploying on-premises requires more manual setup.

1.  **Server Setup:** Provision a server (physical or VM) with your chosen OS (e.g., Ubuntu).
2.  **Python Environment:** Install Python and `pip`. Set up a virtual environment.
3.  **Dependencies:** Install application dependencies from `requirements.txt`.
4.  **WSGI Server:** Install and configure Gunicorn (or uWSGI).
    ```bash
    gunicorn -b 0.0.0.0:5000 run:app
    ```
5.  **Reverse Proxy (Recommended):** Set up Nginx or Apache as a reverse proxy to handle incoming requests, serve static files, and manage SSL.
    *   Example Nginx configuration snippet:
        ```nginx
        server {
            listen 80;
            server_name yourdomain.com;

            location /static {
                alias /path/to/your/app/static;
            }

            location / {
                proxy_pass http://localhost:5000; # Or your Gunicorn address
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            }
        }
        ```
    *   Configure SSL with Let's Encrypt or your own certificates.
6.  **Process Management:** Use a process manager like `systemd` or `supervisor` to ensure Gunicorn runs continuously and restarts on failure.
    *   Example `systemd` service file (`arxivapp.service`):
        ```ini
        [Unit]
        Description=Gunicorn instance for arXiv Paper Search
        After=network.target

        [Service]
        User=youruser
        Group=yourgroup
        WorkingDirectory=/path/to/your/app
        Environment="PATH=/path/to/your/app/venv/bin"
        Environment="SECRET_KEY=your_production_secret_key"
        ExecStart=/path/to/your/app/venv/bin/gunicorn --workers 3 --bind unix:arxivapp.sock -m 007 run:app

        [Install]
        WantedBy=multi-user.target
        ```

*   **Resource Requirements:** Monitor CPU, RAM, and disk usage. Allocate based on expected load.
*   **Security:** Keep OS and all software patched. Implement firewalls (e.g., `ufw`). Secure SSH access. Regularly back up data.
*   **Scaling:** Manual scaling by adding more servers and using a load balancer. Can be complex.
*   **Monitoring:** Use tools like Nagios, Zabbix, or Prometheus/Grafana for server and application monitoring. Centralize logs.

## Project Structure (Key Components)

```
├── app/                    # Main application package
│   ├── static/             # Static files (CSS, JavaScript, images)
│   │   ├── css/style.css
│   │   └── js/main.js
│   ├── templates/          # HTML templates (Jinja2)
│   │   ├── base.html       # Base layout
│   │   └── index.html      # Main page with search and results
│   ├── __init__.py         # Application factory (create_app)
│   ├── arxiv_api.py      # Wrapper for arXiv API interaction
│   ├── models.py           # Data models (e.g., ArxivPaper)
│   ├── routes.py           # Application routes (Flask Blueprints)
│   ├── template_filters.py # Custom Jinja2 template filters
│   └── exceptions.py       # Custom exception classes
├── tests/                  # Unit and integration tests
├── venv/                   # Virtual environment directory (if created here)
├── .env                    # Environment variables (create this file)
├── .gitignore              # Files and directories to ignore by Git
├── config.py               # Configuration settings (dev, prod, test)
├── requirements.txt        # Python package dependencies
├── run.py                  # Script to run the Flask application
└── README.md               # This file
```

## API Endpoints

This application exposes the following HTTP endpoints:

### `/` or `/index`
*   **Method:** `GET`
*   **Description:** Renders the main homepage and search interface.
*   **URL Parameters:** None.
*   **Request Body:** None.
*   **Success Response:**
    *   Code: `200 OK`
    *   Content-Type: `text/html`
    *   Body: HTML page (`index.html`).
*   **Error Response:** See global error handlers (`404.html`, `500.html`).

### `/search`
*   **Method:** `GET`
*   **Description:** Performs a search for papers on arXiv based on the provided query.
*   **URL Parameters:**
    *   `query` (string, required): The search term(s).
    *   `page` (integer, optional, default: `1`): The page number for paginated results.
*   **Request Body:** None.
*   **Success Response:**
    *   Code: `200 OK`
    *   Content-Type: `text/html`
    *   Body: HTML page (`index.html`) displaying search results, pagination, and any relevant messages (e.g., "No results found", "Please enter a search query.").
*   **Error Response:**
    *   If `query` is empty, it typically re-renders `index.html` with an error message like "Please enter a search query."
    *   Handles various exceptions from the arXiv API wrapper (`ValidationException`, `NetworkException`, `ParsingException`, `ArxivAPIException`) by rendering `index.html` with an appropriate error message.
    *   See also global error handlers.

### `/ping`
*   **Method:** `GET`
*   **Description:** A simple health check endpoint for the main blueprint.
*   **URL Parameters:** None.
*   **Request Body:** None.
*   **Success Response:**
    *   Code: `200 OK`
    *   Content-Type: `application/json`
    *   Body: `{"message": "pong"}`
*   **Error Response:** Unlikely for this simple endpoint, but global error handlers would apply.

### `/health`
*   **Method:** `GET`
*   **Description:** A simple application health check endpoint.
*   **URL Parameters:** None.
*   **Request Body:** None.
*   **Success Response:**
    *   Code: `200 OK`
    *   Content-Type: `application/json`
    *   Body: `{"status": "Healthy"}`
*   **Error Response:** Unlikely, but global error handlers would apply.

### Rate Limiting and arXiv API Usage

*   **Application Rate Limiting:** Currently, no application-level rate limiting is explicitly configured (Flask-Limiter is a dependency but not initialized globally).
*   **arXiv API Usage:** This application interacts with the external arXiv API. Developers should be mindful of the [arXiv API usage guidelines](https://arxiv.org/help/api/user-manual), particularly regarding request rates (no more than 1 request per second is a general guideline). The `app/arxiv_api.py` module should ideally incorporate mechanisms to respect these limits.

## Code Structure and Developer Guidelines

### Project Structure (Key Components)

```
├── run.py                  # Script to run the Flask application
└── README.md               # This file
```

### Key Modules Overview

*   **`run.py`**: The main entry point for the application. It creates the Flask app instance using the application factory and runs the development server. For production, this script is used by WSGI servers like Gunicorn (e.g., `gunicorn run:app`).
*   **`config.py`**: Contains different configuration classes (e.g., DevelopmentConfig, ProductionConfig, TestingConfig) for the Flask application. Manages settings like `SECRET_KEY`, `DEBUG` mode, database URIs (if any), and custom application settings like `RESULTS_PER_PAGE`.
*   **`app/__init__.py`**: Implements the application factory pattern (`create_app`). Initializes Flask extensions (like Flask-Caching), registers blueprints, custom template filters, and global error handlers.
*   **`app/routes.py`**: Defines the main application routes (endpoints) using a Flask Blueprint. Handles incoming requests, interacts with services (like `arxiv_api.py`), and renders templates.
*   **`app/arxiv_api.py`**: A wrapper module for interacting with the external arXiv API. It handles constructing API requests, sending them, and parsing the XML responses into a more usable Python format (list of paper dictionaries and total results). It also defines custom exceptions for API-related errors.
*   **`app/models.py`**: (Currently seems to be a placeholder or for future database integration). If a database were used, this would define SQLAlchemy models or other data structures.
*   **`app/template_filters.py`**: Contains custom Jinja2 template filters used to format data within the HTML templates (e.g., formatting dates, authors, truncating text).
*   **`app/exceptions.py`**: Defines custom exception classes specific to the application, particularly for errors related to the arXiv API interaction (e.g., `ArxivAPIException`, `NetworkException`).
*   **`app/static/`**: Contains static assets like CSS files (`style.css`), JavaScript files (`main.js`, `subscribe.js`), and potentially images.
*   **`app/templates/`**: Contains Jinja2 HTML templates, including the base layout (`base.html`), main page (`index.html`), error pages (`404.html`, `500.html`), and any partials or email templates.

### Coding Standards

*   **PEP 8:** Follow PEP 8 guidelines for Python code style. Use a linter like Flake8 or a formatter like Black to help maintain consistency.
*   **Flask Blueprints:** Organize routes into Blueprints for better modularity, especially as the application grows. The current `main` blueprint is a good start.
*   **Configuration:** Keep sensitive information (like `SECRET_KEY`, API keys for other services if added) out of version control. Use environment variables and the `config.py` pattern. The `.env` file (gitignored) is suitable for local development.
*   **Error Handling:** Use specific custom exceptions where appropriate (as done in `app/exceptions.py`). Implement comprehensive error logging.
*   **Comments and Docstrings:** Write clear docstrings for modules, classes, functions, and methods. Use comments to explain complex or non-obvious parts of the code.
*   **Frontend Code:** Keep JavaScript and CSS in separate files under `app/static/`. Maintain clean and readable HTML templates.

### Testing

*   **(Current Status):** The "Running Tests" section in this README is a placeholder. Some individual unit tests might exist (e.g., `tests/test_template_filters.py` mentioned in the README).
*   **Framework:** Consider using PyTest or Python's built-in `unittest` framework for writing and running tests.
*   **Types of Tests:**
    *   **Unit Tests:** Test individual functions and classes in isolation (e.g., utility functions, template filters, arXiv API parsing logic).
    *   **Integration Tests:** Test interactions between components (e.g., a route correctly calling the arXiv API wrapper and processing its output).
    *   **Functional/End-to-End Tests:** Test application behavior from the user's perspective (e.g., using Selenium or Flask's test client to simulate browser interactions).
*   **Running Tests:** Aim for a simple command to run all tests (e.g., `pytest` or `python -m unittest discover tests`).
*   **Test Coverage:** Strive for good test coverage to ensure reliability.

### Extending the Application

Here are some ways the application could be extended:

*   **New Routes/Features:**
    1.  Define new route functions in `app/routes.py` (or a new blueprint).
    2.  Create new HTML templates in `app/templates/` if needed.
    3.  Add any business logic or service interactions (e.g., calling new functions in `app/arxiv_api.py` or other service modules).
*   **New Template Filters:** Add new filter functions to `app/template_filters.py` and register them in `app/__init__.py`.
*   **Database Integration:**
    1.  Choose a database (e.g., PostgreSQL, SQLite).
    2.  Add Flask-SQLAlchemy or another ORM/ODM to `requirements.txt`.
    3.  Initialize it in `app/__init__.py`.
    4.  Define models in `app/models.py`.
    5.  Set up database migrations (e.g., with Flask-Migrate).
*   **User Accounts/Authentication:** Could be added using Flask-Login or Flask-Security. This would involve new models, routes, and templates.
*   **Background Tasks:** For long-running operations (e.g., daily fetching of new papers), consider using a task queue like Celery.

## Automation and CI/CD

### Local Setup and Run Script (`deploy.sh`)

A `deploy.sh` script is provided in the project root to simplify local setup and execution for testing purposes. It automates:

1.  Checking for Python 3.
2.  Creating a virtual environment (`venv`) if it doesn't exist.
3.  Activating the virtual environment.
4.  Installing or upgrading dependencies from `requirements.txt`.

**Usage:**

```bash
./deploy.sh
```
After running the script, you can start the application using `flask run` or `python run.py` within the activated virtual environment.

**Note:** This script is intended for local development and testing. For production deployments, refer to the platform-specific guides in the "Deployment" section, which typically involve using a WSGI server like Gunicorn managed by a process supervisor.

### Continuous Integration (CI) with GitHub Actions

A basic Continuous Integration pipeline is configured using GitHub Actions. The workflow is defined in `.github/workflows/ci.yml` and performs the following steps on every push or pull request to the `main` and `master` branches:

1.  **Checkout Code:** Checks out the repository code.
2.  **Set up Python:** Configures the specified Python version (e.g., 3.9).
3.  **Install Dependencies:** Installs packages listed in `requirements.txt` and `flake8` for linting.
4.  **Lint with Flake8:** Runs `flake8` to check for Python syntax errors, undefined names, and adherence to some style conventions.

This CI setup helps ensure code quality and consistency. As the project evolves, test execution steps can be added to this workflow.

### Further CI/CD Considerations (Not yet fully implemented)

For a more comprehensive CI/CD pipeline, especially for automated deployments, consider the following aspects as outlined in the deployment guides for specific platforms:

*   **Automated Testing:** Integrate automated execution of unit, integration, and functional tests into the CI pipeline. The build should fail if tests do not pass.
*   **Build Artifacts:** For some deployment strategies (e.g., Docker-based), the CI pipeline would build artifacts like Docker images and push them to a container registry (e.g., GitHub Container Registry, Docker Hub, AWS ECR, Google Container Registry).
*   **Automated Deployment (CD):** Extend the CI pipeline to automate deployment to staging and production environments. This typically involves:
    *   Using platform-specific CLI tools (e.g., `eb deploy`, `gcloud app deploy`, `az webapp up`).
    *   Securely managing environment-specific configurations and secrets (e.g., using GitHub Actions secrets to store API keys or deployment credentials).
*   **Rollback Procedures:** Define and, if possible, automate rollback procedures in case a deployment fails or introduces critical issues. This might involve redeploying a previous stable version of the application or image.
*   **Database Migrations:** If the application uses a database with evolving schemas, database migration scripts (e.g., using Flask-Migrate with Alembic) should be integrated into the deployment process. Migrations should be applied automatically and carefully, often before the new application code is fully live.
*   **Environment Validation Checks:** After deployment, automated checks can be run to validate that the application is running correctly in the new environment (e.g., hitting key health check endpoints, performing basic smoke tests).

These advanced CI/CD practices would typically be implemented progressively as the project matures and specific deployment targets are finalized.

## Contributing

(Guidelines for contributing to the project can be added here if open for contributions.)

## License

(License information for the project can be added here.) 