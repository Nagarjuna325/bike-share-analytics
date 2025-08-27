class ChatInterface {
    constructor() {
        this.chatContainer = document.getElementById('chat-container');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.loadingIndicator = document.getElementById('loading');
        
        this.initializeEventListeners();
        this.addWelcomeMessage();
    }
    
    initializeEventListeners() {
        // Send message on button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Send message on Enter key press
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }
    
    addWelcomeMessage() {
        const welcomeMessage = `
            <div class="alert alert-info">
                <h5><i class="fas fa-bicycle"></i> Welcome to Bike Share Analytics Assistant!</h5>
                <p>Ask me questions about bike share data. For example:</p>
                <ul class="mb-0">
                    <li>"What was the average ride time for journeys that started at Congress Avenue in June 2025?"</li>
                    <li>"Which docking point saw the most departures during the first week of June 2025?"</li>
                    <li>"How many kilometres were ridden by women on rainy days in June 2025?"</li>
                </ul>
            </div>
        `;
        this.chatContainer.innerHTML = welcomeMessage;
    }
    
    async sendMessage() {
        const question = this.messageInput.value.trim();
        
        if (!question) {
            return;
        }
        
        // Add user message to chat
        this.addMessage(question, 'user');
        
        // Clear input and show loading
        this.messageInput.value = '';
        this.showLoading(true);
        
        try {
            // Send request to backend - FIXED: Changed from '/query' to '/api/query'
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question })
            });
            
            const data = await response.json();
            
            // Add response to chat
            this.addResponse(data, question);
            
        } catch (error) {
            console.error('Error:', error);
            this.addMessage('Sorry, there was an error processing your request. Please try again.', 'assistant', 'error');
        } finally {
            this.showLoading(false);
        }
    }
    
    addMessage(content, sender, type = 'normal') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const timestamp = new Date().toLocaleTimeString();
        
        let messageClass = 'alert-secondary';
        let icon = 'fas fa-user';
        
        if (sender === 'assistant') {
            icon = 'fas fa-robot';
            if (type === 'error') {
                messageClass = 'alert-danger';
            } else if (type === 'success') {
                messageClass = 'alert-success';
            } else {
                messageClass = 'alert-primary';
            }
        } else {
            messageClass = 'alert-light';
        }
        
        messageDiv.innerHTML = `
            <div class="alert ${messageClass} mb-2">
                <div class="d-flex align-items-start">
                    <i class="${icon} me-2 mt-1"></i>
                    <div class="flex-grow-1">
                        <div class="message-content">${content}</div>
                        <small class="text-muted">${timestamp}</small>
                    </div>
                </div>
            </div>
        `;
        
        this.chatContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    addResponse(data, originalQuestion) {
        let content = '';
        let type = 'normal';
        
        if (data.error) {
            content = `<strong>Error:</strong> ${data.error}`;
            type = 'error';
        } else {
            const result = data.result;
            const sql = data.sql;
            
            content = `<div class="response-content">`;
            
            if (result !== null && result !== undefined) {
                if (typeof result === 'number') {
                    content += `<div class="result-value"><strong>Answer:</strong> ${this.formatResult(result)}</div>`;
                } else if (typeof result === 'string') {
                    content += `<div class="result-value"><strong>Answer:</strong> ${result}</div>`;
                } else if (Array.isArray(result) && result.length > 0) {
                    content += `<div class="result-value"><strong>Results:</strong></div>`;
                    content += this.formatTableResults(result);
                } else {
                    content += `<div class="result-value"><strong>Answer:</strong> No results found</div>`;
                }
            } else {
                content += `<div class="result-value"><strong>Answer:</strong> No results found</div>`;
            }
            
            // Show SQL query in expandable section
            content += `
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#sql-${Date.now()}" aria-expanded="false">
                        Show SQL Query
                    </button>
                    <div class="collapse mt-2" id="sql-${Date.now()}">
                        <div class="card card-body">
                            <code>${sql}</code>
                        </div>
                    </div>
                </div>
            `;
            
            content += `</div>`;
            type = 'success';
        }
        
        this.addMessage(content, 'assistant', type);
    }
    
    formatResult(result) {
        if (typeof result === 'number') {
            // Format numbers appropriately
            if (result % 1 === 0) {
                return result.toString();
            } else {
                return result.toFixed(2);
            }
        }
        return result;
    }
    
    formatTableResults(results) {
        if (!Array.isArray(results) || results.length === 0) {
            return '<p>No results found</p>';
        }
        
        const keys = Object.keys(results[0]);
        
        let html = '<div class="table-responsive mt-2"><table class="table table-sm table-striped">';
        
        // Header
        html += '<thead><tr>';
        keys.forEach(key => {
            html += `<th>${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</th>`;
        });
        html += '</tr></thead>';
        
        // Body
        html += '<tbody>';
        results.slice(0, 10).forEach(row => {  // Limit to 10 rows for display
            html += '<tr>';
            keys.forEach(key => {
                let value = row[key];
                if (typeof value === 'number') {
                    value = this.formatResult(value);
                }
                html += `<td>${value || ''}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table></div>';
        
        if (results.length > 10) {
            html += `<p class="text-muted">Showing first 10 of ${results.length} results</p>`;
        }
        
        return html;
    }
    
    showLoading(show) {
        if (show) {
            this.loadingIndicator.style.display = 'block';
            this.sendButton.disabled = true;
            this.messageInput.disabled = true;
        } else {
            this.loadingIndicator.style.display = 'none';
            this.sendButton.disabled = false;
            this.messageInput.disabled = false;
            this.messageInput.focus();
        }
    }
    
    scrollToBottom() {
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }
}

// Initialize chat interface when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatInterface();
});
