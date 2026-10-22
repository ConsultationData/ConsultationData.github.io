const menuBtn = document.querySelector('.menu-toggle');
const nav = document.querySelector('.nav-links');

if (menuBtn && nav) {
  menuBtn.addEventListener('click', () => nav.classList.toggle('open'));
}

document.querySelectorAll('.nav-links a').forEach(a => {
  a.addEventListener('click', () => nav?.classList.remove('open'));
});

const yearEl = document.getElementById('year');
if (yearEl) {
  yearEl.textContent = new Date().getFullYear();
}

let currentLanguage = 'fr';

const budgetState = {
  currency: 'CAD',
  rate: 1,
  countryCode: 'CA'
};

const aboutVideo = document.getElementById('about-video');

function updateAboutVideo(lang) {
  if (!aboutVideo) return;

  const targetSrc = lang === 'en'
    ? 'Consultation_Data_Presentation_EN.mp4'
    : 'Consultation_Data_Presentation_FR.mp4';

  const currentFile = (aboutVideo.currentSrc || aboutVideo.getAttribute('src') || '').split('/').pop();

  if (currentFile === targetSrc) return;

  const previousTime = Number.isFinite(aboutVideo.currentTime) ? aboutVideo.currentTime : 0;
  const wasPlaying = !aboutVideo.paused && !aboutVideo.ended;

  aboutVideo.src = targetSrc;
  aboutVideo.load();

  aboutVideo.addEventListener('loadedmetadata', () => {
    if (previousTime > 0 && previousTime < aboutVideo.duration) {
      aboutVideo.currentTime = previousTime;
    }

    if (wasPlaying) {
      aboutVideo.muted = true;
      aboutVideo.play().catch(() => {});
    }
  }, { once: true });
}

function formatMoney(cadAmount, currency, rate, lang) {
  const locale = lang === 'fr' ? 'fr-CA' : 'en-CA';
  const amount = cadAmount * rate;

  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      maximumFractionDigits: 0
    }).format(amount);
  } catch (error) {
    return `${Math.round(amount).toLocaleString(locale)} ${currency}`;
  }
}

function renderBudgetOptions(lang = currentLanguage) {
  const budget = document.getElementById('budget');
  const note = document.getElementById('budget-currency-note');
  if (!budget) return;

  const currency = budgetState.currency || 'CAD';
  const rate = Number.isFinite(budgetState.rate) && budgetState.rate > 0
    ? budgetState.rate
    : 1;

  const low = formatMoney(2500, currency, rate, lang);
  const high = formatMoney(5000, currency, rate, lang);

  const labels = lang === 'fr'
    ? {
        placeholder: 'Veuillez sélectionner',
        under: `Moins de ${low}`,
        mid: `${low} à ${high}`,
        high: `${high} et plus`,
        discuss: 'À discuter'
      }
    : {
        placeholder: 'Please select',
        under: `Under ${low}`,
        mid: `${low}–${high}`,
        high: `${high}+`,
        discuss: 'To be discussed'
      };

  [...budget.options].forEach(option => {
    const key = option.dataset.budgetKey;

    if (key && labels[key]) {
      option.textContent = labels[key];
    }

    // The submitted value always keeps CAD as the contractual reference.
    if (key === 'under') {
      option.value = currency === 'CAD'
        ? 'Moins de 2 500 CAD'
        : `Moins de 2 500 CAD (≈ ${low})`;
    }

    if (key === 'mid') {
      option.value = currency === 'CAD'
        ? '2 500 à 5 000 CAD'
        : `2 500 à 5 000 CAD (≈ ${low} à ${high})`;
    }

    if (key === 'high') {
      option.value = currency === 'CAD'
        ? '5 000 CAD et plus'
        : `5 000 CAD et plus (≈ ${high}+)`;
    }

    if (key === 'discuss') {
      option.value = lang === 'fr' ? 'À discuter' : 'To be discussed';
    }
  });

  if (note) {
    if (currency === 'CAD') {
      note.textContent = lang === 'fr'
        ? 'Montants de référence en CAD.'
        : 'Reference amounts shown in CAD.';
    } else {
      note.textContent = lang === 'fr'
        ? `Montants affichés approximativement en ${currency} selon votre pays. La tarification finale demeure établie en CAD.`
        : `Amounts are shown approximately in ${currency} based on your country. Final pricing remains established in CAD.`;
    }
  }
}

function setLanguage(lang) {
  currentLanguage = lang === 'en' ? 'en' : 'fr';
  document.documentElement.lang = currentLanguage;

  document.querySelectorAll('[data-fr][data-en]').forEach(el => {
    el.textContent = el.dataset[currentLanguage];
  });

  document.querySelectorAll('[data-placeholder-fr][data-placeholder-en]').forEach(el => {
    el.placeholder = currentLanguage === 'fr'
      ? el.dataset.placeholderFr
      : el.dataset.placeholderEn;
  });

  const portfolioImage = document.getElementById('portfolio-image');

  if (portfolioImage) {
    if (currentLanguage === 'en') {
      portfolioImage.src = 'realisations_futuristes_en.png';
      portfolioImage.alt = 'Business Intelligence project portfolio';
    } else {
      portfolioImage.src = 'realisations_futuristes.png';
      portfolioImage.alt = 'Portfolio de réalisations en Business Intelligence';
    }
  }

  updateAboutVideo(currentLanguage);

  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === currentLanguage);
  });

  if (menuBtn) {
    menuBtn.setAttribute(
      'aria-label',
      currentLanguage === 'fr' ? 'Ouvrir le menu' : 'Open menu'
    );
  }

  renderBudgetOptions(currentLanguage);
  localStorage.setItem('consultationDataLanguage', currentLanguage);
}

async function fetchJsonWithTimeout(url, timeoutMs = 4500) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

function currencyFromBrowserLocale() {
  const locale = navigator.language || '';
  const region = (locale.split('-')[1] || '').toUpperCase();

  const fallbackMap = {
    CA: 'CAD',
    US: 'USD',
    GB: 'GBP',
    FR: 'EUR',
    DE: 'EUR',
    ES: 'EUR',
    IT: 'EUR',
    BE: 'EUR',
    NL: 'EUR',
    IE: 'EUR',
    PT: 'EUR',
    AT: 'EUR',
    FI: 'EUR',
    GR: 'EUR',
    LU: 'EUR',
    CH: 'CHF',
    AU: 'AUD',
    NZ: 'NZD',
    JP: 'JPY'
  };

  return fallbackMap[region] || 'CAD';
}

async function getCadRate(currency) {
  if (!currency || currency === 'CAD') return 1;

  try {
    const target = currency.toLowerCase();
    const data = await fetchJsonWithTimeout(
      `https://api.frankfurter.dev/v2/rate/cad/${target}`
    );

    const rate = Number(data?.rate);

    if (Number.isFinite(rate) && rate > 0) {
      return rate;
    }
  } catch (error) {
    // Fallback to CAD below.
  }

  return null;
}

async function detectBudgetCurrency() {
  let currency = currencyFromBrowserLocale();
  let countryCode = '';

  try {
    const location = await fetchJsonWithTimeout('https://ipapi.co/json/');

    if (
      typeof location?.currency === 'string' &&
      /^[A-Z]{3}$/.test(location.currency)
    ) {
      currency = location.currency;
    }

    if (typeof location?.country_code === 'string') {
      countryCode = location.country_code.toUpperCase();
    }
  } catch (error) {
    // Browser locale remains the fallback.
  }

  const rate = await getCadRate(currency);

  if (!rate) {
    budgetState.currency = 'CAD';
    budgetState.rate = 1;
    budgetState.countryCode = 'CA';
  } else {
    budgetState.currency = currency;
    budgetState.rate = rate;
    budgetState.countryCode = countryCode || '';
  }

  renderBudgetOptions(currentLanguage);
}

function setupAboutVideo() {
  const aboutSection = document.getElementById('apropos');
  const video = document.getElementById('about-video');

  if (!aboutSection || !video) return;

  video.muted = true;
  video.defaultMuted = true;

  if (!('IntersectionObserver' in window)) {
    return;
  }

  let hasStarted = false;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting && entry.intersectionRatio >= 0.30) {
        if (video.ended) {
          video.currentTime = 0;
        }

        video.muted = true;

        const playPromise = video.play();

        if (playPromise && typeof playPromise.catch === 'function') {
          playPromise.catch(() => {
            // Controls remain available if autoplay is blocked.
          });
        }

        hasStarted = true;
      } else if (hasStarted && !video.paused) {
        video.pause();
      }
    });
  }, {
    threshold: [0, 0.30, 0.60]
  });

  observer.observe(aboutSection);
}

document.querySelectorAll('.lang-btn').forEach(btn => {
  btn.addEventListener('click', () => setLanguage(btn.dataset.lang));
});

const savedLanguage = localStorage.getItem('consultationDataLanguage');
setLanguage(savedLanguage === 'en' ? 'en' : 'fr');

setupAboutVideo();
detectBudgetCurrency();
