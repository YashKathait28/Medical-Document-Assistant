const healthEl = document.getElementById("health");
const uploadBtn = document.getElementById("uploadBtn");
const driveBtn = document.getElementById("driveBtn");
const clearBtn = document.getElementById("clearBtn");
const fileInput = document.getElementById("fileInput");
const uploadStatus = document.getElementById("uploadStatus");
const docList = document.getElementById("docList");
const chatLog = document.getElementById("chatLog");
const chatInput = document.getElementById("chatInput");
const chatBtn = document.getElementById("chatBtn");
const clearChatBtn = document.getElementById("clearChatBtn");
const chatMeta = document.getElementById("chatMeta");
const sectionsInput = document.getElementById("sectionsInput");
const summaryCheck = document.getElementById("summaryCheck");
const reportBtn = document.getElementById("reportBtn");
const reportStatus = document.getElementById("reportStatus");

let sessionId = null;

async function fetchHealth() {
  try {
    const res = await fetch("/health");
    const data = await res.json();
    healthEl.textContent = data.status || "ok";
    const llmStatus = document.getElementById("llmStatus");
    if (llmStatus) {
        if (data.llm_enabled) {
          llmStatus.textContent = `LLM: ${data.llm_provider} (${data.llm_model})`;
        } else {
          llmStatus.textContent = "LLM: disabled (extractive answers)";
        }
    }
  } catch (err) {
    healthEl.textContent = "offline";
  }
}

function renderDocs(docs) {
  docList.innerHTML = "";
  if (!docs.length) {
    docList.innerHTML = "<div class='muted'>No documents yet.</div>";
    return;
  }
  docs.forEach((doc) => {
    const card = document.createElement("div");
    card.className = "doc-card";
    card.innerHTML = `
      <strong>${doc.name}</strong>
      <div class='muted'>chunks: ${doc.chunks} • source: ${doc.source}</div>
      <div class='doc-actions'>
        <button class='button-secondary' data-doc='${doc.id}'>Delete</button>
      </div>
    `;
    const btn = card.querySelector("button[data-doc]");
    btn.addEventListener("click", async () => {
      if (!confirm(`Delete ${doc.name}?`)) {
        return;
      }
      await fetch(`/documents/${doc.id}`, { method: "DELETE" });
      await loadDocs();
    });
    docList.appendChild(card);
  });
}

async function loadDocs() {
  const res = await fetch("/documents");
  const data = await res.json();
  renderDocs(data.documents || []);
}

function addChatEntry(role, text) {
  const entry = document.createElement("div");
  entry.className = "chat-entry";
  entry.innerHTML = `<span>${role}:</span> ${text}`;
  chatLog.appendChild(entry);
  chatLog.scrollTop = chatLog.scrollHeight;
}

uploadBtn.addEventListener("click", async () => {
  const files = fileInput.files;
  if (!files.length) {
    uploadStatus.textContent = "Pick at least one file.";
    return;
  }
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append("files", file));
  uploadStatus.textContent = "Uploading...";
  const res = await fetch("/upload", { method: "POST", body: formData });
  const data = await res.json();
  uploadStatus.textContent = `Uploaded ${data.uploaded?.length || 0} file(s).`;
  await loadDocs();
});

driveBtn.addEventListener("click", async () => {
  uploadStatus.textContent = "Pulling from Drive...";
  const res = await fetch("/ingest/drive", { method: "POST" });
  const data = await res.json();
  uploadStatus.textContent = `Ingested ${data.ingested?.length || 0} file(s).`;
  await loadDocs();
});

clearBtn.addEventListener("click", async () => {
  if (!confirm("Clear all documents? This deletes uploaded files and resets the index.")) {
    return;
  }
  uploadStatus.textContent = "Clearing documents...";
  await fetch("/documents/clear", { method: "POST" });
  sessionId = null;
  chatLog.innerHTML = "";
  chatMeta.textContent = "";
  await loadDocs();
  uploadStatus.textContent = "All documents cleared.";
});

chatBtn.addEventListener("click", async () => {
  const message = chatInput.value.trim();
  if (!message) return;
  addChatEntry("You", message);
  chatInput.value = "";
  chatMeta.textContent = "Thinking...";

  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message })
  });
  const data = await res.json();
  sessionId = data.session_id;

  addChatEntry("Assistant", data.answer);
  if (data.citations?.length) {
    const cite = data.citations.map((c) => {
      const label = `${c.doc_name} (${c.chunk_id})`;
      if (c.source_link) {
        return `<a href='${c.source_link}' target='_blank'>${label}</a>`;
      }
      return label;
    }).join("; ");
    chatMeta.innerHTML = `Citations: ${cite}`;
  } else {
    chatMeta.textContent = "No citations";
  }
});

clearChatBtn.addEventListener("click", async () => {
  if (!confirm("Clear this chat history?")) {
    return;
  }
  const query = sessionId ? `?session_id=${sessionId}` : "";
  await fetch(`/chat/clear${query}`, { method: "POST" });
  sessionId = null;
  chatLog.innerHTML = "";
  chatMeta.textContent = "";
});

reportBtn.addEventListener("click", async () => {
  const raw = sectionsInput.value.trim();
  if (!raw) {
    reportStatus.textContent = "Add at least one section title.";
    return;
  }
  const sections = raw.split(",").map((s) => s.trim()).filter(Boolean);
  reportStatus.textContent = "Generating report...";

  const res = await fetch("/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, sections, include_summary: summaryCheck.checked })
  });
  const data = await res.json();
  reportStatus.innerHTML = `Report ready: <a href='${data.download_url}'>Download PDF</a>`;
});

fetchHealth();
loadDocs();
