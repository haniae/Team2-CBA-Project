/**
 * Premium Voice Recording Component - ChatGPT Style with Enhanced Visuals
 * Features: Gradient backgrounds, animations, smart fallbacks, auto-submit
 */

class PremiumVoiceRecorder {
  constructor(config = {}) {
    this.isRecording = false;
    this.isListening = false;
    this.recordingTime = 0;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.timer = null;
    this.stream = null;
    
    // Configuration
    this.apiBase = config.apiBase || window.API_BASE || window.location.origin;
    this.debug = config.debug !== false;
    this.autoSubmit = config.autoSubmit || false;
    
    // Speech Recognition (Browser API)
    this.speechRecognition = null;
    this.useBrowserSpeechRecognition = true;
    
    // Voice Activity Detection
    this.audioContext = null;
    this.analyser = null;
    this.dataArray = null;
    this.silenceThreshold = 15;
    this.silenceDuration = 2000;
    this.lastSoundTime = 0;
    
    this.init();
  }

  log(...args) {
    if (this.debug) {
      console.log('[PremiumVoiceRecorder]', ...args);
    }
  }

  error(...args) {
    console.error('[PremiumVoiceRecorder ERROR]', ...args);
  }

  init() {
    this.log('Initializing premium voice recorder...');
    
    if (!this.checkBrowserSupport()) {
      this.log('Limited browser support, using fallback mode');
    }
    
    this.createVoiceButton();
    this.bindEvents();
    this.setupSpeechRecognition();
    this.log('Premium voice recorder setup complete');
  }

  checkBrowserSupport() {
    const hasMediaRecorder = !!(navigator.mediaDevices && 
                               navigator.mediaDevices.getUserMedia && 
                               window.MediaRecorder);
    
    const hasSpeechRecognition = !!(window.SpeechRecognition || 
                                   window.webkitSpeechRecognition);
    
    this.log('Browser support:', { hasMediaRecorder, hasSpeechRecognition });
    return hasMediaRecorder || hasSpeechRecognition;
  }

  createVoiceButton() {
    // Check if button already exists
    if (document.getElementById('premium-voice-btn')) {
      this.log('Premium voice button already exists');
      return;
    }

    const chatActions = document.querySelector('.chat-actions');
    if (!chatActions) {
      this.error('Chat actions container not found');
      return;
    }

    // Create premium voice button with enhanced design
    const voiceButton = document.createElement('button');
    voiceButton.id = 'premium-voice-btn';
    voiceButton.type = 'button';
    voiceButton.className = 'premium-voice-btn';
    voiceButton.title = 'Voice Input';
    voiceButton.setAttribute('aria-label', 'Voice Input');
    
    voiceButton.innerHTML = `
      <div class="voice-btn-content">
        <div class="voice-icon-container">
          <svg class="voice-icon microphone" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
            <line x1="8" y1="23" x2="16" y2="23"></line>
          </svg>
          <div class="voice-emoji hidden">🎤</div>
        </div>
        <div class="shine-effect"></div>
        <div class="pulse-rings">
          <div class="pulse-ring"></div>
          <div class="pulse-ring"></div>
          <div class="pulse-ring"></div>
        </div>
      </div>
    `;

    // Create status tooltip
    const statusTooltip = document.createElement('div');
    statusTooltip.id = 'voice-status-tooltip';
    statusTooltip.className = 'voice-status-tooltip hidden';
    statusTooltip.innerHTML = `
      <div class="tooltip-content">
        <span class="status-text">Click to speak</span>
        <div class="recording-timer hidden">0:00</div>
      </div>
    `;

    // Wrap in container
    const wrapper = document.createElement('div');
    wrapper.className = 'premium-voice-wrapper';
    wrapper.appendChild(voiceButton);
    wrapper.appendChild(statusTooltip);

    // Insert before stop button
    const stopButton = document.getElementById('stop-button');
    if (stopButton) {
      chatActions.insertBefore(wrapper, stopButton);
    } else {
      chatActions.appendChild(wrapper);
    }

    this.addPremiumStyles();
    this.log('Premium voice button created');
  }

  addPremiumStyles() {
    if (document.getElementById('premium-voice-styles')) return;

    const style = document.createElement('style');
    style.id = 'premium-voice-styles';
    style.textContent = `
      /* Premium Voice Button Styles */
      .premium-voice-wrapper {
        position: relative;
        display: inline-block;
      }

      .premium-voice-btn {
        position: relative;
        width: 44px;
        height: 44px;
        border: none;
        border-radius: 12px;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        cursor: pointer;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .premium-voice-btn:hover {
        transform: translateY(-2px) scale(1.05);
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
      }

      .premium-voice-btn:active {
        transform: translateY(0) scale(0.98);
      }

      .premium-voice-btn:disabled {
        cursor: not-allowed;
        opacity: 0.6;
        transform: none;
      }

      /* Button States */
      .premium-voice-btn.listening {
        background: linear-gradient(135deg, #4285f4 0%, #34a853 100%);
        animation: listeningPulse 2s infinite;
      }

      .premium-voice-btn.processing {
        background: linear-gradient(135deg, #8b5cf6 0%, #a78bfa 100%);
        animation: processingRotate 1s linear infinite;
      }

      .premium-voice-btn.error {
        background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
        animation: errorShake 0.5s ease-in-out;
      }

      /* Voice Icon Container */
      .voice-btn-content {
        position: relative;
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .voice-icon-container {
        position: relative;
        transition: all 0.3s ease;
      }

      .voice-icon {
        transition: all 0.3s ease;
      }

      .voice-emoji {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 18px;
        transition: all 0.3s ease;
      }

      /* Hover Effects */
      .premium-voice-btn:hover .voice-icon {
        opacity: 0;
        transform: scale(0.8);
      }

      .premium-voice-btn:hover .voice-emoji {
        opacity: 1;
        transform: translate(-50%, -50%) scale(1.2);
      }

      .premium-voice-btn:not(:hover) .voice-emoji {
        opacity: 0;
        transform: translate(-50%, -50%) scale(0.8);
      }

      /* Shine Effect */
      .shine-effect {
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
        transition: left 0.6s ease;
      }

      .premium-voice-btn:hover .shine-effect {
        left: 100%;
      }

      /* Pulse Rings for Listening State */
      .pulse-rings {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        pointer-events: none;
      }

      .pulse-ring {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 44px;
        height: 44px;
        border: 2px solid rgba(66, 133, 244, 0.6);
        border-radius: 12px;
        opacity: 0;
      }

      .premium-voice-btn.listening .pulse-ring {
        animation: pulseRing 2s infinite;
      }

      .premium-voice-btn.listening .pulse-ring:nth-child(2) {
        animation-delay: 0.7s;
      }

      .premium-voice-btn.listening .pulse-ring:nth-child(3) {
        animation-delay: 1.4s;
      }

      /* Status Tooltip */
      .voice-status-tooltip {
        position: absolute;
        bottom: calc(100% + 8px);
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.9);
        color: white;
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 500;
        white-space: nowrap;
        z-index: 1000;
        opacity: 0;
        visibility: hidden;
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
      }

      .voice-status-tooltip:not(.hidden) {
        opacity: 1;
        visibility: visible;
      }

      .voice-status-tooltip::after {
        content: '';
        position: absolute;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        border: 4px solid transparent;
        border-top-color: rgba(0, 0, 0, 0.9);
      }

      .tooltip-content {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .recording-timer {
        color: #4285f4;
        font-weight: 600;
      }

      /* Animations */
      @keyframes listeningPulse {
        0%, 100% { 
          transform: scale(1);
          box-shadow: 0 4px 12px rgba(66, 133, 244, 0.3);
        }
        50% { 
          transform: scale(1.05);
          box-shadow: 0 8px 25px rgba(66, 133, 244, 0.5);
        }
      }

      @keyframes processingRotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }

      @keyframes errorShake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-4px); }
        75% { transform: translateX(4px); }
      }

      @keyframes pulseRing {
        0% {
          opacity: 0;
          transform: translate(-50%, -50%) scale(1);
        }
        10% {
          opacity: 1;
        }
        100% {
          opacity: 0;
          transform: translate(-50%, -50%) scale(2);
        }
      }

      /* Dark Mode Support */
      [data-theme="dark"] .voice-status-tooltip {
        background: rgba(255, 255, 255, 0.1);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
      }

      [data-theme="dark"] .voice-status-tooltip::after {
        border-top-color: rgba(255, 255, 255, 0.1);
      }

      /* Mobile Responsive */
      @media (max-width: 768px) {
        .premium-voice-btn {
          width: 40px;
          height: 40px;
          border-radius: 10px;
        }
        
        .voice-icon-container svg {
          width: 16px;
          height: 16px;
        }
        
        .voice-emoji {
          font-size: 16px;
        }
        
        .pulse-ring {
          width: 40px;
          height: 40px;
          border-radius: 10px;
        }
      }

      /* Auto-submit dialog styles */
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

      .auto-submit-dialog h3 {
        margin: 0 0 16px 0;
        color: #333;
        font-size: 18px;
      }

      .auto-submit-dialog p {
        margin: 0 0 20px 0;
        color: #666;
        line-height: 1.5;
      }

      .auto-submit-dialog .dialog-buttons {
        display: flex;
        gap: 12px;
        justify-content: flex-end;
      }

      .auto-submit-dialog button {
        padding: 8px 16px;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-weight: 500;
        transition: all 0.2s ease;
      }

      .auto-submit-dialog .btn-primary {
        background: #4285f4;
        color: white;
      }

      .auto-submit-dialog .btn-secondary {
        background: #f1f3f4;
        color: #333;
      }

      .auto-submit-dialog button:hover {
        transform: translateY(-1px);
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

      [data-theme="dark"] .auto-submit-dialog {
        background: #2d3748;
        color: white;
      }

      [data-theme="dark"] .auto-submit-dialog h3 {
        color: white;
      }

      [data-theme="dark"] .auto-submit-dialog p {
        color: #a0aec0;
      }

      [data-theme="dark"] .auto-submit-dialog .btn-secondary {
        background: #4a5568;
        color: white;
      }
    `;
    
    document.head.appendChild(style);
    this.log('Premium styles added');
  }

  bindEvents() {
    const voiceBtn = document.getElementById('premium-voice-btn');
    if (voiceBtn) {
      voiceBtn.addEventListener('click', () => this.handleVoiceButtonClick());
      
      // Hover effects for tooltip
      voiceBtn.addEventListener('mouseenter', () => this.showTooltip());
      voiceBtn.addEventListener('mouseleave', () => this.hideTooltip());
      
      this.log('Events bound successfully');
    } else {
      this.error('Premium voice button not found for event binding');
    }
  }

  setupSpeechRecognition() {
    if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
      this.log('Browser speech recognition not supported');
      this.useBrowserSpeechRecognition = false;
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.speechRecognition = new SpeechRecognition();
    
    this.speechRecognition.continuous = false;
    this.speechRecognition.interimResults = true;
    this.speechRecognition.lang = 'en-US';

    this.speechRecognition.onstart = () => {
      this.log('Speech recognition started');
      this.setButtonState('listening');
      this.updateTooltip('Listening...');
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

      // Show interim results in real-time
      if (interimTranscript) {
        this.updateChatInput(interimTranscript, false);
      }

      if (finalTranscript) {
        this.log('Final transcript:', finalTranscript);
        this.handleTranscriptionResult(finalTranscript);
      }
    };

    this.speechRecognition.onerror = (event) => {
      this.error('Speech recognition error:', event.error);
      this.handleSpeechRecognitionError(event.error);
    };

    this.speechRecognition.onend = () => {
      this.log('Speech recognition ended');
      this.setButtonState('normal');
      this.isListening = false;
    };

    this.log('Speech recognition setup complete');
  }

  async handleVoiceButtonClick() {
    this.log('Voice button clicked');

    if (this.isListening) {
      this.stopListening();
      return;
    }

    // Try browser speech recognition first
    if (this.useBrowserSpeechRecognition && this.speechRecognition) {
      this.startBrowserSpeechRecognition();
    } else {
      // Fallback to audio recording + Whisper
      this.startAudioRecording();
    }
  }

  startBrowserSpeechRecognition() {
    try {
      this.isListening = true;
      this.speechRecognition.start();
      this.log('Browser speech recognition started');
    } catch (error) {
      this.error('Failed to start speech recognition:', error);
      this.handleSpeechRecognitionError(error.message);
    }
  }

  stopListening() {
    if (this.speechRecognition && this.isListening) {
      this.speechRecognition.stop();
    }
    if (this.isRecording) {
      this.stopRecording();
    }
    this.setButtonState('normal');
    this.isListening = false;
  }

  async startAudioRecording() {
    this.log('Starting audio recording fallback...');
    
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      this.setupMediaRecorder();
      this.mediaRecorder.start(100);
      this.isRecording = true;
      this.isListening = true;
      this.recordingTime = 0;
      
      this.setButtonState('listening');
      this.updateTooltip('Listening...');
      this.startTimer();
      
      this.log('Audio recording started');
      
    } catch (error) {
      this.error('Failed to start audio recording:', error);
      this.handleMicrophoneError(error);
    }
  }

  setupMediaRecorder() {
    const mimeTypes = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4'
    ];

    let selectedMimeType = '';
    for (const mimeType of mimeTypes) {
      if (MediaRecorder.isTypeSupported(mimeType)) {
        selectedMimeType = mimeType;
        break;
      }
    }

    if (!selectedMimeType) {
      throw new Error('No supported audio MIME type found');
    }

    this.mediaRecorder = new MediaRecorder(this.stream, {
      mimeType: selectedMimeType
    });

    this.audioChunks = [];

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
      }
    };

    this.mediaRecorder.onstop = () => {
      this.handleAudioRecordingStop();
    };

    this.mediaRecorder.onerror = (event) => {
      this.error('MediaRecorder error:', event.error);
      this.showError('Recording error: ' + event.error.message);
    };
  }

  stopRecording() {
    if (!this.isRecording) return;

    this.isRecording = false;
    this.isListening = false;

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }

    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }

    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }

    this.setButtonState('normal');
  }

  async handleAudioRecordingStop() {
    if (this.audioChunks.length === 0) {
      this.showError('No audio recorded. Please try again.');
      return;
    }

    const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
    this.setButtonState('processing');
    this.updateTooltip('Processing...');

    try {
      const apiUrl = `${this.apiBase}/api/voice-to-text-only`;
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      const response = await fetch(apiUrl, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      this.handleTranscriptionResult(data.transcript);

    } catch (error) {
      this.error('Audio processing error:', error);
      this.showError('Error processing voice recording: ' + error.message);
    } finally {
      this.setButtonState('normal');
    }
  }

  handleTranscriptionResult(transcript) {
    if (!transcript || !transcript.trim()) {
      this.showError('No speech detected. Please try again.');
      return;
    }

    this.log('Transcription result:', transcript);
    this.updateChatInput(transcript, true);
    
    // Show success feedback
    this.showSuccess('Voice transcribed successfully');
    
    // Ask about auto-submit if enabled
    if (this.autoSubmit) {
      this.showAutoSubmitDialog(transcript);
    }
  }

  updateChatInput(text, isFinal = false) {
    const chatInput = document.getElementById('chat-input');
    if (!chatInput) {
      this.error('Chat input not found');
      return;
    }

    chatInput.value = text;
    this.autoResizeTextarea(chatInput);
    
    if (isFinal) {
      chatInput.focus();
      chatInput.setSelectionRange(text.length, text.length);
      this.showVoiceInputIndicator(chatInput);
      
      // Enable send button
      const sendButton = document.getElementById('send-button');
      if (sendButton) {
        sendButton.disabled = false;
      }
    }
  }

  autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    const minHeight = 52;
    const maxHeight = 200;
    const scrollHeight = textarea.scrollHeight;
    const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
    
    textarea.style.height = newHeight + 'px';
    textarea.style.overflowY = scrollHeight > maxHeight ? 'scroll' : 'hidden';
  }

  showVoiceInputIndicator(input) {
    input.style.borderColor = '#4285f4';
    input.style.boxShadow = '0 0 0 2px rgba(66, 133, 244, 0.2)';
    
    setTimeout(() => {
      input.style.borderColor = '';
      input.style.boxShadow = '';
    }, 3000);
  }

  showAutoSubmitDialog(transcript) {
    const overlay = document.createElement('div');
    overlay.className = 'dialog-overlay';
    
    const dialog = document.createElement('div');
    dialog.className = 'auto-submit-dialog';
    dialog.innerHTML = `
      <h3>Auto-submit Query?</h3>
      <p>Would you like to automatically send this query?</p>
      <div style="background: #f8f9fa; padding: 12px; border-radius: 6px; margin: 16px 0; font-style: italic;">
        "${transcript}"
      </div>
      <div class="dialog-buttons">
        <button class="btn-secondary" onclick="this.closest('.dialog-overlay').remove()">
          Review First
        </button>
        <button class="btn-primary" onclick="window.voiceRecorder.submitQuery('${transcript.replace(/'/g, "\\'")}'); this.closest('.dialog-overlay').remove();">
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
  }

  submitQuery(transcript) {
    // Trigger the normal form submission
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
      const event = new Event('submit', { bubbles: true, cancelable: true });
      chatForm.dispatchEvent(event);
    }
  }

  setButtonState(state) {
    const button = document.getElementById('premium-voice-btn');
    if (!button) return;

    // Remove all state classes
    button.classList.remove('listening', 'processing', 'error');
    
    // Add new state class
    if (state !== 'normal') {
      button.classList.add(state);
    }

    // Update tooltip based on state
    switch (state) {
      case 'listening':
        this.updateTooltip('Listening...');
        break;
      case 'processing':
        this.updateTooltip('Processing...');
        break;
      case 'error':
        this.updateTooltip('Error occurred');
        setTimeout(() => this.setButtonState('normal'), 2000);
        break;
      default:
        this.updateTooltip('Click to speak');
    }
  }

  showTooltip() {
    const tooltip = document.getElementById('voice-status-tooltip');
    if (tooltip) {
      tooltip.classList.remove('hidden');
    }
  }

  hideTooltip() {
    const tooltip = document.getElementById('voice-status-tooltip');
    if (tooltip && !this.isListening) {
      tooltip.classList.add('hidden');
    }
  }

  updateTooltip(text) {
    const statusText = document.querySelector('.voice-status-tooltip .status-text');
    if (statusText) {
      statusText.textContent = text;
    }
  }

  startTimer() {
    this.timer = setInterval(() => {
      this.recordingTime++;
      this.updateTimer();
    }, 1000);
  }

  updateTimer() {
    const timer = document.querySelector('.recording-timer');
    if (timer) {
      const minutes = Math.floor(this.recordingTime / 60);
      const seconds = this.recordingTime % 60;
      timer.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
      timer.classList.remove('hidden');
    }
  }

  handleSpeechRecognitionError(error) {
    this.setButtonState('error');
    
    let message = 'Voice recognition failed. ';
    switch (error) {
      case 'not-allowed':
      case 'permission-denied':
        message += 'Please allow microphone access and try again.';
        break;
      case 'no-speech':
        message += 'No speech detected. Please speak clearly and try again.';
        break;
      case 'network':
        message += 'Network error. Please check your connection.';
        break;
      default:
        message += 'Please try again or use the fallback mode.';
    }
    
    this.showError(message);
    
    // Offer fallback to audio recording
    if (error === 'not-allowed' && this.checkBrowserSupport()) {
      setTimeout(() => {
        this.showInfo('Tip: You can also try the audio recording mode');
      }, 2000);
    }
  }

  handleMicrophoneError(error) {
    this.setButtonState('error');
    
    let message = 'Microphone access failed. ';
    if (error.name === 'NotAllowedError') {
      message += 'Please allow microphone access in your browser settings.';
    } else if (error.name === 'NotFoundError') {
      message += 'No microphone found. Please connect a microphone.';
    } else {
      message += 'Please check your microphone and try again.';
    }
    
    this.showError(message);
  }

  showError(message) {
    if (typeof showToast === 'function') {
      showToast(message, 'error');
    } else {
      console.error(message);
      alert(message);
    }
  }

  showSuccess(message) {
    if (typeof showToast === 'function') {
      showToast(message, 'success');
    } else {
      console.log(message);
    }
  }

  showInfo(message) {
    if (typeof showToast === 'function') {
      showToast(message, 'info');
    } else {
      console.info(message);
    }
  }

  // Public API
  static isSupported() {
    return !!(
      (navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder) ||
      (window.SpeechRecognition || window.webkitSpeechRecognition)
    );
  }

  enableAutoSubmit() {
    this.autoSubmit = true;
  }

  disableAutoSubmit() {
    this.autoSubmit = false;
  }
}

// Initialize Premium Voice Recorder
if (!window.premiumVoiceRecorderInitialized) {
  window.premiumVoiceRecorderInitialized = true;

  function initializePremiumVoiceRecorder() {
    if (window.voiceRecorder) {
      console.log('[PremiumVoiceRecorder] Already initialized, skipping...');
      return;
    }

    if (!PremiumVoiceRecorder.isSupported()) {
      console.warn('[PremiumVoiceRecorder] Voice features not supported in this browser');
      return;
    }

    const chatActions = document.querySelector('.chat-actions');
    const chatForm = document.getElementById('chat-form');
    
    if (!chatActions || !chatForm) {
      console.warn('[PremiumVoiceRecorder] Chat interface not ready, retrying...');
      if (!window.voiceRecorderRetryCount) window.voiceRecorderRetryCount = 0;
      if (window.voiceRecorderRetryCount < 5) {
        window.voiceRecorderRetryCount++;
        setTimeout(initializePremiumVoiceRecorder, 500);
      }
      return;
    }

    try {
      window.voiceRecorder = new PremiumVoiceRecorder({
        apiBase: window.API_BASE || window.location.origin,
        debug: true,
        autoSubmit: false // Can be enabled later
      });
      console.log('[PremiumVoiceRecorder] Initialized successfully');
    } catch (error) {
      console.error('[PremiumVoiceRecorder] Failed to initialize:', error);
    }
  }

  // Initialize when ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializePremiumVoiceRecorder);
  } else {
    initializePremiumVoiceRecorder();
  }

  setTimeout(initializePremiumVoiceRecorder, 1000);
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PremiumVoiceRecorder;
}
