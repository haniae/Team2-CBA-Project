// Professional Financial AI Chatbot UI
// Enhanced with smooth animations and better UX

const $convoList = document.getElementById('convoList')
const $messages = document.getElementById('messages')
const $composer = document.getElementById('composer')
const $input = document.getElementById('inputBox')
const $scrollBtn = document.getElementById('scrollBtn')
const $apiDot = document.getElementById('apiDot')
const $apiStatus = document.getElementById('apiStatus')
const $newChatBtn = document.getElementById('newChatBtn')

let currentConversation = null
let isTyping = false

function isNearBottom(thresholdPx = 120) {
    const distanceFromBottom = $messages.scrollHeight - $messages.clientHeight - $messages.scrollTop
    return distanceFromBottom <= thresholdPx
}

function setApiStatus(online){
	$apiDot.classList.toggle('online', !!online)
	$apiDot.classList.toggle('offline', !online)
	if ($apiStatus) {
		$apiStatus.textContent = online ? 'Connected' : 'Offline'
		$apiStatus.style.color = online ? '#10B981' : '#8B95A5'
	}
}

async function fetchConversations(){
	try{
		const res = await fetch('/conversations')
		if(!res.ok) throw new Error('no convos')
		const data = await res.json()
		renderConversations(data)
		setApiStatus(true)
	}catch(e){
		// fallback demo
		setApiStatus(false)
		renderConversations([{
			id:'demo-1',title:'Demo: Tickers comparison',updated_at:new Date().toISOString()
		}])
	}
}

function renderConversations(list){
	$convoList.innerHTML = ''
	if (!list || list.length === 0) {
		$convoList.innerHTML = '<div style="text-align:center;padding:20px;opacity:0.5;font-size:13px;">No conversations yet</div>'
		return
	}
	
	list.forEach((c, index)=>{
		const el = document.createElement('div')
		el.className = 'convo-item'
		el.tabIndex = 0
		el.style.animationDelay = `${index * 50}ms`
		
		const metaRow = document.createElement('div')
		metaRow.className = 'meta-row'
		
		const titleDiv = document.createElement('div')
		const title = c.title || c.id
		const date = new Date(c.updated_at || Date.now())
		const timeStr = formatRelativeTime(date)
		titleDiv.innerHTML = `<strong style="font-size:13px;display:block;margin-bottom:4px;">${escapeHtml(title)}</strong><div style="font-size:11px;color:rgba(255,255,255,0.6);">${timeStr}</div>`
		
		const deleteBtn = document.createElement('button')
		deleteBtn.className = 'delete-btn'
		deleteBtn.title = 'Delete conversation'
		deleteBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<line x1="18" y1="6" x2="6" y2="18"></line>
			<line x1="6" y1="6" x2="18" y2="18"></line>
		</svg>`
		
		deleteBtn.addEventListener('click', async (e)=>{
			e.stopPropagation()
			if(!confirm('Delete this conversation?')) return
			
			el.style.opacity = '0.5'
			el.style.pointerEvents = 'none'
			
			try{
				const res = await fetch(`/conversations/${encodeURIComponent(c.id)}`, {method:'DELETE'})
				if(!res.ok) throw new Error('delete failed')
				el.style.transform = 'translateX(-100%)'
				setTimeout(() => el.remove(), 300)
			}catch(err){
				el.style.transform = 'translateX(-100%)'
				setTimeout(() => el.remove(), 300)
			}
		})
		
		metaRow.appendChild(titleDiv)
		metaRow.appendChild(deleteBtn)
		el.appendChild(metaRow)
		el.addEventListener('click', ()=> loadConversation(c.id))
		el.addEventListener('keypress', (e)=> {
			if(e.key === 'Enter') loadConversation(c.id)
		})
		$convoList.appendChild(el)
	})
}

function formatRelativeTime(date) {
	const now = new Date()
	const diff = now - date
	const seconds = Math.floor(diff / 1000)
	const minutes = Math.floor(seconds / 60)
	const hours = Math.floor(minutes / 60)
	const days = Math.floor(hours / 24)
	
	if (seconds < 60) return 'Just now'
	if (minutes < 60) return `${minutes}m ago`
	if (hours < 24) return `${hours}h ago`
	if (days < 7) return `${days}d ago`
	return date.toLocaleDateString()
}

function escapeHtml(text) {
	const div = document.createElement('div')
	div.textContent = text
	return div.innerHTML
}

async function loadConversation(id){
	currentConversation = id
	$messages.innerHTML = '<div class="loading-indicator" style="text-align:center;padding:40px;color:#8B95A5;">Loading conversation...</div>'
	
	try{
		const res = await fetch(`/conversations/${encodeURIComponent(id)}`)
		if(!res.ok) throw new Error('no convo')
		const data = await res.json()
		renderMessages(data.messages || [])
		setApiStatus(true)
	}catch(e){
		// demo messages with welcome
		setApiStatus(false)
		renderMessages([
			{role:'bot',text:'👋 Welcome to BenchmarkOS Analyst Copilot\n\nI\'m your AI-powered financial analysis assistant. I can help you:\n\n• Compare ticker fundamentals\n• Analyze KPIs and metrics\n• Build financial models\n• Generate insights from data\n\nTry asking: "Compare AAPL and MSFT"',ts:Date.now()-60000}
		])
	}
}

function renderMessages(messages){
	$messages.innerHTML = ''
	messages.forEach((m, index)=>{
		const el = createMessageElement(m)
		el.style.animationDelay = `${index * 50}ms`
		$messages.appendChild(el)
	})
	scrollToBottom(false)
}

function createMessageElement(msg) {
	const el = document.createElement('div')
	el.className = 'message ' + (msg.role === 'user' ? 'user' : 'bot')
	
	const meta = document.createElement('div')
	meta.className = 'meta'
	
	if (msg.role === 'user') {
		meta.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:4px;">
			<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
			<circle cx="12" cy="7" r="4"></circle>
		</svg> You`
	} else {
		meta.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:4px;">
			<path d="M13 2L3 14h8l-1 8 10-12h-8l1-8z"/>
		</svg> BenchmarkOS AI`
	}
	
	const text = document.createElement('div')
	text.className = 'text'
	
	// For bot messages, render markdown
	if (msg.role === 'bot') {
		text.innerHTML = renderMarkdown(msg.text)
	} else {
		// User messages stay as plain text
		text.innerText = msg.text
	}
	
	el.appendChild(meta)
	el.appendChild(text)
	
	return el
}

// Simple markdown renderer for bot messages
function renderMarkdown(text) {
	if (!text) return ''
	
	// Escape HTML to prevent XSS
	let html = text
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
	
	// Split into lines for processing
	const lines = html.split('\n')
	let result = []
	let inList = false
	let listType = null
	
	for (let i = 0; i < lines.length; i++) {
		let line = lines[i]
		
		// Headers
		if (line.match(/^### (.+)$/)) {
			if (inList) { result.push(`</${listType}>`); inList = false; }
			result.push(line.replace(/^### (.+)$/, '<h3>$1</h3>'))
		} else if (line.match(/^## (.+)$/)) {
			if (inList) { result.push(`</${listType}>`); inList = false; }
			result.push(line.replace(/^## (.+)$/, '<h2>$1</h2>'))
		} else if (line.match(/^# (.+)$/)) {
			if (inList) { result.push(`</${listType}>`); inList = false; }
			result.push(line.replace(/^# (.+)$/, '<h1>$1</h1>'))
		}
		// Bullet lists
		else if (line.match(/^[\-•]\s+(.+)$/)) {
			if (!inList || listType !== 'ul') {
				if (inList) result.push(`</${listType}>`)
				result.push('<ul>')
				listType = 'ul'
				inList = true
			}
			result.push(line.replace(/^[\-•]\s+(.+)$/, '<li>$1</li>'))
		}
		// Numbered lists
		else if (line.match(/^\d+\.\s+(.+)$/)) {
			if (!inList || listType !== 'ol') {
				if (inList) result.push(`</${listType}>`)
				result.push('<ol>')
				listType = 'ol'
				inList = true
			}
			result.push(line.replace(/^\d+\.\s+(.+)$/, '<li>$1</li>'))
		}
		// Empty line
		else if (line.trim() === '') {
			if (inList) {
				result.push(`</${listType}>`)
				inList = false
				listType = null
			}
			result.push('</p><p>')
		}
		// Regular line
		else {
			if (inList) { result.push(`</${listType}>`); inList = false; listType = null; }
			result.push(line)
		}
	}
	
	// Close any open list
	if (inList) {
		result.push(`</${listType}>`)
	}
	
	// Join and wrap in paragraphs
	html = result.join('\n')
	
	// Bold (**text**)
	html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
	
	// Links [text](url)
	html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
	
	// Wrap in paragraphs
	html = '<p>' + html + '</p>'
	
	// Clean up paragraph tags around headers and lists
	html = html.replace(/<p>\s*<h([123])>/g, '<h$1>')
	html = html.replace(/<\/h([123])>\s*<\/p>/g, '</h$1>')
	html = html.replace(/<p>\s*<ul>/g, '<ul>')
	html = html.replace(/<\/ul>\s*<\/p>/g, '</ul>')
	html = html.replace(/<p>\s*<ol>/g, '<ol>')
	html = html.replace(/<\/ol>\s*<\/p>/g, '</ol>')
	
	// Clean up empty paragraphs and multiple breaks
	html = html.replace(/<p>\s*<\/p>/g, '')
	html = html.replace(/<\/p>\s*<p>/g, '</p><p>')
	
	return html
}

function appendMessage(msg){
    const shouldAutoScroll = isNearBottom(120)
    const el = createMessageElement(msg)
    $messages.appendChild(el)
    if (shouldAutoScroll) {
        scrollToBottom(true)
    }
    return el
}

function showTypingIndicator() {
	if (isTyping) return
	isTyping = true
	
	const el = document.createElement('div')
	el.className = 'message bot typing-indicator'
	el.id = 'typingIndicator'
	el.innerHTML = `
		<div class="meta">
			<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:4px;">
				<path d="M13 2L3 14h8l-1 8 10-12h-8l1-8z"/>
			</svg> BenchmarkOS AI
		</div>
		<div class="text">
			<div style="display:flex;gap:6px;align-items:center;">
				<div class="typing-dot"></div>
				<div class="typing-dot"></div>
				<div class="typing-dot"></div>
			</div>
		</div>
	`
	$messages.appendChild(el)
	scrollToBottom(true)
}

function hideTypingIndicator() {
	isTyping = false
	const indicator = document.getElementById('typingIndicator')
	if (indicator) {
		indicator.style.opacity = '0'
		setTimeout(() => indicator.remove(), 300)
	}
}

function scrollToBottom(smooth=true){
	if(smooth){
		$messages.scrollTo({top:$messages.scrollHeight,behavior:'smooth'})
	} else {
		$messages.scrollTop = $messages.scrollHeight
	}
}

function updateScrollBtnOffset(){
	if(!$scrollBtn || !$messages) return
	const offset = 20
	const btnSize = 40
	const extra = 8
	$scrollBtn.style.bottom = `${offset}px`
	if ($scrollBtn.classList.contains('show')) {
		$messages.style.paddingBottom = `${btnSize + offset + extra}px`
	} else {
		$messages.style.paddingBottom = `16px`
	}
}

// show/hide scroll button

$messages.addEventListener('scroll', ()=>{
	if(!isNearBottom(120)){
		$scrollBtn.classList.add('show')
		$scrollBtn.setAttribute('aria-hidden','false')
	} else {
		$scrollBtn.classList.remove('show')
		$scrollBtn.setAttribute('aria-hidden','true')
	}
	updateScrollBtnOffset()
})

$scrollBtn.addEventListener('click', ()=> { scrollToBottom(true); updateScrollBtnOffset() })

if ($scrollBtn && $messages && $scrollBtn.parentElement !== $messages) {
	$messages.appendChild($scrollBtn)
}

window.addEventListener('resize', updateScrollBtnOffset)
updateScrollBtnOffset()

$composer.addEventListener('submit', async (ev)=>{
	ev.preventDefault()
	const text = $input.value.trim()
	if(!text || isTyping) return
	
	// Add user message
	appendMessage({role:'user',text,ts:Date.now()})
	$input.value = ''
	$input.disabled = true
	
	// Show typing indicator
	showTypingIndicator()
	
	try{
		const res = await fetch('/chat', {
			method:'POST',
			headers:{'Content-Type':'application/json'},
			body:JSON.stringify({text,conversation_id:currentConversation})
		})
		
		if(!res.ok) throw new Error('chat failed')
		
		const data = await res.json()
		const replyText = typeof data.reply === 'string' ? data.reply : (data.answer || JSON.stringify(data))
		
		// Simulate natural typing delay
		await new Promise(resolve => setTimeout(resolve, 500))
		
		hideTypingIndicator()
		appendMessage({role:'bot',text:replyText,ts:Date.now()})
		setApiStatus(true)
	}catch(e){
		console.error('Chat error:', e)
		hideTypingIndicator()
		setApiStatus(false)
		appendMessage({role:'bot',text:'I apologize, but I\'m having trouble connecting to the server. Please check your connection and try again.',ts:Date.now()})
	} finally {
		$input.disabled = false
		$input.focus()
	}
})

// New chat button handler
$newChatBtn.addEventListener('click', () => {
	currentConversation = null
	$messages.innerHTML = ''
	renderMessages([
		{role:'bot',text:'👋 New conversation started!\n\nHow can I help you with financial analysis today?',ts:Date.now()}
	])
	$input.focus()
})

// Suggested prompts click handlers
document.querySelectorAll('.prompt').forEach(btn => {
	btn.addEventListener('click', () => {
		const promptText = btn.textContent.trim()
		$input.value = promptText
		$input.focus()
	})
})

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
	// Ctrl/Cmd + K to focus input
	if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
		e.preventDefault()
		$input.focus()
	}
	// Escape to blur input
	if (e.key === 'Escape' && document.activeElement === $input) {
		$input.blur()
	}
})

// Initialize
async function init() {
	await fetchConversations()
	loadConversation('demo-1')
	$input.focus()
}

init()

