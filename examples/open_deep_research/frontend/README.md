# Open Deep Research Frontend

A web-based frontend for the Open Deep Research application, which uses SmolaGents to perform deep research on the web.

## Features

- User-friendly interface for submitting research questions
- Real-time updates of research progress using WebSockets
- Support for multiple language models
- Research history tracking
- Responsive design for desktop and mobile

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure you have set up the backend requirements as well:

```bash
cd ..
pip install -r requirements.txt
```

3. Set up your environment variables in a `.env` file:

```
HF_TOKEN=your_huggingface_token
SERPAPI_API_KEY=your_serpapi_key
OPENAI_API_KEY=your_openai_key
```

## Usage

1. Start the Flask application:

```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5001`

3. Enter your research question, select a model, and click "Start Research"

## Development

- `app.py`: Main Flask application
- `templates/`: HTML templates
- `static/css/`: CSS stylesheets
- `static/js/`: JavaScript files

## Integration with Backend

This frontend integrates with the Open Deep Research backend (`run.py`) to perform web research using SmolaGents. The backend handles:

- Web browsing and search
- Text analysis
- Visual content analysis
- Code generation for data processing

## License

See the main project license file. 