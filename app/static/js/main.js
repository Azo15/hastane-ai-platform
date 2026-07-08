/* ═══════════════════════════════════════════════════════════════════════════
   app/static/js/main.js
   Hastane AI Platformu — Chatbot AJAX ve Dinamik UI İşlemleri
   ═══════════════════════════════════════════════════════════════════════════ */

"use strict";

// ─── Global Sohbet Geçmişi ────────────────────────────────────────────────
window.currentConversationId = null;
let conversationHistory = [];

// ─── DOM Referansları ─────────────────────────────────────────────────────
const chatMessages   = document.getElementById("chat-messages");
const chatInput      = document.getElementById("chat-input");
const sendBtn        = document.getElementById("send-btn");
const ticketBtn      = document.getElementById("open-ticket-btn");
const ticketListBody = document.getElementById("ticket-list-body");
const ticketCount    = document.getElementById("ticket-count");

// ─── Bildirim Yardımcıları (Local Storage) ──────────────────────────────────
function getDismissedTickets() {
  try {
    return JSON.parse(localStorage.getItem("dismissed_tickets")) || [];
  } catch (e) {
    return [];
  }
}

function dismissNotification(ticketId, event) {
  if (event) event.stopPropagation();

  const dismissed = getDismissedTickets();
  if (!dismissed.includes(ticketId)) {
    dismissed.push(ticketId);
    localStorage.setItem("dismissed_tickets", JSON.stringify(dismissed));
  }

  // Animasyonla DOM'dan kaldır
  const el = document.getElementById(`notif-item-${ticketId}`);
  if (el) {
    el.style.opacity = "0";
    el.style.transform = "translateX(30px)";
    setTimeout(() => {
      el.remove();
      
      const list = document.getElementById("notif-list");
      if (list && list.querySelectorAll(".notif-item").length === 0) {
        list.innerHTML = `
          <div style="padding:28px 18px; text-align:center; color:#a0aec0; font-size:13px;">
            <div style="font-size:32px; margin-bottom:8px;"><i class="bi bi-bell-slash text-muted"></i></div>
            Henüz yeni bildirim yok.
          </div>`;
      }
    }, 300);
  }

  // Açık sayaç değerini azalt
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

  // "Kayıt yok" veya "yükleniyor" varsa temizle
  const emptyOrLoading = list.querySelector("div[style*='text-align:center']");
  if (emptyOrLoading) emptyOrLoading.remove();

  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const timeStr = `Bugün ${pad(now.getHours())}:${pad(now.getMinutes())}`;

  let icon  = '<i class="bi bi-ticket-perforated-fill text-primary" style="font-size:18px;"></i>';
  let title = `Talep #${ticket.id} (Açık)`;
  let desc  = ticket.problem_description
    ? ticket.problem_description.substring(0, 60) + (ticket.problem_description.length > 60 ? "..." : "")
    : "Yeni ticket oluşturuldu.";

  if (type === "auto") {
    icon  = '<i class="bi bi-robot text-primary" style="font-size:18px;"></i>';
    title = `Otomatik Talep #${ticket.id}`;
  }

  const el = document.createElement("div");
  el.id = `notif-item-${ticket.id}`;
  el.className = "notif-item unread";
  el.setAttribute("onclick", `showTicketDetails(${ticket.id})`);
  el.style.cssText = [
    "padding:12px 18px",
    "border-bottom:1px solid #f1f5f9",
    "background:#eff6ff",
    "transition:all 0.3s ease",
    "display:flex",
    "gap:12px",
    "align-items:flex-start",
    "cursor:pointer",
    "animation:slideInRight 0.3s ease",
  ].join(";");

  el.innerHTML = `
    <span style="display:inline-flex; align-items:center; margin-top:2px;">${icon}</span>
    <div style="min-width:0; flex:1;">
      <div style="font-size:13px;font-weight:600;color:#1a202c;">${title}</div>
      <div style="font-size:12px;color:#718096;margin-top:2px;
                  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
        ${escapeHtml(desc)}
      </div>
      <div style="font-size:11px;color:#a0aec0;margin-top:3px;display:flex;justify-content:space-between;align-items:center;">
        <span>${timeStr}</span>
        <button class="btn btn-sm p-0 text-primary fw-semibold" 
                onclick="dismissNotification(${ticket.id}, event)"
                style="font-size:11px;text-decoration:none;border:none;background:none;cursor:pointer;">
          Okundu İşaretle
        </button>
      </div>
    </div>
  `;

  list.insertBefore(el, list.firstChild);

  // Sayacı artır (Açık ticket ise)
  if (badge) {
    const current = parseInt(badge.textContent) || 0;
    badge.textContent = current + 1;
    badge.style.display = "";
  }
  if (dot) dot.style.display = "";

  const bellIcon = document.querySelector("#notif-btn .bi-bell-fill");
  if (bellIcon) {
    bellIcon.style.animation = "none";
    bellIcon.offsetHeight;
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

    // Detay modalında kullanmak üzere küresel değişkene kaydet
    window.allLoadedTickets = tickets;

    if (loading) loading.remove();

    const dismissed = getDismissedTickets();

    // Okunmuş olarak işaretlenmeyenleri filtrele
    const activeNotifications = tickets.filter(t => !dismissed.includes(t.id));

    if (activeNotifications.length === 0) {
      list.innerHTML = `
        <div style="padding:28px 18px; text-align:center; color:#a0aec0; font-size:13px;">
          <div style="font-size:32px; margin-bottom:8px;"><i class="bi bi-bell-slash text-muted"></i></div>
          Henüz yeni bildirim yok.
        </div>`;
      if (badge) badge.style.display = "none";
      if (dot)   dot.style.display   = "none";
      return;
    }

    list.innerHTML = "";

    // API'den gelen liste zaten azalan sırada (en yeni ilk). Sadece ilk 5'i alıyoruz.
    const recent = activeNotifications.slice(0, 5);
    const openCount = activeNotifications.filter(t => t.status === "Açık").length;

    recent.forEach(ticket => {
      const isOpen   = ticket.status === "Açık";
      const icon     = isOpen 
        ? '<i class="bi bi-ticket-perforated-fill text-primary" style="font-size:18px;"></i>' 
        : '<i class="bi bi-check-circle-fill text-success" style="font-size:18px;"></i>';
      const bg       = isOpen ? "#eff6ff" : "#f8fafc";
      const desc     = ticket.problem_description || "Destek talebi oluşturuldu.";
      const descShort = desc.length > 58 ? desc.substring(0, 58) + "…" : desc;

      const el = document.createElement("div");
      el.id = `notif-item-${ticket.id}`;
      el.className = isOpen ? "notif-item unread" : "notif-item";
      el.setAttribute("onclick", `showTicketDetails(${ticket.id})`);
      el.style.cssText = [
        "padding:12px 18px",
        "border-bottom:1px solid #f1f5f9",
        "background:" + bg,
        "transition:all 0.3s ease",
        "display:flex",
        "gap:12px",
        "align-items:flex-start",
        "cursor:pointer",
      ].join(";");

      el.innerHTML = `
        <span style="display:inline-flex; align-items:center; margin-top:2px;">${icon}</span>
        <div style="min-width:0; flex:1;">
          <div style="font-size:13px;font-weight:600;color:#1a202c;">
            Talep #${ticket.id} (${isOpen ? "Açık" : "Çözüldü"})
          </div>
          <div style="font-size:12px;color:#718096;margin-top:2px;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${escapeHtml(desc)}">
            ${escapeHtml(descShort)}
          </div>
          <div style="font-size:11px;color:#a0aec0;margin-top:3px;display:flex;justify-content:space-between;align-items:center;">
            <span>${ticket.date_created || ""}</span>
            <button class="btn btn-sm p-0 text-primary fw-semibold" 
                    onclick="dismissNotification(${ticket.id}, event)"
                    style="font-size:11px;text-decoration:none;border:none;background:none;cursor:pointer;">
              Okundu İşaretle
            </button>
          </div>
        </div>`;

      list.appendChild(el);
    });

    // Badge: toplam açık ticket sayısı
    if (badge) {
      badge.textContent  = totalOpen;
      badge.style.display = totalOpen > 0 ? "" : "none";
    }
    if (dot) dot.style.display = totalOpen > 0 ? "" : "none";

  } catch (e) {
    if (loading) loading.innerHTML =
      `<div style="padding:20px;text-align:center;color:#fc8181;font-size:12px;">
         ⚠️ Bildirimler yüklenemedi.
       </div>`;
    console.warn("Bildirim yükleme hatası:", e);
  }
}

// Sayfa yüklenince bildirimleri çek
document.addEventListener("DOMContentLoaded", initNotifications);

// ─── Destek Talebi Detay Modalı Gösterimi ──────────────────────────────────
async function showTicketDetails(ticketId) {
  let ticket = (window.allLoadedTickets || []).find(t => t.id === ticketId);

  // Küreselde yoksa sunucudan çek
  if (!ticket) {
    try {
      const resp = await fetch("/chatbot/tickets");
      if (resp.ok) {
        const data = await resp.json();
        window.allLoadedTickets = data.tickets || [];
        ticket = window.allLoadedTickets.find(t => t.id === ticketId);
      }
    } catch (e) {
      console.error("Talep detay yükleme hatası:", e);
    }
  }

  if (!ticket) {
    showToast("⚠️ Talebe ait detaylar bulunamadı.", "error");
    return;
  }

  // Modalı doldur
  document.getElementById("modal-ticket-id").textContent = `Talep #${ticket.id}`;
  
  const statusBadge = document.getElementById("modal-ticket-status");
  if (ticket.status === "Açık") {
    statusBadge.innerHTML = '<i class="bi bi-exclamation-circle-fill me-1"></i> Açık Destek Talebi';
    statusBadge.style.background = "#fee2e2";
    statusBadge.style.color = "#b91c1c";
  } else {
    statusBadge.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Çözüldü / Kapatıldı';
    statusBadge.style.background = "#dcfce7";
    statusBadge.style.color = "#15803d";
  }

  document.getElementById("modal-ticket-desc").textContent = ticket.problem_description || "Açıklama yok.";
  
  const userMsgContainer = document.getElementById("modal-user-msg-container");
  const userMsgEl = document.getElementById("modal-user-msg");
  if (ticket.user_message) {
    userMsgContainer.style.display = "block";
    userMsgEl.textContent = ticket.user_message;
  } else {
    userMsgContainer.style.display = "none";
  }

  const aiRespContainer = document.getElementById("modal-ai-resp-container");
  const aiRespEl = document.getElementById("modal-ai-resp");
  if (ticket.ai_response) {
    aiRespContainer.style.display = "block";
    aiRespEl.textContent = ticket.ai_response;
  } else {
    aiRespContainer.style.display = "none";
  }

  document.getElementById("modal-ticket-date").textContent = ticket.date_created || "";

  // Talebi Kapat butonu aksiyonu
  const actionBtn = document.getElementById("modal-ticket-action-btn");
  if (ticket.status === "Açık") {
    actionBtn.style.display = "block";
    actionBtn.onclick = async () => {
      actionBtn.disabled = true;
      actionBtn.textContent = "Kapatılıyor...";
      try {
        const resp = await fetch(`/chatbot/ticket/${ticket.id}/close`, { method: "POST" });
        const resData = await resp.json();
        if (resData.success) {
          statusBadge.textContent = "✅ Çözüldü / Kapatıldı";
          statusBadge.style.background = "#dcfce7";
          statusBadge.style.color = "#15803d";
          actionBtn.style.display = "none";
          showToast("✓ Destek talebi başarıyla kapatıldı.", "success");
          
          // Chatbot sayfasındaki tabloyu anlık güncelle
          const row = document.getElementById(`ticket-row-${ticket.id}`);
          if (row) {
            const tableBadge = row.querySelector(".ticket-status-badge");
            if (tableBadge) {
              tableBadge.className = "ticket-status-badge ticket-status-closed";
              tableBadge.innerHTML = "✅ Çözüldü";
            }
            const closeBtn = row.querySelector(".btn-danger-modern");
            if (closeBtn) closeBtn.replaceWith(document.createTextNode("—"));
          }
          
          // Bildirim panelini yenile
          initNotifications();
          
          // Sayfa sayacını güncelle (eğer chatbot sayfasındaysa)
          if (typeof updateTicketCount === "function") {
            updateTicketCount();
          }
        }
      } catch (err) {
        showToast("⚠️ İşlem sırasında bir hata oluştu.", "error");
        console.error(err);
      } finally {
        actionBtn.disabled = false;
        actionBtn.textContent = "✓ Talebi Kapat";
      }
    };
  } else {
    actionBtn.style.display = "none";
  }

  // Modalı göster
  const modalEl = document.getElementById("ticketDetailModal");
  const modal = new bootstrap.Modal(modalEl);
  modal.show();
}

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

  const icons = { 
    success: '<i class="bi bi-check-circle-fill text-success" style="font-size:16px;"></i>', 
    error: '<i class="bi bi-x-circle-fill text-danger" style="font-size:16px;"></i>', 
    warning: '<i class="bi bi-exclamation-triangle-fill text-warning" style="font-size:16px;"></i>', 
    info: '<i class="bi bi-info-circle-fill text-info" style="font-size:16px;"></i>' 
  };
  const toast = document.createElement("div");
  toast.className = `toast-item ${type}`;
  toast.innerHTML = `
    <span class="toast-icon" style="display:inline-flex; align-items:center; justify-content:center;">${icons[type] || ""}</span>
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
  const avatarIcon  = isUser 
    ? '<i class="bi bi-person-fill text-white" style="font-size: 14px;"></i>' 
    : '<i class="bi bi-robot text-white" style="font-size: 14px;"></i>';
  const bubbleClass = isUser ? "user" : "ai";
  const alignment   = isUser ? "user" : "";

  // Metni HTML olarak güvenli şekilde göster (satır sonlarını koru)
  const safeText = escapeHtml(text).replace(/\n/g, "<br>");

  const wrapper = document.createElement("div");
  wrapper.className = `message-wrapper ${alignment}`;
  wrapper.innerHTML = `
    <div class="message-avatar ${avatarClass}" style="display:inline-flex; align-items:center; justify-content:center;">${avatarIcon}</div>
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
    <div class="message-avatar ai" style="display:inline-flex; align-items:center; justify-content:center;">
      <i class="bi bi-robot text-white" style="font-size: 14px;"></i>
    </div>
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

      // Konuşmayı veritabanına otomatik kaydet/güncelle
      await autoSaveConversation();

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
    ticketBtn.innerHTML = '<i class="bi bi-ticket-perforated-fill me-1"></i> Destek Talebi Aç';
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
      }" style="display:inline-flex; align-items:center; gap:4px;">
        ${ticket.status === "Açık" 
          ? '<i class="bi bi-exclamation-circle-fill"></i>' 
          : '<i class="bi bi-check-circle-fill"></i>'} ${ticket.status}
      </span>
    </td>
    <td>
      <button 
        class="btn-danger-modern" 
        onclick="closeTicket(${ticket.id})"
        id="close-btn-${ticket.id}"
        style="display:inline-flex; align-items:center; gap:4px;"
      >
        <i class="bi bi-x-circle"></i> Kapat
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

// ─── No-Show Tahmin Sonucunu Dinamik Ekrana Yazma (AJAX) ───────────────────
function renderPredictionResult(res) {
  const container = document.getElementById("prediction-result-container");
  if (!container) return;

  let statusText = "";
  let statusIcon = "";
  if (res.risk_color === "success") {
    statusText = "Düşük No-Show Riski";
    statusIcon = '<i class="bi bi-check-circle-fill text-success"></i>';
  } else if (res.risk_color === "warning") {
    statusText = "Orta No-Show Riski";
    statusIcon = '<i class="bi bi-exclamation-triangle-fill text-warning"></i>';
  } else {
    statusText = "Yüksek No-Show Riski";
    statusIcon = '<i class="bi bi-exclamation-octagon-fill text-danger"></i>';
  }

  const predictionText = res.prediction === 1 ? "gelmeme" : "gelme";

  let suggestion = "";
  if (res.risk_color === "success") {
    suggestion = "Standart randevu sürecine devam edilebilir. Ek müdahale gerekmemektedir.";
  } else if (res.risk_color === "warning") {
    suggestion = "SMS hatırlatması yapılması ve randevu günü tekrar aranması önerilir.";
  } else {
    suggestion = "Randevu günü sabahı hasta aranmalı, alternatif slot planlanmalı ve randevu hatırlatma katmanı artırılmalıdır.";
  }

  container.innerHTML = `
    <div class="prediction-result-card ${res.risk_color} mb-4 animate-in" id="prediction-result" style="animation: slideInRight 0.3s ease;">
      <div class="d-flex align-items-center gap-4 flex-wrap">
        <!-- Risk Dairesi -->
        <div class="risk-score-circle ${res.risk_color}">
          <div class="risk-score-value">%${res.risk_score}</div>
          <div class="risk-score-unit">Risk</div>
        </div>

        <!-- Detaylar -->
        <div class="flex-grow-1">
          <h4 style="font-family:'Outfit',sans-serif; font-weight:700; margin-bottom:4px; display:flex; align-items:center; gap:6px;">
            ${statusIcon} ${statusText}
          </h4>
          <p style="font-size:13px; color:var(--text-secondary); margin-bottom:12px;">
            Tahmin: Bu hastanın randevuya <strong>${predictionText}</strong> olasılığı yüksektir.
            Risk Skoru: <strong>${res.risk_score}%</strong>
          </p>

          <!-- Risk Bar -->
          <div class="risk-bar-container" style="max-width:400px;">
            <div class="risk-bar ${res.risk_color}" style="width: ${res.risk_score}%; transition: width 0.8s cubic-bezier(0.1, 0.8, 0.25, 1);"></div>
          </div>

          <!-- Öneri -->
          <div class="mt-3 p-3 rounded-3" style="background: rgba(255,255,255,0.6); border: 1px solid rgba(0,0,0,0.08); font-size: 13px;">
            <i class="bi bi-lightbulb-fill text-warning me-1"></i> <strong>Öneri:</strong> ${suggestion}
          </div>
        </div>
      </div>
    </div>
  `;
}

// ─── Sohbet Geçmişini Sıfırlama (AJAX) ──────────────────────────────────────
function clearChat() {
  if (!confirm("Sohbet geçmişinizi temizlemek istediğinize emin misiniz?")) return;

  // 1. Dizi geçmişini temizle
  conversationHistory = [];

  // 2. DOM alanını temizle ve varsayılan karşılama mesajını ekle
  if (chatMessages) {
    chatMessages.innerHTML = `
      <div class="message-wrapper">
        <div class="message-avatar ai" style="display:inline-flex; align-items:center; justify-content:center;">
          <i class="bi bi-robot text-white" style="font-size: 14px;"></i>
        </div>
        <div>
          <div class="message-bubble ai">
            Merhaba! Ben Hastane IT Destek Asistanıyım.<br><br>
            Bilgisayar, yazıcı, internet, ağ veya <strong>HBYS</strong> ile ilgili 
            yaşadığınız sorunları benimle paylaşabilirsiniz. 
            Size en hızlı çözümü sunmaya çalışacağım.<br><br>
            Nasıl yardımcı olabilirim?
          </div>
          <div class="message-time">Şimdi</div>
        </div>
      </div>
    `;
  }

  showToast("Sohbet geçmişi sıfırlandı.", "success");
}

// ─── Yeni Sohbet Başlatma ───────────────────────────────────────────────────
function startNewChat() {
  window.currentConversationId = null;
  conversationHistory = [];
  
  if (chatMessages) {
    chatMessages.innerHTML = `
      <div class="message-wrapper">
        <div class="message-avatar ai" style="display:inline-flex; align-items:center; justify-content:center;">
          <i class="bi bi-robot text-white" style="font-size: 14px;"></i>
        </div>
        <div>
          <div class="message-bubble ai">
            Merhaba! Ben Hastane IT Destek Asistanıyım.<br><br>
            Bilgisayar, yazıcı, internet, ağ veya <strong>HBYS</strong> ile ilgili 
            yaşadığınız sorunları benimle paylaşabilirsiniz. 
            Size en hızlı çözümü sunmaya çalışacağım.<br><br>
            Nasıl yardımcı olabilirim?
          </div>
          <div class="message-time">Şimdi</div>
        </div>
      </div>
    `;
  }

  // Sol menüdeki aktif seçimi temizle
  document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
  
  if (chatInput) chatInput.focus();
}

// ─── Otomatik Sohbet Geçmişi Kaydı (AJAX) ──────────────────────────────────
async function autoSaveConversation() {
  if (conversationHistory.length === 0) return;
  try {
    const response = await fetch("/chatbot/conversation/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conversation_id: window.currentConversationId,
        messages: conversationHistory
      })
    });
    const data = await response.json();
    if (data.success) {
      const isNew = !window.currentConversationId;
      window.currentConversationId = data.conversation_id;
      
      // Sidebar listesini güncelle
      updateHistorySidebarUI(data.conversation_id, data.title, isNew);
    }
  } catch (e) {
    console.warn("Otomatik sohbet kaydı başarısız oldu:", e);
  }
}

// ─── Geçmiş Listesi Arayüzünü Güncelleme ─────────────────────────────────────
function updateHistorySidebarUI(id, title, isNew) {
  const list = document.getElementById("chat-history-list");
  if (!list) return;

  const noHistoryMsg = document.getElementById("no-history-msg");
  if (noHistoryMsg) noHistoryMsg.remove();

  if (isNew) {
    const div = document.createElement("div");
    div.className = "history-item active";
    div.id = `history-item-${id}`;
    div.setAttribute("onclick", `loadConversation(${id})`);
    div.innerHTML = `
      <span class="history-title" id="history-title-${id}">${escapeHtml(title)}</span>
      <button class="delete-history-btn" onclick="deleteConversation(${id}, event)">
        <i class="bi bi-x"></i>
      </button>
    `;
    list.insertBefore(div, list.firstChild);
  } else {
    const titleEl = document.getElementById(`history-title-${id}`);
    if (titleEl) {
      titleEl.textContent = title;
    }
    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
    const currentItem = document.getElementById(`history-item-${id}`);
    if (currentItem) {
      currentItem.classList.add("active");
    }
  }
}

// ─── Geçmiş Konuşmayı Yükleme ──────────────────────────────────────────────
async function loadConversation(id) {
  try {
    const resp = await fetch("/chatbot/conversations");
    const data = await resp.json();
    if (data.success) {
      const conv = data.conversations.find(c => c.id === id);
      if (conv) {
        window.currentConversationId = id;
        conversationHistory = conv.messages || [];

        if (chatMessages) {
          chatMessages.innerHTML = "";
          conversationHistory.forEach(msg => {
            appendMessage(msg.role === "user" ? "user" : "assistant", msg.content);
          });
        }

        document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
        const currentItem = document.getElementById(`history-item-${id}`);
        if (currentItem) {
          currentItem.classList.add("active");
        }
        showToast("Konuşma başarıyla yüklendi.", "success");
      }
    }
  } catch (error) {
    console.error("Konuşma yüklenirken hata:", error);
    showToast("Sohbet geçmişi yüklenemedi.", "error");
  }
}

// ─── Geçmiş Konuşmayı Silme ────────────────────────────────────────────────
async function deleteConversation(id, event) {
  if (event) event.stopPropagation();

  if (!confirm("Bu konuşmayı kalıcı olarak silmek istediğinize emin misiniz?")) return;

  try {
    const resp = await fetch(`/chatbot/conversation/${id}/delete`, {
      method: "DELETE"
    });
    const data = await resp.json();
    if (data.success) {
      const el = document.getElementById(`history-item-${id}`);
      if (el) el.remove();

      if (window.currentConversationId === id) {
        startNewChat();
      }

      const list = document.getElementById("chat-history-list");
      if (list && list.querySelectorAll(".history-item").length === 0) {
        list.innerHTML = `<div id="no-history-msg" style="font-size: 11px; color: var(--text-muted); text-align: center; padding-top: 20px;">Geçmiş yok.</div>`;
      }
      showToast("Sohbet silindi.", "success");
    }
  } catch (error) {
    console.error("Sohbet silinirken hata:", error);
    showToast("Sohbet silinemedi.", "error");
  }
}

// ─── Raporları PDF veya Excel (CSV) Olarak Çıkarma ─────────────────────────
function exportPDF() {
  window.print();
}

async function exportExcel() {
  try {
    const resp = await fetch("/chatbot/tickets");
    const data = await resp.json();
    if (!data.success || !data.tickets) {
      showToast("Talepler çekilirken hata oluştu.", "error");
      return;
    }

    const tickets = data.tickets;
    if (tickets.length === 0) {
      showToast("Dışa aktarılacak bilet verisi bulunmuyor.", "warning");
      return;
    }

    // CSV formatında oluştur
    let csvContent = "\ufeff"; // Türkçe karakterlerin Excel'de düzgün açılması için BOM
    csvContent += "Bilet ID,Problem Aciklamasi,Kullanici Mesaji,AI Cevabi,Olusturulma Tarihi,Durum\n";

    tickets.forEach(t => {
      const row = [
        t.id,
        `"${(t.problem_description || "").replace(/"/g, '""')}"`,
        `"${(t.user_message || "").replace(/"/g, '""')}"`,
        `"${(t.ai_response || "").replace(/"/g, '""')}"`,
        t.date_created || "",
        t.status || ""
      ].join(",");
      csvContent += row + "\n";
    });

    // İndirme işlemini tetikle
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", "hastane_it_destek_talepleri.csv");
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showToast("IT Destek biletleri başarıyla CSV formatında indirildi.", "success");
  } catch (error) {
    console.error("Dışa aktarma hatası:", error);
    showToast("Excel dosyası oluşturulurken hata oluştu.", "error");
  }
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

  // No-Show Tahmin Formunu AJAX ile gönderme
  const predictForm = document.getElementById("predict-form");
  if (predictForm) {
    predictForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const submitBtn = predictForm.querySelector("button[type='submit']");
      const origBtnText = submitBtn.innerHTML;
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Riski Tahmin Ediyor...';

      const formData = new FormData(predictForm);
      const data = {};
      formData.forEach((value, key) => {
        data[key] = value;
      });

      // Checkbox verilerini sıfır/bir yap (Flask'a uyumlu olması için)
      const checkboxes = ['hipertension', 'diabetes', 'alcoholism', 'handcap', 'sms_received'];
      checkboxes.forEach(cb => {
        data[cb] = formData.has(cb) ? parseInt(formData.get(cb)) : 0;
      });

      try {
        const response = await fetch("/no-show/predict", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data)
        });

        const res = await response.json();

        if (res && res.risk_score !== undefined) {
          renderPredictionResult(res);
          showToast("No-Show risk olasılığı hesaplandı.", "success");
        } else {
          showToast("Tahmin hesaplanırken hata oluştu.", "error");
        }
      } catch (error) {
        console.error("Tahmin Hatası:", error);
        showToast("Sunucuyla bağlantı kurulamadı.", "error");
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origBtnText;
      }
    });
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
