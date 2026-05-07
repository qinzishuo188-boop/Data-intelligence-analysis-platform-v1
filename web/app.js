const state = {
  dataset: null,
  chart: null,
};

const palette = ["#67c2ff", "#2dd4bf", "#ffb65c", "#ff8f70", "#7ee0ff", "#8f7cf7"];

const procurementSample = "2025年第一季度，平台采购数据覆盖水果、粮油和日用品三大品类。水果品类中，红富士苹果采购金额为126000元，同比增长12.6%，占水果品类采购额的34%；花牛苹果采购金额为87000元，同比增长6.2%，占比23%。粮油品类中，大米采购金额为158000元，环比增长8.4%；面粉采购金额为121000元，环比增长5.1%；大豆油采购金额为96300元。平台以华东和华北区域为主，华东区域贡献占比46%，华北占比31%。用户画像以家庭采购和社区团购为主，核心用户集中在30至45岁。";
const growthSample = "根据2025年AI消费电子行业分析，AI PC、AI手机和智能穿戴是增长最快的三类产品。AI PC线上平台销售额同比增长58.3%，AI手机同比增长45.2%，智能穿戴同比增长32.7%。平台分布上，京东和天猫贡献主要销售额，抖音渠道增速最高。华东、华南和华北是主要销售区域，一线及新一线城市用户占比超过61%。报告指出，平台间竞争关系明显，京东在客单价上领先，抖音在增速和年轻用户渗透上表现突出。";

function setBanner(message, type = "info") {
  const banner = document.getElementById("statusBanner");
  banner.className = `status-banner ${type}`;
  banner.textContent = message;
}

function setButtonBusy(buttonId, busy, idleText, busyText) {
  const button = document.getElementById(buttonId);
  if (!button) return;
  button.disabled = busy;
  button.textContent = busy ? busyText : idleText;
}

async function checkHealth() {
  const badge = document.getElementById("healthBadge");
  const aiBadge = document.getElementById("aiBadge");
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    badge.textContent = data.ok ? "服务正常" : "服务异常";
    badge.className = `badge ${data.ok ? "success" : "danger"}`;
    if (aiBadge) {
      const enabled = Boolean(data.ai?.enabled);
      aiBadge.textContent = enabled ? `AI 已连接: ${data.ai.model}` : "AI 未配置";
      aiBadge.className = `badge ${enabled ? "success" : "pending"}`;
    }
  } catch {
    badge.textContent = "未启动";
    badge.className = "badge danger";
    if (aiBadge) {
      aiBadge.textContent = "AI 未检测";
      aiBadge.className = "badge pending";
    }
  }
}
async function ingestRequest(options) {
  const res = await fetch("/api/ingest", options);
  const data = await res.json();
  if (!data.ok) {
    setBanner(data.error || "操作失败，请检查输入内容。", "error");
    throw new Error(data.error || "ingest failed");
  }
  setDataset(data.dataset);
  setBanner("识别完成，结构化表格与图表推荐已生成。", "success");
}

async function uploadFile() {
  const file = document.getElementById("fileInput").files[0];
  if (!file) {
    setBanner("请先选择文件。", "error");
    return;
  }
  const formData = new FormData();
  formData.append("file", file);
  setButtonBusy("uploadBtn", true, "上传文件并解析", "正在解析...");
  try {
    await ingestRequest({ method: "POST", body: formData });
  } finally {
    setButtonBusy("uploadBtn", false, "上传文件并解析", "正在解析...");
  }
}

async function uploadText() {
  return uploadTextByMode("auto");
}

async function uploadTextByMode(mode) {
  const text = document.getElementById("textInput").value.trim();
  if (!text) {
    setBanner("请先粘贴文本内容。", "error");
    return;
  }
  const buttonId = mode === "ai" ? "textAiBtn" : "textRuleBtn";
  const idleText = mode === "ai" ? "AI 提取" : "常规提取";
  const busyText = mode === "ai" ? "AI 提取中..." : "常规提取中...";
  setButtonBusy(buttonId, true, idleText, busyText);
  try {
    await ingestRequest({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, mode }),
    });
  } finally {
    setButtonBusy(buttonId, false, idleText, busyText);
  }
}

function formatDisplayName(dataset) {
  if (!dataset) return "未导入";
  if (dataset.sourceKind === "text") return "文本识别";
  return dataset.sourceName || "文件导入";
}

function suggestionList(dataset) {
  if (!dataset) return [];
  return dataset.charts || dataset.suggestions || [];
}

function setDataset(dataset) {
  state.dataset = dataset;
  document.getElementById("datasetMeta").textContent = "";
  document.getElementById("sourceBadge").textContent = formatDisplayName(dataset);
  document.getElementById("rowBadge").textContent = String(dataset.rowCount);
  document.getElementById("renderBadge").textContent = String(suggestionList(dataset).length);
  document.getElementById("exportLinks").innerHTML = "";

  renderSelectors(dataset);
  renderSuggestions(suggestionList(dataset));
  renderTable(dataset.rows || [], dataset.columns || []);

  const firstSuggestion = suggestionList(dataset)[0];
  if (firstSuggestion) {
    applySuggestion(firstSuggestion);
  } else {
    renderChart();
  }
}
function renderSelectors(dataset) {
  const xField = document.getElementById("xField");
  const yFields = document.getElementById("yFields");
  xField.innerHTML = `<option value="">自动索引</option>`;
  yFields.innerHTML = "";

  dataset.columns.forEach((column) => {
    const xOption = document.createElement("option");
    xOption.value = column.name;
    xOption.textContent = `${column.name}${column.numeric ? " · 数值" : " · 文本"}`;
    xField.appendChild(xOption);

    if (column.numeric) {
      const yOption = document.createElement("option");
      yOption.value = column.name;
      yOption.textContent = column.name;
      yFields.appendChild(yOption);
    }
  });

  if (dataset.categoryColumns?.length) {
    xField.value = dataset.categoryColumns[0];
  }

  const defaultY = dataset.numericColumns.slice(0, 2);
  [...yFields.options].forEach((option) => {
    option.selected = defaultY.includes(option.value);
  });
}

function renderSuggestions(suggestions) {
  const wrap = document.getElementById("suggestions");
  wrap.innerHTML = "";
  if (!suggestions.length) {
    wrap.innerHTML = `<span class="chip">暂无推荐</span>`;
    return;
  }
  suggestions.forEach((suggestion) => {
    const button = document.createElement("button");
    button.className = "chip";
    button.textContent = suggestion.title;
    button.title = suggestion.reason || suggestion.title;
    button.onclick = () => applySuggestion(suggestion);
    wrap.appendChild(button);
  });
}

function renderTable(rows, columns) {
  const wrap = document.getElementById("tableWrap");
  if (!rows.length || !columns.length) {
    wrap.innerHTML = "<div class=\"empty\">暂无结构化表格</div>";
    return;
  }

  const header = columns.map((column) => `<th>${column.name}</th>`).join("");
  const body = rows.map((row) => {
    const cells = columns.map((column) => {
      const value = row[column.name];
      return `<td>${value === null || value === undefined ? "" : value}</td>`;
    }).join("");
    return `<tr>${cells}</tr>`;
  }).join("");

  wrap.innerHTML = `<table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;
}

function selectedYFields() {
  return [...document.getElementById("yFields").selectedOptions].map((option) => option.value);
}

function applySuggestion(suggestion) {
  document.getElementById("chartType").value = suggestion.type;
  document.getElementById("xField").value = suggestion.x || "";
  const y = suggestion.y || [];
  [...document.getElementById("yFields").options].forEach((option) => {
    option.selected = y.includes(option.value);
  });
  renderChart();
}

function buildSeries(field, type, data, index, stacked, area) {
  return {
    name: field,
    type,
    stack: stacked ? "total" : undefined,
    smooth: type === "line",
    areaStyle: area ? { opacity: 0.18 } : undefined,
    symbolSize: 10,
    lineStyle: { width: 3 },
    itemStyle: { color: palette[index % palette.length] },
    emphasis: { focus: "series" },
    data,
  };
}

function buildChartOption(dataset, type, xField, yFields) {
  const rows = dataset.rows || [];
  const categories = xField ? rows.map((row) => row[xField]) : rows.map((_, index) => `第${index + 1}项`);
  const background = "transparent";

  if (type === "pie" || type === "rosePie") {
    const y = yFields[0];
    return {
      backgroundColor: background,
      tooltip: { trigger: "item" },
      legend: { bottom: 0, textStyle: { color: "#24466c", fontSize: 13, fontWeight: 600 } },
      series: [{
        type: "pie",
        radius: type === "rosePie" ? [28, 130] : ["42%", "72%"],
        roseType: type === "rosePie" ? "area" : undefined,
        center: ["50%", "44%"],
        label: { color: "#163252", fontSize: 13, fontWeight: 700 },
        data: categories.map((name, index) => ({ name, value: Number(rows[index][y]) || 0 })),
      }],
    };
  }

  if (type === "funnel") {
    const y = yFields[0];
    return {
      backgroundColor: background,
      tooltip: { trigger: "item" },
      series: [{
        type: "funnel",
        left: "8%",
        top: 30,
        bottom: 20,
        width: "84%",
        minSize: "20%",
        maxSize: "100%",
        sort: "descending",
        label: { color: "#163252", fontWeight: 700 },
        itemStyle: { borderColor: "#fff", borderWidth: 2 },
        data: categories.map((name, index) => ({ name, value: Number(rows[index][y]) || 0 })),
      }],
    };
  }

  if (type === "scatter") {
    const y = yFields[0];
    const x = xField || dataset.numericColumns[0];
    return {
      backgroundColor: background,
      tooltip: { trigger: "item" },
      grid: { left: 62, right: 30, top: 60, bottom: 56 },
      xAxis: {
        type: "value",
        name: x,
        axisLabel: { color: "#3a5a81", fontSize: 14, fontWeight: 600 },
        nameTextStyle: { color: "#24466c", fontSize: 15, fontWeight: 700 },
        splitLine: { lineStyle: { color: "rgba(143,178,214,0.16)" } },
      },
      yAxis: {
        type: "value",
        name: y,
        axisLabel: { color: "#3a5a81", fontSize: 14, fontWeight: 600 },
        nameTextStyle: { color: "#24466c", fontSize: 15, fontWeight: 700 },
        splitLine: { lineStyle: { color: "rgba(143,178,214,0.16)" } },
      },
      series: [{
        type: "scatter",
        symbolSize: 16,
        itemStyle: { color: palette[0], shadowBlur: 16, shadowColor: "rgba(103,194,255,0.35)" },
        data: rows.map((row) => [Number(row[x]) || 0, Number(row[y]) || 0]),
      }],
    };
  }

  if (type === "radar") {
    const indicators = yFields.map((field) => {
      const values = rows.map((row) => Number(row[field]) || 0);
      return { name: field, max: Math.max(...values, 1) * 1.2 };
    });
    return {
      backgroundColor: background,
      tooltip: {},
      legend: { bottom: 0, textStyle: { color: "#24466c", fontSize: 13, fontWeight: 600 } },
      radar: {
        indicator: indicators,
        radius: "60%",
        axisName: { color: "#183654", fontSize: 13, fontWeight: 700 },
        splitLine: { lineStyle: { color: "rgba(143,178,214,0.18)" } },
        splitArea: { areaStyle: { color: ["rgba(103,194,255,0.03)", "rgba(45,212,191,0.03)"] } },
      },
      series: [{
        type: "radar",
        itemStyle: { color: palette[0] },
        areaStyle: { color: "rgba(103,194,255,0.18)" },
        data: rows.slice(0, 6).map((row, index) => ({
          name: categories[index],
          value: yFields.map((field) => Number(row[field]) || 0),
        })),
      }],
    };
  }

  const isHorizontal = type === "horizontalBar";
  const area = type === "area";
  const stacked = type === "stackedBar";
  const actualType = isHorizontal || stacked ? "bar" : area ? "line" : type;

  const option = {
    backgroundColor: background,
    color: palette,
    tooltip: { trigger: "axis" },
    legend: { top: 8, textStyle: { color: "#24466c", fontSize: 13, fontWeight: 700 } },
    grid: { left: isHorizontal ? 132 : 76, right: 30, top: 70, bottom: 90, containLabel: true },
    series: yFields.map((field, index) => {
      const data = rows.map((row) => Number(row[field]) || 0);
      return buildSeries(field, actualType, data, index, stacked, area);
    }),
  };

  if (isHorizontal) {
    option.xAxis = {
      type: "value",
      axisLabel: { color: "#2e5078", fontSize: 13, fontWeight: 700, width: 116, overflow: "truncate" },
      splitLine: { lineStyle: { color: "rgba(143,178,214,0.16)" } },
    };
    option.yAxis = {
      type: "category",
      data: categories,
      axisLabel: { color: "#2e5078", fontSize: 13, fontWeight: 700 },
      axisLine: { lineStyle: { color: "rgba(143,178,214,0.22)" } },
    };
  } else {
    option.xAxis = {
      type: "category",
      data: categories,
      axisLabel: { color: "#2e5078", fontSize: 13, fontWeight: 700, interval: 0, rotate: categories.length > 7 ? 22 : 0 },
      axisLine: { lineStyle: { color: "rgba(143,178,214,0.22)" } },
    };
    option.yAxis = {
      type: "value",
      axisLabel: { color: "#2e5078", fontSize: 13, fontWeight: 700 },
      splitLine: { lineStyle: { color: "rgba(143,178,214,0.16)" } },
    };
  }

  return option;
}

function ensureChartInstance() {
  if (!state.chart) {
    state.chart = echarts.init(document.getElementById("chartCanvas"));
    window.addEventListener("resize", () => state.chart && state.chart.resize());
  }
}

function renderChart() {
  if (!state.dataset) return;

  const type = document.getElementById("chartType").value;
  const xField = document.getElementById("xField").value;
  const yFields = selectedYFields();

  if (!yFields.length) {
    setBanner("当前图表类型至少需要选择一个数值字段。", "error");
    return;
  }

  ensureChartInstance();
  state.chart.setOption(buildChartOption(state.dataset, type, xField, yFields), true);
  setBanner("图形视图已刷新，可以继续切换图表方案或直接导出。", "success");
}

async function exportAll() {
  if (!state.dataset?.datasetId) {
    setBanner("请先导入真实数据后再导出。", "error");
    return;
  }

  const payload = {
    datasetId: state.dataset.datasetId,
    chartType: document.getElementById("chartType").value,
    xField: document.getElementById("xField").value,
    yFields: selectedYFields(),
    title: state.dataset.title || "数据智能分析汇报",
  };

  const requestExport = async (formats) => {
    const res = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, formats }),
    });
    const data = await res.json();
    if (!data.ok) {
      throw new Error(data.error || "导出失败。");
    }
    return data.exports || {};
  };

  setButtonBusy("exportBtn", true, "导出 PNG / Excel / PPT", "正在导出图片...");
  try {
    const pngExports = await requestExport(["png"]);
    document.getElementById("exportLinks").innerHTML = `
      <a href="${pngExports.pngUrl}" target="_blank">下载 PNG 图表</a>
      <span>Excel / PPT 正在后台生成...</span>
    `;
    setBanner("PNG 图片已生成，Excel / PPT 继续后台导出。", "success");

    setButtonBusy("exportBtn", true, "导出 PNG / Excel / PPT", "生成 Excel / PPT...");
    const officeExports = await requestExport(["excel", "pptx"]);
    document.getElementById("exportLinks").innerHTML = `
      <a href="${pngExports.pngUrl}" target="_blank">下载 PNG 图表</a>
      <a href="${officeExports.excelUrl}" target="_blank">下载 Excel 分析稿</a>
      <a href="${officeExports.pptxUrl}" target="_blank">下载 PPT 展示稿</a>
    `;
    setBanner("全部导出完成，可直接打开结果文件。", "success");
  } catch (error) {
    setBanner(error.message || "导出失败。", "error");
  } finally {
    setButtonBusy("exportBtn", false, "导出 PNG / Excel / PPT", "正在导出...");
  }
}

function loadProcurementSample() {
  document.getElementById("textInput").value = procurementSample;
  setBanner("采购示例已填入，可直接体验字段识别、结构化建表与图表推荐。", "info");
}

function loadGrowthSample() {
  document.getElementById("textInput").value = growthSample;
  setBanner("行业分析示例已填入，适合测试趋势、平台和用户画像识别能力。", "info");
}

document.getElementById("uploadBtn").addEventListener("click", uploadFile);
document.getElementById("textRuleBtn").addEventListener("click", () => uploadTextByMode("rule"));
document.getElementById("textAiBtn").addEventListener("click", () => uploadTextByMode("ai"));
document.getElementById("renderBtn").addEventListener("click", renderChart);
document.getElementById("sampleBtn").addEventListener("click", loadProcurementSample);
document.getElementById("fillParagraphBtn").addEventListener("click", loadGrowthSample);
document.getElementById("exportBtn").addEventListener("click", exportAll);

checkHealth();
loadProcurementSample();
