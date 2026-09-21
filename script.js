const menuBtn = document.querySelector('.menu-toggle');
const nav = document.querySelector('.nav-links');

if (menuBtn && nav) {
  menuBtn.addEventListener('click', () => nav.classList.toggle('open'));
}

document.querySelectorAll('.nav-links a').forEach(a => {
  a.addEventListener('click', () => nav?.classList.remove('open'));
});

document.getElementById('year').textContent = new Date().getFullYear();

function setLanguage(lang) {
  document.documentElement.lang = lang;

  document.querySelectorAll('[data-fr][data-en]').forEach(el => {
    el.textContent = el.dataset[lang];
  });

  document.querySelectorAll('[data-placeholder-fr][data-placeholder-en]').forEach(el => {
    el.placeholder = lang === 'fr' ? el.dataset.placeholderFr : el.dataset.placeholderEn;
  });
  const portfolioImage = document.getElementById('portfolio-image');
  if (portfolioImage) {
    if (lang === 'en') {
      portfolioImage.src = 'realisations_futuristes_en.png';
      portfolioImage.alt = 'Business Intelligence project portfolio';
    } else {
      portfolioImage.src = 'realisations_futuristes.png';
      portfolioImage.alt = 'Portfolio de réalisations en Business Intelligence';
    }
  }

  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });

  const menuLabel = lang === 'fr' ? 'Ouvrir le menu' : 'Open menu';
  if (menuBtn) menuBtn.setAttribute('aria-label', menuLabel);

  localStorage.setItem('consultationDataLanguage', lang);
}

document.querySelectorAll('.lang-btn').forEach(btn => {
  btn.addEventListener('click', () => setLanguage(btn.dataset.lang));
});

const savedLanguage = localStorage.getItem('consultationDataLanguage');
setLanguage(savedLanguage === 'en' ? 'en' : 'fr');