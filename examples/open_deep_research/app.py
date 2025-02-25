import os
import sys
import threading
import json
import re
import time
import logging
import gradio as gr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gradio_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path to import from run.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

# Global variables to store the current research session
current_model = None
current_agent = None
current_question = None
is_processing = False
research_output = []

class OutputCapture:
    """Capture agent outputs for display in Gradio."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.messages = []
        self.current_step = 0
        self.step_pattern = re.compile(r'━+\s*Step\s+(\d+)\s*━+')
        self.duration_pattern = re.compile(r'\[Step\s+\d+:\s+Duration\s+([\d.]+)\s+seconds')
        self.tokens_pattern = re.compile(r'Input tokens:\s+(\d+)\s+\|\s+Output tokens:\s+(\d+)')
        self.tool_pattern = re.compile(r'Calling tools:\s+(.+)')
        self.code_block_pattern = re.compile(r'```(?:py)?(.*?)```', re.DOTALL)
        self.execution_pattern = re.compile(r'─\s*Executing parsed code:\s*─+\s*(.*?)\s*─+', re.DOTALL)
        self.output_pattern = re.compile(r'Output message of the LLM:\s*─+\s*(.*?)\s*─+', re.DOTALL)
        self.initial_plan_pattern = re.compile(r'─+\s*Initial plan\s*─+\s*(.*?)\s*━+', re.DOTALL)
        self.updated_plan_pattern = re.compile(r'─+\s*Updated plan\s*─+\s*(.*?)\s*━+', re.DOTALL)
    
    def handle_output(self, message, message_type="info"):
        with self.lock:
            # Try to categorize the message
            message_type = self._categorize_message(message, message_type)
            
            # Log the message
            logger.info(f"[{message_type}] {message[:100]}...")
            
            # Store the message
            self.messages.append({
                'content': message,
                'type': message_type,
                'timestamp': time.time()
            })
    
    def _categorize_message(self, message, default_type):
        """Categorize the message based on its content."""
        if isinstance(message, str):
            # Check for step information
            step_match = self.step_pattern.search(message)
            if step_match:
                self.current_step = int(step_match.group(1))
                return "step_header"
            
            # Check for duration and token information
            if self.duration_pattern.search(message) or self.tokens_pattern.search(message):
                return "step_stats"
            
            # Check for tool calls
            if self.tool_pattern.search(message):
                return "tool_call"
            
            # Check for code blocks
            if self.code_block_pattern.search(message):
                return "code_block"
            
            # Check for code execution
            if self.execution_pattern.search(message):
                return "code_execution"
            
            # Check for LLM output
            if self.output_pattern.search(message):
                return "llm_output"
            
            # Check for initial plan
            if self.initial_plan_pattern.search(message):
                return "initial_plan"
            
            # Check for updated plan
            if self.updated_plan_pattern.search(message):
                return "updated_plan"
            
            # Check for thought process
            if message.strip().startswith("Thought:"):
                return "thought_process"
            
            # Check for final answer
            if "Final answer:" in message:
                return "final_answer"
        
        return default_type
    
    def get_messages(self):
        with self.lock:
            return self.messages.copy()
    
    def clear(self):
        with self.lock:
            self.messages = []
            self.current_step = 0

output_capture = OutputCapture()

# Monkey patch the print function to capture output
original_print = print
def patched_print(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    output_capture.handle_output(message)
    return original_print(*args, **kwargs)

# Replace the print function
print = patched_print

# Monkey patch sys.stdout.write to capture more output
original_stdout_write = sys.stdout.write
def patched_stdout_write(text):
    if text.strip():  # Only process non-empty text
        output_capture.handle_output(text)
    return original_stdout_write(text)

sys.stdout.write = patched_stdout_write

def run_research(question, model_id):
    """Run the research process in a background thread."""
    global current_model, current_agent, current_question, is_processing
    
    if is_processing:
        logger.warning("Research already in progress")
        return "Research already in progress. Please wait."
    
    logger.info(f"Starting research on: {question} with model: {model_id}")
    is_processing = True
    current_question = question
    output_capture.clear()
    
    # Start research in a background thread
    thread = threading.Thread(target=_run_research_thread, args=(question, model_id))
    thread.daemon = True
    thread.start()
    
    return "Research started. Please wait for results..."

def _run_research_thread(question, model_id):
    """Background thread to run the research process."""
    global current_model, current_agent, current_question, is_processing
    
    try:
        # Get the model
        logger.info(f"Getting model: {model_id}")
        current_model = get_model(model_id)
        
        # Create the browser
        logger.info("Creating browser")
        browser = SimpleTextBrowser(**BROWSER_CONFIG)
        
        # Create the tools
        logger.info("Creating tools")
        text_limit = 100000
        document_inspection_tool = TextInspectorTool(current_model, text_limit)
        
        WEB_TOOLS = [
            GoogleSearchTool(),
            VisitTool(browser),
            PageUpTool(browser),
            PageDownTool(browser),
            FinderTool(browser),
            FindNextTool(browser),
            ArchiveSearchTool(browser),
            document_inspection_tool,
        ]
        
        # Create the web browser agent
        output_capture.handle_output(f"Starting research on: {question}", "info")
        output_capture.handle_output(f"Using model: {model_id}", "info")
        
        output_capture.handle_output("Initializing web browser agent...", "info")
        logger.info("Creating web browser agent")
        text_webbrowser_agent = ToolCallingAgent(
            model=current_model,
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
        
        # Override the agent's print function to capture output
        try:
            text_webbrowser_agent._print = output_capture.handle_output
        except (AttributeError, TypeError):
            logger.warning("Could not override agent's print function")
        
        # Create the manager agent
        output_capture.handle_output("Initializing manager agent...", "info")
        logger.info("Creating manager agent")
        manager_agent = CodeAgent(
            model=current_model,
            tools=[visualizer, document_inspection_tool],
            max_steps=12,
            verbosity_level=2,
            additional_authorized_imports=AUTHORIZED_IMPORTS,
            planning_interval=4,
            managed_agents=[text_webbrowser_agent],
        )
        
        # Override the agent's print function to capture output
        try:
            manager_agent._print = output_capture.handle_output
        except (AttributeError, TypeError):
            logger.warning("Could not override agent's print function")
        
        # Run the research
        output_capture.handle_output("Starting research process...", "info")
        logger.info("Running research")
        answer = manager_agent.run(question)
        
        output_capture.handle_output("Research completed!", "success")
        logger.info("Research completed")
        output_capture.handle_output(f"Final answer: {answer}", "final_answer")
    except Exception as e:
        logger.error(f"Error during research: {str(e)}", exc_info=True)
        output_capture.handle_output(f"Error: {str(e)}", "error")
    finally:
        is_processing = False
        logger.info("Research process finished")

def format_message(message):
    """Format a message for display in the Gradio interface."""
    content = message['content']
    msg_type = message['type']
    
    if msg_type == "step_header":
        return f"## {content}"
    elif msg_type == "step_stats":
        return f"*{content}*"
    elif msg_type == "thought_process":
        return f"**Thought:** {content.replace('Thought:', '').strip()}"
    elif msg_type == "code_block":
        # Extract code from the code block
        code_match = output_capture.code_block_pattern.search(content)
        if code_match:
            code = code_match.group(1).strip()
            return f"```python\n{code}\n```"
        return f"```\n{content}\n```"
    elif msg_type == "code_execution":
        # Extract execution output
        exec_match = output_capture.execution_pattern.search(content)
        if exec_match:
            execution = exec_match.group(1).strip()
            return f"**Executing:**\n```\n{execution}\n```"
        return content
    elif msg_type == "tool_call":
        # Format tool calls
        tool_match = output_capture.tool_pattern.search(content)
        if tool_match:
            tool_info = tool_match.group(1).strip()
            try:
                tool_json = json.loads(tool_info.replace("'", '"'))
                return f"**Tool Call:**\n```json\n{json.dumps(tool_json, indent=2)}\n```"
            except:
                return f"**Tool Call:**\n{tool_info}"
        return content
    elif msg_type == "llm_output":
        # Extract LLM output
        output_match = output_capture.output_pattern.search(content)
        if output_match:
            output_text = output_match.group(1).strip()
            return f"**LLM Output:**\n{output_text}"
        return content
    elif msg_type == "initial_plan" or msg_type == "updated_plan":
        # Extract plan
        plan_match = None
        if msg_type == "initial_plan":
            plan_match = output_capture.initial_plan_pattern.search(content)
        else:
            plan_match = output_capture.updated_plan_pattern.search(content)
            
        if plan_match:
            plan_text = plan_match.group(1).strip()
            plan_title = "Initial Plan" if msg_type == "initial_plan" else "Updated Plan"
            return f"### {plan_title}:\n{plan_text}"
        return content
    elif msg_type == "final_answer":
        return f"### Final Answer:\n{content.replace('Final answer:', '').strip()}"
    else:
        return content

def get_formatted_output():
    """Get the formatted output for display."""
    messages = output_capture.get_messages()
    if not messages:
        return "Waiting for research to begin..."
    
    formatted_messages = [format_message(msg) for msg in messages]
    return "\n\n".join(formatted_messages)

def create_ui():
    """Create the Gradio interface."""
    logger.info("Creating Gradio UI")
    
    # CSS for better formatting
    css = """
    .gradio-container {
        max-width: 1200px !important;
        margin: 0 auto;
    }
    
    .output-box {
        height: 600px;
        overflow-y: auto;
        font-family: 'Source Sans Pro', sans-serif;
        line-height: 1.5;
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f9f9f9;
    }
    
    .output-box h2, .output-box h3 {
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    
    .output-box h2 {
        color: #2563eb;
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 0.25rem;
    }
    
    .output-box h3 {
        color: #4b5563;
    }
    
    .output-box pre {
        background-color: #f3f4f6;
        padding: 0.75rem;
        border-radius: 0.25rem;
        overflow-x: auto;
        margin: 0.5rem 0;
    }
    
    .output-box code {
        font-family: 'Fira Code', monospace;
        font-size: 0.9rem;
    }
    
    .output-box p {
        margin: 0.5rem 0;
    }
    
    .output-box strong {
        color: #4b5563;
    }
    
    .output-box em {
        color: #6b7280;
    }
    
    .status-processing {
        color: #2563eb;
        font-weight: 600;
    }
    
    .status-completed {
        color: #10b981;
        font-weight: 600;
    }
    
    .status-error {
        color: #ef4444;
        font-weight: 600;
    }
    
    .research-title {
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #1f2937;
    }
    """
    
    with gr.Blocks(css=css, theme=gr.themes.Soft()) as app:
        gr.Markdown("# Open Deep Research")
        gr.Markdown("Ask a research question and get a comprehensive answer.")
        
        with gr.Row():
            with gr.Column(scale=3):
                question_input = gr.Textbox(
                    label="Research Question",
                    placeholder="Enter your research question here...",
                    lines=3
                )
                
                with gr.Row():
                    model_dropdown = gr.Dropdown(
                        label="Model",
                        choices=[
                            "o3-min",
                            "openai/gpt-4o",
                            "anthropic/claude-3-opus",
                            "anthropic/claude-3-sonnet"
                        ],
                        value="o3-min"
                    )
                    submit_button = gr.Button("Start Research", variant="primary")
                
                status_text = gr.Textbox(label="Status", value="Ready", interactive=False)
            
            with gr.Column(scale=7):
                # Add a title for the research output
                output_title = gr.Markdown("### Research Output", visible=True)
                
                # Use a Markdown component with custom CSS class for better formatting
                output_box = gr.Markdown(
                    value="Waiting for research to begin...",
                    elem_classes=["output-box"]
                )
                
                # Hidden refresh button for automatic updates
                refresh_btn = gr.Button("Refresh Output", visible=False)
        
        # Example questions
        gr.Examples(
            examples=[
                ["What is the capital of China?"],
                ["What were the economic impacts of the 1929 stock market crash?"],
                ["How does photosynthesis work?"],
                ["What are the main theories about dark matter?"]
            ],
            inputs=question_input
        )
        
        # Function to update the output display
        def update_output():
            return get_formatted_output()
        
        # Function to update status and start auto-refresh
        def start_research_and_setup_refresh(question, model_id):
            status = run_research(question, model_id)
            return status
        
        # Set up event handlers
        submit_button.click(
            fn=start_research_and_setup_refresh,
            inputs=[question_input, model_dropdown],
            outputs=status_text
        )
        
        # Set up the refresh button to update the output
        refresh_btn.click(
            fn=update_output,
            inputs=[],
            outputs=output_box
        )
        
        # Use JavaScript to automatically click the refresh button every second
        app.load(js="""
        function setupAutoRefresh() {
            const refreshInterval = setInterval(() => {
                const refreshBtn = document.querySelector('button[value="Refresh Output"]');
                if (refreshBtn) {
                    refreshBtn.click();
                } else {
                    clearInterval(refreshInterval);
                }
            }, 1000);
        }
        
        if (window.gradio_loaded) {
            setupAutoRefresh();
        } else {
            document.addEventListener('DOMContentLoaded', setupAutoRefresh);
        }
        """)
        
    return app

if __name__ == "__main__":
    logger.info("Starting Gradio app")
    app = create_ui()
    try:
        app.launch(server_name="0.0.0.0", server_port=7860)
    except Exception as e:
        logger.error(f"Error launching app: {str(e)}", exc_info=True) 