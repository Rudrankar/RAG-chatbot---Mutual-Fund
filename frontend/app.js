const API_URL = 'http://localhost:8000/api/query';

const chatFeed = document.getElementById('chat-feed');
const queryInput = document.getElementById('query-input');
const sendBtn = document.getElementById('send-btn');

// Listeners
sendBtn.addEventListener('click', submitQuery);
queryInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        submitQuery();
    }
});

function sendExample(queryText) {
    queryInput.value = queryText;
    submitQuery();
}

function scrollToBottom() {
    chatFeed.scrollTop = chatFeed.scrollHeight;
}

function submitQuery() {
    const query = queryInput.value.trim();
    if (!query) return;
    
    // Clear Input
    queryInput.value = '';
    
    // 1. Render User Message
    renderMessage(query, 'user');
    scrollToBottom();
    
    // 2. Add Bot Loader Typing bubble
    const loaderId = appendLoaderBubble();
    scrollToBottom();
    
    // 3. API Request
    fetch(API_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: query })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network error or API failure.');
        }
        return response.json();
    })
    .then(data => {
        removeLoaderBubble(loaderId);
        
        // Render Bot response
        renderBotMessage(data);
        scrollToBottom();
    })
    .catch(error => {
        removeLoaderBubble(loaderId);
        renderMessage('Error: Failed to connect to server. Ensure backend is running.', 'bot', true);
        scrollToBottom();
    });
}

function renderMessage(text, sender, isError = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    if (isError) msgDiv.classList.add('error-message');
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerText = text;
    
    msgDiv.appendChild(bubble);
    chatFeed.appendChild(msgDiv);
}

function appendLoaderBubble() {
    const loaderId = 'loader_' + Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot';
    msgDiv.id = loaderId;
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    const loader = document.createElement('div');
    loader.className = 'loader';
    loader.innerHTML = '<span></span><span></span><span></span>';
    
    bubble.appendChild(loader);
    msgDiv.appendChild(bubble);
    chatFeed.appendChild(msgDiv);
    
    return loaderId;
}

function removeLoaderBubble(loaderId) {
    const loader = document.getElementById(loaderId);
    if (loader) {
        loader.remove();
    }
}

function renderBotMessage(data) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot';
    
    if (data.is_refusal) {
        msgDiv.classList.add('refusal');
    }
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    // Add compliance tag for refusals
    if (data.is_refusal) {
        const complianceTag = document.createElement('div');
        complianceTag.className = 'tag';
        complianceTag.innerHTML = '<span>⚠️</span> Compliance Advisory Refusal';
        bubble.appendChild(complianceTag);
    }
    
    // Add Answer text
    const textNode = document.createElement('p');
    textNode.innerText = data.answer;
    bubble.appendChild(textNode);
    
    // Add Citation Link
    if (data.citation_url) {
        const citationBox = document.createElement('div');
        citationBox.className = 'citation-box';
        citationBox.innerHTML = `
            <span>Source:</span>
            <a class="citation-link" href="${data.citation_url}" target="_blank" rel="noopener noreferrer">
                ${getFriendlyDomain(data.citation_url)} <span class="citation-arrow">↗</span>
            </a>
        `;
        bubble.appendChild(citationBox);
    }
    
    msgDiv.appendChild(bubble);
    
    // Add Footer Date stamp
    if (data.last_updated) {
        const footer = document.createElement('div');
        footer.className = 'message-footer';
        footer.innerText = `Last updated from sources: ${data.last_updated}`;
        msgDiv.appendChild(footer);
    }
    
    chatFeed.appendChild(msgDiv);
}

function getFriendlyDomain(url) {
    try {
        const hostname = new URL(url).hostname;
        return hostname.replace('www.', '');
    } catch (e) {
        return 'Source Link';
    }
}
