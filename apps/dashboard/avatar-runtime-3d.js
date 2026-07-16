const stage = document.querySelector("#stage");
const fallback = document.querySelector("#fallback");
const stateBadge = document.querySelector("#stateBadge");
const connectionBadge = document.querySelector("#connectionBadge");
const subtitle = document.querySelector("#subtitle");
const voiceAudio = document.querySelector("#voiceAudio");

let THREE = null;
let renderer = null;
let scene = null;
let camera = null;
let rig = null;
let lastEventId = "";
let state = "idle";
let speakingUntil = 0;
let mouthLevel = 0;
let analyser = null;
let audioData = null;
let audioContextStarted = false;
let activeAudioObjectUrl = "";

async function loadThree() {
  try {
    THREE = await import("https://unpkg.com/three@0.166.1/build/three.module.js");
    return true;
  } catch {
    fallback.hidden = false;
    connectionBadge.textContent = "fallback";
    return false;
  }
}

function makeMaterial(color, roughness = 0.72, metalness = 0.02) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness });
}

function addMesh(parent, geometry, material, position, scale = [1, 1, 1]) {
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(...position);
  mesh.scale.set(...scale);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function initScene() {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0f172a);

  camera = new THREE.PerspectiveCamera(35, stage.clientWidth / stage.clientHeight, 0.1, 100);
  camera.position.set(0, 1.62, 6.1);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(stage.clientWidth, stage.clientHeight);
  renderer.shadowMap.enabled = true;
  stage.prepend(renderer.domElement);

  const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
  keyLight.position.set(2.8, 4.4, 4);
  keyLight.castShadow = true;
  scene.add(keyLight);

  const rimLight = new THREE.DirectionalLight(0x60a5fa, 1.2);
  rimLight.position.set(-4, 2, -1);
  scene.add(rimLight);
  scene.add(new THREE.HemisphereLight(0xdbeafe, 0x111827, 1.6));

  const floor = addMesh(
    scene,
    new THREE.CircleGeometry(2.6, 64),
    new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.9 }),
    [0, -1.28, 0],
    [1, 1, 1]
  );
  floor.rotation.x = -Math.PI / 2;

  rig = buildAvatarRig();
  scene.add(rig.root);

  window.addEventListener("resize", resize);
  resize();
  requestAnimationFrame(animate);
}

function buildAvatarRig() {
  const root = new THREE.Group();
  const skin = makeMaterial(0xd7b08c, 0.82);
  const hair = makeMaterial(0x15191f, 0.86);
  const cloth = makeMaterial(0x2563eb, 0.68);
  const dark = makeMaterial(0x020617, 0.7);
  const white = makeMaterial(0xf8fafc, 0.6);

  const body = addMesh(root, new THREE.CapsuleGeometry(0.62, 1.1, 16, 32), cloth, [0, -0.74, 0]);
  body.rotation.x = 0.03;

  addMesh(root, new THREE.SphereGeometry(0.18, 32, 16), skin, [-0.74, -0.52, 0], [0.78, 1.18, 0.78]);
  addMesh(root, new THREE.SphereGeometry(0.18, 32, 16), skin, [0.74, -0.52, 0], [0.78, 1.18, 0.78]);

  const neck = addMesh(root, new THREE.CylinderGeometry(0.18, 0.21, 0.32, 32), skin, [0, 0.08, 0]);
  const head = addMesh(root, new THREE.SphereGeometry(0.58, 48, 32), skin, [0, 0.74, 0], [0.86, 1.08, 0.82]);
  const hairCap = addMesh(root, new THREE.SphereGeometry(0.6, 48, 16, 0, Math.PI * 2, 0, Math.PI * 0.55), hair, [0, 0.88, -0.02], [0.9, 0.72, 0.84]);
  hairCap.rotation.x = -0.12;

  const leftEye = addMesh(root, new THREE.SphereGeometry(0.045, 16, 10), dark, [-0.19, 0.8, 0.43]);
  const rightEye = addMesh(root, new THREE.SphereGeometry(0.045, 16, 10), dark, [0.19, 0.8, 0.43]);
  const leftEyeLight = addMesh(root, new THREE.SphereGeometry(0.014, 8, 6), white, [-0.205, 0.815, 0.462]);
  const rightEyeLight = addMesh(root, new THREE.SphereGeometry(0.014, 8, 6), white, [0.175, 0.815, 0.462]);

  const nose = addMesh(root, new THREE.ConeGeometry(0.055, 0.16, 24), skin, [0, 0.69, 0.48], [0.72, 1, 0.72]);
  nose.rotation.x = Math.PI / 2;

  const mouth = addMesh(root, new THREE.BoxGeometry(0.22, 0.034, 0.018), dark, [0, 0.51, 0.49]);
  const jaw = addMesh(root, new THREE.SphereGeometry(0.24, 32, 12), skin, [0, 0.45, 0.18], [1.3, 0.5, 0.72]);

  return {
    root,
    body,
    neck,
    head,
    hairCap,
    leftEye,
    rightEye,
    leftEyeLight,
    rightEyeLight,
    nose,
    mouth,
    jaw,
  };
}

function resize() {
  if (!renderer || !camera) return;
  const width = stage.clientWidth || 1;
  const height = stage.clientHeight || 1;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}

function audioLevel() {
  if (!analyser || !audioData) {
    return performance.now() < speakingUntil ? 0.35 + Math.sin(performance.now() * 0.025) * 0.24 : 0;
  }
  analyser.getByteFrequencyData(audioData);
  const slice = audioData.slice(2, 32);
  const average = slice.reduce((sum, value) => sum + value, 0) / Math.max(slice.length, 1);
  return Math.min(1, average / 150);
}

function animate(now = 0) {
  requestAnimationFrame(animate);
  if (!renderer || !scene || !camera || !rig) return;

  const t = now * 0.001;
  const targetMouth = audioLevel();
  mouthLevel += (targetMouth - mouthLevel) * 0.28;
  const idleBreath = Math.sin(t * 1.7) * 0.018;
  const speaking = mouthLevel > 0.05 || performance.now() < speakingUntil;
  const thinking = state === "thinking";
  const listening = state === "listening";

  rig.root.position.y = idleBreath;
  rig.head.rotation.y = Math.sin(t * 0.7) * 0.08 + (listening ? -0.06 : 0);
  rig.head.rotation.x = Math.sin(t * 0.9) * 0.035 + (thinking ? 0.08 : 0);
  rig.hairCap.rotation.y = rig.head.rotation.y * 0.2;
  rig.nose.rotation.y = rig.head.rotation.y * 0.4;
  rig.mouth.scale.y = 1 + mouthLevel * 7.5;
  rig.mouth.scale.x = 1 + mouthLevel * 0.5;
  rig.mouth.position.y = 0.51 - mouthLevel * 0.018;
  rig.jaw.position.y = 0.45 - mouthLevel * 0.045;
  rig.body.scale.y = 1 + idleBreath * 0.04;

  stateBadge.textContent = speaking ? "speaking" : state;
  renderer.render(scene, camera);
}

async function setupAudioAnalyser() {
  if (audioContextStarted) return;
  try {
    const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
    const context = new AudioContextCtor();
    const source = context.createMediaElementSource(voiceAudio);
    analyser = context.createAnalyser();
    analyser.fftSize = 128;
    audioData = new Uint8Array(analyser.frequencyBinCount);
    source.connect(analyser);
    analyser.connect(context.destination);
    audioContextStarted = true;
  } catch {
    analyser = null;
    audioData = null;
  }
}

function speakWithBrowserVoice(text) {
  if (!text || !("speechSynthesis" in window)) {
    speakingUntil = performance.now() + Math.max(1200, text.length * 180);
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-CN";
  utterance.rate = 1.08;
  utterance.pitch = 0.92;
  utterance.onstart = () => {
    state = "speaking";
    speakingUntil = performance.now() + Math.max(1400, text.length * 190);
  };
  utterance.onend = () => {
    speakingUntil = Math.max(speakingUntil, performance.now() + 250);
  };
  utterance.onerror = () => {
    speakingUntil = performance.now() + Math.max(1200, text.length * 180);
  };
  window.speechSynthesis.speak(utterance);
}

async function playVoice(url, text) {
  if (!url) {
    connectionBadge.textContent = "browser voice";
    speakWithBrowserVoice(text);
    return;
  }
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`voice http ${response.status}`);
    const blob = await response.blob();
    if (activeAudioObjectUrl) URL.revokeObjectURL(activeAudioObjectUrl);
    activeAudioObjectUrl = URL.createObjectURL(blob);
    await setupAudioAnalyser();
    voiceAudio.src = activeAudioObjectUrl;
    speakingUntil = performance.now() + Math.max(1600, text.length * 170);
    await voiceAudio.play();
    connectionBadge.textContent = "clone voice";
  } catch (error) {
    connectionBadge.textContent = "browser voice";
    speakWithBrowserVoice(text);
  }
}

function absoluteAudioUrl(url) {
  if (!url) return "";
  return new URL(url, window.location.origin).toString();
}

async function handleEvent(event) {
  if (!event || !event.event_id) return;
  lastEventId = event.event_id;
  const payload = event.payload || {};
  if (event.type === "state") {
    state = payload.state || "idle";
    subtitle.textContent = `状态：${state}`;
  } else if (event.type === "say") {
    state = "speaking";
    const text = payload.text || "";
    subtitle.textContent = text || "数字我正在说话";
    await playVoice(absoluteAudioUrl(payload.audio_url || payload.audio_chunks?.[0]?.audio_url || ""), text);
  }
  await ackEvent(event.event_id, event.type);
}

async function ackEvent(eventId, type) {
  try {
    await fetch("/api/avatar3d/runtime-ack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId, status: `${type}_handled` }),
    });
  } catch {
    // The next poll will still advance by lastEventId in this runtime.
  }
}

async function pollEvents() {
  while (true) {
    try {
      const response = await fetch(`/api/avatar3d/runtime-events?after=${encodeURIComponent(lastEventId)}&timeout=10`, {
        cache: "no-store",
      });
      const data = await response.json();
      if (!data.ok) throw new Error(data.error || "event poll failed");
      const events = data.result?.events || [];
      connectionBadge.textContent = events.length ? "event" : "connected";
      for (const event of events) {
        await handleEvent(event);
      }
    } catch (error) {
      connectionBadge.textContent = "bridge offline";
      await new Promise((resolve) => setTimeout(resolve, 1200));
    }
  }
}

stage.addEventListener("click", () => {
  if (voiceAudio.paused && voiceAudio.src) {
    voiceAudio.play().catch(() => {});
  }
});

if (await loadThree()) {
  initScene();
}
pollEvents();
