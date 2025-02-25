// Initialize Socket.io connection
const socket = io();

// DOM Elements
const questionInput = document.getElementById('question-input');
const modelSelect = document.getElementById('model-select');
const startResearchBtn = document.getElementById('start-research-btn');
const currentQuestionEl = document.getElementById('current-question');
const statusIndicator = document.getElementById('status-indicator');
const welcomeMessage = document.getElementById('welcome-message');
const researchOutput = document.getElementById('research-output');
const statusMessage = document.getElementById('status-message');
const progressBar = document.querySelector('.progress');
const historyList = document.getElementById('history-list');
const exampleQuestions = document.querySelectorAll('.example-question');

// Research history
let researchHistory = JSON.parse(localStorage.getItem('researchHistory')) || [];

// Application state
let isProcessing = false;

// Initialize the application
function init() {
    loadModels();
    renderHistory();
    setupEventListeners();
}

// Load available models
function loadModels() {
    fetch('/api/models')
        .then(response => response.json())
        .then(models => {
            modelSelect.innerHTML = '';
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.name;
                option.title = model.description;
                modelSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading models:', error);
            showError('Failed to load available models. Please refresh the page.');
        });
}

// Set up event listeners
function setupEventListeners() {
    // Start research button
    startResearchBtn.addEventListener('click', startResearch);
    
    // Example questions
    exampleQuestions.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            questionInput.value = link.textContent;
            questionInput.focus();
        });
    });
    
    // Socket.io event listeners
    socket.on('connect', () => {
        console.log('Connected to server');
        updateStatus('Ready', 'secondary');
    });
    
    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        updateStatus('Disconnected', 'danger');
    });
    
    socket.on('progress_update', handleProgressUpdate);
    socket.on('research_update', handleResearchUpdate);
    
    // Check current status on page load
    checkStatus();
}

// Start a new research
function startResearch() {
    const question = questionInput.value.trim();
    const modelId = modelSelect.value;
    
    if (!question) {
        showError('Please enter a research question.');
        return;
    }
    
    if (isProcessing) {
        showError('Research is already in progress. Please wait for it to complete.');
        return;
    }
    
    // Reset UI
    researchOutput.innerHTML = '';
    welcomeMessage.classList.add('d-none');
    researchOutput.classList.remove('d-none');
    progressBar.classList.remove('d-none');
    
    // Update status
    isProcessing = true;
    updateStatus('Processing', 'primary');
    currentQuestionEl.textContent = question;
    
    // Send request to server
    fetch('/api/research', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question, model_id: modelId })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to start research');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Research started:', data);
        // Add to history
        addToHistory(question, modelId);
    })
    .catch(error => {
        console.error('Error starting research:', error);
        showError(error.message);
        isProcessing = false;
        updateStatus('Error', 'danger');
        progressBar.classList.add('d-none');
    });
}

// Handle progress updates from the server
function handleProgressUpdate(data) {
    console.log('Progress update:', data);
    
    if (data.type === 'success' || data.type === 'error') {
        isProcessing = false;
        progressBar.classList.add('d-none');
        updateStatus(data.type === 'success' ? 'Completed' : 'Error', data.type === 'success' ? 'success' : 'danger');
    }
    
    addOutputItem(data.message, data.type);
    statusMessage.textContent = data.message;
}

// Handle research updates from the server
function handleResearchUpdate(data) {
    console.log('Research update:', data);
    addOutputItem(data.message, data.type);
}

// Add an item to the research output
function addOutputItem(message, type = 'info') {
    const item = document.createElement('div');
    item.className = `output-item ${type}`;
    
    // Format the message based on type
    if (type === 'tool_output' && typeof message === 'string') {
        // Try to detect if it's JSON and format it
        try {
            if (message.trim().startsWith('{') || message.trim().startsWith('[')) {
                const jsonData = JSON.parse(message);
                const formattedJson = JSON.stringify(jsonData, null, 2);
                const pre = document.createElement('pre');
                pre.textContent = formattedJson;
                item.appendChild(pre);
            } else {
                item.textContent = message;
            }
        } catch (e) {
            // Not valid JSON, just display as text
            item.textContent = message;
        }
    } else if (type === 'answer') {
        // Format the answer with markdown-like styling
        const formattedMessage = message
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>');
        
        item.innerHTML = formattedMessage;
    } else {
        item.textContent = message;
    }
    
    researchOutput.appendChild(item);
    
    // Scroll to bottom
    researchOutput.scrollTop = researchOutput.scrollHeight;
}

// Update the status indicator
function updateStatus(status, type) {
    statusIndicator.textContent = status;
    statusIndicator.className = `badge bg-${type}`;
}

// Show an error message
function showError(message) {
    addOutputItem(message, 'error');
    statusMessage.textContent = message;
}

// Check the current status of any ongoing research
function checkStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            isProcessing = data.is_processing;
            
            if (isProcessing) {
                // Research is in progress
                welcomeMessage.classList.add('d-none');
                researchOutput.classList.remove('d-none');
                progressBar.classList.remove('d-none');
                updateStatus('Processing', 'primary');
                currentQuestionEl.textContent = data.current_question;
                
                // Load current output
                loadCurrentOutput();
            }
        })
        .catch(error => {
            console.error('Error checking status:', error);
        });
}

// Load the current research output
function loadCurrentOutput() {
    fetch('/api/output')
        .then(response => response.json())
        .then(data => {
            researchOutput.innerHTML = '';
            data.forEach(item => {
                addOutputItem(item.message, item.type);
            });
        })
        .catch(error => {
            console.error('Error loading output:', error);
        });
}

// Add a research question to history
function addToHistory(question, modelId) {
    const timestamp = new Date().toISOString();
    const historyItem = { question, modelId, timestamp };
    
    // Add to the beginning of the array
    researchHistory.unshift(historyItem);
    
    // Limit history to 10 items
    if (researchHistory.length > 10) {
        researchHistory.pop();
    }
    
    // Save to localStorage
    localStorage.setItem('researchHistory', JSON.stringify(researchHistory));
    
    // Update UI
    renderHistory();
}

// Render the research history
function renderHistory() {
    historyList.innerHTML = '';
    
    if (researchHistory.length === 0) {
        const emptyItem = document.createElement('div');
        emptyItem.className = 'text-muted small';
        emptyItem.textContent = 'No research history yet';
        historyList.appendChild(emptyItem);
        return;
    }
    
    researchHistory.forEach((item, index) => {
        const historyItem = document.createElement('a');
        historyItem.href = '#';
        historyItem.className = 'list-group-item list-group-item-action history-item';
        
        const date = new Date(item.timestamp);
        const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        
        historyItem.innerHTML = `
            <div class="d-flex w-100 justify-content-between">
                <h6 class="mb-1">${truncateText(item.question, 30)}</h6>
                <small>${formattedDate}</small>
            </div>
        `;
        
        historyItem.addEventListener('click', (e) => {
            e.preventDefault();
            questionInput.value = item.question;
            
            // Set the model if it exists in the select options
            const modelOption = Array.from(modelSelect.options).find(option => option.value === item.modelId);
            if (modelOption) {
                modelSelect.value = item.modelId;
            }
        });
        
        historyList.appendChild(historyItem);
    });
}

// Helper function to truncate text
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', init); 