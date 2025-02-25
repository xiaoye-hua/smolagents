# Open Deep Research

A web-based application for conducting deep research using AI agents.

## Overview

Open Deep Research is a tool that allows users to ask research questions and receive comprehensive answers. The application uses AI agents to search the web, analyze information, and provide detailed responses.

## Features

- Ask research questions and get comprehensive answers
- Real-time updates of the research process
- Support for multiple language models
- Detailed step-by-step explanation of the research process
- Web browsing capabilities for information gathering

## Implementation Options

### 1. Gradio Implementation (Recommended)

The Gradio implementation provides a simple, clean interface that matches the behavior of the [Hugging Face Space](https://huggingface.co/spaces/m-ric/open_Deep-Research).

#### Running the Gradio App

```bash
# Install dependencies
poetry install

# Run the app
./run_gradio.sh
# or
poetry run python app.py
```

The Gradio app will be available at http://localhost:7860

### 2. Flask Implementation

The Flask implementation provides a more customizable interface with WebSocket support for real-time updates.

#### Running the Flask App

```bash
# Install dependencies
poetry install

# Run the app
cd frontend
poetry run python app.py
```

The Flask app will be available at http://localhost:5002

## Usage

1. Enter your research question in the text box
2. Select a language model from the dropdown
3. Click "Start Research"
4. Wait for the research process to complete
5. Review the detailed answer and research process

## Example Questions

- What is the capital of China?
- What were the economic impacts of the 1929 stock market crash?
- How does photosynthesis work?
- What are the main theories about dark matter?

## Dependencies

- Python 3.9+
- Poetry for dependency management
- OpenAI API key (for GPT models)
- Anthropic API key (for Claude models)

## License

This project is open source and available under the MIT License.
