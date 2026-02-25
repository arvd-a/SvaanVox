// ═══════════════════════════════════════════════════════════════
// SvaanVox — Frontend Application Logic
// ═══════════════════════════════════════════════════════════════

let currentTab = 'home';
let libraryData = [];
let activeFilter = 'all';
let parsedScript = null;   // { parts: [{name, segments:[...]}] }
let bgmMap = {};            // { partIndex: bgmFilePath }
const audio = document.getElementById('audio-el');
const VOICES = [
    { id: "v2/en_speaker_0", name: "Aria (Female, Calm)" },
    { id: "v2/en_speaker_1", name: "Blake (Male, Deep)" },
    { id: "v2/en_speaker_2", name: "Clara (Female, Warm)" },
    { id: "v2/en_speaker_3", name: "Derek (Male, Strong)" },
    { id: "v2/en_speaker_4", name: "Elena (Female, Bright)" },
    { id: "v2/en_speaker_5", name: "Felix (Male, Friendly)" },
    { id: "v2/en_speaker_6", name: "Grace (Female, Neutral)" },
    { id: "v2/en_speaker_7", name: "Henry (Male, Narrator)" },
    { id: "v2/en_speaker_8", name: "Isla (Female, Soft)" },
    { id: "v2/en_speaker_9", name: "Jack (Male, Energetic)" },
];

// ── Tab switching ──
function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.nav-btn').forEach(b => { b.classList.remove('nav-active', 'text-gray-200'); b.classList.add('text-gray-400'); });
    const a = document.getElementById('tab-' + tab);
    if (a) { a.classList.add('nav-active', 'text-gray-200'); a.classList.remove('text-gray-400'); }

    ['view-home', 'view-create', 'view-timeline', 'view-library'].forEach(v => {
        const el = document.getElementById(v);
        el.classList.add('hidden'); el.classList.remove('flex');
    });

    if (tab === 'home') { show('view-home', 'flex'); }
    else if (tab === 'create') { show('view-create', 'flex'); }
    else if (tab === 'library') { document.getElementById('view-library').classList.remove('hidden'); loadLibrary(); }
}

function show(id, display = 'block') { const el = document.getElementById(id); el.classList.remove('hidden'); if (display === 'flex') el.classList.add('flex'); }

// ── Mode switch ──
function onModeChange() {
    const m = document.getElementById('input-mode').value;
    document.getElementById('tts-panel').classList.toggle('hidden', m === 'audiobook');
    document.getElementById('audiobook-panel').classList.toggle('hidden', m !== 'audiobook');
}
onModeChange();

// ── Char count ──
const textInput = document.getElementById('input-text');
if (textInput) textInput.addEventListener('input', function () { document.getElementById('char-count').textContent = this.value.length + ' characters'; });

// ── Drag & drop ──
const dropZone = document.getElementById('docx-drop');
if (dropZone) {
    dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', e => {
        e.preventDefault(); dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) { uploadDocxFile(e.dataTransfer.files[0]); }
    });
}

// ── DOCX Upload ──
function uploadDocx(input) { if (input.files.length) uploadDocxFile(input.files[0]); }

async function uploadDocxFile(file) {
    if (!file.name.toLowerCase().endsWith('.docx')) { alert('Please upload a .docx file'); return; }
    const fd = new FormData();
    fd.append('file', file);
    try {
        const res = await fetch('/upload-script', { method: 'POST', body: fd });
        const data = await res.json();
        if (data.error) { alert(data.error); return; }
        parsedScript = data;
        bgmMap = {};
        document.getElementById('docx-info').classList.remove('hidden');
        document.getElementById('docx-info').textContent = '✓ ' + file.name + ' — ' + data.parts.length + ' part(s) detected';
        document.getElementById('btn-gen-audiobook').classList.remove('hidden');
        renderTimeline();
        // Show timeline in workspace
        ['view-home', 'view-create', 'view-library'].forEach(v => { document.getElementById(v).classList.add('hidden'); document.getElementById(v).classList.remove('flex'); });
        show('view-timeline');
    } catch (e) { alert('Upload error: ' + e.message); }
}

// ── Render Timeline ──
function renderTimeline() {
    if (!parsedScript) return;
    const container = document.getElementById('timeline-parts');
    const typeColors = { title: 'border-l-golden bg-golden/5', dialogue: 'border-l-saffron bg-saffron/5', narrator: 'border-l-gray-500 bg-white/5', sfx: 'border-l-tri bg-tri/5' };
    const typeIcons = { title: '👑', dialogue: '💬', narrator: '📖', sfx: '🔊' };

    container.innerHTML = parsedScript.parts.map((part, pi) => {
        const segsHtml = part.segments.map((seg, si) => {
            const color = typeColors[seg.type] || typeColors.narrator;
            const icon = typeIcons[seg.type] || '📖';
            const voiceOpts = seg.type === 'sfx' ? '' : VOICES.map(v =>
                `<option value="${v.id}" ${v.id === seg.voice ? 'selected' : ''}>${v.name}</option>`
            ).join('');
            const voiceSelect = seg.type === 'sfx' ? `<span class="text-[10px] text-gray-600">auto</span>` :
                `<select onchange="updateSegVoice(${pi},${si},this.value)" class="bg-deep border border-border rounded px-1.5 py-0.5 text-[11px] text-gray-300 focus:outline-none">${voiceOpts}</select>`;

            return `<div class="seg-chip flex items-start gap-2 p-2.5 rounded-lg border-l-2 ${color} mb-1.5" data-pi="${pi}" data-si="${si}">
                <span class="text-sm mt-0.5">${icon}</span>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="text-[10px] font-bold uppercase tracking-wider ${seg.type === 'dialogue' ? 'text-saffron' : seg.type === 'title' ? 'text-golden' : seg.type === 'sfx' ? 'text-tri' : 'text-gray-500'}">${seg.type}</span>
                        ${seg.character ? `<span class="text-[10px] text-gray-400">— ${seg.character}</span>` : ''}
                        ${seg.emotion && seg.emotion !== 'neutral' ? `<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-white/5 text-gray-400">${seg.emotion}</span>` : ''}
                    </div>
                    <p class="text-xs text-gray-300 mt-1 leading-relaxed">${seg.text.length > 120 ? seg.text.slice(0, 120) + '…' : seg.text}</p>
                </div>
                <div class="flex-shrink-0">${voiceSelect}</div>
            </div>`;
        }).join('');

        const hasBgm = bgmMap[pi] ? true : false;
        return `<div class="part-card bg-card border border-border rounded-xl overflow-hidden fade-up" style="animation-delay:${pi * 80}ms">
            <div class="flex items-center justify-between px-4 py-3 bg-surface/50 border-b border-border cursor-pointer" onclick="togglePart(${pi})">
                <div class="flex items-center gap-2">
                    <svg class="w-4 h-4 text-saffron transition-transform part-chevron-${pi}" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7"/></svg>
                    <span class="text-sm font-bold text-gray-200">${part.name}</span>
                    <span class="text-[10px] text-gray-600">${part.segments.length} segments</span>
                </div>
                <div class="flex items-center gap-2">
                    ${hasBgm ? '<span class="text-[10px] text-tri font-medium">🎵 BGM set</span>' : ''}
                    <label class="flex items-center gap-1 cursor-pointer" onclick="event.stopPropagation()">
                        <span class="text-[10px] text-gray-500">🎵 BGM</span>
                        <input type="file" accept=".wav" class="hidden" onchange="uploadBgm(${pi},this)"/>
                        <button onclick="event.stopPropagation(); this.previousElementSibling.click()" class="text-[10px] px-2 py-1 rounded bg-white/5 text-gray-400 hover:bg-white/10 hover:text-saffron transition-colors">Add</button>
                    </label>
                </div>
            </div>
            <div class="part-body-${pi} p-3 space-y-0">${segsHtml}</div>
        </div>`;
    }).join('');
}

function togglePart(pi) {
    const body = document.querySelector('.part-body-' + pi);
    const chevron = document.querySelector('.part-chevron-' + pi);
    if (body) { body.classList.toggle('hidden'); }
    if (chevron) { chevron.classList.toggle('rotate-180'); }
}

function updateSegVoice(pi, si, voice) {
    if (parsedScript && parsedScript.parts[pi] && parsedScript.parts[pi].segments[si]) {
        parsedScript.parts[pi].segments[si].voice = voice;
    }
}

// ── BGM Upload per part ──
async function uploadBgm(partIndex, input) {
    if (!input.files.length) return;
    const fd = new FormData();
    fd.append('file', input.files[0]);
    try {
        const res = await fetch('/upload-music', { method: 'POST', body: fd });
        const data = await res.json();
        if (data.error) { alert(data.error); return; }
        bgmMap[partIndex] = data.path;
        renderTimeline();
    } catch (e) { alert('BGM upload error: ' + e.message); }
}

// ── Generate Audiobook ──
async function generateAudiobook() {
    if (!parsedScript) { alert('Please upload a script first.'); return; }
    const btn = document.getElementById('btn-gen-audiobook');
    btn.disabled = true; btn.classList.add('opacity-50');
    document.getElementById('gen-ab-text').textContent = 'Generating…';

    // Show loading
    ['view-home', 'view-timeline', 'view-library'].forEach(v => { document.getElementById(v).classList.add('hidden'); document.getElementById(v).classList.remove('flex'); });
    show('view-create', 'flex');
    document.getElementById('create-idle').classList.add('hidden');
    document.getElementById('create-loading').classList.remove('hidden');

    const enableSfx = document.getElementById('sfx-toggle').checked;
    try {
        const res = await fetch('/generate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ parts: parsedScript.parts, bgm_map: bgmMap, enable_sfx: enableSfx, mode: 'audiobook' })
        });
        const data = await res.json();
        if (data.error) { alert('Error: ' + data.error); }
        else { loadTrack(data.filename, data.url, data.duration_s, data.voice); switchTab('library'); }
    } catch (e) { alert('Error: ' + e.message); }
    finally {
        btn.disabled = false; btn.classList.remove('opacity-50');
        document.getElementById('gen-ab-text').textContent = 'Generate Audiobook';
        document.getElementById('create-idle').classList.remove('hidden');
        document.getElementById('create-loading').classList.add('hidden');
    }
}

// ── Generate Standard TTS ──
async function generateTTS() {
    const text = document.getElementById('input-text').value.trim();
    if (!text) { alert('Please enter text.'); return; }
    const voice = document.getElementById('input-voice').value;
    const btn = document.getElementById('btn-gen-tts');
    btn.disabled = true; btn.classList.add('opacity-50');
    document.getElementById('gen-tts-text').textContent = 'Generating…';

    switchTab('create');
    document.getElementById('create-idle').classList.add('hidden');
    document.getElementById('create-loading').classList.remove('hidden');

    try {
        const res = await fetch('/generate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, voice_preset: voice, mode: 'standard' })
        });
        const data = await res.json();
        if (data.error) { alert('Error: ' + data.error); }
        else { loadTrack(data.filename, data.url, data.duration_s, data.voice); switchTab('library'); }
    } catch (e) { alert('Error: ' + e.message); }
    finally {
        btn.disabled = false; btn.classList.remove('opacity-50');
        document.getElementById('gen-tts-text').textContent = 'Generate Audio';
        document.getElementById('create-idle').classList.remove('hidden');
        document.getElementById('create-loading').classList.add('hidden');
    }
}

// ── Library ──
async function loadLibrary() {
    try { const res = await fetch('/library'); libraryData = await res.json(); renderLibrary(); } catch (e) { console.error(e); }
}

function renderLibrary() {
    const grid = document.getElementById('library-grid');
    const empty = document.getElementById('library-empty');
    const search = document.getElementById('search-input').value.toLowerCase();
    let filtered = libraryData;
    if (activeFilter !== 'all') filtered = filtered.filter(f => f.filename.includes(activeFilter));
    if (search) filtered = filtered.filter(f => f.filename.toLowerCase().includes(search));

    if (!filtered.length) { grid.innerHTML = ''; empty.classList.remove('hidden'); empty.classList.add('flex'); return; }
    empty.classList.add('hidden'); empty.classList.remove('flex');

    grid.innerHTML = filtered.map((file, i) => {
        const name = file.filename.replace('svaanvox_', '').replace('.wav', '').replace(/_/g, ' ');
        const date = new Date(file.created).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        const isAB = file.filename.includes('audiobook');
        return `<div class="audio-card bg-card border border-border border-l-4 ${isAB ? 'border-l-saffron' : 'border-l-tri'} rounded-xl p-4 cursor-pointer fade-up group" style="animation-delay:${i * 50}ms" onclick="loadTrack('${file.filename}','${file.url}')">
            <div class="flex items-start justify-between mb-3">
                <div class="w-10 h-10 rounded-lg bg-gradient-to-br ${isAB ? 'from-saffron/20 to-amber-500/10' : 'from-tri/20 to-emerald-500/10'} flex items-center justify-center">
                    <svg class="w-5 h-5 ${isAB ? 'text-saffron' : 'text-tri'}" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/></svg>
                </div>
                <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onclick="event.stopPropagation();downloadFile('${file.url}','${file.filename}')" class="p-1.5 rounded-lg hover:bg-white/10 text-gray-500 hover:text-saffron transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg></button>
                    <button onclick="event.stopPropagation();deleteFile('${file.filename}')" class="p-1.5 rounded-lg hover:bg-white/10 text-gray-500 hover:text-crimson transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button>
                </div>
            </div>
            <p class="text-sm font-semibold text-gray-200 truncate capitalize">${name}</p>
            <div class="flex items-center gap-2 mt-2">
                <span class="text-[10px] font-medium px-2 py-0.5 rounded-full ${isAB ? 'bg-saffron/10 text-saffron' : 'bg-tri/10 text-tri'}">${isAB ? '🎧 Audiobook' : '🎙️ Standard'}</span>
                <span class="text-[10px] text-gray-600">${file.size_kb} KB</span>
            </div>
            <p class="text-[11px] text-gray-600 mt-2">${date}</p>
        </div>`;
    }).join('');
}

function filterLibrary() { renderLibrary(); }
function filterByMode(mode) {
    activeFilter = mode;
    document.querySelectorAll('.filter-btn').forEach(b => { b.classList.remove('active-filter', 'text-gray-300'); b.classList.add('text-gray-500'); });
    const btn = document.querySelector(`.filter-btn[data-filter="${mode}"]`);
    if (btn) { btn.classList.add('active-filter', 'text-gray-300'); btn.classList.remove('text-gray-500'); }
    renderLibrary();
}
async function deleteFile(fn) { if (!confirm('Delete?')) return; await fetch('/library/' + fn, { method: 'DELETE' }); loadLibrary(); }
function downloadFile(url, fn) { const a = document.createElement('a'); a.href = url; a.download = fn; a.click(); }

// ── Player ──
let isPlaying = false;
function loadTrack(fn, url, dur, voice) {
    audio.src = url; audio.load();
    document.getElementById('player-title').textContent = fn.replace('svaanvox_', '').replace('.wav', '').replace(/_/g, ' ');
    document.getElementById('player-subtitle').textContent = voice || 'SvaanVox';
    isPlaying = false; updatePlayIcon();
    audio.play().then(() => { isPlaying = true; updatePlayIcon() }).catch(() => { });
}
function togglePlay() { if (!audio.src) return; if (isPlaying) audio.pause(); else audio.play(); isPlaying = !isPlaying; updatePlayIcon(); }
function updatePlayIcon() { document.getElementById('icon-play').classList.toggle('hidden', isPlaying); document.getElementById('icon-pause').classList.toggle('hidden', !isPlaying); }
function skipForward() { audio.currentTime = Math.min(audio.duration, audio.currentTime + 10); }
function skipBackward() { audio.currentTime = Math.max(0, audio.currentTime - 10); }
function scrubAudio() { if (!audio.duration) return; audio.currentTime = (document.getElementById('scrubber').value / 100) * audio.duration; }
function setVolume() { audio.volume = document.getElementById('volume').value; const m = audio.volume === 0; document.getElementById('icon-vol').classList.toggle('hidden', m); document.getElementById('icon-mute').classList.toggle('hidden', !m); }
function toggleMute() { const v = document.getElementById('volume'); if (audio.volume > 0) { audio._pv = audio.volume; audio.volume = 0; v.value = 0 } else { audio.volume = audio._pv || .8; v.value = audio.volume } const m = audio.volume === 0; document.getElementById('icon-vol').classList.toggle('hidden', m); document.getElementById('icon-mute').classList.toggle('hidden', !m); }
function formatTime(s) { if (isNaN(s)) return '0:00'; const m = Math.floor(s / 60), sec = Math.floor(s % 60); return m + ':' + (sec < 10 ? '0' : '') + sec; }
audio.addEventListener('timeupdate', () => { document.getElementById('time-current').textContent = formatTime(audio.currentTime); document.getElementById('time-total').textContent = formatTime(audio.duration); if (audio.duration) document.getElementById('scrubber').value = (audio.currentTime / audio.duration) * 100; });
audio.addEventListener('ended', () => { isPlaying = false; updatePlayIcon() });

// ── Init ──
switchTab('home');
