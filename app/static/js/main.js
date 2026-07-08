/* ═══════════════════════════════════════════════════════════════════════════
   app/static/js/main.js
   Hastane AI Platformu — Chatbot AJAX ve Dinamik UI İşlemleri
   ═══════════════════════════════════════════════════════════════════════════ */

"use strict";

// ─── Global Sohbet Geçmişi ────────────────────────────────────────────────
const conversationHistory = [];

// ─── DOM Referansları ─────────────────────────────────────────────────────
const chatMessages   = document.getElementById("chat-messages");
const chatInput      = document.getElementById("chat-input");
const sendBtn        = document.getElementById("send-btn");
const ticketBtn      = document.getElementById("open-ticket-btn");
const ticketListBody = document.getElementById("ticket-list-body");
const ticketCount    = document.getElementById("ticket-count");

// ─── Bildirim: Okundu İşaretleme ──────────────────────────────────────────
function markRead(el) {
  if (!el.classList.contains("unread")) return;
  el.classList.remove("unread");
  el.style.background = "#ffffff";

  // Okunmamış sayısını güncelle
  const badge = document.getElementById("notif-count-badge");
  const dot   = document.getElementById("notif-dot");
  if (badge) {
    const current = parseInt(badge.textContent) || 0;
    const newCount = Math.max(0, current - 1);
    badge.textContent = newCount;
    if (newCount === 0) {
      badge.style.display = "none";
      if (dot) dot.style.display = "none";
    }
  }
}


// ─── Bildirim Paneline Yeni Bildirim Ekle ─────────────────────────────────
function addNotification(ticket, type = "ticket") {
  const list  = document.getElementById("notif-list");
  const badge = document.getElementById("notif-count-badge");
  const dot   = document.getElementById("notif-dot");
  if (!list) return;

  // Zaman etiketi
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const timeStr = `Bugün ${pad(now.getHours())}:${pad(now.getMinutes())}`;

  // İkon ve başlık seçimi
  let icon  = "🎫";
  let title = `Yeni Destek Talebi #${ticket.id}`;
  let desc  = ticket.problem_description
    ? ticket.problem_description.substring(0, 60) + (ticket.problem_description.length > 60 ? "..." : "")
    : "Yeni ticket oluşturuldu.";

  if (type === "auto") {
    icon  = "🤖";
    title = `Otomatik Ticket #${ticket.id} Oluşturuldu`;
  }

  // Bildirim elementi
  const el = document.createElement("div");
  el.className = "notif-item unread";
  el.setAttribute("onclick", "markRead(this)");
  el.style.cssText = [
    "padding:12px 18px",
    "border-bottom:1px solid #f1f5f9",
    "cursor:pointer",
    "background:#eff6ff",
    "transition:background 0.2s",
    "display:flex",
    "gap:12px",
    "align-items:flex-start",
    "animation:slideInRight 0.3s ease",
  ].join(";");

  el.innerHTML = `
    <span style="font-size:20px;margin-top:2px;">${icon}</span>
    <div>
      <div style="font-size:13px;font-weight:600;color:#1a202c;">${title}</div>
      <div style="font-size:12px;color:#718096;margin-top:2px;">${desc}</div>
      <div style="font-size:11px;color:#a0aec0;margin-top:3px;">${timeStr}</div>
    </div>
  `;

  // En üste ekle
  list.insertBefore(el, list.firstChild);

  // Sayacı artır
  if (badge) {
    const current = parseInt(badge.textContent) || 0;
    badge.textContent = current + 1;
    badge.style.display = "";
  }
  if (dot) dot.style.display = "";

  // Çanı hafifçe salla (animasyon)
  const bellIcon = document.querySelector("#notif-btn .bi-bell-fill");
  if (bellIcon) {
    bellIcon.style.animation = "none";
    bellIcon.offsetHeight; // reflow
    bellIcon.style.animation = "bell-shake 0.5s ease";
  }
}

// ─── Sayfa Yüklenince Gerçek Bildirimleri Çek ────────────────────────────
async function initNotifications() {
  const list    = document.getElementById("notif-list");
  const badge   = document.getElementById("notif-count-badge");
  const dot     = document.getElementById("notif-dot");
  const loading = document.getElementById("notif-loading");
  if (!list) return;

  try {
    const resp = await fetch("/chatbot/tickets");
    if (!resp.ok) throw new Error("API yanıt vermedi");
    const data = await resp.json();

    const tickets = data.tickets || [];

    // Yükleniyor yazısını kaldır
    if (loading) loading.remove();

    if (tickets.length === 0) {
      list.innerHTML = `
        <div style="padding:24px; text-align:center; color:#a0aec0; font-size:13px;">
          <div style="font-size:28px; margin-bottom:8px;">🔔</div>
          Henüz bildirim yok.
        </div>`;
      if (badge) { badge.textContent = "0"; badge.style.display = "none"; }
      if (dot)   dot.style.display = "none";
      return;
    }

    // En son 5 ticketı göster (en yeniden eskiye)
    const recent = tickets.slice().reverse().slice(0, 5);
    const openCount = recent.filter(t => t.status === "Açık").length;

    recent.forEach(ticket => {
      const isOpen   = ticket.status === "Açık";
      const icon     = isOpen ? "🎫" : "✅";
      const bg       = isOpen ? "#eff6ff" : "#f8fafc";
      const descText = (ticket.problem_description || "Ticket oluşturuldu.")
                       .substring(0, 55) + (ticket.problem_description?.length > 55 ? "…" : "");

      const el = document.createElement("div");
      el.className = isOpen ? "notif-item unread" : "notif-item";
      el.setAttribute("onclick", "markRead(this)");
      el.style.cssText = [
        "padding:12px 18px",
        "border-bottom:1px solid #f1f5f9",
        "cursor:pointer",
        `background:${bg}`,
        "transition:background 0.2s",
        "display:flex",
        "gap:12px",
        "align-items:flex-start",
      ].join(";");

      el.innerHTML = `
        <span style="font-size:20px;margin-top:2px;">${icon}</span>
        <div>
          <div style="font-size:13px;font-weight:600;color:#1a202c;">
            ${isOpen ? "Açık" : "Çözüldü"} Destek Talebi #${ticket.id}
          </div>
          <div style="font-size:12px;color:#718096;margin-top:2px;">${escapeHtml(descText)}</div>
          <div style="font-size:11px;color:#a0aec0;margin-top:3px;">${ticket.date_created || ""}</div>
        </div>`;

      list.appendChild(el);
    });

    // Badge güncelle
    if (badge) {
      badge.textContent = openCount;
      badge.style.display = openCount > 0 ? "" : "none";
    }
    if (dot) dot.style.display = openCount > 0 ? "" : "none";

  } catch (e) {
    if (loading) loading.innerHTML = `<div style="padding:16px;text-align:center;color:#a0aec0;font-size:12px;">Bildirimler yüklenemedi.</div>`;
    console.warn("Bildirim yükleme hatası:", e);
  }
}

// Sayfa yüklenince bildirimleri çek
document.addEventListener("DOMContentLoaded", initNotifications);

// ─── Saat Güncelleyici ────────────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById("current-time");
  if (!el) return;
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  el.textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}
setInterval(updateClock, 1000);
updateClock();

// ─── Toast Bildirimi ──────────────────────────────────────────────────────
function showToast(message, type = "success") {
  const container =
    document.querySelector(".toast-container-custom") ||
    (() => {
      const c = document.createElement("div");
      c.className = "toast-container-custom";
      document.body.appendChild(c);
      return c;
    })();

  const icons = { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" };
  const toast = document.createElement("div");
  toast.className = `toast-item ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || "ℹ️"}</span>
    <span class="toast-message">${message}</span>
    <span class="toast-close" onclick="this.parentElement.remove()">✕</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(20px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 350);
  }, 4500);
}

// ─── Mesaj Ekleme ─────────────────────────────────────────────────────────
function appendMessage(role, text, timestamp = null) {
  if (!chatMessages) return;

  const now = timestamp || new Date();
  const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(
    now.getMinutes()
  ).padStart(2, "0")}`;

  const isUser = role === "user";
  const avatarClass = isUser ? "user" : "ai";
  const avatarIcon  = isUser ? "👤" : "🤖";
  const bubbleClass = isUser ? "user" : "ai";
  const alignment   = isUser ? "user" : "";

  // Metni HTML olarak güvenli şekilde göster (satır sonlarını koru)
  const safeText = escapeHtml(text).replace(/\n/g, "<br>");

  const wrapper = document.createElement("div");
  wrapper.className = `message-wrapper ${alignment}`;
  wrapper.innerHTML = `
    <div class="message-avatar ${avatarClass}">${avatarIcon}</div>
    <div>
      <div class="message-bubble ${bubbleClass}">${safeText}</div>
      <div class="message-time">${timeStr}</div>
    </div>
  `;

  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return wrapper;
}

// ─── "Yazıyor..." Göstergesi ──────────────────────────────────────────────
function showTypingIndicator() {
  if (!chatMessages) return null;
  const wrapper = document.createElement("div");
  wrapper.className = "message-wrapper";
  wrapper.id = "typing-indicator";
  wrapper.innerHTML = `
    <div class="message-avatar ai">🤖</div>
    <div class="typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return wrapper;
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

// ─── Mesaj Gönderme ───────────────────────────────────────────────────────
async function sendMessage() {
  if (!chatInput || !sendBtn) return;

  const text = chatInput.value.trim();
  if (!text) return;

  // Kullanıcı mesajını ekle
  appendMessage("user", text);
  conversationHistory.push({ role: "user", content: text });

  chatInput.value = "";
  chatInput.style.height = "auto";
  sendBtn.disabled = true;

  const typingEl = showTypingIndicator();

  try {
    const response = await fetch("/chatbot/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: conversationHistory.slice(-10), // Son 10 mesaj bağlamı
      }),
    });

    const data = await response.json();

    removeTypingIndicator();

    if (data.success || data.response) {
      appendMessage("assistant", data.response);
      conversationHistory.push({ role: "assistant", content: data.response });

      // Otomatik ticket oluşturuldu mu?
      if (data.ticket_created && data.ticket) {
        showToast(
          `🎫 Destek talebi #${data.ticket.id} otomatik oluşturuldu.`,
          "warning"
        );
        addTicketToTable(data.ticket);
        updateTicketCount();
      }
    } else {
      appendMessage(
        "assistant",
        data.response || "⚠️ Yanıt alınamadı. Lütfen tekrar deneyin."
      );
    }
  } catch (error) {
    removeTypingIndicator();
    appendMessage(
      "assistant",
      "⚠️ Sunucu bağlantısı kesildi. Sayfayı yenileyip tekrar deneyiniz."
    );
    console.error("Chat API hatası:", error);
  } finally {
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

// ─── Manuel Ticket Oluşturma ──────────────────────────────────────────────
async function openTicket() {
  if (!ticketBtn) return;

  // Son kullanıcı mesajını al
  const lastUserMsg =
    conversationHistory
      .filter((m) => m.role === "user")
      .pop()?.content || "";

  const description =
    lastUserMsg ||
    prompt("Lütfen sorun açıklamasını girin:") ||
    "Manuel destek talebi";

  if (!description) return;

  ticketBtn.disabled = true;
  ticketBtn.textContent = "Oluşturuluyor...";

  try {
    const response = await fetch("/chatbot/create-ticket", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        description: description,
        user_message: lastUserMsg,
      }),
    });

    const data = await response.json();

    if (data.success) {
      showToast(`🎫 ${data.message}`, "success");
      appendMessage(
        "assistant",
        `✅ Destek talebiniz #${data.ticket.id} numarası ile oluşturuldu. Teknik ekibimiz en kısa sürede sizinle iletişime geçecektir.`
      );
      addTicketToTable(data.ticket);
      updateTicketCount();
    } else {
      showToast("❌ Ticket oluşturulamadı: " + data.error, "error");
    }
  } catch (error) {
    showToast("❌ Sunucu hatası. Lütfen tekrar deneyin.", "error");
    console.error("Ticket oluşturma hatası:", error);
  } finally {
    ticketBtn.disabled = false;
    ticketBtn.innerHTML = '🎫 Destek Talebi (Ticket) Aç';
  }
}

// ─── Ticket Tablosuna Satır Ekleme ────────────────────────────────────────
function addTicketToTable(ticket) {
  if (!ticketListBody) return;

  // "Kayıt yok" satırını kaldır
  const emptyRow = ticketListBody.querySelector(".empty-row");
  if (emptyRow) emptyRow.remove();

  const tr = document.createElement("tr");
  tr.id = `ticket-row-${ticket.id}`;
  tr.innerHTML = `
    <td><span class="fw-bold text-primary">#${ticket.id}</span></td>
    <td>${escapeHtml(ticket.problem_description.substring(0, 80))}${
    ticket.problem_description.length > 80 ? "..." : ""
  }</td>
    <td>${ticket.date_created}</td>
    <td>
      <span class="ticket-status-badge ticket-status-${
        ticket.status === "Açık" ? "open" : "closed"
      }">
        ${ticket.status === "Açık" ? "🔴" : "✅"} ${ticket.status}
      </span>
    </td>
    <td>
      <button 
        class="btn-danger-modern" 
        onclick="closeTicket(${ticket.id})"
        id="close-btn-${ticket.id}"
      >
        ✓ Kapat
      </button>
    </td>
  `;

  // En üste ekle
  ticketListBody.insertBefore(tr, ticketListBody.firstChild);

  // Bildirim çanına da ekle
  const isAuto = ticket.problem_description && ticket.problem_description.startsWith("Otomatik");
  addNotification(ticket, isAuto ? "auto" : "ticket");
}

// ─── Ticket Kapatma ───────────────────────────────────────────────────────
async function closeTicket(ticketId) {
  const btn = document.getElementById(`close-btn-${ticketId}`);
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Kapatılıyor...";
  }

  try {
    const response = await fetch(`/chatbot/ticket/${ticketId}/close`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    const data = await response.json();

    if (data.success) {
      // Satırdaki durum badge'ini güncelle
      const row = document.getElementById(`ticket-row-${ticketId}`);
      if (row) {
        const badge = row.querySelector(".ticket-status-badge");
        if (badge) {
          badge.className = "ticket-status-badge ticket-status-closed";
          badge.textContent = "✅ Çözüldü";
        }
        if (btn) {
          btn.disabled = true;
          btn.textContent = "Kapalı";
          btn.style.opacity = "0.5";
        }
      }
      showToast(`Ticket #${ticketId} çözüldü olarak işaretlendi.`, "success");
      updateTicketCount();
    } else {
      showToast("❌ Ticket kapatılamadı.", "error");
      if (btn) { btn.disabled = false; btn.textContent = "✓ Kapat"; }
    }
  } catch (error) {
    showToast("❌ Sunucu hatası.", "error");
    if (btn) { btn.disabled = false; btn.textContent = "✓ Kapat"; }
  }
}

// ─── Ticket Sayısı Güncelleyici ───────────────────────────────────────────
async function updateTicketCount() {
  try {
    const response = await fetch("/chatbot/tickets");
    const data = await response.json();
    if (ticketCount && data.success) {
      ticketCount.textContent = data.open_count;
    }
  } catch (_) {}
}

// ─── Textarea Otomatik Boyut ───────────────────────────────────────────────
function autoResizeTextarea(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 100) + "px";
}

// ─── No-Show Risk Bar Animasyonu ──────────────────────────────────────────
function animateRiskBars() {
  document.querySelectorAll(".risk-bar[data-width]").forEach((bar) => {
    const width = bar.getAttribute("data-width");
    setTimeout(() => {
      bar.style.width = width + "%";
    }, 200);
  });
}

// ─── HTML Escape Yardımcısı ───────────────────────────────────────────────
function escapeHtml(text) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

// ─── Olay Dinleyicileri ───────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Chatbot olayları
  if (sendBtn) {
    sendBtn.addEventListener("click", sendMessage);
  }

  if (chatInput) {
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    chatInput.addEventListener("input", () => autoResizeTextarea(chatInput));
  }

  if (ticketBtn) {
    ticketBtn.addEventListener("click", openTicket);
  }

  // Risk bar animasyonları
  animateRiskBars();

  // Topbar saati başlat
  updateClock();

  // Ticket sayısını güncelle (chatbot sayfasındaysa)
  if (ticketCount) {
    updateTicketCount();
    // Her 30 saniyede bir güncelle
    setInterval(updateTicketCount, 30000);
  }

  // Animasyon sınıfı uygula
  document.querySelectorAll(".animate-in").forEach((el, i) => {
    el.style.animationDelay = `${i * 0.08}s`;
  });
});
