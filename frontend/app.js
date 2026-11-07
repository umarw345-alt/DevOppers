const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const resumeDropzone = $('#resumeDropzone');
const resumeInput = $('#resumeInput');
const resumeFile = $('#resumeFile');
const resumeBrowse = $('#resumeBrowse');
const reviewPanel = $('#reviewPanel');
const sharePanel = $('#sharePanel');
const toast = $('#toast');
let toastTimer;

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
}

function markResumeReady(fileName = 'Jordan-Lee-Resume.pdf') {
  resumeFile.querySelector('strong').textContent = fileName;
  resumeFile.classList.remove('hidden');
  resumeDropzone.classList.add('ready');
  $('#completionValue').textContent = '60';
  showToast('Resume uploaded — ready to scan.');
  setTimeout(() => startScan(), 500);
}

function startScan() {
  const copy = $('.upload-copy');
  const original = copy.innerHTML;
  copy.innerHTML = '<strong>Scanning your resume…</strong><span>Finding the details that make you, you.</span><small class="scan-progress">0%</small>';
  let progress = 0;
  const timer = setInterval(() => {
    progress += 20;
    copy.querySelector('.scan-progress').textContent = `${progress}% complete`;
    if (progress >= 100) {
      clearInterval(timer);
      copy.innerHTML = original;
      reviewPanel.classList.remove('hidden');
      $('#completionValue').textContent = '80';
      showToast('Scan complete — review your profile details.');
    }
  }, 220);
}

resumeBrowse.addEventListener('click', (event) => { event.stopPropagation(); resumeInput.click(); });
resumeDropzone.addEventListener('click', (event) => { if (!event.target.closest('button')) resumeInput.click(); });
resumeDropzone.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') resumeInput.click(); });
resumeInput.addEventListener('change', () => { if (resumeInput.files[0]) markResumeReady(resumeInput.files[0].name); });

['dragenter', 'dragover'].forEach((eventName) => resumeDropzone.addEventListener(eventName, (event) => { event.preventDefault(); resumeDropzone.classList.add('dragging'); }));
['dragleave', 'drop'].forEach((eventName) => resumeDropzone.addEventListener(eventName, (event) => { event.preventDefault(); resumeDropzone.classList.remove('dragging'); }));
resumeDropzone.addEventListener('drop', (event) => { const file = event.dataTransfer.files[0]; if (file) markResumeReady(file.name); });

$('.remove-file').addEventListener('click', (event) => { event.stopPropagation(); resumeFile.classList.add('hidden'); reviewPanel.classList.add('hidden'); resumeInput.value = ''; $('#completionValue').textContent = '40'; showToast('Resume removed.'); });

const photoInput = $('#photoInput');
$('#photoBrowse').addEventListener('click', () => photoInput.click());
$('#photoDropzone').addEventListener('click', (event) => { if (!event.target.closest('button')) photoInput.click(); });
photoInput.addEventListener('change', () => {
  const file = photoInput.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => { $('#photoPlaceholder').style.backgroundImage = `url(${reader.result})`; $('#photoPlaceholder').style.backgroundSize = 'cover'; $('#photoPlaceholder').textContent = ''; $('#cardAvatar').style.backgroundImage = `url(${reader.result})`; $('#cardAvatar').style.backgroundSize = 'cover'; $('#cardAvatar').textContent = ''; };
  reader.readAsDataURL(file);
  showToast('Profile photo added.');
});

$('#continueButton').addEventListener('click', () => { sharePanel.classList.remove('hidden'); sharePanel.scrollIntoView({ behavior: 'smooth', block: 'center' }); $('#completionValue').textContent = '100'; showToast('Your portable card is ready to share.'); });

const themeNames = { navy: 'Midnight navy', coral: 'Sunset coral', lime: 'Fieldwork green', paper: 'Warm paper' };
$$('.theme-swatch').forEach((swatch) => swatch.addEventListener('click', () => { $$('.theme-swatch').forEach((item) => item.classList.remove('active')); swatch.classList.add('active'); $('#walletCard').className = `wallet-card theme-${swatch.dataset.theme}`; $('#themeName').textContent = themeNames[swatch.dataset.theme]; }));

const cardSwitch = $$('.preview-switch').find((button) => button.textContent.trim() === 'Card');
$('#portfolioSwitch').addEventListener('click', () => { $('#cardPreviewWrap').classList.add('hidden'); $('#portfolioPreview').classList.remove('hidden'); $$('.preview-switch').forEach((item) => item.classList.remove('active')); $('#portfolioSwitch').classList.add('active'); $('#captionText').textContent = 'Your public portfolio — no login or app download required.'; });
cardSwitch.addEventListener('click', () => { $('#cardPreviewWrap').classList.remove('hidden'); $('#portfolioPreview').classList.add('hidden'); $$('.preview-switch').forEach((item) => item.classList.remove('active')); cardSwitch.classList.add('active'); $('#captionText').textContent = 'This is what recruiters see when they scan your pass.'; });

$('#copyLink').addEventListener('click', async () => { try { await navigator.clipboard.writeText('https://jordanlee.dev/portfolio'); } catch {} showToast('Portfolio link copied to clipboard.'); });
$$('.wallet-button').forEach((button) => button.addEventListener('click', () => showToast('Wallet integration is ready for the backend pass service.')));
