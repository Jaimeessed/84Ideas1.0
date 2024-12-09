# 84Ideas1.0

## Project Overview

This project is a web application built with Flask. It includes features such as user authentication, role management, client management, and integration with OpenAI for an AI-assisted Q&A feature.

## Features

- User authentication (login, registration)
- Role-based access control
- Client management
- Admin module
- Integration with OpenAI for Q&A
- Various HTML templates for different pages (e.g., login, register, dashboard, contact)

## Prerequisites

- Docker
- Docker Compose
- Python 3.8+
- PostgreSQL

## Setup

### Environment Variables

Copy the `.env.example` file and name it `.env`, then update it with the actual secret values.

> Take care to never share secrets in a code repository!

### Virtual Environment

Create and activate a virtual environment:

```sh
python -m venv venv
source venv/bin/activate
```
