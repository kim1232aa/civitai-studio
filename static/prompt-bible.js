/* v0821o136-prompt-bible — structured reverse prompt. Never invent character facts. */
(function (root) {
  "use strict";
  var HEAD = "【反推提示词】";
  var KEYS = ["主体", "外观", "服装", "姿态", "场景", "光线", "构图", "画面", "运镜", "约束", "负面"];

  function parseLabeled(text) {
    var map = {};
    var current = null;
    var unlabeled = [];
    String(text || "")
      .replace(/\r/g, "")
      .split("\n")
      .forEach(function (line) {
        var m = line.match(/^(?:【)?([\u4e00-\u9fff]{2,6})(?:】)?[：:]\s*(.*)$/);
        var key = m && m[1];
        if (key === "反推提示词") return;
        if (key && (KEYS.indexOf(key) >= 0 || key === "视觉描述")) {
          current = key;
          map[key] = m[2] || "";
          return;
        }
        if (current) {
          map[current] = (map[current] ? map[current] + "\n" : "") + line;
        } else if (line.trim() && line.trim() !== HEAD) {
          unlabeled.push(line);
        }
      });
    return { map: map, unlabeled: unlabeled.join("\n").trim() };
  }

  function formatReversePrompt(caption) {
    var raw = String(caption || "").trim();
    if (!raw) return "";
    var parsed = parseLabeled(raw);
    var map = parsed.map;
    var filled = KEYS.some(function (k) {
      return String(map[k] || "").trim();
    });
    var lines = [HEAD];
    var visual = String(map["视觉描述"] || "").trim();
    if (!filled) {
      lines.push("视觉描述：" + (visual || raw));
    } else if (visual || parsed.unlabeled) {
      lines.push("视觉描述：" + (visual || parsed.unlabeled));
    }
    KEYS.forEach(function (k) {
      lines.push(k + "：" + String(map[k] || "").trim());
    });
    return lines.join("\n");
  }

  var api = {
    HEAD: HEAD,
    KEYS: KEYS,
    parseLabeled: parseLabeled,
    formatReversePrompt: formatReversePrompt,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.PromptBible = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
