# 🎤 Voice Recording Integration Guide

This guide explains how to use the newly integrated voice recording feature in your Finalyze Chatbot.

## 🚀 Quick Start

### 1. Install Dependencies

**Python Dependencies (already added to requirements.txt):**
```bash
pip install -r requirements.txt
```

**Node.js Dependencies:**
```bash
cd webui
npm install
```

### 2. Configure OpenAI API Key

Ensure your OpenAI API key is properly configured in your settings. The voice feature uses OpenAI's Whisper model for speech-to-text conversion.

### 3. Start the Server

```bash
cd app
python run_chatbot.py
```

### 4. Access the Web Interface

Open your browser to `http://localhost:8000` and look for the 🎤 button next to the chat input.

## 🎯 Features

### Voice Recording
- **Start Recording**: Click the 🎤 microphone button
- **Stop Recording**: Click the ⏹ stop button or wait for automatic silence detection
- **Real-time Timer**: Shows recording duration
- **Visual Feedback**: Button changes color and shows recording status

### Automatic Silence Detection
- Automatically stops recording after 2 seconds of silence
- Helps prevent accidentally long recordings
- Can be manually overridden by clicking stop

### Audio Processing
- Uses OpenAI Whisper for high-quality speech-to-text conversion
- Supports multiple audio formats (WebM, MP3, WAV)
- Automatic noise suppression and echo cancellation
- Handles various accents and languages

### Integration
- Seamlessly integrates with existing chat interface
- Maintains conversation context
- Works with all existing chatbot features
- Responsive design for mobile and desktop

## 🔧 Technical Implementation

### Backend (FastAPI)
- **Endpoint**: `POST /api/voice-to-text`
- **Input**: Audio file (multipart/form-data)
- **Output**: JSON with transcript and chatbot response
- **Processing**: OpenAI Whisper → Chatbot → Response

### Frontend (JavaScript)
- **File**: `webui/voice-recorder.js`
- **Integration**: Automatically loads with existing interface
- **Browser APIs**: MediaRecorder, Web Audio API, getUserMedia
- **Compatibility**: Modern browsers with microphone support

## 🛠️ Customization

### Silence Detection Settings
Edit `webui/voice-recorder.js`:
```javascript
this.silenceThreshold = 10;     // Audio level threshold
this.silenceDuration = 2000;    // Milliseconds of silence before auto-stop
```

### Audio Quality Settings
Modify the MediaRecorder configuration:
```javascript
this.mediaRecorder = new MediaRecorder(this.stream, {
  mimeType: 'audio/webm;codecs=opus',
  audioBitsPerSecond: 128000  // Adjust quality vs file size
});
```

### UI Styling
The voice recorder inherits your existing theme. Customize in `webui/voice-recorder.js` within the `addStyles()` method.

## 🔍 Testing

Run the test script to verify everything is working:
```bash
python test_voice_integration.py
```

This will check:
- Server connectivity
- Endpoint availability
- Dependencies
- Configuration

## 🐛 Troubleshooting

### Common Issues

**"Could not access microphone"**
- Grant microphone permissions in your browser
- Check if another application is using the microphone
- Try refreshing the page

**"Voice processing failed"**
- Verify OpenAI API key is configured
- Check internet connection
- Ensure audio file is not corrupted

**Voice button not appearing**
- Check browser console for JavaScript errors
- Verify `voice-recorder.js` is loading
- Ensure browser supports MediaRecorder API

### Browser Compatibility
- **Chrome/Edge**: Full support
- **Firefox**: Full support
- **Safari**: Supported (iOS 14.3+)
- **Mobile browsers**: Generally supported

### HTTPS Requirement
Voice recording requires HTTPS in production. For local development, `localhost` works with HTTP.

## 📱 Mobile Support

The voice recorder is fully responsive and works on mobile devices:
- Touch-friendly button sizing
- Optimized for mobile browsers
- Handles device orientation changes
- Works with mobile microphones

## 🔒 Privacy & Security

- Audio is processed server-side and immediately deleted
- No audio files are permanently stored
- Transcripts follow your existing data retention policies
- OpenAI API calls follow their privacy policy

## 🎨 UI Integration

The voice recorder seamlessly integrates with your existing Finalyze interface:
- Matches your current theme colors
- Responsive design
- Consistent with existing button styles
- Accessible keyboard navigation

## 📊 Performance

- **Latency**: ~2-5 seconds for transcription
- **Audio Quality**: Optimized for speech recognition
- **File Size**: Compressed audio format
- **Memory**: Minimal impact on browser performance

## 🔄 Future Enhancements

Potential improvements you could add:
- Text-to-speech for responses
- Multiple language support
- Audio playback of recordings
- Batch voice processing
- Voice commands for navigation

## 📞 Support

If you encounter issues:
1. Check the browser console for errors
2. Run the test script: `python test_voice_integration.py`
3. Verify all dependencies are installed
4. Check OpenAI API key configuration

---

**Enjoy your new voice-powered chatbot experience! 🎉**
