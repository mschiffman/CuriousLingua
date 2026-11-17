// One-time importer: reads lesson data out of the old LANGUAGES pages and writes
// content/<course>/<strand>/<slug>.json for the new site. Nothing in LANGUAGES is changed.
// usage: node tools/import_legacy.js "C:\Users\...\LANGUAGES"
const fs = require("fs"), path = require("path"), vm = require("vm");
const SRC = process.argv[2], OUT = path.join(__dirname, "..", "content");
const BASE = "https://languages.rmlives.com/";
const NAMES = ["AUD_DIR","AUD_EXT","IMG_DIR","IMG_EXT","categories","quiz","quizTags","pages","TRANSLATION"];

function data(html) {
  const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).filter(b => /const AUD_DIR/.test(b));
  if (!blocks.length) return null;
  const code = blocks[0] + "\n;({" + NAMES.map(n => `${n}: typeof ${n} === "undefined" ? undefined : ${n}`).join(",") + "})";
  try { return vm.runInNewContext(code, {}, { timeout: 2000 }); } catch (e) { return null; }
}
const text = s => s.replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&#8239;/g, "\u202F").replace(/&quot;/g, '"').replace(/\s+/g, " ").trim();
const rel = u => (u || "").startsWith(BASE) ? u.slice(BASE.length) : u;
function write(course, strand, slug, obj) {
  const dir = path.join(OUT, course, strand); fs.mkdirSync(dir, { recursive: true });
  const f = path.join(dir, slug + ".json");
  if (fs.existsSync(f)) { // keep hand edits: level, topic, order are never overwritten
    const old = JSON.parse(fs.readFileSync(f, "utf8"));
    for (const k of ["level","level_provisional","topic","order","title","subtitle"]) if (k in old) obj[k] = old[k];
  }
  fs.writeFileSync(f, JSON.stringify(obj, null, 1) + "\n"); return f;
}

// ---- French expressions: topic groups as in sitemap.html
const FR_GROUP = { Positive: "admiration compliment excitement thank congrats", Negative: "annoyance disbelief dismissal quality refusal critique fatigue regret" };
const frGroup = s => Object.keys(FR_GROUP).find(g => FR_GROUP[g].split(" ").includes(s)) || "Conversational";
const FR_A1 = "greetings thank apology understand requests likes_dislikes directions restaurant help wishes".split(" ");
const FR_B1 = "connectors fillers iMean idioms doucement voila quality dismissal disbelief critique miscellaneous".split(" ");
let n = { fr: 0, en: 0, read: 0, voc: 0 };
for (const f of fs.readdirSync(path.join(SRC, "fr/expression"))) {
  if (!f.endsWith(".html") || /^(me-|slides-|video-|archive)|_quiz/.test(f)) continue;
  const html = fs.readFileSync(path.join(SRC, "fr/expression", f), "utf8"), d = data(html);
  if (!d || !d.categories) continue;
  const slug = f.slice(0, -5);
  write("fr", "expressions", slug, {
    title: text((html.match(/<h1[\s\S]*?<\/h1>/) || [""])[0]), subtitle: text((html.match(/<\/h1>\s*(<p[\s\S]*?<\/p>)/) || ["", ""])[1]),
    level: FR_A1.includes(slug) ? "a1" : FR_B1.includes(slug) ? "b1" : "a2", level_provisional: true,
    strand: "expressions", topic: frGroup(slug), type: "cards", legacy: "fr/expression/" + f,
    aud_dir: rel(d.AUD_DIR), aud_ext: d.AUD_EXT, categories: d.categories, quiz: d.quiz, quizTags: d.quizTags });
  n.fr++;
}
// ---- English expressions (the Speaking strand)
const EN_ORDER = "greet_goodbye thank apology exclamation not_understanding ask offer_accept polite_refusal likes_dislikes opinion agree_disagree small_talk wishes_celebrations invitations comfort compliments advice directions shopping restaurant phone health classroom emergency".split(" ");
for (const f of fs.readdirSync(path.join(SRC, "eng/expressions"))) {
  if (!f.endsWith(".html") || /_quiz/.test(f)) continue;
  const html = fs.readFileSync(path.join(SRC, "eng/expressions", f), "utf8"), d = data(html);
  if (!d || !d.categories) continue;
  const slug = f.slice(0, -5), i = EN_ORDER.indexOf(slug);
  write("eng", "speaking", slug, {
    title: text((html.match(/<h1[\s\S]*?<\/h1>/) || [""])[0]), subtitle: text((html.match(/<\/h1>\s*(<p[\s\S]*?<\/p>)/) || ["", ""])[1]),
    level: i >= 0 && i < 9 ? "a1" : "a2", level_provisional: true, order: i < 0 ? 99 : i + 1,
    strand: "speaking", topic: "Everyday expressions", type: "cards", legacy: "eng/expressions/" + f,
    aud_dir: rel(d.AUD_DIR), aud_ext: d.AUD_EXT, categories: d.categories, quiz: d.quiz, quizTags: d.quizTags });
  n.en++;
}
// ---- Stories and picture vocabulary (readers)
function group(slug) {
  if (/^voc[_-]/.test(slug)) return ["vocabulary", "Picture words", "pre-a1"];
  if (/^1\./.test(slug)) return ["reading", "Level 1 readers", "pre-a1"];
  if (/^2\./.test(slug)) return ["reading", "Level 2 readers", "a1"];
  if (/^s\d/.test(slug)) return ["reading", "Science and nature", "a2"];
  if (/^hb/.test(slug)) return ["reading", "Science and nature", "a2"];
  if (/lion|ant_|boy_wolf|bundle|fox|goose|hare|Dog_and/i.test(slug)) return ["reading", "Aesop's fables", "a2"];
  return ["reading", "Fairy tales and stories", "a2"];
}
for (const f of fs.readdirSync(path.join(SRC, "stories"))) {
  if (!f.endsWith(".html") || /quiz|_mix/.test(f)) continue;
  const html = fs.readFileSync(path.join(SRC, "stories", f), "utf8");
  if (!/ytstory\.js/.test(html)) continue;
  const d = data(html); if (!d || !d.pages) continue;
  const slug = f.slice(0, -5), [strand, topic, level] = group(slug);
  const lang = (html.match(/<html lang="(\w+)"/) || [, "en"])[1];
  const course = lang === "fr" ? "fr" : "eng";
  write(course, course === "fr" ? "reading" : strand, slug, {
    title: text((html.match(/<title>[\s\S]*?<\/title>/) || [""])[0]),
    level, level_provisional: true, strand: course === "fr" ? "reading" : strand, topic: course === "fr" ? "Nature" : topic, type: "reader", legacy: "stories/" + f,
    img_dir: (d.IMG_DIR || "").replace(/^\//, ""), img_ext: d.IMG_EXT || "jpg", aud_dir: rel(d.AUD_DIR), aud_ext: d.AUD_EXT || "mp3",
    translation: d.TRANSLATION, pages: d.pages });
  strand === "vocabulary" ? n.voc++ : n.read++;
}
console.log("imported:", n);
