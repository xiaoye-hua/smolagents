import os
import sys
import threading
import json
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

# Add the parent directory to sys.path to import from run.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run import get_model, BROWSER_CONFIG, AUTHORIZED_IMPORTS, TextInspectorTool
from scripts.text_web_browser import (
    SimpleTextBrowser,
    VisitTool,
    PageUpTool,
    PageDownTool,
    FinderTool,
    FindNextTool,
    ArchiveSearchTool,
)
from scripts.visual_qa import visualizer
from smolagents import (
    CodeAgent,
    GoogleSearchTool,
    LiteLLMModel,
    ToolCallingAgent,
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'open-deep-research-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global variables to store the current research session
current_model = None
current_agent = None
current_question = None
is_processing = False
research_output = []

def update_progress(message, message_type="info"):
    """Send progress updates to the frontend via WebSocket."""
    socketio.emit('progress_update', {
        'message': message,
        'type': message_type
    })

class WebSocketHandler:
    """Handler to capture agent outputs and send them to the frontend."""
    
    def __init__(self):
        self.lock = threading.Lock()
    
    def handle_output(self, message, message_type="tool_output"):
        with self.lock:
            research_output.append({
                'message': message,
                'type': message_type
            })
            socketio.emit('research_update', {
                'message': message,
                'type': message_type
            })

ws_handler = WebSocketHandler()

# Monkey patch the print function to capture output
original_print = print
def patched_print(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    ws_handler.handle_output(message)
    return original_print(*args, **kwargs)

def run_research(question, model_id):
    """Run the research process with the given question and model."""
    global is_processing, current_question, research_output
    
    is_processing = True
    current_question = question
    research_output = []
    
    try:
        update_progress(f"Starting research on: {question}")
        update_progress(f"Using model: {model_id}")
        
        # Initialize model and tools
        model = get_model(model_id)
        text_limit = 100000
        document_inspection_tool = TextInspectorTool(model, text_limit)
        browser = SimpleTextBrowser(**BROWSER_CONFIG)
        
        WEB_TOOLS = [
            GoogleSearchTool(),
            VisitTool(browser),
            PageUpTool(browser),
            PageDownTool(browser),
            FinderTool(browser),
            FindNextTool(browser),
            ArchiveSearchTool(browser),
            TextInspectorTool(model, text_limit),
        ]
        
        update_progress("Initializing web browser agent...")
        text_webbrowser_agent = ToolCallingAgent(
            model=model,
            tools=WEB_TOOLS,
            max_steps=20,
            verbosity_level=2,
            planning_interval=4,
            name="search_agent",
            description="""A team member that will search the internet to answer your question.
        Ask him for all your questions that require browsing the web.
        Provide him as much context as possible, in particular if you need to search on a specific timeframe!
        And don't hesitate to provide him with a complex search task, like finding a difference between two webpages.
        Your request must be a real sentence, not a google search! Like "Find me this information (...)" rather than a few keywords.
        """,
            provide_run_summary=True,
        )
        text_webbrowser_agent.prompt_templates["managed_agent"]["task"] += """You can navigate to .txt online files.
        If a non-html page is in another format, especially .pdf or a Youtube video, use tool 'inspect_file_as_text' to inspect it.
        Additionally, if after some searching you find out that you need more information to answer the question, you can use `final_answer` with your request for clarification as argument to request for more information."""
        
        # Try to override the print function in the agent
        try:
            text_webbrowser_agent._print = ws_handler.handle_output
        except (AttributeError, TypeError):
            # If direct override fails, use monkey patching
            sys.stdout.write = lambda x: ws_handler.handle_output(x)
        
        update_progress("Initializing manager agent...")
        manager_agent = CodeAgent(
            model=model,
            tools=[visualizer, document_inspection_tool],
            max_steps=12,
            verbosity_level=2,
            additional_authorized_imports=AUTHORIZED_IMPORTS,
            planning_interval=4,
            managed_agents=[text_webbrowser_agent],
        )
        
        # Try to override the print function in the agent
        try:
            manager_agent._print = ws_handler.handle_output
        except (AttributeError, TypeError):
            # If direct override fails, use monkey patching
            pass  # Already patched above
        
        update_progress("Starting research process...")
        answer = manager_agent.run(question)
        
        update_progress("Research completed!", "success")
        update_progress(f"Final answer: {answer}", "answer")
        
        return answer
    except Exception as e:
        error_message = f"Error during research: {str(e)}"
        update_progress(error_message, "error")
        return error_message
    finally:
        is_processing = False
        # Restore original print function
        sys.stdout.write = original_print

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/models')
def get_available_models():
    """Return a list of available models."""
    models = [
        {"id": "o3-min", "name": "GPT-4o Mini", "description": "Fast and efficient model for general research"},
        {"id": "openai/gpt-4o", "name": "GPT-4o", "description": "More powerful model for complex research"},
        {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus", "description": "High-quality research with excellent reasoning"},
        {"id": "anthropic/claude-3-sonnet", "name": "Claude 3 Sonnet", "description": "Balanced performance and speed"}
    ]
    return jsonify(models)

@app.route('/api/research', methods=['POST'])
def start_research():
    """Start a new research process."""
    global is_processing
    
    if is_processing:
        return jsonify({"error": "Research already in progress"}), 400
    
    data = request.json
    question = data.get('question')
    model_id = data.get('model_id', 'o3-min')
    
    if not question:
        return jsonify({"error": "Question is required"}), 400
    
    # Start research in a background thread
    thread = threading.Thread(target=run_research, args=(question, model_id))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "Research started", "question": question})

@app.route('/api/status')
def get_status():
    """Get the current status of the research process."""
    return jsonify({
        "is_processing": is_processing,
        "current_question": current_question,
        "output_length": len(research_output)
    })

@app.route('/api/output')
def get_output():
    """Get the current research output."""
    return jsonify(research_output)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001) 