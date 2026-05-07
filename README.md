# 数据智能分析平台 V1.0

数据智能分析平台 V1.0 是一个面向数据整理、图表生成和汇报材料制作的本地 Web 工具。平台支持上传表格文件或粘贴中文业务文本，自动完成数据解析、结构化建表、图表推荐、可视化预览，并支持导出图片、Excel 和 PPT 报告。

项目采用 Python 本地服务和静态前端页面实现，适合课程设计、作品展示、数据分析原型和个人效率工具场景。

## 功能概览

- 文件导入：支持 CSV、Excel、JSON、TXT、Word、PDF 等数据源。
- 文本解析：支持粘贴中文业务文本、行业分析内容和 OCR 识别结果。
- 智能建表：自动识别时间、品类、平台、金额、增长率、占比、用户画像、地域、趋势和对比关系。
- 图表推荐：根据字段类型推荐柱状图、折线图、饼图、玫瑰图、漏斗图、雷达图、散点图等图表。
- 可视化预览：前端页面基于 ECharts 展示交互式图表。
- 导出报告：支持导出 PNG 图片、Excel 文件和 PPT 汇报文件。
- AI 提取：可通过环境变量或配置文件接入兼容 OpenAI Chat Completions 的接口。

## 技术栈

- 后端：Python、`http.server`、Pandas、Pillow、openpyxl、python-docx、pypdf
- 前端：HTML、CSS、JavaScript、ECharts
- PPT 导出：Node.js、PptxGenJS
- 运行方式：本地 Python 服务，默认端口 `8866`

## 项目结构

```text
Data-intelligence-analysis-platform-v1/
├─ 平台服务.py                 # 本地 Web 服务和接口入口
├─ start_platform.py           # 跨文件名启动入口
├─ analysis_engine.py          # 数据清洗、字段识别和图表推荐
├─ ai_table_extractor.py       # AI 结构化提取
├─ text_recognition.py         # 文本规则解析
├─ export_ppt_report.mjs       # PPT 报告导出脚本
├─ requirements.txt            # Python 依赖
├─ package.json                # Node.js 依赖
├─ first_setup.bat             # Windows 初始化 Python 环境脚本
├─ 启动数据智能分析平台.bat        # Windows 一键启动脚本
├─ web/
│  ├─ index.html               # 前端页面
│  ├─ app.js                   # 前端交互逻辑
│  └─ styles.css               # 页面样式
└─ runtime/
   └─ ai_provider_config.example.json
```

## 环境要求

- Python 3.11 或更高版本
- Node.js 18 或更高版本
- npm

只使用基础数据解析和图表预览时，主要依赖 Python。需要导出 PPT 时，还需要安装 Node.js 依赖。

## 下载项目

```bash
git clone https://github.com/qinzishuo188-boop/Data-intelligence-analysis-platform-v1.git
cd Data-intelligence-analysis-platform-v1
```

也可以在 GitHub 页面点击 `Code`，选择 `Download ZIP` 下载后解压使用。

## 安装依赖

安装 Python 依赖：

```bash
python -m pip install -r requirements.txt
```

安装 PPT 导出所需的 Node.js 依赖：

```bash
npm install
```

Windows 用户也可以直接运行：

```bat
first_setup.bat
```

该脚本会在 `runtime/python` 下创建本地 Python 环境并安装依赖。

## 启动项目

方式一：使用 Python 命令启动。

```bash
python start_platform.py
```

方式二：Windows 下双击或运行：

```bat
启动数据智能分析平台.bat
```

启动成功后访问：

```text
http://127.0.0.1:8866
```

健康检查接口：

```text
http://127.0.0.1:8866/api/health
```

## AI 配置

AI 提取功能支持通过环境变量配置：

```text
CHART_AI_ENABLED=true
CHART_AI_BASE_URL=https://api.example.com/v1
CHART_AI_API_KEY=your-api-key
CHART_AI_MODEL=your-model-name
CHART_AI_TIMEOUT=120
CHART_AI_MAX_WORKERS=3
```

也可以复制配置示例：

```bash
copy runtime\ai_provider_config.example.json runtime\ai_provider_config.json
```

macOS / Linux：

```bash
cp runtime/ai_provider_config.example.json runtime/ai_provider_config.json
```

然后按实际接口信息修改 `runtime/ai_provider_config.json`。

## 使用流程

1. 启动平台并打开 `http://127.0.0.1:8866`。
2. 上传 CSV、Excel、JSON、TXT、Word、PDF 文件，或直接粘贴中文文本。
3. 选择常规提取或 AI 提取。
4. 查看系统生成的结构化表格、字段识别结果和图表推荐。
5. 根据推荐切换图表类型和指标字段。
6. 导出 PNG、Excel 或 PPT 汇报文件。

## 常用命令

```bash
python -m pip install -r requirements.txt
npm install
python start_platform.py
```

## 端口被占用

启动脚本会尝试释放 `8866` 端口。如果手动启动时端口被占用，可以先关闭占用该端口的程序，再重新运行：

```bash
python start_platform.py
```

## 常见问题

### 页面打不开

确认服务已经启动，并访问：

```text
http://127.0.0.1:8866
```

### 文件解析失败

检查文件格式是否为 CSV、Excel、JSON、TXT、Word 或 PDF。CSV 文件建议使用 UTF-8 或 GBK 编码。

### PPT 导出失败

先确认 Node.js 依赖已经安装：

```bash
npm install
```

然后重新启动平台再导出 PPT。

### AI 提取不可用

检查 `CHART_AI_API_KEY` 或 `runtime/ai_provider_config.json` 是否已配置。未配置时，平台仍可使用常规规则提取。

## 版权说明

本项目仅用于学习、课程设计、作品展示或个人研究用途。
