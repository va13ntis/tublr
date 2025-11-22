# Tublr

A simple YouTube video downloader built with FastAPI.

## Features

- FastAPI backend
- YouTube video and audio downloading
- Basic web interface with Tailwind CSS
- Two-factor authentication for security
- QR code generation for 2FA registration

## Prerequisites

- Python 3.8+
- npm (for Tailwind CSS only)
- SQLite (included in Python)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tublr.git
cd tublr
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On Unix or MacOS
source .venv/bin/activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Install development dependencies (optional):
```bash
pip install -r requirements-dev.txt
```

5. Install and build Tailwind CSS:
```bash
npm install tailwindcss@latest
npx tailwindcss -i ./app/static/css/input.css -o ./app/static/css/output.css --watch
```

## Development

1. Start the development server:
```bash
uvicorn app.main:app --reload
```

2. Run tests (Work in Progress):
```bash
pytest
```

## Project Structure

```
tublr/
├── app/                    # Main application package
│   ├── main.py            # Application entry point
│   ├── db.py              # Database configuration
│   ├── templates/         # HTML templates
│   ├── static/           # Static files
│   └── views/            # View handlers
├── tests/                 # Test suite (WIP)
├── assets/               # Project assets
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
├── requirements-test.txt # Test dependencies
└── dockerfile           # Docker configuration
```

## Docker Support

The project includes Docker support. To build and run the container:

```bash
docker build -t tublr .
docker run -p 8000:8000 tublr
```

## Disclaimer

This software is provided "as is", without warranty of any kind. The author is not responsible for any misuse or any consequences arising from the use of this software. Users are solely responsible for ensuring their use of this software complies with all applicable laws and YouTube's terms of service.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastAPI for the web framework
- SQLAlchemy for database ORM
- Tailwind CSS for styling
- All other open-source contributors 