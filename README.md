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

## Contributing

(Guidelines for contributing to the project can be added here if open for contributions.)

## License

(License information for the project can be added here.) 