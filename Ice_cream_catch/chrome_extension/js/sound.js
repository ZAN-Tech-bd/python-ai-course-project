// Happy little sound effects and a gentle background tune, synthesized with Web Audio (no sound files).
const MUTE_KEY = "icecream.muted";

class Sound {
  constructor() {
    this.ctx = null;
    this.master = null;
    this.musicTimer = null;
    this.musicStep = 0;
    try { this.muted = localStorage.getItem(MUTE_KEY) === "1"; } catch { this.muted = false; }
  }

  /** Browsers only allow audio after a user gesture or once the page has camera access; call often. */
  unlock() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      this.ctx = new AC();
      this.master = this.ctx.createGain();
      this.master.gain.value = this.muted ? 0 : 0.5;
      this.master.connect(this.ctx.destination);
    }
    if (this.ctx.state === "suspended") this.ctx.resume().catch(() => {});
  }

  toggleMute() {
    this.muted = !this.muted;
    try { localStorage.setItem(MUTE_KEY, this.muted ? "1" : "0"); } catch { /* storage unavailable */ }
    if (this.master) this.master.gain.value = this.muted ? 0 : 0.5;
    return this.muted;
  }

  tone(freq, dur, { type = "sine", vol = 0.3, at = 0, slide = 0 } = {}) {
    if (!this.ctx || this.ctx.state !== "running") return;
    const t0 = this.ctx.currentTime + at;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (slide) osc.frequency.exponentialRampToValueAtTime(Math.max(30, freq + slide), t0 + dur);
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(vol, t0 + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(gain).connect(this.master);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }

  // ---- effects ----
  catch(streak = 0) {
    const base = 520 * Math.pow(2, Math.min(streak, 12) / 12); // climbs a note with every catch in a row
    this.tone(base, 0.12, { type: "triangle", vol: 0.35, slide: base * 0.6 });
  }
  gold() { [784, 988, 1175, 1568].forEach((f, i) => this.tone(f, 0.18, { type: "triangle", vol: 0.25, at: i * 0.07 })); }
  rainbow() { [523, 659, 784, 1047, 1319].forEach((f, i) => this.tone(f, 0.2, { type: "square", vol: 0.08, at: i * 0.06 })); }
  freeze() { this.tone(1800, 0.6, { type: "sine", vol: 0.15, slide: -1400 }); this.tone(2400, 0.4, { vol: 0.08, at: 0.1, slide: -1800 }); }
  yuck() { this.tone(220, 0.35, { type: "sawtooth", vol: 0.15, slide: -150 }); this.tone(160, 0.3, { type: "square", vol: 0.08, at: 0.12, slide: -90 }); }
  splat() { this.tone(180, 0.12, { type: "sine", vol: 0.12, slide: -120 }); }
  tower() { [523, 659, 784, 1047, 784, 1047].forEach((f, i) => this.tone(f, 0.16, { type: "triangle", vol: 0.25, at: i * 0.09 })); }
  join() { this.tone(330, 0.18, { type: "triangle", vol: 0.25, slide: 400 }); }
  beep() { this.tone(660, 0.15, { type: "square", vol: 0.12 }); }
  go() { this.tone(990, 0.35, { type: "square", vol: 0.14 }); }
  win() {
    [523, 523, 659, 784, 659, 784, 1047].forEach((f, i) =>
      this.tone(f, 0.22, { type: "triangle", vol: 0.28, at: i * 0.13 }));
  }

  // ---- background tune: a soft ice-cream-truck style loop ----
  startMusic() {
    if (this.musicTimer) return;
    const melody = [784, 659, 784, 880, 784, 659, 523, 587, 659, 587, 523, 587, 659, 0, 659, 0,
                    698, 659, 587, 659, 698, 784, 880, 784, 659, 523, 587, 659, 523, 0, 0, 0];
    const bass = [131, 196, 165, 196, 147, 196, 175, 196];
    this.musicTimer = setInterval(() => {
      const i = this.musicStep++ % melody.length;
      if (melody[i]) this.tone(melody[i], 0.2, { type: "triangle", vol: 0.06 });
      if (i % 4 === 0) this.tone(bass[(i / 4) % bass.length], 0.3, { type: "sine", vol: 0.08 });
    }, 210);
  }
  stopMusic() {
    clearInterval(this.musicTimer);
    this.musicTimer = null;
  }
}

export const sound = new Sound();
