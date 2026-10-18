
const state = {
  lang: localStorage.getItem('consultationDataLanguage') === 'en' ? 'en' : 'fr',
  theme: 'all',
  subject: 'all',
  page: 1,
  perPage: 9,
  articles: []
};

const labels = {
  fr: {
    all:'Tous',
    themes:['Langage de programmation','Visualisation de données','Analyse de données'],
    subjects:['R','Power BI','Power Query'],
    articleCount:n => `${n} article${n>1?'s':''}`,
    dateLocale:'fr-CA'
  },
  en: {
    all:'All',
    themes:['Programming language','Data visualization','Data analysis'],
    subjects:['R','Power BI','Power Query'],
    articleCount:n => `${n} article${n>1?'s':''}`,
    dateLocale:'en-CA'
  }
};

const themeMap = {
  fr: {'Préparation des données':'Préparation des données','Analyse de données':'Analyse de données','Tableaux de bord':'Tableaux de bord','Formation':'Formation'},
  en: {'Data preparation':'Data preparation','Data analysis':'Data analysis','Dashboards':'Dashboards','Training':'Training'}
};

function normalizeClass(value){
  return 'subject-' + value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
}

function setLanguage(lang){
  state.lang = lang;
  state.theme = 'all';
  state.subject = 'all';
  state.page = 1;
  localStorage.setItem('consultationDataLanguage', lang);
  document.documentElement.lang = lang;
  document.querySelectorAll('[data-fr][data-en]').forEach(el => el.textContent = el.dataset[lang]);
  document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.lang === lang));
  renderFilters();
  renderArticles();
}

function renderFilters(){
  const l = labels[state.lang];
  const themeEl = document.getElementById('themeFilters');
  const subjectEl = document.getElementById('subjectFilters');

  const themes = [l.all, ...l.themes];
  const subjects = [l.all, ...l.subjects];

  themeEl.innerHTML = themes.map((x,i)=>`<button class="filter-btn ${((i===0&&state.theme==='all')||state.theme===x)?'active':''}" data-theme="${i===0?'all':x}">${x}</button>`).join('');
  subjectEl.innerHTML = subjects.map((x,i)=>`<button class="filter-btn ${((i===0&&state.subject==='all')||state.subject===x)?'active':''}" data-subject="${i===0?'all':x}">${x}</button>`).join('');

  themeEl.querySelectorAll('button').forEach(btn=>btn.addEventListener('click',()=>{state.theme=btn.dataset.theme;state.page=1;renderFilters();renderArticles();}));
  subjectEl.querySelectorAll('button').forEach(btn=>btn.addEventListener('click',()=>{state.subject=btn.dataset.subject;state.page=1;renderFilters();renderArticles();}));
}

function translatedTheme(a){
  if(state.lang==='fr') {
    const map={
      'Programming language':'Langage de programmation',
      'Data visualization':'Visualisation de données',
      'Data analysis':'Analyse de données'
    };
    return map[a.theme] || a.theme;
  }
  const map={
    'Langage de programmation':'Programming language',
    'Visualisation de données':'Data visualization',
    'Analyse de données':'Data analysis'
  };
  return map[a.theme] || a.theme;
}

function translatedSubject(a){
  return a.subject;
}

function filteredArticles(){
  return state.articles
    .filter(a=>a.lang===state.lang)
    .filter(a=>state.theme==='all' || translatedTheme(a)===state.theme)
    .filter(a=>state.subject==='all' || translatedSubject(a)===state.subject)
    .sort((a,b)=>new Date(b.date)-new Date(a.date));
}

function renderArticles(){
  const all = filteredArticles();
  const maxPage = Math.max(1, Math.ceil(all.length/state.perPage));
  if(state.page>maxPage) state.page=maxPage;
  const start=(state.page-1)*state.perPage;
  const rows=all.slice(start,start+state.perPage);
  const grid=document.getElementById('articlesGrid');
  const empty=document.getElementById('emptyState');
  document.getElementById('articleCount').textContent=labels[state.lang].articleCount(all.length);

  grid.innerHTML=rows.map(a=>{
    const subject=translatedSubject(a);
    const theme=translatedTheme(a);
    const formatted=new Intl.DateTimeFormat(labels[state.lang].dateLocale,{year:'numeric',month:'long',day:'numeric'}).format(new Date(a.date+'T12:00:00'));
    return `<article class="article-card">
      <a class="article-link" href="${a.url}" target="_blank" rel="noopener">
        <div class="article-thumb ${normalizeClass(subject)}"><strong>${subject}</strong></div>
        <div class="article-body">
          <span class="article-source">${a.source}</span>
          <h2 class="article-title">${a.title}</h2>
          <span class="article-date">${formatted}</span>
          <p class="article-excerpt">${a.excerpt || ''}</p>
          <div class="article-tags"><span class="article-tag">${theme}</span><span class="article-tag">${subject}</span></div>
        </div>
      </a>
    </article>`;
  }).join('');

  empty.hidden=rows.length!==0;
  renderPagination(maxPage);
}

function renderPagination(maxPage){
  const p=document.getElementById('pagination');
  let html=`<button class="page-btn" data-go="${state.page-1}" ${state.page===1?'disabled':''}>‹</button>`;
  for(let i=1;i<=maxPage;i++) html+=`<button class="page-btn ${i===state.page?'active':''}" data-go="${i}">${i}</button>`;
  html+=`<button class="page-btn" data-go="${state.page+1}" ${state.page===maxPage?'disabled':''}>›</button>`;
  p.innerHTML=html;
  p.querySelectorAll('[data-go]').forEach(btn=>btn.addEventListener('click',()=>{
    const target=Number(btn.dataset.go);
    if(target>=1&&target<=maxPage){state.page=target;renderArticles();window.scrollTo({top:document.querySelector('.blog-listing').offsetTop-80,behavior:'smooth'});}
  }));
}

document.querySelector('.menu-toggle')?.addEventListener('click',()=>document.querySelector('.nav-links')?.classList.toggle('open'));
document.querySelectorAll('.lang-btn').forEach(btn=>btn.addEventListener('click',()=>setLanguage(btn.dataset.lang)));
document.getElementById('year').textContent=new Date().getFullYear();

fetch('blog-data.json',{cache:'no-store'})
  .then(r=>r.json())
  .then(data=>{state.articles=data.articles||[];setLanguage(state.lang);})
  .catch(()=>{state.articles=[];setLanguage(state.lang);});
