// Only needed when the page shells or site.js change (new utility classes).
// Rebuild with tools\rebuild_css.bat. Adding lessons never needs it.
module.exports = {
  content: ["./tools/build.py", "./assets/js/*.js"],
  theme: {
    extend: {
      colors: {
        paper: "#FAF7F2", ink: "#1E2330", muted: "#5B6475", line: "#E4DCCF", card: "#FFFFFF",
        accent: "rgb(var(--accent) / <alpha-value>)", good: "#1B7550", bad: "#B3261E",
      },
      fontFamily: {
        display: ['"Fraunces"', '"Noto Sans Myanmar"', "Georgia", "serif"],
        body: ['"Atkinson Hyperlegible"', '"Noto Sans Myanmar"', "system-ui", "sans-serif"],
      },
    },
  },
};
