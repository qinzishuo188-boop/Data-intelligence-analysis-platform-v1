import fs from "node:fs/promises";
import pptxgen from "pptxgenjs";

function addText(slide, text, x, y, w, h, fontSize, color = "183153", bold = false) {
  slide.addText(String(text || ""), {
    x,
    y,
    w,
    h,
    fontFace: "Microsoft YaHei",
    fontSize,
    color,
    bold,
    margin: 0,
    breakLine: false,
    fit: "shrink",
  });
}

function safeCell(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}

async function main() {
  const specPath = process.argv[2];
  const specText = (await fs.readFile(specPath, "utf8")).replace(/^\uFEFF/, "");
  const spec = JSON.parse(specText);

  const pptx = new pptxgen();
  pptx.author = "数据智能分析平台";
  pptx.subject = "数据智能分析报告";
  pptx.title = spec.headline || "数据智能分析汇报";
  pptx.company = "Data Intelligence Analysis Platform";
  pptx.lang = "zh-CN";
  pptx.layout = "LAYOUT_WIDE";
  pptx.theme = {
    headFontFace: "Microsoft YaHei",
    bodyFontFace: "Microsoft YaHei",
    lang: "zh-CN",
  };

  const cover = pptx.addSlide();
  cover.background = { color: "F7FBFF" };
  cover.addShape(pptx.ShapeType.roundRect, {
    x: 0.25,
    y: 0.25,
    w: 12.83,
    h: 7.0,
    fill: { color: "FFFFFF" },
    line: { color: "D9E5F3", width: 1 },
    radius: 0.18,
  });
  addText(cover, spec.headline || "数据智能分析汇报", 0.65, 0.55, 8.8, 0.5, 28, "123A6B", true);
  addText(cover, `图表类型：${spec.chartType || "bar"}`, 0.65, 1.15, 3.6, 0.28, 14, "53708F");
  addText(cover, spec.summaryText || "系统已生成结构化数据与图表建议。", 0.65, 1.55, 11.2, 0.55, 15, "38556F");

  cover.addImage({
    path: spec.chartImage,
    x: 0.58,
    y: 2.55,
    w: 7.9,
    h: 3.75,
    sizing: { type: "contain", x: 0.58, y: 2.55, w: 7.9, h: 3.75 },
  });
  cover.addShape(pptx.ShapeType.roundRect, {
    x: 8.85,
    y: 2.55,
    w: 3.6,
    h: 3.75,
    fill: { color: "F8FBFF" },
    line: { color: "D9E5F3", width: 1 },
    radius: 0.14,
  });
  addText(cover, "分析要点", 9.12, 2.83, 1.8, 0.28, 18, "1565C0", true);

  let y = 3.35;
  for (const line of (spec.insights || []).slice(0, 5)) {
    addText(cover, `• ${line}`, 9.12, y, 2.85, 0.42, 12, "38556F");
    y += 0.58;
  }

  const tableSlide = pptx.addSlide();
  tableSlide.background = { color: "F7FBFF" };
  addText(tableSlide, "结构化数据预览", 0.55, 0.42, 3.4, 0.36, 26, "123A6B", true);
  addText(tableSlide, "展示前 8 行关键数据，便于直接用于 PPT 和汇报材料。", 0.55, 0.85, 5.6, 0.25, 13, "53708F");

  const columns = spec.columns || [];
  const rows = spec.rows || [];
  const tableValues = [
    columns.map((column) => ({ text: safeCell(column), options: { bold: true, color: "FFFFFF", fill: "1565C0" } })),
    ...rows.slice(0, 8).map((row) => columns.map((col) => safeCell(row[col]))),
  ];
  if (columns.length) {
    tableSlide.addTable(tableValues, {
      x: 0.5,
      y: 1.28,
      w: 12.3,
      h: 5.35,
      border: { type: "solid", color: "D9E5F3", pt: 1 },
      fontFace: "Microsoft YaHei",
      fontSize: 10,
      color: "264766",
      valign: "mid",
      margin: 0.06,
    });
  } else {
    addText(tableSlide, "暂无结构化数据", 0.55, 1.35, 3.0, 0.4, 16, "53708F");
  }

  const ideaSlide = pptx.addSlide();
  ideaSlide.background = { color: "F7FBFF" };
  addText(ideaSlide, "图表建议与洞察", 0.55, 0.48, 3.8, 0.38, 26, "123A6B", true);

  let cardTop = 1.35;
  for (const text of (spec.chartIdeas || []).slice(0, 5)) {
    ideaSlide.addShape(pptx.ShapeType.roundRect, {
      x: 0.58,
      y: cardTop,
      w: 12.1,
      h: 0.72,
      fill: { color: "FFFFFF" },
      line: { color: "D9E5F3", width: 1 },
      radius: 0.12,
    });
    addText(ideaSlide, text, 0.9, cardTop + 0.22, 10.9, 0.28, 18, "264766", true);
    cardTop += 0.92;
  }

  await pptx.writeFile({ fileName: spec.pptxPath });
  console.log(spec.pptxPath);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
