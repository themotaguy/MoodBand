// Builds the mid-term presentation (Oct 28, 2026): Docs/MoodBand_Midterm_Presentation.pptx
// Numbers come from model/results/benchmark/*.csv so the slides match the repo.
// Usage (from repo root): PPTX_SKILL_DIR=<pptx skill dir> node presentation/build_midterm.js
// (the skill provides scripts/apply_theme.js, which writes the theme colours into the file).
// Charts are drawn from shapes because Keynote does not import pptxgenjs charts.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");

const SKILL = process.env.PPTX_SKILL_DIR;
const { applyTheme } = require(path.join(SKILL, "scripts/apply_theme.js"));

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "Docs", "MoodBand_Midterm_Presentation.pptx");
const RESULTS = path.join(ROOT, "model", "results", "benchmark");

const THEME = {
  name: "MoodBand",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1C1B3A", lt1: "FFFFFF", dk2: "4A4870", lt2: "F3F3F8",
    accent1: "4F46B8", accent2: "E0952B", accent3: "1F9E8F", accent4: "C8504B",
    accent5: "8F8CB8", accent6: "DCDAF0", hlink: "4F46B8", folHlink: "4A4870",
  },
};
const HEX = THEME.colors;
// Indigo sequential ramp for the confusion-matrix cells (light -> dark).
const RAMP = ["F1F0FB", "DEDCF5", "C4C1EC", "A6A2E0", "8681D2", "6761C3", "4C45A9", "342E86"];

// ---------- data ----------
function readCsv(file) {
  const [header, ...rows] = fs.readFileSync(path.join(RESULTS, file), "utf8").trim().split("\n");
  const keys = header.split(",");
  return rows.map(r => Object.fromEntries(r.split(",").map((v, i) => [keys[i], v])));
}
const summary = readCsv("summary.csv");
const cmRows = readCsv("confusion_matrices.csv");
const CLASSES = ["happy", "neutral", "sad", "stressed"];
function confusion(model) {
  return CLASSES.map(rep => {
    const r = cmRows.find(x => x.model === model && x.reported === rep);
    const counts = CLASSES.map(c => Number(r[c]));
    const total = counts.reduce((a, b) => a + b, 0);
    return counts.map(c => c / total);
  });
}
const score = name => Number(summary.find(s => s.model === name).balanced_accuracy_mean);

// ---------- helpers ----------
async function iconPng(Icon, hex) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Icon, { size: 256, color: "#" + hex }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
  pres.title = "MoodBand mid-term presentation";
  pres.author = "Ritik Pravin Mota";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  // Icons are pre-rendered once per (icon, colour).
  const cache = new Map();
  const icon = async (Icon, hex = "FFFFFF") => {
    const key = Icon.name + hex;
    if (!cache.has(key)) cache.set(key, await iconPng(Icon, hex));
    return cache.get(key);
  };
  async function iconCircle(slide, Icon, x, y, d, fill, name) {
    slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { type: "none" }, objectName: name + " circle" });
    const pad = d * 0.24;
    slide.addImage({ data: await icon(Icon), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, altText: name, objectName: name + " icon" });
  }
  function card(slide, x, y, w, h, name, fill = C.background2) {
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { type: "none" }, objectName: name });
  }
  const T = (slide, text, opts) => slide.addText(text, { isTextBox: true, margin: 0, color: C.text1, fontSize: 14, valign: "top", ...opts });

  // ---------- layouts ----------
  pres.defineSlideMaster({
    title: "Title (dark)",
    background: { color: C.text1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 1.45, w: 8.8, h: 1.05, fontSize: 54, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 2.6, w: 8.8, h: 0.9, fontSize: 20, color: C.accent6, valign: "top", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "Title only",
    background: { color: C.background1 },
    margin: [0.5, 0.5, 0.5, 0.5],
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.35, w: 9.0, h: 0.75, fontSize: 32, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
      { text: { text: "MoodBand · Mid-term · Oct 28, 2026", options: { x: 0.5, y: 5.2, w: 5, h: 0.3, fontSize: 10, color: C.text2, margin: 0 } } },
    ],
    slideNumber: { x: 9.0, y: 5.2, w: 0.5, h: 0.3, fontSize: 10, color: C.text2, align: "right" },
  });
  pres.defineSlideMaster({
    title: "Closing (dark)",
    background: { color: C.text1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.35, w: 9.0, h: 0.75, fontSize: 32, bold: true, color: C.background1, valign: "middle", align: "left", margin: 0 }, text: "" } },
    ],
    slideNumber: { x: 9.0, y: 5.2, w: 0.5, h: 0.3, fontSize: 10, color: C.accent6, align: "right" },
  });
  const content = (sectionTitle, title) => {
    const s = pres.addSlide({ masterName: "Title only", sectionTitle });
    s.addText(title, { placeholder: "title" });
    return s;
  };

  // ================= INTRODUCTION =================
  pres.addSection({ title: "Introduction" });

  // 1 — Title
  {
    const s = pres.addSlide({ masterName: "Title (dark)", sectionTitle: "Introduction" });
    s.addText("MoodBand", { placeholder: "title" });
    s.addText("Inclusive mood detection and adaptive feedback from a consumer wearable", { placeholder: "body" });
    await iconCircle(s, fa.FaHeartbeat, 0.6, 0.55, 0.7, C.accent2, "Heartbeat");
    T(s, [
      { text: "Mid-term presentation · October 28, 2026", options: { breakLine: true, bold: true } },
      { text: "Ritik Pravin Mota · M.S. Data Science", options: { breakLine: true } },
      { text: "Supervisor: Prof. Rached Zantout · Khoury College of Computer Sciences, Northeastern University" },
    ], { x: 0.6, y: 3.9, w: 8.8, h: 1.0, color: C.background1, fontSize: 14, paraSpaceAfter: 4 });
    s.addNotes("MoodBand detects a user's mood from a Fitbit and responds with feedback they can see, hear or feel, designed from the start for both sighted and visually impaired users. In ten minutes: the problem and the idea, what's built so far, and what's left.");
  }

  // 2 — Problem
  {
    const s = content("Introduction", "Mood tools stop at tracking");
    const items = [
      [fa.FaPencilAlt, "Self-report only", "Most apps rely on people remembering to log their mood: easy to forget, always after the fact."],
      [fa.FaSyncAlt, "No closed loop", "Tools log or chart mood, but rarely help someone regulate it in the moment."],
      [fa.FaUniversalAccess, "Visual-first", "Dashboards and colour charts exclude visually impaired users, and screen readers don't reliably fill the gap."],
    ];
    for (const [i, [Ic, head, body]] of items.entries()) {
      const x = 0.5 + i * 3.15;
      card(s, x, 1.4, 2.85, 3.45, head + " card");
      await iconCircle(s, Ic, x + 0.3, 1.7, 0.7, [C.accent1, C.accent2, C.accent3][i], head);
      T(s, head, { x: x + 0.3, y: 2.6, w: 2.3, h: 0.45, fontSize: 20, bold: true, fontFace: THEME.headFontFace });
      T(s, body, { x: x + 0.3, y: 3.15, w: 2.3, h: 1.55 });
    }
    s.addNotes("Three gaps. First, most mood tools depend on self-report. Second, they track mood but don't help regulate it. Third, they're built for the screen: my literature review found screen readers don't reliably make these apps usable for visually impaired people. MoodBand targets all three.");
  }

  // 3 — Solution pipeline
  {
    const s = content("Introduction", "MoodBand closes the loop");
    const steps = [
      [fa.FaHeartbeat, "Sense", "Fitbit heart rate and steps via the Google Health API, on Android and iOS"],
      [fa.FaBrain, "Classify", "A model reads the last 30 minutes: happy, neutral, sad, stressed, angry"],
      [fa.FaBalanceScale, "Decide", "Acts only when confident, persistent, and not right after exercise"],
      [fa.FaMobileAlt, "Feedback", "The phone plays audio, vibration or visual cues for the user's profile"],
    ];
    for (const [i, [Ic, head, body]] of steps.entries()) {
      const x = 0.5 + i * 2.3;
      card(s, x, 1.4, 2.0, 2.75, head + " step");
      await iconCircle(s, Ic, x + 0.25, 1.65, 0.6, C.accent1, head);
      T(s, head, { x: x + 0.25, y: 2.4, w: 1.6, h: 0.4, fontSize: 18, bold: true, fontFace: THEME.headFontFace });
      T(s, body, { x: x + 0.25, y: 2.85, w: 1.6, h: 1.25 });
      if (i < 3) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 2.04, y: 2.62, w: 0.22, h: 0.3, fill: { color: C.accent5 }, line: { type: "none" }, objectName: "Arrow " + (i + 1) });
    }
    await iconCircle(s, fa.FaFlask, 0.5, 4.45, 0.4, C.accent2, "Offline first");
    T(s, "Built and tested offline on public datasets first; the live Fitbit and the user trial come last.", { x: 1.05, y: 4.47, w: 8.4, h: 0.4, valign: "middle", color: C.text2 });
    s.addNotes("The system is a four-stage loop. Sense: heart rate and steps from a Fitbit through Google's cloud API, which is why it works on both Android and iOS. Classify: a model reads the last 30 minutes of data. Decide: a cautious decision module chooses whether to say anything at all. Feedback: the phone delivers it through the channels that suit the user. Following my supervisor's advice, everything is built offline on public data before the live Fitbit.");
  }

  // ================= PROGRESS =================
  pres.addSection({ title: "Progress so far" });

  // 4 — Milestones
  {
    const s = content("Progress so far", "Progress so far");
    const done = [
      [fa.FaBookOpen, "Literature review", "23 references, now covering interventions and feedback timing"],
      [fa.FaFileAlt, "Proposal updated", "Revised with the final review and current design"],
      [fa.FaChartBar, "First mood model", "LifeSnaps baseline: 0.33 vs 0.25 chance"],
      [fa.FaFlask, "Model benchmark", "Six models compared on identical splits"],
      [fa.FaSlidersH, "Feedback module", "Guardrails tuned by simulation; 23 automated tests"],
      [fa.FaMobileAlt, "iPhone prototype", "Notifications, haptics and VoiceOver; all device checks pass"],
    ];
    for (const [i, [Ic, head, body]] of done.entries()) {
      const x = 0.5 + (i % 3) * 3.15, y = 1.3 + Math.floor(i / 3) * 1.9;
      card(s, x, y, 2.85, 1.75, head + " card");
      await iconCircle(s, Ic, x + 0.25, y + 0.25, 0.5, C.accent3, head);
      T(s, head, { x: x + 0.9, y: y + 0.27, w: 1.75, h: 0.45, fontSize: 16, bold: true, valign: "middle" });
      T(s, body, { x: x + 0.25, y: y + 0.88, w: 2.4, h: 0.75 });
    }
    s.addNotes("Six milestones are done: the literature review with 23 references, the updated proposal, a first mood model, a benchmark of six models, the feedback-decision module, and an iPhone prototype tested end to end. The next slides cover each of the technical pieces.");
  }

  // 5 — First model
  {
    const s = content("Progress so far", "A first model: real but modest signal");
    const facts = [
      [fa.FaDatabase, "LifeSnaps dataset: Fitbit Sense, 71 people, about 4 months"],
      [fa.FaListUl, "1,961 in-the-moment mood reports from 61 people, mapped to 4 moods"],
      [fa.FaClock, "Features from the 30 minutes before each report, as the app would see them"],
      [fa.FaUserFriends, "Tested only on people the model never saw in training"],
    ];
    for (const [i, [Ic, text]] of facts.entries()) {
      const y = 1.45 + i * 0.75;
      await iconCircle(s, Ic, 0.5, y, 0.5, C.accent1, "Fact " + (i + 1));
      T(s, text, { x: 1.2, y, w: 4.4, h: 0.5, valign: "middle" });
    }
    card(s, 6.0, 1.4, 3.5, 2.9, "Headline stat card");
    T(s, score("Random Forest").toFixed(2), { x: 6.3, y: 1.6, w: 2.9, h: 1.1, fontSize: 66, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
    T(s, "balanced accuracy for the Random Forest on unseen people", { x: 6.3, y: 2.75, w: 2.9, h: 0.6 });
    T(s, "Chance is 0.25 (four moods)", { x: 6.3, y: 3.55, w: 2.9, h: 0.4, color: C.text2, italic: true });
    T(s, "Tried and dropped: last night's HRV and sleep (hurt accuracy on new people) and the PMData dataset (once-a-day labels too coarse).",
      { x: 0.5, y: 4.55, w: 9.0, h: 0.5, color: C.text2, fontSize: 13 });
    s.addNotes("The model is trained on LifeSnaps, a public Fitbit dataset whose participants reported their mood several times a day. For each report I use heart rate and steps from the 30 minutes before it, which mirrors how the app will work live. Tested on people it has never seen, the Random Forest reaches 0.33 balanced accuracy against 0.25 chance: a real signal, but a modest one. Overnight HRV and a second dataset didn't help.");
  }

  // 6 — Benchmark chart
  {
    const s = content("Progress so far", "The Random Forest stays");
    const order = [...summary].sort((a, b) => b.balanced_accuracy_mean - a.balanced_accuracy_mean);
    // Drawn from shapes, not addChart(): Keynote doesn't import pptxgenjs charts, and the
    // deck may be presented from Keynote. Same scale for bars, ticks and the chance line.
    const x0 = 2.45, x1 = 5.85, vmax = 0.4, top = 1.4, rowH = 0.52;
    const X = v => x0 + (v / vmax) * (x1 - x0);
    for (const t of [0, 0.1, 0.2, 0.3, 0.4]) {
      s.addShape(pres.shapes.LINE, { x: X(t), y: top - 0.05, w: 0, h: rowH * order.length + 0.05, line: { color: "E4E3EE", width: 0.75 }, objectName: "Gridline " + t });
      T(s, t.toFixed(1), { x: X(t) - 0.3, y: top + rowH * order.length + 0.05, w: 0.6, h: 0.25, fontSize: 10, color: C.text2, align: "center" });
    }
    order.forEach((o, i) => {
      const v = Number(o.balanced_accuracy_mean), y = top + i * rowH;
      T(s, o.model, { x: 0.5, y, w: 1.85, h: rowH, fontSize: 12, align: "right", valign: "middle", color: C.text2 });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x0, y: y + 0.11, w: X(v) - x0, h: 0.3, rectRadius: 0.05,
        fill: { color: o.model === "Majority class" ? C.accent5 : C.accent1 }, line: { type: "none" }, objectName: o.model + " bar" });
      T(s, v.toFixed(3), { x: X(v) + 0.06, y, w: 0.6, h: rowH, fontSize: 11, valign: "middle" });
    });
    s.addShape(pres.shapes.LINE, { x: X(0.25), y: top - 0.05, w: 0, h: rowH * order.length + 0.05, line: { color: HEX.dk2, width: 1.25 }, objectName: "Chance line" });
    T(s, "Balanced accuracy on unseen people, mean of 5 seeds. Dark line = chance (0.25).", { x: 0.5, y: 4.85, w: 5.6, h: 0.3, fontSize: 11, color: C.text2 });
    const points = [
      ["SVM 0.351 vs Random Forest 0.334", "Ahead on plain predictions, on every split, mainly by catching sad"],
      ["But not with probabilities", "Which feedback needs: the SVM then drops to 0.320 and never predicts sad"],
      ["More complex is not better", "Boosting and the neural network do worse; extra Fitbit signals (sleep, HRV, calories) didn't help either"],
    ];
    for (const [i, [head, body]] of points.entries()) {
      const y = 1.4 + i * 1.18;
      T(s, head, { x: 6.45, y, w: 3.05, h: 0.35, bold: true, fontSize: 15 });
      T(s, body, { x: 6.45, y: y + 0.38, w: 3.05, h: 0.75 });
    }
    s.addNotes("To check whether a more complex model helps, I compared six models on exactly the same data and splits. On plain predictions the SVM edges out the Random Forest on every split, mostly because it catches sad far more often. But the feedback module needs probabilities to decide when to act, and once the SVM gives them its advantage disappears: it drops to 0.320 and almost never predicts sad or stressed, so in the simulation it never suggested a break. So the Random Forest stays. Gradient boosting and a small neural network do worse. With about two thousand labels, model capacity isn't the bottleneck; the information in heart rate and steps is. I also tried adding the other signals the Google Health API offers: heart rate adjusted for activity, calories, exercise, and last night's sleep, HRV, oxygen and skin temperature. None of them improved accuracy on new people, and the overnight ones made it worse. So the limit is the signal and the number of people, not the model or the features. The next steps are more data and learning each user's own patterns.");
  }

  // 7 — Confusion matrices
  {
    const s = content("Progress so far", "Where the models get confused");
    const tables = [["Random Forest", confusion("Random Forest")], ["SVM (RBF)", confusion("SVM (RBF)")]];
    tables.forEach(([name, cm], t) => {
      const x = 0.5 + t * 4.7;
      T(s, name, { x, y: 1.3, w: 4.3, h: 0.35, bold: true, fontSize: 16 });
      const header = [{ text: "reported ↓ / predicted →", options: { fontSize: 10, color: C.text2, bold: false } },
        ...CLASSES.map(c => ({ text: c, options: { bold: true, color: C.text1, align: "center" } }))];
      const rows = cm.map((row, i) => [
        { text: CLASSES[i], options: { bold: true, color: C.text1 } },
        ...row.map(v => {
          const step = Math.min(RAMP.length - 1, Math.floor(v * 2 * RAMP.length));
          return { text: `${Math.round(v * 100)}%`, options: { align: "center", fill: { color: RAMP[step] }, color: step >= 4 ? "FFFFFF" : HEX.dk1, bold: i === CLASSES.indexOf(CLASSES[i]) && false } };
        }),
      ]);
      s.addTable([header, ...rows], {
        x, y: 1.75, w: 4.3, colW: [1.06, 0.81, 0.81, 0.81, 0.81], rowH: 0.48,
        fontSize: 14, fontFace: THEME.bodyFontFace, valign: "middle",
        border: { type: "solid", pt: 1.5, color: "FFFFFF" }, objectName: name + " confusion matrix",
      });
    });
    T(s, "Share of each reported mood predicted as each class (rows sum to 100%), pooled over 5 seeds. Darker = larger share. Both models mix up neutral with stressed and happy; the SVM finds sad far more often.",
      { x: 0.5, y: 4.35, w: 9.0, h: 0.7, fontSize: 13, color: C.text2 });
    s.addNotes("These confusion matrices show where the errors are. Read each row as: of the times people reported this mood, how often did the model predict each class. Both models confuse neutral with stressed and happy, which is expected since heart rate and steps can look similar across those states. On plain predictions the SVM's advantage is the sad row, 32 percent versus 17 percent, but as the previous slide showed, that advantage doesn't survive once it gives probabilities.");
  }

  // 8 — Interventions and profiles
  {
    const s = content("Progress so far", "A response for each mood, for each user");
    const rows = [
      ["Stressed", "Breathing pacer at 6 breaths/min, felt as vibration", "Breathwork and haptic-pacer studies"],
      ["Sad", "Music that matches a low mood, then brightens", "Iso principle (one small study)"],
      ["Angry", "Calming timer", "Design choice"],
      ["Happy / neutral", "Nothing, to avoid alert fatigue", "Inferred from fatigue evidence"],
      ["Recovery", "A brief, quiet positive cue", "Design choice"],
    ];
    const hdr = ["Mood", "Response", "Basis"].map(h => ({ text: h, options: { bold: true, color: C.background1, fill: { color: C.accent1 } } }));
    s.addTable([hdr, ...rows.map((r, i) => r.map((v, j) => ({ text: v, options: { bold: j === 0, fill: { color: i % 2 ? C.background1 : C.background2 }, color: j === 2 ? C.text2 : C.text1 } })))], {
      x: 0.5, y: 1.35, w: 5.9, colW: [1.35, 2.75, 1.8], fontSize: 13, fontFace: THEME.bodyFontFace, valign: "middle",
      border: { type: "none" }, margin: [0.06, 0.1, 0.06, 0.1], objectName: "Mood to intervention table",
    });
    const profiles = [
      [fa.FaEye, "Sighted", "Visual + vibration"],
      [fa.FaLowVision, "Low vision", "Audio + vibration, optional high contrast"],
      [fa.FaBlind, "Blind", "Audio + vibration, never visual-only"],
    ];
    for (const [i, [Ic, head, body]] of profiles.entries()) {
      const y = 1.35 + i * 1.25;
      card(s, 6.7, y, 2.8, 1.12, head + " profile card");
      await iconCircle(s, Ic, 6.88, y + 0.3, 0.5, C.accent2, head);
      T(s, head, { x: 7.55, y: y + 0.12, w: 1.85, h: 0.32, bold: true, fontSize: 15 });
      T(s, body, { x: 7.55, y: y + 0.45, w: 1.85, h: 0.62, fontSize: 13 });
    }
    s.addNotes("Each mood gets a response grounded in the literature where evidence exists: a vibration-paced breathing exercise for stress, and music that starts low and brightens for sadness. Where there's no evidence, for anger and for positive feedback, I've marked it as a design choice to test. Happy and neutral get no feedback at all, to avoid fatigue. On the right are the three accessibility profiles: blind users always get audio and vibration together.");
  }

  // 9 — Decision module
  {
    const s = content("Progress so far", "Cautious by design");
    const rules = [
      [fa.FaCheckCircle, "Acts only on a confident prediction that persists"],
      [fa.FaRunning, "Ignores “stressed” right after exercise"],
      [fa.FaMoon, "At most 4 a day, 30 minutes apart, never at night"],
      [fa.FaQuestionCircle, "Always asks first, then “Was this right?”"],
    ];
    for (const [i, [Ic, text]] of rules.entries()) {
      const y = 1.45 + i * 0.78;
      await iconCircle(s, Ic, 0.5, y, 0.5, C.accent3, "Rule " + (i + 1));
      T(s, text, { x: 1.2, y, w: 4.3, h: 0.5, valign: "middle" });
    }
    card(s, 6.0, 1.35, 3.5, 1.45, "Interventions per day card");
    T(s, "1.2", { x: 6.3, y: 1.45, w: 1.4, h: 0.9, fontSize: 48, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
    T(s, "suggestions per person per day", { x: 6.3, y: 2.35, w: 3.0, h: 0.4 });
    card(s, 6.0, 2.95, 3.5, 1.45, "Precision card");
    T(s, "1 in 3", { x: 6.3, y: 3.0, w: 2.6, h: 0.85, fontSize: 48, bold: true, color: C.accent4, fontFace: THEME.headFontFace });
    T(s, [{ text: "match the reported mood", options: { breakLine: true } }, { text: "Chance: 1 in 4", options: { color: C.text2, italic: true } }], { x: 6.3, y: 3.8, w: 3.0, h: 0.55 });
    T(s, "Simulated on 1,295 real days (about 101,000 predictions). A stricter threshold cuts interruptions, not errors: the model's confidence doesn't track whether it's right, so asking first and learning from “Was this right?” matter.",
      { x: 0.5, y: 4.6, w: 9.0, h: 0.5, fontSize: 12, color: C.text2 });
    s.addNotes("Because the model is modest, the decision module is deliberately cautious. It needs a confident, persistent prediction, ignores stress right after exercise, limits how often it speaks, and always asks before starting. I replayed predictions across 1,295 real days: it suggests a break about 1.2 times a day, and those suggestions match the person's reported mood about one time in three, versus one in four by chance. Raising the threshold didn't improve that, which tells us the confidence isn't calibrated. The 'Was this right?' answers are how it will learn each person.");
  }

  // 10 — iPhone prototype
  {
    const s = content("Progress so far", "Tested on a real iPhone");
    const flow = [
      [fa.FaBell, "Notification", "“Want a 1-minute breathing break?”"],
      [fa.FaPlayCircle, "Start or Not now", "Nothing plays until the user agrees"],
      [fa.FaWind, "Breathing break", "Vibration, breathing circle and voice"],
      [fa.FaComments, "Was this right?", "Yes, no or snooze, kept as a label"],
    ];
    for (const [i, [Ic, head, body]] of flow.entries()) {
      const x = 0.5 + i * 2.3;
      card(s, x, 1.35, 2.0, 1.75, head + " step");
      await iconCircle(s, Ic, x + 0.2, 1.55, 0.45, C.accent1, head);
      T(s, head, { x: x + 0.2, y: 2.08, w: 1.65, h: 0.33, bold: true, fontSize: 14 });
      T(s, body, { x: x + 0.2, y: 2.43, w: 1.65, h: 0.62, fontSize: 13 });
      if (i < 3) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 2.04, y: 2.07, w: 0.22, h: 0.3, fill: { color: C.accent5 }, line: { type: "none" }, objectName: "Flow arrow " + (i + 1) });
    }
    const findings = [
      [fa.FaHandPaper, "Vibration is only felt in the hand", "Barely noticeable on a table and not at all in a pocket, so suggestions arrive as a notification and play once opened."],
      [fa.FaVolumeUp, "VoiceOver talked over the app's voice", "Spoken guidance now goes through VoiceOver when it is on, so the two never overlap."],
    ];
    for (const [i, [Ic, head, body]] of findings.entries()) {
      const x = 0.5 + i * 4.65;
      card(s, x, 3.3, 4.35, 1.55, head + " finding");
      await iconCircle(s, Ic, x + 0.22, 3.5, 0.45, C.accent2, head);
      T(s, head, { x: x + 0.85, y: 3.5, w: 3.3, h: 0.45, bold: true, fontSize: 14, valign: "middle" });
      T(s, body, { x: x + 0.22, y: 4.05, w: 3.95, h: 0.75, fontSize: 13 });
    }
    s.addNotes("The app is built in React Native, so one codebase covers Android and iOS. I've tested it end to end on an iPhone: a notification suggests a break, the user chooses to start, the break plays, and it ends by asking whether the suggestion was right. Testing changed the design twice. Phone vibration is only felt in the hand, so suggestions now arrive as a notification first. And VoiceOver overlapped with the app's own voice, so guidance is now spoken through VoiceOver.");
  }

  // ================= WHAT'S LEFT =================
  pres.addSection({ title: "What's left" });

  // 11 — Remaining work
  {
    const s = content("What's left", "What's left");
    const cols = [
      [fa.FaDatabase, "Data and model", "Weeks 7–10", ["EmoPhone and TILES-2018 (anger)", "Train the five-mood model", "Re-run the benchmark"]],
      [fa.FaPlug, "Integration", "Weeks 11–13", ["Model + decisions in the app", "Save answers as labels", "Live Fitbit via Google Health API"]],
      [fa.FaUserCheck, "Trial and report", "Weeks 14–16", ["User trial, after consent", "Evaluate model and feedback", "Final report"]],
    ];
    for (const [i, [Ic, head, weeks, items]] of cols.entries()) {
      const x = 0.5 + i * 3.15;
      card(s, x, 1.35, 2.85, 3.5, head + " card");
      await iconCircle(s, Ic, x + 0.25, 1.6, 0.55, [C.accent1, C.accent3, C.accent2][i], head);
      T(s, [{ text: head, options: { bold: true, fontSize: 16, breakLine: true } }, { text: weeks, options: { fontSize: 13, color: C.text2 } }],
        { x: x + 0.25, y: 2.3, w: 2.4, h: 0.6 });
      T(s, items.map((t, k) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: k < items.length - 1 } })),
        { x: x + 0.25, y: 3.05, w: 2.45, h: 1.65, paraSpaceAfter: 6 });
    }
    s.addNotes("Three phases remain, following the proposal's timeline. First, the data: anger is required, so I need the EmoPhone and TILES datasets, then I'll train the five-mood model and re-run the benchmark on each dataset. Second, integration: connect the model and decision module to the app, save the users' answers, and connect the live Fitbit through the Google Health API. Third, a user trial with volunteers once consent is in place, then evaluation and the final report.");
  }

  // 12 — Risks and support needed (closing)
  {
    const s = pres.addSlide({ masterName: "Closing (dark)", sectionTitle: "What's left" });
    s.addText("Risks and support needed", { placeholder: "title" });
    const risks = [
      ["Dataset access", "EmoPhone request pending; TILES-2018 agreement needs a Northeastern signature"],
      ["Modest signal", "Heart rate and steps carry limited mood information; learn per person from user answers"],
      ["Trial participants", "Friends only, so no visually impaired users; stated as a limitation, checked with VoiceOver"],
      ["Consent", "User-trial agreement to confirm before recruiting"],
    ];
    risks.forEach(([head, body], i) => {
      const y = 1.35 + i * 0.75;
      T(s, head, { x: 0.5, y, w: 2.3, h: 0.6, bold: true, fontSize: 15, color: C.accent2, valign: "middle" });
      T(s, body, { x: 2.9, y, w: 6.6, h: 0.6, color: C.background1, valign: "middle" });
    });
    T(s, "Thank you. Questions?", { x: 0.5, y: 4.45, w: 9.0, h: 0.55, fontSize: 24, bold: true, color: C.background1, fontFace: THEME.headFontFace });
    s.addNotes("The main risks: access to the datasets with anger labels, where the TILES agreement needs Northeastern's signature; the modest signal, which I'll address by learning from each user's answers; and a trial without visually impaired participants, which I state as a limitation. Thank you, happy to take questions.");
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("Wrote " + path.relative(ROOT, OUT));
}

main().catch(e => { console.error(e); process.exit(1); });
