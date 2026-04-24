document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const micBtn = document.getElementById('mic-button');
    const sendBtn = document.getElementById('send-btn');
    const textInput = document.getElementById('text-input');
    const messagesContainer = document.getElementById('messages-container');
    const conversationArea = document.getElementById('conversation-area');
    const welcomeSection = document.getElementById('welcome-section');
    const promptChips = document.querySelectorAll('.prompt-chip');
    
    const langToggle = document.getElementById('language-toggle');
    const btnMl = document.getElementById('btn-malayalam');
    const btnEn = document.getElementById('btn-english');
    
    const apiKeyModal = document.getElementById('api-key-modal');
    const apiKeyInput = document.getElementById('api-key-input');
    const saveApiKeyBtn = document.getElementById('save-api-key');
    
    // State
    let currentLang = 'ml-IN'; // ml-IN or en-US
    let isListening = false;
    let geminiApiKey = localStorage.getItem('gemini_api_key') || '';
    
    // Check API Key
    if (!geminiApiKey) {
        apiKeyModal.classList.add('active');
    }
    
    saveApiKeyBtn.addEventListener('click', () => {
        const key = apiKeyInput.value.trim();
        if (key) {
            localStorage.setItem('gemini_api_key', key);
            geminiApiKey = key;
            apiKeyModal.classList.remove('active');
        }
    });

    // Language Toggle
    langToggle.addEventListener('click', (e) => {
        if(e.target.dataset.lang) {
            btnMl.classList.remove('active');
            btnEn.classList.remove('active');
            e.target.classList.add('active');
            currentLang = e.target.dataset.lang === 'ml' ? 'ml-IN' : 'en-US';
        }
    });

    // --- Web Speech API (Speech to Text) ---
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        
        recognition.onstart = () => {
            isListening = true;
            micBtn.classList.add('listening');
            micBtn.querySelector('.mic-icon').classList.add('hidden');
            micBtn.querySelector('.stop-icon').classList.remove('hidden');
            textInput.placeholder = currentLang === 'ml-IN' ? "സംസാരിക്കൂ..." : "Listening...";
        };
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            textInput.value = transcript;
            processUserInput(transcript);
        };
        
        recognition.onerror = (event) => {
            console.error("Speech recognition error", event.error);
            stopListening();
        };
        
        recognition.onend = () => {
            stopListening();
        };
    } else {
        console.warn("Speech Recognition API not supported in this browser.");
    }
    
    function toggleListening() {
        if (isListening) {
            recognition.stop();
        } else {
            if (recognition) {
                recognition.lang = currentLang;
                recognition.start();
            }
        }
    }
    
    function stopListening() {
        isListening = false;
        micBtn.classList.remove('listening');
        micBtn.querySelector('.mic-icon').classList.remove('hidden');
        micBtn.querySelector('.stop-icon').classList.add('hidden');
        textInput.placeholder = currentLang === 'ml-IN' ? "മലയാളത്തിൽ ടൈപ്പ് ചെയ്യൂ..." : "Type here...";
    }
    
    micBtn.addEventListener('click', toggleListening);
    
    // --- Speech Synthesis API (Text to Speech) ---
    function speakText(text) {
        if (!window.speechSynthesis) return;
        
        // Stop any ongoing speech
        window.speechSynthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = currentLang;
        utterance.rate = 0.9; // Slightly slower for clarity
        
        // Try to find a Malayalam voice if available
        const voices = window.speechSynthesis.getVoices();
        const mlVoice = voices.find(v => v.lang.includes('ml'));
        if (mlVoice) utterance.voice = mlVoice;
        
        window.speechSynthesis.speak(utterance);
    }
    
    // Ensure voices are loaded
    if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    }

    // --- Gemini API Integration ---
    async function fetchGeminiResponse(prompt) {
        if (!geminiApiKey) {
            apiKeyModal.classList.add('active');
            return "Please provide a Gemini API Key to continue.";
        }
        
        try {
            const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${geminiApiKey}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contents: [{
                        parts: [{
                            text: `You are an expert agricultural assistant in Kerala. Answer the following query concisely (under 50 words). If the query is in Malayalam, answer in Malayalam. Query: ${prompt}`
                        }]
                    }],
                    generationConfig: {
                        temperature: 0.3,
                        maxOutputTokens: 150
                    }
                })
            });
            
            const data = await response.json();
            if (data.error) throw new Error(data.error.message);
            
            return data.candidates[0].content.parts[0].text;
        } catch (error) {
            console.error("Gemini API Error:", error);
            return currentLang === 'ml-IN' ? "ക്ഷമിക്കണം, ഒരു സാങ്കേതിക തകരാർ സംഭവിച്ചു." : "Sorry, a technical error occurred.";
        }
    }

    // --- UI Interactions ---
    async function processUserInput(text) {
        if (!text.trim()) return;
        textInput.value = '';
        
        // Hide welcome, show chat
        welcomeSection.style.display = 'none';
        conversationArea.style.display = 'block';
        
        // Add User Message
        addMessage(text, 'user');
        
        // Add AI Loading State
        const loadingId = addMessage("...", 'ai', true);
        
        // Fetch Response
        const aiResponse = await fetchGeminiResponse(text);
        
        // Update AI Message
        updateMessage(loadingId, aiResponse);
        
        // Speak Response
        speakText(aiResponse);
    }
    
    function addMessage(text, sender, isLoading = false) {
        const id = 'msg-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;
        msgDiv.id = id;
        
        msgDiv.innerHTML = `
            <div class="msg-bubble ${isLoading ? 'loading' : ''}">${text}</div>
        `;
        
        messagesContainer.appendChild(msgDiv);
        window.scrollTo(0, document.body.scrollHeight);
        return id;
    }
    
    function updateMessage(id, text) {
        const msgDiv = document.getElementById(id);
        if (msgDiv) {
            const bubble = msgDiv.querySelector('.msg-bubble');
            bubble.classList.remove('loading');
            bubble.textContent = text;
        }
    }
    
    // Event Listeners
    sendBtn.addEventListener('click', () => processUserInput(textInput.value));
    textInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') processUserInput(textInput.value);
    });
    
    promptChips.forEach(chip => {
        chip.addEventListener('click', () => {
            processUserInput(chip.dataset.prompt);
        });
    });
});
