/**
 * ChatGPT-Style Voice Recording Implementation
 * Achieves the exact user flow: Click → Listen → Auto-fill → Optional Auto-submit → Chat
 */

class ChatGPTVoiceRecorder {
  constructor() {
    this.isListening = false;
    this.speechRecognition = null;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.stream = null;
    
    this.init();
  }

  init() {
    console.log('🎤 Initializing ChatGPT-style voice recorder...');
    this.createVoiceButton();
    this.setupSpeechRecognition();
    this.bindEvents();
  }

  createVoiceButton() {
    const chatActions = document.querySelector('.chat-actions');
    if (!chatActions || document.getElementById('voice-btn')) return;

    // Create voice button with ChatGPT styling
    const voiceButton = document.createElement('button');
    voiceButton.id = 'voice-btn';
    voiceButton.type = 'button';
    voiceButton.className = 'voice-btn';
    voiceButton.title = 'Voice input';
    voiceButton.innerHTML = `
      <svg class="voice-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
        <line x1="12" y1="19" x2="12" y2="23"></line>
        <line x1="8" y1="23" x2="16" y2="23"></line>
      </svg>
    `;

    // Insert before stop button
    const stopButton = document.getElementById('stop-button');
    if (stopButton) {
      chatActions.insertBefore(voiceButton, stopButton);
    } else {
      chatActions.appendChild(voiceButton);
    }

    this.addStyles();
    console.log('✅ Voice button created');
  }

  addStyles() {
    if (document.getElementById('voice-styles')) return;

    const style = document.createElement('style');
    style.id = 'voice-styles';
    style.textContent = `
      .voice-btn {
        background: linear-gradient(145deg, #0066FF 0%, #4A90E2 50%, #60A5FA 100%);
        border: none;
        border-radius: 12px;
        color: white;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 44px;
        width: 44px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(0, 102, 255, 0.3);
      }

      .voice-btn:hover {
        transform: translateY(-2px) scale(1.05);
        box-shadow: 0 8px 25px rgba(0, 102, 255, 0.4);
        background: linear-gradient(145deg, #0052CC 0%, #3D7BC8 50%, #4A90E2 100%);
        color: white;
      }

      .voice-btn.listening {
        background: linear-gradient(145deg, #0066FF 0%, #4A90E2 50%, #60A5FA 100%);
        color: white;
        animation: pulse 1.5s infinite;
        box-shadow: 0 4px 12px rgba(0, 102, 255, 0.4);
      }

      .voice-btn.processing {
        background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
        color: white;
        cursor: not-allowed;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
      }

      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
      }

      .voice-input-indicator {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
      }

      .auto-submit-dialog {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        max-width: 400px;
        width: 90%;
      }

      .dialog-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 9999;
      }

      .auto-submit-dialog h3 {
        margin: 0 0 16px 0;
        color: #333;
        font-size: 18px;
      }

      .auto-submit-dialog .transcript-preview {
        background: #f8f9fa;
        padding: 12px;
        border-radius: 6px;
        margin: 16px 0;
        font-style: italic;
        border-left: 3px solid #3b82f6;
      }

      .auto-submit-dialog .dialog-buttons {
        display: flex;
        gap: 12px;
        justify-content: flex-end;
        margin-top: 20px;
      }

      .auto-submit-dialog button {
        padding: 8px 16px;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-weight: 500;
        transition: all 0.2s ease;
      }

      .btn-primary {
        background: #3b82f6;
        color: white;
      }

      .btn-secondary {
        background: #f1f3f4;
        color: #333;
      }

      .auto-submit-dialog button:hover {
        transform: translateY(-1px);
      }

      [data-theme="dark"] .auto-submit-dialog {
        background: #2d3748;
        color: white;
      }

      [data-theme="dark"] .auto-submit-dialog h3 {
        color: white;
      }

      [data-theme="dark"] .transcript-preview {
        background: #4a5568;
        color: white;
      }

      [data-theme="dark"] .btn-secondary {
        background: #4a5568;
        color: white;
      }
    `;
    document.head.appendChild(style);
  }

  setupSpeechRecognition() {
    if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
      console.log('⚠️ Browser speech recognition not supported, will use audio recording');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.speechRecognition = new SpeechRecognition();
    
    this.speechRecognition.continuous = false;
    this.speechRecognition.interimResults = true;
    this.speechRecognition.lang = 'en-US';

    this.speechRecognition.onstart = () => {
      console.log('🎧 Speech recognition started');
      this.setButtonState('listening');
    };

    this.speechRecognition.onresult = (event) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      // Show real-time transcription in chat input
      if (interimTranscript || finalTranscript) {
        this.updateChatInput(finalTranscript || interimTranscript, !!finalTranscript);
      }

      if (finalTranscript) {
        console.log('✅ Final transcript:', finalTranscript);
        this.handleTranscriptionComplete(finalTranscript);
      }
    };

    this.speechRecognition.onerror = (event) => {
      console.error('❌ Speech recognition error:', event.error);
      this.handleError(event.error);
    };

    this.speechRecognition.onend = () => {
      console.log('🔚 Speech recognition ended');
      this.isListening = false;
      this.setButtonState('normal');
    };

    console.log('✅ Speech recognition setup complete');
  }

  bindEvents() {
    const voiceBtn = document.getElementById('voice-btn');
    if (voiceBtn) {
      voiceBtn.addEventListener('click', () => this.handleVoiceClick());
    }
  }

  handleVoiceClick() {
    console.log('🎤 Voice button clicked');

    if (this.isListening) {
      this.stopListening();
      return;
    }

    // Try browser speech recognition first (instant)
    if (this.speechRecognition) {
      this.startBrowserSpeechRecognition();
    } else {
      // Fallback to audio recording
      this.startAudioRecording();
    }
  }

  startBrowserSpeechRecognition() {
    try {
      this.isListening = true;
      this.speechRecognition.start();
      console.log('🚀 Browser speech recognition started - listening immediately');
    } catch (error) {
      console.error('❌ Failed to start speech recognition:', error);
      this.startAudioRecording(); // Fallback
    }
  }

  async startAudioRecording() {
    console.log('🎙️ Starting audio recording fallback...');
    
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      this.mediaRecorder = new MediaRecorder(this.stream);
      this.audioChunks = [];
      this.isListening = true;

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        this.handleAudioRecordingStop();
      };

      this.mediaRecorder.start();
      this.setButtonState('listening');
      
      // Auto-stop after 10 seconds
      setTimeout(() => {
        if (this.isListening) {
          this.stopListening();
        }
      }, 10000);

    } catch (error) {
      console.error('❌ Audio recording failed:', error);
      this.handleError('microphone-access-denied');
    }
  }

  stopListening() {
    if (this.speechRecognition && this.isListening) {
      this.speechRecognition.stop();
    }
    
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.stop();
    }

    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }

    this.isListening = false;
    this.setButtonState('normal');
  }

  async handleAudioRecordingStop() {
    if (this.audioChunks.length === 0) {
      this.showError('No audio recorded. Please try again.');
      return;
    }

    this.setButtonState('processing');
    
    try {
      const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      const response = await fetch('/api/voice-to-text-only', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      this.handleTranscriptionComplete(data.transcript);

    } catch (error) {
      console.error('❌ Audio processing failed:', error);
      this.showError('Failed to process audio. Please try again.');
    } finally {
      this.setButtonState('normal');
    }
  }

  updateChatInput(text, isFinal = false) {
    const chatInput = document.getElementById('chat-input');
    if (!chatInput) return;

    // Auto-fill the chat input with transcribed text
    chatInput.value = text;
    
    // Auto-resize textarea
    this.autoResizeTextarea(chatInput);
    
    if (isFinal) {
      // Focus and position cursor at end
      chatInput.focus();
      chatInput.setSelectionRange(text.length, text.length);
      
      // Show visual indicator this came from voice
      this.showVoiceInputIndicator(chatInput);
      
      // Enable send button
      const sendButton = document.getElementById('send-button');
      if (sendButton) {
        sendButton.disabled = false;
      }
    }
  }

  handleTranscriptionComplete(transcript) {
    if (!transcript || !transcript.trim()) {
      this.showError('No speech detected. Please try again.');
      return;
    }

    console.log('✅ Transcription complete:', transcript);
    
    // Show success message
    this.showSuccess('Voice transcribed successfully');
    
    // Show auto-submit dialog
    this.showAutoSubmitDialog(transcript);
  }

  showAutoSubmitDialog(transcript) {
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'dialog-overlay';
    
    // Create dialog
    const dialog = document.createElement('div');
    dialog.className = 'auto-submit-dialog';
    dialog.innerHTML = `
      <h3>Send this message?</h3>
      <div class="transcript-preview">"${this.escapeHtml(transcript)}"</div>
      <div class="dialog-buttons">
        <button class="btn-secondary" onclick="this.closest('.dialog-overlay').remove()">
          Review First
        </button>
        <button class="btn-primary" onclick="window.voiceRecorder.submitQuery(); this.closest('.dialog-overlay').remove();">
          Send Now
        </button>
      </div>
    `;
    
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        overlay.remove();
      }
    });

    // Auto-close after 10 seconds
    setTimeout(() => {
      if (document.body.contains(overlay)) {
        overlay.remove();
      }
    }, 10000);
  }

  submitQuery() {
    // Trigger normal chat form submission
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
      const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
      chatForm.dispatchEvent(submitEvent);
      console.log('📤 Auto-submitted query via normal chat flow');
    }
  }

  autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    const minHeight = 52;
    const maxHeight = 200;
    const newHeight = Math.min(Math.max(textarea.scrollHeight, minHeight), maxHeight);
    textarea.style.height = newHeight + 'px';
    textarea.style.overflowY = newHeight >= maxHeight ? 'scroll' : 'hidden';
  }

  showVoiceInputIndicator(input) {
    input.classList.add('voice-input-indicator');
    setTimeout(() => {
      input.classList.remove('voice-input-indicator');
    }, 3000);
  }

  setButtonState(state) {
    const button = document.getElementById('voice-btn');
    if (!button) return;

    button.classList.remove('listening', 'processing');
    
    if (state === 'listening') {
      button.classList.add('listening');
      button.title = 'Listening... Click to stop';
    } else if (state === 'processing') {
      button.classList.add('processing');
      button.title = 'Processing...';
    } else {
      button.title = 'Voice input';
    }
  }

  handleError(error) {
    this.setButtonState('normal');
    
    let message = 'Voice input failed. ';
    if (error === 'not-allowed' || error === 'microphone-access-denied') {
      message += 'Please allow microphone access and try again.';
    } else if (error === 'no-speech') {
      message += 'No speech detected. Please speak clearly and try again.';
    } else {
      message += 'Please try again.';
    }
    
    this.showError(message);
  }

  showError(message) {
    if (typeof showToast === 'function') {
      showToast(message, 'error');
    } else {
      console.error(message);
    }
  }

  showSuccess(message) {
    if (typeof showToast === 'function') {
      showToast(message, 'success');
    } else {
      console.log(message);
    }
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  static isSupported() {
    return !!(
      (window.SpeechRecognition || window.webkitSpeechRecognition) ||
      (navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder)
    );
  }
}

// Initialize when DOM is ready
function initializeVoiceRecorder() {
  if (window.voiceRecorder) {
    console.log('Voice recorder already initialized');
    return;
  }

  if (!ChatGPTVoiceRecorder.isSupported()) {
    console.warn('Voice recording not supported in this browser');
    return;
  }

  const chatActions = document.querySelector('.chat-actions');
  if (!chatActions) {
    console.log('Chat interface not ready, retrying...');
    setTimeout(initializeVoiceRecorder, 500);
    return;
  }

  try {
    window.voiceRecorder = new ChatGPTVoiceRecorder();
    console.log('🎉 ChatGPT-style voice recorder initialized successfully');
  } catch (error) {
    console.error('Failed to initialize voice recorder:', error);
  }
}

// Initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeVoiceRecorder);
} else {
  initializeVoiceRecorder();
}

// Also try after a delay for dynamic content
setTimeout(initializeVoiceRecorder, 1000);

// Export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ChatGPTVoiceRecorder;
}
