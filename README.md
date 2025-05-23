![PyPI](https://img.shields.io/pypi/v/mkdocs-with-confluence)
[![Build Status](https://app.travis-ci.com/pawelsikora/mkdocs-with-confluence.svg?token=Nxwjs6L2kEPqZeJARZzo&branch=main)](https://app.travis-ci.com/pawelsikora/mkdocs-with-confluence)
[![codecov](https://codecov.io/gh/pawelsikora/mkdocs-with-confluence/branch/master/graph/badge.svg)](https://codecov.io/gh/pawelsikora/mkdocs-with-confluence)
![PyPI - Downloads](https://img.shields.io/pypi/dm/mkdocs-with-confluence)
![GitHub contributors](https://img.shields.io/github/contributors/pawelsikora/mkdocs-with-confluence)
![PyPI - License](https://img.shields.io/pypi/l/mkdocs-with-confluence)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/mkdocs-with-confluence)
# mkdocs-with-confluence 

MkDocs plugin that converts markdown pages into confluence markup
and export it to the Confluence page

## Setup
Install the plugin using pip:

`pip install mkdocs-with-confluence`

Activate the plugin in `mkdocs.yml`:

```yaml
plugins:
  - search
  - mkdocs-with-confluence
```

More information about plugins in the [MkDocs documentation: mkdocs-plugins](https://www.mkdocs.org/user-guide/plugins/).

## Usage

Use following config and adjust it according to your needs:

```yaml
  - mkdocs-with-confluence:
        host_url: https://<YOUR_CONFLUENCE_DOMAIN>/rest/api/content
        space: <YOUR_SPACE>
        parent_page_name: <YOUR_ROOT_PARENT_PAGE>
        username: <YOUR_USERNAME_TO_CONFLUENCE>
        password: <YOUR_PASSWORD_TO_CONFLUENCE>
        enabled_if_env: MKDOCS_TO_CONFLUENCE
        #verbose: true
        #debug: true
        dryrun: true
```

## Parameters:

### Requirements
- md2cf
- mimetypes
- mistune
#!SECTION

## Features
* **Automatic Upload:** Publishes MkDocs site (or select pages) to Confluence when run `mkdocs build`.
* **Hierarchy Preservation:** Replicates MkDocs navigation structure (sections and pages) in Confluence under a specified parent page.
* **Page Creation & Updates:** Creates new pages or updates existing ones based on title matching.
* **Attachment Handling:** Automatically uploads images referenced in Markdown and updates them if they change.
* **Flexible Configuration:** Control target Confluence instance, space, parent page, authentication, and more.
* **Environment Variable Support:** Configure credentials and other settings via environment variables for better security and CI/CD integration.
* **Dry Run Mode:** Test the publishing process without making any actual changes to Confluence.
* **Conditional Publishing:** Enable or disable the plugin based on an environment variable.
* **Verbose/Debug Logging:** Get detailed output for troubleshooting.

## Configuration Basic Setup
Activate the plugin in your `mkdocs.yml` file and provide the necessary configuration:

```yaml
plugins:
  - search
  - with-confluence:
      host_url: "[https://your-domain.atlassian.net/wiki/rest/api/content](https://your-domain.atlassian.net/wiki/rest/api/content)"
      # ^ Required: Your Confluence instance's REST API URL.
      #   For Confluence Cloud, it typically looks like: https://<YOUR_DOMAIN>.atlassian.net/wiki/rest/api/content
      #   For Confluence Server, it might be: https://<YOUR_CONFLUENCE_URL>/rest/api/content

      space: "YOUR_SPACE_KEY"
      # ^ Required: The unique key for your Confluence space.
      #   You can usually find this in the URL when Browse the space (e.g., .../display/SPACEKEY/...)
      #   or in Space Settings -> Space Details.

      parent_page_name: "My Project Documentation"
      # ^ Optional: The title of an existing page in Confluence under which all your MkDocs pages will be nested.
      #   If omitted, pages are created at the root of the space (or based on MkDocs nav structure from space root).
      #   It's recommended to create a dedicated parent page in Confluence first.

      # --- Authentication ---
      username: "your_confluence_email@example.com"
      # ^ Required: Your Confluence username, often your email address.
      #   Can also be set via JIRA_USERNAME environment variable.

      api_token: "YOUR_CONFLUENCE_API_TOKEN"
      # ^ Required for Confluence Cloud (recommended): Your Confluence API Token.
      #   See 'Authentication' section below for how to generate one.
      #   Can also be set via CONFLUENCE_API_TOKEN environment variable.
      #   If api_token is provided, 'password' will be ignored.

      password: "YOUR_CONFLUENCE_PASSWORD"
      # ^ For Confluence Server or if not using api_token (less secure).
      #   Can also be set via JIRA_PASSWORD environment variable.

      # --- Optional Settings ---
      # enabled_if_env: "PUBLISH_TO_CONFLUENCE"
      # ^ Only publish if the environment variable PUBLISH_TO_CONFLUENCE is set to "1".
      # verbose: false
      # debug: false
      # dryrun: false # Set to true to test without making actual changes to Confluence.

```