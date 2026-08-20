const API_URL = "http://127.0.0.1:8000";
const token = localStorage.getItem("access_token");
const chatBody = document.querySelector(".chat-body");
const chatInput = document.querySelector(".chat-input-wrap input");
const sendButton = document.querySelector(".chat-input-wrap button");
const newChatButtons = document.querySelectorAll(".new-chat-btn");
const sidebar = document.querySelector(".chat-sidebar");
let conversationId = null;

if (!token && window.location.pathname.endsWith("chat.html")) window.location.href = "login.html";

document.querySelector("#chat-home")?.classList.toggle("d-none", !token);
document.querySelector("#logout-btn")?.addEventListener("click", () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("username");
  localStorage.removeItem("useremail");
  window.location.href = "index.html";
});
window.logout = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("username");
  localStorage.removeItem("useremail");
  window.location.href = "index.html";
};

function addMessage(text, type) {
  const wrapper = document.createElement("div");
  wrapper.className = `chat-message ${type === "user" ? "user" : "assistant"}`;
  const bubble = document.createElement("div");
  bubble.className = `bubble ${type === "user" ? "user-bubble" : ""}`;
  bubble.textContent = text;
  wrapper.appendChild(bubble);
  chatBody.appendChild(wrapper);
  chatBody.scrollTop = chatBody.scrollHeight;
  return wrapper;
}

function addSources(sources) {
  if (!sources?.length) return;
  const sourceBox = document.createElement("div");
  sourceBox.className = "source-list";
  sourceBox.innerHTML = `<div class="source-title"><span>Sources</span></div>`;
  sources.forEach((source) => {
    const item = document.createElement("div");
    item.className = "source-item";
    if (typeof source === "string") {
      item.textContent = `• ${source}`;
    } else {
      const confidence = Math.round((Number(source.confidence || 0) * 100));
      item.textContent = `• Page ${source.page_number || "?"} | ${source.section || "General"} | Chunk ${source.chunk_number || "?"} | Confidence ${confidence}%`;
    }
    sourceBox.appendChild(item);
  });
  chatBody.appendChild(sourceBox);
}

async function sendQuestion() {
  const question = chatInput.value.trim();
  if (!question || !token) return;
  addMessage(question, "user");
  chatInput.value = "";
  chatInput.disabled = true;
  sendButton.disabled = true;
  const thinking = addMessage("Searching the guideline...", "assistant");
  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ message: question, conversation_id: conversationId }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "The chat request failed.");
    conversationId = data.conversation_id;
    thinking.remove();
    addMessage(data.reply, "assistant");
    addSources(data.sources);
  } catch (error) {
    thinking.remove();
    addMessage(error.message, "assistant");
  } finally {
    chatInput.disabled = false;
    sendButton.disabled = false;
    chatInput.focus();
  }
}

function resetChat() {
  conversationId = null;
  chatBody.replaceChildren();
  addMessage("Hello! I am MedGuide AI. Ask me about low back pain or sciatica.", "assistant");
  document.querySelector(".message-suggestions")?.classList.remove("d-none");
}

function showConversation(messages) {
  chatBody.replaceChildren();
  document.querySelector(".message-suggestions")?.classList.add("d-none");
  messages.forEach((message) => {
    addMessage(message.content, message.role);
    if (message.role === "assistant") addSources(message.sources || []);
  });
}

async function loadConversation(id) {
  const response = await fetch(`${API_URL}/api/conversations/${id}/messages`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Could not load conversation.");
  conversationId = id;
  showConversation(data.messages);
}

sendButton?.addEventListener("click", sendQuestion);
chatInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendQuestion(); }
});
document.querySelectorAll(".message-suggestions button").forEach((button) => {
  button.addEventListener("click", () => { chatInput.value = button.textContent.trim(); sendQuestion(); });
});
newChatButtons.forEach((button) => button.addEventListener("click", resetChat));

async function loadConversations() {
  if (!sidebar || !token) return;
  const response = await fetch(`${API_URL}/api/conversations`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) return;
  const data = await response.json();
  data.conversations.forEach((conversation) => {
    const item = document.createElement("button");
    item.className = "chat-item";
    item.textContent = conversation.title;
    item.type = "button";
    item.addEventListener("click", () => loadConversation(conversation.id).catch((error) => addMessage(error.message, "assistant")));
    sidebar.appendChild(item);
  });
}
loadConversations();
