// Minimal frontend app for packaged static UI
const $convoList = document.getElementById('convoList')
const $messages = document.getElementById('messages')
const $composer = document.getElementById('composer')
const $input = document.getElementById('inputBox')
const $scrollBtn = document.getElementById('scrollBtn')
const $apiDot = document.getElementById('apiDot')

let currentConversation = null

function setApiStatus(online){
	$apiDot.classList.toggle('online', !!online)
	$apiDot.classList.toggle('offline', !online)
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
	list.forEach(c=>{
		const el = document.createElement('div')
		el.className = 'convo-item'
		el.tabIndex = 0
		const metaRow = document.createElement('div')
		metaRow.className = 'meta-row'
		const titleDiv = document.createElement('div')
		titleDiv.innerHTML = `<strong>${c.title || c.id}</strong><div style="font-size:12px;color:rgba(255,255,255,0.7)">${new Date(c.updated_at||Date.now()).toLocaleString()}</div>`
		const deleteBtn = document.createElement('button')
		deleteBtn.className = 'delete-btn'
		deleteBtn.title = 'Delete conversation'
		deleteBtn.innerHTML = '✕'
		deleteBtn.addEventListener('click', async (e)=>{
			e.stopPropagation()
			const ok = confirm('Delete this conversation?')
			if(!ok) return
			// try backend delete
			try{
				const res = await fetch(`/conversations/${encodeURIComponent(c.id)}`, {method:'DELETE'})
				if(!res.ok) throw new Error('delete failed')
				// remove from UI
				el.remove()
			}catch(err){
				// fallback: remove locally and notify
				el.remove()
				alert('Conversation removed locally. Server delete may not be available.')
			}
		})
		metaRow.appendChild(titleDiv)
		metaRow.appendChild(deleteBtn)
		el.appendChild(metaRow)
		el.addEventListener('click', ()=> loadConversation(c.id))
		$convoList.appendChild(el)
	})
}

async function loadConversation(id){
	currentConversation = id
	$messages.innerHTML = ''
	try{
		const res = await fetch(`/conversations/${encodeURIComponent(id)}`)
		if(!res.ok) throw new Error('no convo')
		const data = await res.json()
		renderMessages(data.messages || [])
		setApiStatus(true)
	}catch(e){
		// demo messages
		setApiStatus(false)
		renderMessages([
			{role:'bot',text:'Welcome — try typing: compare AAPL MSFT',ts:Date.now()-60000},
			{role:'user',text:'compare AAPL MSFT',ts:Date.now()-30000},
			{role:'bot',text:'Benchmark summary for AAPL, MSFT (FY2024, FY2025):\n- Adjusted net margin: MSFT 36.1%\n- Return on equity: AAPL 164.6%\n- P/E ratio: AAPL 40.31',ts:Date.now()}
		])
	}
}

function renderMessages(messages){
	$messages.innerHTML = ''
	messages.forEach(m=>{
		const el = document.createElement('div')
		el.className = 'message ' + (m.role === 'user' ? 'user':'bot')
		const meta = document.createElement('div')
		meta.className = 'meta'
		meta.textContent = m.role === 'user' ? 'You' : 'BENCHMARKOS'
		const text = document.createElement('div')
		text.className = 'text'
		text.innerText = m.text
		el.appendChild(meta)
		el.appendChild(text)
		$messages.appendChild(el)
	})
	scrollToBottom(false)
}

function appendMessage(msg){
	const el = document.createElement('div')
	el.className = 'message ' + (msg.role === 'user' ? 'user':'bot')
	const meta = document.createElement('div')
	meta.className = 'meta'
	meta.textContent = msg.role === 'user' ? 'You' : 'BENCHMARKOS'
	const text = document.createElement('div')
	text.className = 'text'
	text.innerText = msg.text
	el.appendChild(meta)
	el.appendChild(text)
	$messages.appendChild(el)
	scrollToBottom(true)
}

function scrollToBottom(smooth=true){
	if(smooth){
		$messages.scrollTo({top:$messages.scrollHeight,behavior:'smooth'})
	} else {
		$messages.scrollTop = $messages.scrollHeight
	}
}

// show/hide scroll button
$messages.addEventListener('scroll', ()=>{
	const threshold = $messages.scrollHeight - $messages.clientHeight - $messages.scrollTop
	if($messages.scrollTop + $messages.clientHeight < $messages.scrollHeight - 60){
		$scrollBtn.classList.add('show')
		$scrollBtn.setAttribute('aria-hidden','false')
	} else {
		$scrollBtn.classList.remove('show')
		$scrollBtn.setAttribute('aria-hidden','true')
	}
})

$scrollBtn.addEventListener('click', ()=> scrollToBottom(true))

$composer.addEventListener('submit', async (ev)=>{
	ev.preventDefault()
	const text = $input.value.trim()
	if(!text) return
	appendMessage({role:'user',text,ts:Date.now()})
	$input.value = ''
	// try backend chat endpoint
	try{
		const res = await fetch('/chat', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,conversation_id:currentConversation})})
		if(!res.ok) throw new Error('chat failed')
		const data = await res.json()
		const replyText = typeof data.reply === 'string' ? data.reply : (data.answer || JSON.stringify(data))
		appendMessage({role:'bot',text:replyText,ts:Date.now()})
		setApiStatus(true)
	}catch(e){
		setApiStatus(false)
		// fallback canned reply
		appendMessage({role:'bot',text:'(demo) I received: ' + text,ts:Date.now()})
	}
})

// init
fetchConversations()
loadConversation('demo-1')

