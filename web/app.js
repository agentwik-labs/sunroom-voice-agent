const LABELS = {
  contact_name:'Name', phone:'Phone', email:'Email', job_number_or_address:'Job # / address', zip_code:'ZIP',
  service_area:'Service area', install_age:'Installed', category:'Problem type', summary:'Summary',
  details:'Details', impact:'Impact', started:'Started', insurance_claim:'Insurance claim', photos:'Photos',
  callback_window:'Call back', homeowner:'Homeowner', city:'City', room_type:'Room type',
  building_onto:'Built onto', approx_size:'Size', main_use:'Main use', features:'Features', hoa:'HOA', timeline:'Timeline',
  budget:'Budget', financing_interest:'Financing', street_address:'Street address',
  best_time:'Best time to call', heard_about_us:'Heard about us', notes:'Notes', status:'Status',
};
const PRETTY = {
  four_season:'Four-season', three_season:'Three-season', screen_room:'Screen room', patio_cover:'Patio cover',
  solarium:'Solarium', new_foundation:'New foundation', replace_existing:'Replacing existing', asap:'As soon as possible',
  within_3_months:'Within 3 months', '3_6_months':'3–6 months', exploring:'Just exploring', under_25k:'Under $25k',
  '25k_50k':'$25k–$50k', '50k_80k':'$50k–$80k', '80k_plus':'$80k+', leak:'Leak', storm_damage:'Storm damage',
  glass_window_door:'Glass, window or door', structural:'Structural', electrical_hvac:'Electrical or HVAC',
  install_punch_list:'Install punch list', warranty_question:'Warranty question', billing_financing:'Billing or financing',
  safety_or_open_to_weather:'Unsafe or open to weather', room_unusable_or_damage_worsening:'Unusable or getting worse',
  usable_needs_fixing:'Usable, needs fixing', question_or_request:'Question or request', yes:'Yes', no:'No',
  buying:'Buying a home', unsure:'Unsure', deck:'Deck', patio:'Patio',
};
const PRIORITY_TONE = {P1:'crit', P2:'warn', P3:'ok', P4:'ok'};
const LEAD_TONE = {Hot:'crit', Warm:'warn', Nurture:'ok'};

let records = [], selected = null, lastJson = null, known = null, selectCallId = null;

function el(tag, props = {}, ...kids){
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'class') n.className = v; else if (k === 'on') n.onclick = v; else n.setAttribute(k, v);
  }
  n.append(...kids.filter(k => k != null));
  return n;
}
const idOf = r => r.ticket_id || r.quote_id || r._call?.call_id;
const isTicket = r => !!r.ticket_id;
const when = r => r.created ? new Date(r.created).toLocaleString([], {month:'short', day:'numeric', hour:'numeric', minute:'2-digit'}) : '';
const show = v => Array.isArray(v) ? v.map(x => PRETTY[x] || x).join(', ') : (PRETTY[v] || v);

function fieldList(r){
  const dl = el('dl');
  for (const [key, label] of Object.entries(LABELS)) {
    const v = r[key];
    if (v == null || v === '' || (Array.isArray(v) && !v.length)) continue;
    dl.append(el('dt', {}, label), el('dd', {}, String(show(v))));
  }
  return dl;
}

function scoreCard(r){
  const factors = el('ul', {class:'factors'});
  for (const f of r.score_factors || []) {
    factors.append(el('li', {},
      el('div', {class:'row'}, el('span', {}, f.factor), el('span', {class:'pts'}, `${f.points} of ${f.max}`)),
      el('div', {class:'meter', role:'img', 'aria-label':`${f.factor}: ${f.points} of ${f.max}`},
        el('span', {style:`width:${f.max ? 100 * f.points / f.max : 0}%`}))));
  }
  return el('section', {class:'card'},
    el('h2', {}, 'Lead score from their answers'),
    el('div', {class:'hero'}, el('span', {class:'num'}, String(r.likelihood_score ?? '–')), el('span', {class:'of'}, '/ 100')),
    factors,
    el('p', {class:'note'}, 'A fixed points rule, not a trained prediction.'));
}

function chips(title, items){
  return items?.length ? el('p', {class:'chips'}, el('span', {class:'chipTitle'}, title), items.join(' · ')) : null;
}

const SENTIMENT_TONE = {Positive:'ok', Neutral:'', Mixed:'warn', Frustrated:'warn', Angry:'crit'};

function analysisCards(a){
  const s = a.sentiment, p = a.purchase;
  const gauge = value => el('div', {class:'meter', role:'img', 'aria-label':`${value} out of 100`}, el('span', {style:`width:${value}%`}));
  const sentiment = el('section', {class:'card'},
    el('h2', {}, 'Caller sentiment'),
    el('div', {class:'hero'}, el('span', {class:'num'}, String(s.score)), el('span', {class:'of'}, '/ 100'),
      el('span', {class:`pill ${SENTIMENT_TONE[s.label] ?? ''}`, style:'margin-left:auto;align-self:center'}, s.label)),
    el('div', {class:'bar'}, gauge(s.score)),
    el('p', {class:'read'}, `${s.start} at the start, ${s.end.toLowerCase()} by the end. ${s.reason}`),
    s.quote ? el('blockquote', {}, `“${s.quote}”`) : null);
  const purchase = el('section', {class:'card'},
    el('h2', {}, 'Likelihood of purchase'),
    p.applies
      ? el('div', {class:'hero'}, el('span', {class:'num'}, `${p.likelihood}%`))
      : el('div', {class:'hero'}, el('span', {class:'num', style:'font-size:28px'}, 'Not a sales call')),
    p.applies ? el('div', {class:'bar'}, gauge(p.likelihood)) : null,
    el('p', {class:'read'}, p.reason),
    chips('Good signs', p.positive_signals), chips('Risks', p.risks));
  const summary = el('section', {class:'card full'},
    el('h2', {}, 'After the call'),
    el('p', {class:'read', style:'padding-top:14px'}, a.summary),
    el('p', {class:'read'}, el('strong', {}, 'Next step: '), a.next_action),
    el('p', {class:'note'}, 'AI estimate from the transcript. It doesn’t hear tone of voice and hasn’t been checked against real sales.'));
  return [summary, sentiment, purchase];
}

function routingCard(r){
  const rows = el('dl');
  [['Priority', r.priority], ['Sent to', r.queue], ['Respond within', r.response_target], ['Warranty', r.warranty],
   ['Also notified', (r.also_notify || []).join(', ') || 'Nobody else']]
    .forEach(([k, v]) => rows.append(el('dt', {}, k), el('dd', {}, v || '–')));
  return el('section', {class:'card'}, el('h2', {}, 'Routing'), rows);
}

const audioUrls = {};
const clock = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

async function loadAudio(player, id){
  try {
    audioUrls[id] ||= URL.createObjectURL(await (await fetch(`/api/audio/${id}`)).blob());
    player.src = audioUrls[id];
    // Browser recordings don't store their length, so seek past the end once to find it.
    player.onloadedmetadata = () => {
      if (player.duration !== Infinity) return;
      player.ontimeupdate = () => { player.ontimeupdate = null; player.currentTime = 0; };
      player.currentTime = 1e9;
    };
  } catch { player.replaceWith(el('p', {class:'note'}, 'Could not load the recording.')); }
}

function callFacts(meta){
  const gaps = [...(meta.reply_gaps || [])].sort((a, b) => a - b);
  const typical = gaps.length ? ` · usually replied in ${gaps[Math.floor(gaps.length / 2)].toFixed(1)}s` : '';
  return `${meta.engine === 'live' ? 'GPT-Live' : 'Realtime'}${typical}`;
}

function recordingCard(meta){
  const player = el('audio', {controls:'', preload:'metadata'});
  const lines = el('ul', {class:'lines'});
  for (const line of meta.transcript || []) {
    if (line.role === 'event') { lines.append(el('li', {class:'event'}, line.text)); continue; }
    lines.append(el('li', {}, el('button', {on(){ if (meta.has_audio) { player.currentTime = line.t; player.play(); } }},
      el('span', {class:'at'}, clock(line.t)), el('span', {class:'who2'}, line.role === 'user' ? 'Caller' : 'Agent'), el('span', {}, line.text))));
  }
  if (meta.has_audio) loadAudio(player, meta.call_id);
  return el('section', {class:'card full'},
    el('h2', {}, `Recording${meta.duration ? ` (${clock(meta.duration)})` : ''}`, el('span', {style:'text-transform:none;letter-spacing:0;font-weight:400'}, callFacts(meta))),
    meta.has_audio ? player : el('p', {class:'note', style:'padding-top:16px'}, 'No audio was saved for this call.'),
    lines);
}

function testCard(test){
  const body = el('tbody');
  for (const c of test.checks) {
    body.append(el('tr', {}, el('td', {}, c.name), el('td', {}, String(c.expected)), el('td', {}, String(c.actual)),
      el('td', {}, el('span', {class:`pill ${c.passed ? 'ok' : 'crit'}`}, c.passed ? 'Pass' : 'Fail'))));
  }
  return el('section', {class:'card full'},
    el('h2', {}, `Test: ${test.label}`, el('span', {class:`pill ${test.passed ? 'ok' : 'crit'}`}, test.passed ? 'Passed' : 'Failed')),
    el('div', {style:'overflow-x:auto'}, el('table', {class:'checks'},
      el('thead', {}, el('tr', {}, ...['Check', 'Expected', 'Actual', 'Result'].map(t => el('th', {}, t)))), body)));
}

function jsonCard(r){
  const {_call, ...saved} = r;
  const text = JSON.stringify(_call?.analysis ? {...saved, after_call_analysis:_call.analysis} : saved, null, 2);
  const copy = el('button', {class:'ghost', on(){
    navigator.clipboard.writeText(text).then(() => { copy.textContent = 'Copied'; setTimeout(() => copy.textContent = 'Copy JSON', 1500); });
  }}, 'Copy JSON');
  return el('section', {class:'card full'}, el('h2', {}, 'Saved record (JSON)', copy), el('pre', {}, text));
}

const hasRecord = r => !!(r.ticket_id || r.quote_id);
const summary = r => !hasRecord(r) ? 'Nothing saved' : isTicket(r) ? `Service · ${r.priority}` : `New lead · ${r.likelihood_score ?? '–'}/100`;

function render(){
  const app = document.getElementById('app');
  if (!records.length) {
    app.replaceChildren(el('section', {class:'card full'}, el('div', {class:'empty'},
      el('strong', {}, 'Nothing captured yet'),
      'The ticket or lead appears here as soon as the agent saves it, near the end of the call.')));
    return;
  }
  const r = records.find(x => idOf(x) === selected) || records[0];
  const rows = el('tbody');
  for (const x of records) {
    const a = x._call?.analysis;
    const row = el('tr', {on(){ selected = idOf(x); render(); }});
    if (x === r) row.setAttribute('aria-current', 'true');
    rows.append(row);
    row.append(
      el('td', {}, el('button', {class:'rowBtn', on(ev){ ev.stopPropagation(); selected = idOf(x); render(); }}, x.contact_name || 'Unfinished call'),
        el('span', {class:'meta'}, `${summary(x)} · ${when(x)}`),
        x._call?.test ? el('span', {class:`pill ${x._call.test.passed ? 'ok' : 'crit'}`, style:'margin-top:4px;font-size:12px'}, x._call.test.passed ? 'Test passed' : 'Test failed') : null),
      el('td', {}, a?.needs || '–'), el('td', {}, a?.wants || '–'), el('td', {}, a?.result || '–'),
      el('td', {class:'nowrap'}, a ? `${a.sentiment.label} (${a.sentiment.score})` : '–'),
      el('td', {class:'nowrap'}, !a ? '–' : a.purchase.applies ? `${a.purchase.likelihood}%` : 'Not a sale'));
  }
  const list = el('div', {style:'overflow-x:auto'}, el('table', {class:'calls'},
    el('thead', {}, el('tr', {}, ...['Caller', 'Needs', 'Wants', 'Result', 'Sentiment', 'Purchase'].map(t => el('th', {}, t)))), rows));
  const pill = !hasRecord(r)
    ? el('span', {class:'pill'}, 'Ended before anything was saved')
    : isTicket(r)
    ? el('span', {class:`pill ${PRIORITY_TONE[r.priority] || ''}`}, `${r.priority} priority`)
    : el('span', {class:`pill ${LEAD_TONE[r.lead_score] || ''}`}, `${r.lead_score} lead`);
  const top = el('section', {class:'card'}, el('div', {class:'top'},
    el('div', {},
      el('p', {class:'title'}, r.contact_name || 'Unfinished call'),
      el('p', {class:'sub'}, `${!hasRecord(r) ? 'Call' : isTicket(r) ? `Service ticket ${idOf(r)}` : `New sunroom lead ${idOf(r)}`} · ${when(r)}`),
      pill)));
  app.replaceChildren(
    el('section', {class:'card'}, el('h2', {}, `Calls (${records.length})`), list),
    el('div', {id:'detail'}, top,
      el('div', {class:'two'},
        ...(r._call?.analysis ? analysisCards(r._call.analysis) : []),
        r._call?.analysis_error ? el('section', {class:'card full'}, el('p', {class:'read', style:'padding-top:14px'}, `The after-call analysis didn’t finish: ${r._call.analysis_error}`)) : null,
        r._call?.test ? testCard(r._call.test) : null,
        r._call ? recordingCard(r._call) : null,
        hasRecord(r) ? (isTicket(r) ? routingCard(r) : scoreCard(r)) : null,
        hasRecord(r) ? el('section', {class:'card'}, el('h2', {}, 'Captured from the call'), fieldList(r)) : null,
        hasRecord(r) ? jsonCard(r) : null)));
}

async function poll(){
  const status = document.getElementById('status');
  try {
    const res = await fetch('/api/records');
    const text = await res.text();
    status.className = ''; status.textContent = 'Ready';
    if (text === lastJson) return;
    lastJson = text; records = JSON.parse(text);
    const ids = new Set(records.map(idOf));
    if (known) { const fresh = records.find(x => !known.has(idOf(x))); if (fresh) selected = idOf(fresh); }
    const moved = records.find(x => x._call?.call_id === selectCallId); if (moved) { selected = idOf(moved); selectCallId = null; }
    known = ids;
    render();
  } catch {
    status.className = 'down'; status.textContent = 'Local server stopped';
  }
}
poll(); setInterval(poll, 1500);

/* ---------- the voice call: browser <-> OpenAI over WebRTC ---------- */
const OPENAI_CALLS_URL = 'https://api.openai.com/v1/realtime/calls';
const AGENT_LOUD = 0.012, MIC_LOUD = 0.02; // loudness that counts as someone talking
const btn = document.getElementById('callBtn');
const stateEl = document.getElementById('callState');
const transcript = document.getElementById('transcript');
const typeForm = document.getElementById('typeForm');
const typeBox = document.getElementById('typeBox');
const testPick = document.getElementById('testPick');
const testBtn = document.getElementById('testBtn');
const enginePick = document.getElementById('enginePick');
const MAX_TEST_TURNS = 30;
let call = null, stopTests = false;

/* The call moves through these phases, in this order; errors drop it back to idle with a message.
   The current phase is on <section id="call" data-phase>, so styles, tests and scripts can read it.
     loading    the page is fetching its settings
     idle       no call; Start call and Run test call are available (unless an API key is still needed)
     starting   asking for the microphone and connecting
     connected  talking; the status line shows who is speaking
     ending     the agent is saying goodbye
     saving     the call is over; the recording is uploading and the analysis is running */
const PHASE_TEXT = {loading:'Loading…', starting:'Connecting…', connected:'Connected', ending:'Wrapping up…',
                    saving:'Saving the recording and analyzing the call…'};
let phase = 'loading', keyNeeded = false;

function setState(text, isError = false){ stateEl.textContent = text; stateEl.className = isError ? 'error' : ''; }
function setPhase(next, text = PHASE_TEXT[next], isError = false){
  phase = next;
  document.getElementById('call').dataset.phase = next;
  const inCall = next === 'connected' || next === 'ending';
  btn.textContent = inCall ? 'End call' : 'Start call'; btn.classList.toggle('end', inCall);
  btn.disabled = keyNeeded || next === 'loading' || next === 'starting';
  testBtn.disabled = testPick.disabled = enginePick.disabled = keyNeeded || !(next === 'idle' || next === 'saving');
  typeForm.hidden = !inCall || !!call?.scenario;
  if (text != null) setState(text, isError);
}
function elapsed(){ return call?.startedAt ? (performance.now() - call.startedAt) / 1000 : 0; }
function bubble(id, role, text, pending = false){
  let b = id && transcript.querySelector(`[data-id="${CSS.escape(id)}"]`);
  if (!b) {
    b = el('div', {class:`msg ${role}`});
    if (id) b.dataset.id = id;
    b.dataset.role = role; b.dataset.t = elapsed().toFixed(1);
    transcript.append(b);
  }
  b.textContent = text;
  b.classList.toggle('pending', pending);
  transcript.scrollTop = transcript.scrollHeight;
  return b;
}
function note(text){
  const n = el('div', {class:'handoff'}, text);
  n.dataset.role = 'event'; n.dataset.t = elapsed().toFixed(1);
  transcript.append(n);
}
function readTranscript(){
  return [...transcript.children].filter(n => n.dataset.role && !n.classList.contains('pending'))
    .map(n => ({role:n.dataset.role, t:+n.dataset.t, text:n.textContent.trim()})).filter(l => l.text);
}
function send(event){ if (call?.dc.readyState === 'open') call.dc.send(JSON.stringify(event)); }
function respond(agent, extra){
  send({type:'response.create', response: extra ? {instructions: `${agent.instructions}\n\nRight now: ${extra}`} : {}});
}
async function postJson(url, body){
  const res = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body || {})});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}
function loudnessMeter(ctx, stream){
  const analyser = ctx.createAnalyser(); analyser.fftSize = 1024;
  ctx.createMediaStreamSource(stream).connect(analyser);
  const data = new Float32Array(analyser.fftSize);
  return () => { analyser.getFloatTimeDomainData(data); return Math.sqrt(data.reduce((sum, v) => sum + v * v, 0) / data.length); };
}
function iceGathered(pc){
  return new Promise(res => {
    if (pc.iceGatheringState === 'complete') return res();
    const timer = setTimeout(res, 3000);
    pc.addEventListener('icegatheringstatechange', () => { if (pc.iceGatheringState === 'complete') { clearTimeout(timer); res(); } });
  });
}

/* Resolves once the call has ended and been saved: true if it connected, false if it never got that far. */
async function startCall(scenario = null){
  const engine = enginePick.value;
  setPhase('starting', scenario ? 'Starting test call…' : 'Asking for your microphone…');
  const ctx = new AudioContext();
  await ctx.resume();
  let mic, micDest = null;
  if (scenario) {
    micDest = ctx.createMediaStreamDestination(); // the simulated caller speaks into this
    mic = micDest.stream;
    // Pure digital silence stops audio packets, so the agent never hears the caller finish. A faint hiss keeps them flowing.
    const hiss = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    hiss.getChannelData(0).forEach((_, i, d) => { d[i] = (Math.random() - 0.5) * 0.002; });
    const hissSource = ctx.createBufferSource();
    hissSource.buffer = hiss; hissSource.loop = true; hissSource.connect(micDest); hissSource.start();
  } else {
    try {
      mic = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true, noiseSuppression:true}});
    } catch {
      ctx.close();
      setPhase('idle', 'Microphone blocked. Allow it from the icon in the address bar, then try again.', true);
      return false;
    }
  }
  try {
    setState('Connecting…');
    const recDest = ctx.createMediaStreamDestination(); // both voices, mixed, for the recording
    ctx.createMediaStreamSource(mic).connect(recDest);
    const pc = new RTCPeerConnection();
    const audio = new Audio(); audio.autoplay = true;
    let agentLoudness = () => 0;
    pc.ontrack = e => {
      audio.srcObject = e.streams[0];
      ctx.createMediaStreamSource(e.streams[0]).connect(recDest);
      agentLoudness = loudnessMeter(ctx, e.streams[0]);
    };
    pc.addTrack(mic.getAudioTracks()[0], mic);
    const dc = pc.createDataChannel('oai-events');
    const chunks = [];
    const recorder = new MediaRecorder(recDest.stream, {mimeType:'audio/webm;codecs=opus'});
    recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    let finished; const done = new Promise(res => { finished = () => res(true); });
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    let session, answer;
    if (engine === 'live') {
      await iceGathered(pc);
      session = await postJson('/api/session', {scenario, engine, sdp: pc.localDescription.sdp});
      answer = session.answer_sdp;
    } else {
      session = await postJson('/api/session', {scenario, engine});
      const res = await fetch(OPENAI_CALLS_URL, {method:'POST', body: offer.sdp,
        headers:{Authorization:`Bearer ${session.client_secret}`, 'Content-Type':'application/sdp'}});
      if (!res.ok) throw new Error(`OpenAI refused the connection (${res.status})`);
      answer = await res.text();
    }
    transcript.replaceChildren();
    const micLoudness = scenario ? () => 0 : loudnessMeter(ctx, mic);
    call = {pc, dc, mic, audio, ctx, micDest, recorder, chunks, finished, done, scenario, engine, sessionId: session.session_id,
            agent: session.agent, greeting: session.greeting, turnDetection: session.turn_detection, interrupts: session.interrupts,
            text: {}, turns: 0, responding: false, toolsPending: false, callerTalking: false,
            spoken: [], gaps: [], interruptions: 0, agentLoudness: () => agentLoudness(), micLoudness,
            agentTalking: false, agentQuietSince: performance.now(), agentTalkingSince: 0, heardAgent: false,
            callerEndedAt: 0, micWasLoud: false, micQuietSince: 0, liveBubble: {user: 0, assistant: 0}, liveRole: null};
    const started = () => {
      recorder.start(1000); call.startedAt = performance.now();
      setPhase('connected');
      call.ticker = setInterval(tick, 100);
      if (scenario) resetWatchdog();
    };
    dc.onopen = () => {
      if (engine === 'live') return; // wait for session.started
      started();
      respond(call.agent, call.agent.greeting);
    };
    dc.onmessage = e => {
      const event = JSON.parse(e.data);
      if (event.type === 'session.started') {
        started();
        send({type:'session.commentary.append', event_id:'greeting_1', delegation_id:null, content:call.greeting});
      }
      (engine === 'live' ? handleLiveEvent : handleEvent)(event);
    };
    pc.onconnectionstatechange = () => {
      clearTimeout(call?.dropTimer);
      if (call?.pc !== pc) return;
      if (pc.connectionState === 'failed') endCall('The connection dropped. Check the internet, then press Start call.', true);
      // "disconnected" often recovers by itself, so give it a moment.
      if (pc.connectionState === 'disconnected') {
        setState('Connection is unstable, trying to recover…', true);
        call.dropTimer = setTimeout(() => { if (call?.pc === pc) endCall('The connection dropped. Check the internet, then press Start call.', true); }, 8000);
      }
    };
    await pc.setRemoteDescription({type:'answer', sdp: answer});
    return done;
  } catch (err) {
    mic.getTracks().forEach(t => t.stop());
    const c = call;
    if (c) { endCall(err.message, true); await c.done; } else { ctx.close(); setPhase('idle', err.message, true); }
    return false;
  }
}

function endCall(message = 'Call ended. The analysis and recording are on the right.', isError = false){
  if (!call) return;
  const c = call, entries = readTranscript(), duration = elapsed();
  [c.hangupTimer, c.watchdog, c.dropTimer].forEach(clearTimeout); clearInterval(c.ticker);
  if (c.engine === 'live' && c.dc.readyState === 'open') c.dc.send(JSON.stringify({type:'session.close', event_id:'close_1'}));
  c.stoppedRecording = new Promise(res => {
    if (c.recorder.state === 'recording') { c.recorder.onstop = res; c.recorder.stop(); } else res();
  });
  call = null;
  c.dc.close(); c.pc.close(); c.mic.getTracks().forEach(t => t.stop()); c.audio.srcObject = null;
  setPhase('saving');
  if (isError) setState(message, true);
  saveCall(c, entries, duration, message, isError);
}

async function saveCall(c, entries, duration, message, isError){
  try {
    await c.stoppedRecording;
    const blob = new Blob(c.chunks, {type:'audio/webm'});
    if (blob.size) {
      const res = await fetch(`/api/call/audio?session_id=${c.sessionId}`, {method:'POST', body: blob});
      if (!res.ok) throw new Error('The server did not accept the recording.');
    }
    await postJson('/api/call/finish', {session_id:c.sessionId, transcript:entries, duration, interruptions:c.interruptions, spoken:c.spoken, reply_gaps:c.gaps});
    selectCallId = c.sessionId;
    await poll();
    if (!call) setPhase('idle', message, isError);
  } catch (err) {
    if (!call) setPhase('idle', `Couldn't save the recording: ${err.message}`, true);
  } finally {
    c.ctx.close(); c.finished();
  }
}

/* Watches both voices ten times a second: timing, turn-taking and hanging up work the same on either model. */
function tick(){
  const c = call;
  if (!c) return;
  const now = performance.now();
  const loud = c.agentLoudness() > AGENT_LOUD;
  if (loud && !c.agentTalking) {
    c.agentTalking = true; c.agentTalkingSince = now; c.heardAgent = true; c.line = null;
    if (c.callerEndedAt) { c.gaps.push(+((now - c.callerEndedAt) / 1000).toFixed(2)); c.callerEndedAt = 0; }
    if (c.overlapSince && !c.scenario) c.overlapSince = 0;
  }
  if (loud) c.agentLastLoud = now;
  if (!loud && c.agentTalking && now - c.agentLastLoud > 300) {
    c.agentTalking = false; c.agentQuietSince = now;
    if (c.overlapSince && now - c.overlapSince < 2500) c.interruptions++;
    c.overlapSince = 0;
    if (phase === 'connected' && c.engine === 'live') setState('Your turn');
  }
  if (!c.scenario) { // a real caller: when they stop talking starts the reply timer
    const micLoud = c.micLoudness() > MIC_LOUD;
    if (micLoud) { c.micWasLoud = true; c.micQuietSince = now; }
    else if (c.micWasLoud && now - c.micQuietSince > 300) { c.micWasLoud = false; if (!c.agentTalking) c.callerEndedAt = c.micQuietSince; }
    return;
  }
  // test caller
  if (phase === 'ending' || c.callerTalking) return;
  if (c.saidBye && !c.agentTalking && now - Math.max(c.agentQuietSince, c.byeAt) > 3000) return endCall();
  if (c.saidBye) return;
  if (c.interrupts && c.agentTalking && !c.toolsPending && now - c.agentTalkingSince > 1300 && c.cutAt !== c.agentTalkingSince && elapsed() > 8) {
    c.cutAt = c.agentTalkingSince;
    return testCallerSpeak();
  }
  if (!c.heardAgent || c.agentTalking || c.responding || c.toolsPending) return;
  const quiet = now - c.agentQuietSince;
  if (quiet > 150 && !c.line) { c.line = fetchCallerLine(c); c.pause = 450 + Math.random() * 500; } // think while they finish, like people do
  if (quiet > c.pause) testCallerSpeak();
}

function fetchCallerLine(c){
  return postJson('/api/test/next', {session_id:c.sessionId, transcript:readTranscript()});
}

async function testCallerSpeak(){
  const c = call;
  if (!c || c.callerTalking) return;
  if (++c.turns > MAX_TEST_TURNS) return endCall('The test call ran too long, so it was ended.', true);
  c.callerTalking = true;
  try {
    const {line, audio} = await (c.line || fetchCallerLine(c));
    c.line = null;
    if (call !== c) return;
    const bytes = Uint8Array.from(atob(audio), ch => ch.charCodeAt(0));
    const buffer = await c.ctx.decodeAudioData(bytes.buffer);
    if (call !== c) return;
    resetWatchdog();
    setState('Test caller speaking…');
    c.spoken.push(line);
    const source = c.ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(c.micDest); source.connect(c.ctx.destination);
    source.onended = () => {
      c.callerTalking = false; c.callerEndedAt = performance.now();
      if (/\b(bye|goodbye|adiós|adios)\b/i.test(line)) { c.saidBye = true; c.byeAt = performance.now(); }
    };
    source.start();
    if (c.agentTalking) c.overlapSince = performance.now(); // the caller's voice has now started over the agent's
  } catch (err) {
    c.callerTalking = false;
    if (call === c) endCall(`Test call failed: ${err.message}`, true);
  }
}

function resetWatchdog(){
  clearTimeout(call.watchdog);
  call.watchdog = setTimeout(() => endCall('The test call stalled, so it was ended.', true), 45000);
}

/* ---------- Realtime events ---------- */
async function runTool(item){
  if (item.name === 'end_call') return {end: true, output: 'Ending the call.'};
  return postJson('/api/tool', {session_id: call.sessionId, name: item.name, arguments: item.arguments});
}

async function handleToolCalls(calls){
  call.toolsPending = true;
  let greeting = null, end = false;
  for (const item of calls) {
    let result;
    try { result = await runTool(item); } catch (err) { result = {output: `Tool error: ${err.message}`}; }
    if (!call) return;
    send({type:'conversation.item.create', item:{type:'function_call_output', call_id:item.call_id, output:result.output}});
    if (result.handoff) {
      call.agent = result.handoff; greeting = result.handoff.greeting;
      send({type:'session.update', session:{type:'realtime', instructions:result.handoff.instructions, tools:result.handoff.tools}});
      note(`Now with ${result.handoff.label}`);
    }
    if (result.end) end = true;
  }
  if (end) {
    setPhase('ending');
    call.hangupTimer = setTimeout(() => endCall(), 10000);
    respond(call.agent, 'Say one short, friendly goodbye. Do not ask anything else.');
  } else {
    respond(call.agent, greeting);
  }
  call.toolsPending = false;
}

function handleEvent(e){
  if (!call) return;
  if (call.scenario) resetWatchdog();
  switch (e.type) {
    case 'input_audio_buffer.speech_started': setState('Listening…'); bubble(e.item_id, 'user', '…', true); break;
    case 'conversation.item.input_audio_transcription.delta':
      call.text[e.item_id] = (call.text[e.item_id] || '') + e.delta; bubble(e.item_id, 'user', call.text[e.item_id], true); break;
    case 'conversation.item.input_audio_transcription.completed': bubble(e.item_id, 'user', e.transcript.trim() || '(unclear)'); break;
    case 'response.created': call.responding = true; break;
    case 'response.output_audio_transcript.delta':
      setState('Agent speaking…'); call.text[e.item_id] = (call.text[e.item_id] || '') + e.delta; bubble(e.item_id, 'assistant', call.text[e.item_id]); break;
    case 'output_audio_buffer.stopped':
      if (phase === 'ending' && call.goodbyeDone) { endCall(); break; }
      if (!call.interruptible) { // the greeting is out, so the caller can now talk over the agent
        call.interruptible = true;
        send({type:'session.update', session:{type:'realtime', audio:{input:{turn_detection:call.turnDetection}}}});
      }
      setState(phase === 'ending' ? PHASE_TEXT.ending : 'Your turn');
      break;
    case 'response.done': {
      call.responding = false;
      const calls = (e.response.output || []).filter(o => o.type === 'function_call' && o.status === 'completed');
      if (phase === 'ending') call.goodbyeDone = true;
      if (calls.length) handleToolCalls(calls);
      if (e.response.status === 'failed') setState(e.response.status_details?.error?.message || 'The agent hit an error.', true);
      break;
    }
    case 'error':
      if (e.error?.code === 'conversation_already_has_active_response') break; // it's already replying, which is fine
      console.error('Realtime error', e.error); setState(e.error?.message || 'Something went wrong.', true); break;
  }
}

/* ---------- GPT-Live events ---------- */
function liveTranscript(role, delta){
  const c = call, now = performance.now();
  c.liveLast ||= {};
  // Talking over each other shouldn't shatter a sentence into fragments, so only a real pause starts a new bubble.
  if (!c.liveBubble[role] || now - (c.liveLast[role] || 0) > 1500) { c.liveBubble[role]++; c.text[`${role}${c.liveBubble[role]}`] = ''; }
  c.liveLast[role] = now;
  const id = `${role}${c.liveBubble[role]}`;
  c.text[id] += delta;
  // Sound tags like [inhale] can arrive split across fragments, including one still open at the end.
  const clean = c.text[id].replace(/\[[^\]]*\]/g, '').replace(/\[[^\]]*$/, '').replace(/\uFFFD/g, '').replace(/\s+/g, ' ');
  if (clean.trim()) bubble(id, role, clean);
}

async function handleLiveTool(item){
  const c = call;
  c.toolsPending = true;
  if (item.name === 'end_call') {
    send({type:'response.item.create', event_id:`tool_result_${item.call_id}`, item:{type:'function_call_output', call_id:item.call_id, output:'Call ending.'}});
    setPhase('ending');
    send({type:'session.commentary.append', event_id:'goodbye_1', delegation_id:null, content:'Say one short, friendly goodbye now.'});
    c.hangupTimer = setTimeout(() => endCall(), 6000);
    c.toolsPending = false;
    return;
  }
  let result;
  try { result = await postJson('/api/tool', {session_id:c.sessionId, name:item.name, arguments:item.arguments}); }
  catch (err) { result = {output:`Tool error: ${err.message}`}; }
  if (call !== c) return;
  send({type:'response.item.create', event_id:`tool_result_${item.call_id}`, item:{type:'function_call_output', call_id:item.call_id, output:result.output}});
  send({type:'response.create', event_id:`continue_${item.call_id}`});
  c.toolsPending = false;
}

function handleLiveEvent(e){
  if (!call) return;
  if (call.scenario) resetWatchdog();
  switch (e.type) {
    case 'session.input_transcript.delta': liveTranscript('user', e.delta); break;
    case 'session.output_transcript.delta': liveTranscript('assistant', e.delta); setState('Agent speaking…'); break;
    case 'session.delegation.created': call.responding = true; break;
    case 'response.event': {
      const ev = e.event;
      if (ev.type === 'response.output_item.done' && ev.item?.type === 'function_call') handleLiveTool(ev.item);
      if (['response.completed', 'response.failed', 'response.incomplete'].includes(ev.type)) call.responding = false;
      break;
    }
    case 'session.closed': endCall(); break;
    case 'error': console.error('GPT-Live error', e.error); setState(e.error?.message || 'Something went wrong.', true); break;
  }
}

async function runTests(){
  stopTests = false;
  const ids = testPick.value === 'all' ? [...testPick.options].map(o => o.value).filter(v => v !== 'all') : [testPick.value];
  for (const [i, id] of ids.entries()) {
    if (stopTests) break;
    const connected = await startCall(id);
    if (!connected) break; // the error stays on screen instead of the next test wiping it
    if (ids.length > 1 && !stopTests) setState(`Finished test ${i + 1} of ${ids.length}`);
  }
}

function needKey(needed){
  keyNeeded = needed;
  document.getElementById('keyForm').hidden = !needed;
  setPhase(phase, null); // re-derive the controls, keep the status text
}
document.getElementById('keyForm').onsubmit = async ev => {
  ev.preventDefault();
  const box = document.getElementById('keyBox');
  try {
    setState('Checking your key…');
    await postJson('/api/key', {key: box.value.trim()});
    box.value = ''; needKey(false); setState('Key accepted. Press Start call.');
  } catch (err) { setState(err.message, true); }
};

setPhase('loading', '');
fetch('/api/config').then(r => r.json()).then(({tests, engines, default_engine, has_key}) => {
  testPick.append(...tests.map(t => el('option', {value:t.id}, t.label)), el('option', {value:'all'}, 'All test calls, one after another'));
  enginePick.append(...Object.entries(engines).map(([id, label]) => el('option', {value:id}, label)));
  enginePick.value = default_engine;
  needKey(!has_key);
  setPhase('idle', '');
}).catch(() => setPhase('idle', 'Could not load the settings. Is the server running? Refresh to try again.', true));
testBtn.onclick = runTests;
btn.onclick = () => { if (call) { stopTests = true; endCall(); } else startCall(); };
typeForm.onsubmit = ev => {
  ev.preventDefault();
  const text = typeBox.value.trim();
  if (!text || !call) return;
  typeBox.value = '';
  if (call.engine === 'live') {
    call.liveRole = null; bubble(null, 'user', text);
    send({type:'session.commentary.append', event_id:`typed_${Date.now()}`, delegation_id:null, content:`The caller typed this instead of speaking: ${text}. Reply to it now.`});
    return;
  }
  bubble(null, 'user', text);
  send({type:'conversation.item.create', item:{type:'message', role:'user', content:[{type:'input_text', text}]}});
  respond(call.agent);
};
