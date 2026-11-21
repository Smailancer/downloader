(() => {
  "use strict";

  /* ---------------- text (English / Arabic) */
  const T = {
    en: {
      headline: "Drop a link.<br>Keep the video.",
      lede: "TikTok, Instagram, YouTube, X, Facebook, Reddit and more. No account needed.",
      label: "Video link", placeholder: "https://…", paste: "Paste", go: "Get video",
      quality: "Quality", audio: "Audio (MP3)", another: "Download another video",
      howTitle: "Faster on your phone",
      how1: "Install this app: in Chrome, open the menu and tap “Install app”.",
      how2: "In TikTok, Instagram or X, tap Share on any video.",
      how3: "Pick “Downloader” from the list. The video opens here, ready to save.",
      install: "Install app",
      foot: "Download only videos you own or have permission to save.",
      reading: "Reading the link…", noUrl: "Paste a link that starts with https://",
      pasteDenied: "Your browser blocked pasting. Long-press the box and choose Paste.",
      download: q => `Download ${q}`, queued: "Waiting for a free slot…",
      preparing: p => `Preparing… ${p}%`, saveFile: size => `Save file${size ? ` (${size})` : ""}`,
      saved: "Saved. Check your Downloads.", network: "No connection to the server. Check your internet and try again.",
      errors: {
        bad_url: "Paste a link that starts with https://",
        unsupported: "This site isn't supported. Try a link from YouTube, TikTok, Instagram, X, Facebook or Reddit.",
        login: "This video is private or needs a login, so it can't be downloaded.",
        gone: "This video isn't available anymore. Check the link.",
        too_big: "This video is too large for the server (limit 700 MB).",
        too_long: "This video is too long (limit 2 hours).",
        no_video: "This post has no video.",
        bot_check: "YouTube is asking this server to prove it isn't a bot. Try again later.",
        blocked: "This site is blocking the server right now. Try again later.",
        short_link: "This is a short share link the server couldn't open. Open it in your browser, copy the full address, and paste that here.",
        busy: "The server is busy. Try again in a minute.",
        expired: "This download expired. Start it again.",
        failed: "Couldn't read this link. Check that it opens in your browser, then try again.",
      },
      by: "by",
    },
    ar: {
      headline: "ألصِق الرابط.<br>احتفظ بالفيديو.",
      lede: "تيك توك، إنستغرام، يوتيوب، إكس، فيسبوك، ريديت وغيرها. بلا حساب.",
      label: "رابط الفيديو", placeholder: "https://…", paste: "لصق", go: "جلب الفيديو",
      quality: "الجودة", audio: "صوت فقط (MP3)", another: "تحميل فيديو آخر",
      howTitle: "أسرع على هاتفك",
      how1: "ثبّت التطبيق: من قائمة Chrome اختر «تثبيت التطبيق».",
      how2: "في تيك توك أو إنستغرام أو إكس، اضغط «مشاركة» على أي فيديو.",
      how3: "اختر «Downloader» من القائمة، فيُفتح الفيديو هنا جاهزًا للحفظ.",
      install: "تثبيت التطبيق",
      foot: "حمّل فقط الفيديوهات التي تملكها أو لديك إذن بحفظها.",
      reading: "جارٍ قراءة الرابط…", noUrl: "ألصِق رابطًا يبدأ بـ https://",
      pasteDenied: "المتصفح منع اللصق. اضغط مطولًا على الخانة واختر «لصق».",
      download: q => `تحميل ${q}`, queued: "في انتظار دور شاغر…",
      preparing: p => `جارٍ التجهيز… ${p}%`, saveFile: size => `حفظ الملف${size ? ` (${size})` : ""}`,
      saved: "تم الحفظ. تفقّد مجلد التنزيلات.", network: "تعذّر الاتصال بالخادم. تحقّق من الإنترنت وأعد المحاولة.",
      errors: {
        bad_url: "ألصِق رابطًا يبدأ بـ https://",
        unsupported: "هذا الموقع غير مدعوم. جرّب رابطًا من يوتيوب أو تيك توك أو إنستغرام أو إكس أو فيسبوك أو ريديت.",
        login: "هذا الفيديو خاص أو يتطلب تسجيل الدخول، لذا لا يمكن تحميله.",
        gone: "هذا الفيديو لم يعد متاحًا. تحقّق من الرابط.",
        too_big: "حجم الفيديو أكبر من حدّ الخادم (700 ميغابايت).",
        too_long: "الفيديو أطول من الحد المسموح (ساعتان).",
        no_video: "هذا المنشور لا يحتوي على فيديو.",
        bot_check: "يوتيوب يطلب من الخادم إثبات أنه ليس روبوتًا. أعد المحاولة لاحقًا.",
        blocked: "هذا الموقع يحجب الخادم حاليًا. أعد المحاولة لاحقًا.",
        short_link: "هذا رابط مشاركة مختصر لم يستطع الخادم فتحه. افتحه في المتصفح، وانسخ العنوان الكامل، ثم ألصقه هنا.",
        busy: "الخادم مشغول. أعد المحاولة بعد دقيقة.",
        expired: "انتهت صلاحية هذا التحميل. ابدأه من جديد.",
        failed: "تعذّرت قراءة الرابط. تأكّد أنه يفتح في متصفحك ثم أعد المحاولة.",
      },
      by: "بواسطة",
    },
  };

  const $ = id => document.getElementById(id);
  const form = $("form"), input = $("url"), msg = $("msg"), goBtn = $("goBtn");
  const sheet = $("sheet"), chips = $("chips"), saveBtn = $("saveBtn"), saveLabel = $("saveLabel"), barFill = $("barFill");

  let lang = localStore("lang") || ((navigator.language || "en").startsWith("ar") ? "ar" : "en");
  let current = null;      // video info
  let job = null;          // { id, timer }

  function localStore(key, value) {
    try {
      if (value === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, value);
    } catch { return null; }
  }

  function t(key, ...args) {
    const v = T[lang][key];
    return typeof v === "function" ? v(...args) : v;
  }

  function applyLang() {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.querySelectorAll("[data-i18n]").forEach(el => {
      const key = el.dataset.i18n;
      if (key === "headline") el.innerHTML = t(key); else el.textContent = t(key);
    });
    input.placeholder = t("placeholder");
    $("langBtn").textContent = lang === "ar" ? "English" : "عربي";
    if (current) {
      $("uploader").textContent = current.uploader ? `${t("by")} ${current.uploader}` : "";
      renderChips(); resetSave();
    }
    if (msg.classList.contains("error")) say("");
  }

  $("langBtn").addEventListener("click", () => {
    lang = lang === "ar" ? "en" : "ar";
    localStore("lang", lang);
    applyLang();
  });

  /* ---------------- helpers */
  function say(text, isError = false) {
    msg.textContent = text || "";
    msg.classList.toggle("error", isError);
  }

  function extractUrl(text) {
    const m = (text || "").match(/https?:\/\/[^\s]+/);
    return m ? m[0].replace(/[.,;)!"']+$/, "") : "";
  }

  function fmtDuration(s) {
    if (!s) return "";
    s = Math.round(s);
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = String(s % 60).padStart(2, "0");
    return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
  }

  function fmtSize(b) {
    if (!b) return "";
    return b > 1e9 ? `${(b / 1e9).toFixed(1)} GB` : `${Math.max(1, Math.round(b / 1e6))} MB`;
  }

  function errText(code) {
    return T[lang].errors[code] || T[lang].errors.failed;
  }

  async function api(path, opts) {
    let res;
    try { res = await fetch(path, opts); } catch { throw new Error(t("network")); }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      if (data.detail) console.warn("[downloader]", data.error, data.detail);
      throw new Error(errText(data.error));
    }
    return data;
  }

  /* ---------------- step 1: read the link */
  async function lookup(raw) {
    const url = extractUrl(raw);
    if (!url) { say(t("noUrl"), true); input.focus(); return; }
    input.value = url;
    stopJob();
    sheet.hidden = true;
    goBtn.setAttribute("aria-busy", "true");
    goBtn.disabled = true;
    say(t("reading"));
    try {
      current = await api(`/api/info?url=${encodeURIComponent(url)}`);
      say("");
      render();
    } catch (e) {
      say(e.message, true);
    } finally {
      goBtn.removeAttribute("aria-busy");
      goBtn.disabled = false;
    }
  }

  function render() {
    $("thumb").src = current.thumbnail || "";
    $("thumb").alt = current.title;
    $("dur").textContent = fmtDuration(current.duration);
    $("platform").textContent = current.platform;
    $("title").textContent = current.title;
    $("uploader").textContent = current.uploader ? `${t("by")} ${current.uploader}` : "";
    renderChips();
    resetSave();
    sheet.hidden = false;
    sheet.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  }

  function renderChips() {
    const options = [...(current.qualities || []).map(q => ({ v: String(q), label: `${q}p` })), { v: "audio", label: t("audio") }];
    const preferred = options.find(o => o.v === "720") || options[0];
    const checked = chips.querySelector("input:checked")?.value || preferred.v;
    chips.replaceChildren(...options.map(o => {
      const label = document.createElement("label");
      label.className = "chip";
      const radio = Object.assign(document.createElement("input"), { type: "radio", name: "q", value: o.v, checked: o.v === checked });
      radio.addEventListener("change", resetSave);
      const span = document.createElement("span");
      span.textContent = o.label;
      label.append(radio, span);
      return label;
    }));
  }

  function selectedQuality() {
    const v = chips.querySelector("input:checked")?.value || "720";
    return { v, label: v === "audio" ? "MP3" : `${v}p` };
  }

  /* ---------------- step 2: prepare + save */
  function resetSave() {
    if (job) return;
    saveBtn.className = "save";
    saveBtn.disabled = false;
    barFill.style.width = "0";
    saveLabel.textContent = t("download", selectedQuality().label);
    saveBtn.onclick = startJob;
  }

  async function startJob() {
    const q = selectedQuality();
    saveBtn.className = "save working";
    saveBtn.disabled = true;
    saveLabel.textContent = t("queued");
    try {
      const { id } = await api("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: current.url, quality: q.v }),
      });
      job = { id };
      poll();
    } catch (e) {
      job = null;
      say(e.message, true);
      resetSave();
    }
  }

  async function poll() {
    if (!job) return;
    try {
      const s = await api(`/api/jobs/${job.id}`);
      if (s.status === "done") return finish(s);
      if (s.status === "error") {
        if (s.detail) console.warn("[downloader]", s.error, s.detail);
        throw new Error(errText(s.error));
      }
      barFill.style.width = `${s.progress || 0}%`;
      saveLabel.textContent = s.status === "queued" ? t("queued") : t("preparing", s.progress || 0);
      job.timer = setTimeout(poll, 1000);
    } catch (e) {
      job = null;
      say(e.message, true);
      resetSave();
    }
  }

  function finish(s) {
    const fileUrl = `/api/jobs/${job.id}/file`;
    job = null;
    barFill.style.width = "100%";
    saveBtn.className = "save ready";
    saveBtn.disabled = false;
    saveLabel.textContent = t("saveFile", fmtSize(s.size));
    const download = () => {
      const a = Object.assign(document.createElement("a"), { href: fileUrl, download: s.filename || "" });
      document.body.append(a); a.click(); a.remove();
      say(t("saved"));
    };
    saveBtn.onclick = download;
    download(); // start right away; the button stays as a fallback
  }

  function stopJob() {
    if (job?.timer) clearTimeout(job.timer);
    job = null;
  }

  /* ---------------- inputs */
  form.addEventListener("submit", e => { e.preventDefault(); lookup(input.value); });

  $("pasteBtn").addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) lookup(text); else input.focus();
    } catch {
      say(t("pasteDenied"), true);
      input.focus();
    }
  });

  $("againBtn").addEventListener("click", e => {
    e.preventDefault();
    stopJob();
    current = null;
    sheet.hidden = true;
    input.value = "";
    say("");
    window.scrollTo({ top: 0 });
    input.focus();
  });

  /* ---------------- PWA: install + share target */
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }

  let deferredPrompt = null;
  window.addEventListener("beforeinstallprompt", e => {
    e.preventDefault();
    deferredPrompt = e;
    $("installBtn").hidden = false;
  });
  $("installBtn").addEventListener("click", async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = null;
    $("installBtn").hidden = true;
  });

  applyLang();

  // Opened from the Android share sheet: /?url=…  or  /?text=Look+at+this+https://…
  const params = new URLSearchParams(location.search);
  const shared = params.get("url") || params.get("text") || params.get("title");
  if (shared) {
    history.replaceState(null, "", "/");
    lookup(shared);
  }
})();
