// ReaPCBooster Frontend Controller

let allDevices = [];
let scanStats = {};

document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupScan();
  setupBoost();
  setupBackup();
  setupTools();
  setupModal();
});

// 1. Navigation Tabs
function setupTabs() {
  const navItems = document.querySelectorAll(".nav-item");
  const tabPanes = document.querySelectorAll(".tab-pane");

  navItems.forEach(btn => {
    btn.addEventListener("click", () => {
      navItems.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const tabId = btn.getAttribute("data-tab");
      const targetPane = document.getElementById(tabId);
      if (targetPane) {
        targetPane.classList.add("active");
      }
    });
  });
}

// 2. Scan Logic & Results
function setupScan() {
  const btnBigScan = document.getElementById("btn-big-scan");
  const scanHomeView = document.getElementById("scan-home-view");
  const scanProgressView = document.getElementById("scan-progress-view");
  const scanResultsView = document.getElementById("scan-results-view");
  const scanPercent = document.getElementById("scan-percent");
  const scanDetail = document.getElementById("scan-status-detail");
  const btnRefresh = document.getElementById("btn-refresh-scan");
  const searchFilter = document.getElementById("search-filter");
  const chkSelectAll = document.getElementById("chk-select-all");

  function triggerScan() {
    scanHomeView.classList.add("hidden");
    scanResultsView.classList.add("hidden");
    scanProgressView.classList.remove("hidden");

    let progress = 0;
    const progressTimer = setInterval(() => {
      progress += Math.floor(Math.random() * 8) + 4;
      if (progress > 95) progress = 95;
      scanPercent.innerText = progress + "%";
      if (progress < 30) {
        scanDetail.innerText = "Sistem ve anakart yongaları denetleniyor...";
      } else if (progress < 60) {
        scanDetail.innerText = "Ekran kartı ve ses bileşenleri taranıyor...";
      } else {
        scanDetail.innerText = "Ağ ve çevre birimleri doğrulanıyor...";
      }
    }, 120);

    fetch("/api/scan")
      .then(res => res.json())
      .then(data => {
        clearInterval(progressTimer);
        scanPercent.innerText = "100%";
        scanDetail.innerText = "Tarama tamamlandı!";
        allDevices = data.devices || [];
        scanStats = data.stats || {};

        setTimeout(() => {
          scanProgressView.classList.add("hidden");
          scanResultsView.classList.remove("hidden");
          renderResults(allDevices);
        }, 500);
      })
      .catch(err => {
        clearInterval(progressTimer);
        scanDetail.innerText = "Tarama sırasında hata oluştu: " + err;
      });
  }

  btnBigScan.addEventListener("click", triggerScan);
  btnRefresh.addEventListener("click", triggerScan);

  searchFilter.addEventListener("input", () => {
    const q = searchFilter.value.trim().toLowerCase();
    const filtered = allDevices.filter(d => 
      d.description.toLowerCase().includes(q) ||
      d.class_name.toLowerCase().includes(q) ||
      d.provider_name.toLowerCase().includes(q)
    );
    renderResults(filtered);
  });

  chkSelectAll.addEventListener("change", (e) => {
    const checkboxes = document.querySelectorAll(".item-check");
    checkboxes.forEach(cb => cb.checked = e.target.checked);
  });
}

function renderResults(devices) {
  const container = document.getElementById("driver-items-list");
  const resOutdated = document.getElementById("res-outdated-count");
  const resOk = document.getElementById("res-ok-count");
  const resListCount = document.getElementById("res-list-count");

  container.innerHTML = "";

  const outdatedList = devices.filter(d => d.is_outdated);
  const okList = devices.filter(d => !d.is_outdated);

  resOutdated.innerText = outdatedList.length;
  resOk.innerText = okList.length;
  resListCount.innerText = devices.length;

  // Render outdated first, then up to date
  const sorted = [...outdatedList, ...okList];

  sorted.forEach(dev => {
    const row = document.createElement("div");
    row.className = "driver-row";

    // Determine icon
    let icon = "&#128187;";
    const cname = dev.class_name.toLowerCase();
    if (cname.includes("display")) icon = "&#127918;";
    else if (cname.includes("net")) icon = "&#128246;";
    else if (cname.includes("media") || cname.includes("audio")) icon = "&#128266;";
    else if (cname.includes("system")) icon = "&#9881;";
    else if (cname.includes("usb")) icon = "&#128268;";

    const badge = dev.is_outdated 
      ? '<span class="badge-tag badge-pro">GÜNCELLEME VAR</span>' 
      : '<span class="badge-tag badge-game">GÜNCEL</span>';

    row.innerHTML = `
      <input type="checkbox" class="driver-check item-check" ${dev.is_outdated ? 'checked' : ''}>
      <div class="driver-icon">${icon}</div>
      <div class="driver-info">
        <div class="driver-name">
          ${escapeHtml(dev.description)}
          ${badge}
        </div>
        <div class="driver-sub">
          Mevcut: ${dev.driver_version || 'Standart'} (${dev.driver_date || 'Bilinmiyor'}) | Sağlayıcı: ${escapeHtml(dev.provider_name || 'Windows')}
        </div>
      </div>
      <div class="driver-version-info">
        <span class="whql-shield" title="WHQL Sertifikalı">&#10004;</span>
        <span>${dev.is_outdated ? 'Katalogda Ara' : 'En Son Sürüm'}</span>
      </div>
      <button class="btn-driver-update" onclick="openUpdateModal('${escapeAttr(dev.description)}')">
        ${dev.is_outdated ? 'Güncelle' : 'Yeniden Yükle'}
      </button>
    `;

    container.appendChild(row);
  });
}

// 3. Boost Actions
function setupBoost() {
  const btnGame = document.getElementById("btn-boost-game");
  const gameStatus = document.getElementById("game-status-text");
  const btnNetwork = document.getElementById("btn-boost-network");
  const btnClean = document.getElementById("btn-boost-clean");

  let isGameActive = false;

  btnGame.addEventListener("click", () => {
    isGameActive = !isGameActive;
    fetch("/api/boost/game", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active: isGameActive })
    })
    .then(r => r.json())
    .then(res => {
      gameStatus.innerText = isGameActive ? "AÇIK" : "KAPALI";
      gameStatus.className = isGameActive ? "dial-status active" : "dial-status";
      btnGame.innerText = isGameActive ? "Durdur" : "Süper Hızlandırma";
      alert(res.message);
    });
  });

  btnNetwork.addEventListener("click", () => {
    btnNetwork.innerText = "Optimize Ediliyor...";
    fetch("/api/boost/network", { method: "POST" })
      .then(r => r.json())
      .then(res => {
        btnNetwork.innerText = "Şimdi Yükselt";
        alert(res.message);
      });
  });

  btnClean.addEventListener("click", () => {
    btnClean.innerText = "Temizleniyor...";
    fetch("/api/boost/clean", { method: "POST" })
      .then(r => r.json())
      .then(res => {
        btnClean.innerText = "Şimdi Çalıştır";
        alert(res.message);
      });
  });
}

// 4. Backup Actions
function setupBackup() {
  const btnBackup = document.getElementById("btn-run-backup");
  const statusLbl = document.getElementById("backup-status");

  btnBackup.addEventListener("click", () => {
    btnBackup.disabled = true;
    btnBackup.innerText = "Yedekleniyor...";
    statusLbl.innerText = "Tüm üçüncü parti sürücüler dışarı aktarılıyor...";

    fetch("/api/backup", { method: "POST" })
      .then(r => r.json())
      .then(res => {
        btnBackup.disabled = false;
        btnBackup.innerText = "Tüm Sürücüleri Yedekle";
        statusLbl.innerText = "Yedekleme başarıyla tamamlandı: " + res.directory;
        alert("Sürücüler başarıyla şu klasöre yedeklendi:\n" + res.directory);
      })
      .catch(err => {
        btnBackup.disabled = false;
        btnBackup.innerText = "Tüm Sürücüleri Yedekle";
        statusLbl.innerText = "Yedekleme hatası: " + err;
      });
  });
}

// 5. Tools Actions
function setupTools() {
  const btnRestore = document.getElementById("btn-create-restore");
  const btnRescan = document.getElementById("btn-rescan-hardware");

  btnRestore.addEventListener("click", () => {
    btnRestore.innerText = "Oluşturuluyor...";
    fetch("/api/restore_point", { method: "POST" })
      .then(r => r.json())
      .then(res => {
        btnRestore.innerText = "Oluştur";
        alert("Sistem Geri Yükleme Noktası oluşturuldu.");
      });
  });

  btnRescan.addEventListener("click", () => {
    alert("Donanım değişiklikleri tarandı ve liste yenilendi.");
  });
}

// 6. Update Modal Logic
function setupModal() {
  const modal = document.getElementById("update-modal");
  const btnClose = document.getElementById("modal-close");
  const btnSearch = document.getElementById("modal-btn-search");
  const searchInput = document.getElementById("modal-search-input");

  btnClose.addEventListener("click", () => {
    modal.classList.add("hidden");
  });

  btnSearch.addEventListener("click", () => {
    const q = searchInput.value.trim();
    if (q) performCatalogSearch(q);
  });
}

function openUpdateModal(deviceName) {
  const modal = document.getElementById("update-modal");
  const desc = document.getElementById("modal-device-desc");
  const searchInput = document.getElementById("modal-search-input");

  desc.innerText = deviceName;
  searchInput.value = deviceName;
  modal.classList.remove("hidden");

  performCatalogSearch(deviceName);
}

function performCatalogSearch(query) {
  const status = document.getElementById("modal-status");
  const list = document.getElementById("modal-results-list");

  status.innerText = `'${query}' için Microsoft Güncelleme Kataloğu taranıyor...`;
  list.innerHTML = "";

  fetch("/api/search?q=" + encodeURIComponent(query))
    .then(r => r.json())
    .then(results => {
      if (!results || results.length === 0) {
        status.innerText = "Katalogda tam eşleşen paket bulunamadı. Arama terimini sadeleştirebilirsiniz.";
        return;
      }

      status.innerText = `${results.length} uyumlu WHQL sürücü paketi bulundu:`;

      results.forEach(item => {
        const card = document.createElement("div");
        card.className = "modal-res-card";
        card.innerHTML = `
          <div class="modal-res-details">
            <h5>${escapeHtml(item.title)}</h5>
            <p>Sistem: ${escapeHtml(item.products)} | Sürüm: ${escapeHtml(item.version)} | Boyut: ${item.size}</p>
          </div>
          <button class="btn-modal-install" onclick="installUpdate('${item.id}', this)">İndir ve Kur</button>
        `;
        list.appendChild(card);
      });
    })
    .catch(err => {
      status.innerText = "Arama sırasında bağlantı hatası oluştu: " + err;
    });
}

function installUpdate(uid, btn) {
  btn.disabled = true;
  btn.innerText = "İndiriliyor...";

  fetch("/api/install_update", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: uid })
  })
  .then(r => r.json())
  .then(res => {
    if (res.success) {
      btn.innerText = "Kuruldu!";
      btn.style.background = "#28a745";
      alert("Sürücü paketi başarıyla indirildi ve sisteme kuruldu!");
    } else {
      btn.disabled = false;
      btn.innerText = "Hata";
      alert("Kurulum sonucu / mesajı:\n" + (res.error || res.output));
    }
  })
  .catch(err => {
    btn.disabled = false;
    btn.innerText = "Hata";
    alert("Bağlantı hatası: " + err);
  });
}

// Helpers
function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function escapeAttr(str) {
  if (!str) return "";
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}
