const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const workspace = path.resolve(__dirname, "..");
const root = process.env.MASTERPLOP_POWERBI_OUTPUT_ROOT
  ? path.resolve(process.env.MASTERPLOP_POWERBI_OUTPUT_ROOT)
  : path.join(__dirname, "source");
const projectName = "Masterplop_Executive";
const reportDir = path.join(root, `${projectName}.Report`);
const modelDir = path.join(root, `${projectName}.SemanticModel`);
const reportDefinition = path.join(reportDir, "definition");
const pagesDir = path.join(reportDefinition, "pages");
const modelDefinition = path.join(modelDir, "definition");
const tableDir = path.join(modelDefinition, "tables");
const dataDir = path.join(root, "data");
const resourceDir = path.join(reportDir, "StaticResources", "RegisteredResources");
const sourceDataDir = path.join(workspace, "data", "processed", "dashboard");

const colors = {
  navy: "#0B1532",
  page: "#F5F7FB",
  card: "#FFFFFF",
  ink: "#172033",
  muted: "#667085",
  border: "#E2E8F2",
  blue: "#1A56DB",
  yellow: "#FBBF24",
  purple: "#7C3AED",
  green: "#16A34A",
  red: "#C24141",
};

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function cleanDir(dir) {
  if (fs.existsSync(dir)) {
    try {
      fs.rmSync(dir, { recursive: true, force: true, maxRetries: 3, retryDelay: 150 });
    } catch (error) {
      // Power BI Desktop can retain short-lived file handles after closing.
      // Every generated artifact is overwritten below, so keeping the folder is safe.
      if (!["EPERM", "EBUSY"].includes(error.code)) throw error;
    }
  }
  ensureDir(dir);
}

function writeJson(filePath, value) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function writeText(filePath, value) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, value.replace(/\r?\n/g, "\r\n"), "utf8");
}

function copyFile(source, target) {
  ensureDir(path.dirname(target));
  fs.copyFileSync(source, target);
}

function copyFirstRows(source, target, count) {
  const lines = fs.readFileSync(source, "utf8").trim().split(/\r?\n/);
  writeText(target, `${[lines[0], ...lines.slice(1, count + 1)].join("\n")}\n`);
}

function literal(value) {
  if (typeof value === "boolean") return { expr: { Literal: { Value: value ? "true" : "false" } } };
  if (typeof value === "number") return { expr: { Literal: { Value: `${value}D` } } };
  return { expr: { Literal: { Value: `'${String(value).replace(/'/g, "''")}'` } } };
}

function intLiteral(value) {
  return { expr: { Literal: { Value: `${value}L` } } };
}

function fill(color) {
  return { solid: { color: literal(color) } };
}

function sourceRef(table) {
  return { SourceRef: { Entity: table } };
}

function col(table, name, alias = name) {
  return {
    field: { Column: { Expression: sourceRef(table), Property: name } },
    queryRef: `${table}.${name}`,
    nativeQueryRef: alias,
  };
}

function measure(table, name, alias = name) {
  return {
    field: { Measure: { Expression: sourceRef(table), Property: name } },
    queryRef: `${table}.${name}`,
    nativeQueryRef: alias,
  };
}

function filterFor(projection, index) {
  return {
    name: `f_${String(index).padStart(2, "0")}_${projection.nativeQueryRef.replace(/[^A-Za-z0-9]/g, "_").slice(0, 16)}`,
    field: projection.field,
    type: projection.field.Measure ? "Advanced" : "Categorical",
  };
}

function visualObjects(title, type, accent = colors.blue, style = {}) {
  const base = {};

  if (type === "cardVisual") {
    const labelShow = style.labelShow ?? style.categoryLabelShow ?? true;
    const valueColor = style.valueColor ?? style.calloutColor ?? accent;
    const valueFontSize = style.valueFontSize ?? style.calloutFontSize ?? 20;
    base.layout = [{
      properties: {
        topOuterMargin: intLiteral(0),
        bottomOuterMargin: intLiteral(0),
        leftOuterMargin: intLiteral(0),
        rightOuterMargin: intLiteral(0),
        paddingUniform: intLiteral(style.padding ?? 8),
      },
      selector: { id: "default" },
    }];
    base.shapeCustomRectangle = [{
      properties: {
        tileShape: literal("rectangleRoundedByPixel"),
        rectangleRoundedCurve: intLiteral(style.radius ?? 12),
      },
      selector: { id: "default" },
    }];
    base.border = [{ properties: { show: literal(false) } }];
    base.outline = [{ properties: { show: literal(false) }, selector: { id: "default" } }];
    base.accentBar = [{ properties: { show: literal(false) }, selector: { id: "default" } }];
    base.fillCustom = [{ properties: { show: literal(false) } }];
    base.value = [{
      properties: {
        show: literal(true),
        fontColor: fill(valueColor),
        fontSize: literal(valueFontSize),
        bold: literal(style.valueBold ?? true),
        horizontalAlignment: literal(style.valueAlignment ?? "left"),
        labelDisplayUnits: literal(1),
      },
      selector: { id: "default" },
    }];
    base.label = [{
      properties: {
        show: literal(labelShow),
        fontColor: fill(style.labelColor ?? colors.muted),
        fontSize: literal(style.labelFontSize ?? 9),
        bold: literal(style.labelBold ?? true),
        horizontalAlignment: literal(style.labelAlignment ?? "left"),
        position: literal(style.labelPosition ?? "aboveValue"),
      },
      selector: { id: "default" },
    }];
  }

  if (["clusteredBarChart", "clusteredColumnChart", "lineChart", "waterfallChart"].includes(type)) {
    base.categoryAxis = [{ properties: {
      show: literal(true), labelColor: fill(colors.muted), fontSize: literal(9),
      titleShow: literal(false),
    } }];
    base.valueAxis = [{ properties: {
      show: literal(true), labelColor: fill(colors.muted), fontSize: literal(9),
      titleShow: literal(false), gridlineShow: literal(true), gridlineColor: fill("#E8EDF5"),
    } }];
    if (!style.useThemeColors) {
      base.dataPoint = [{
        properties: { fill: fill(accent) },
        selector: { data: [{ dataViewWildcard: { matchingOption: 0 } }] },
      }];
    }
    base.labels = [{ properties: {
      show: literal(style.labelsShow ?? true), color: fill(colors.ink), fontSize: literal(9),
      labelDisplayUnits: literal(1),
    } }];
  }

  if (type === "lineChart") {
    base.lineStyles = [{ properties: {
      strokeWidth: literal(3), lineChartType: literal("straight"), showMarker: literal(true),
    } }];
    base.markers = [{ properties: { show: literal(true), markerSize: literal(8), borderShow: literal(false) } }];
  }

  if (type === "slicer") {
    base.items = [{ properties: { fontColor: fill(colors.ink), textSize: literal(10) } }];
    base.header = [{ properties: { show: literal(true), fontColor: fill(colors.ink), textSize: literal(10) } }];
  }

  if (type === "tableEx") {
    base.grid = [{ properties: { outlineColor: fill(colors.border), gridVertical: literal(false) } }];
    base.columnHeaders = [{ properties: { fontColor: fill(colors.ink), backColor: fill("#EEF4FF"), fontSize: literal(10) } }];
    base.values = [{ properties: { fontColorPrimary: fill(colors.ink), backColorPrimary: fill(colors.card), fontSize: literal(9) } }];
  }
  return base;
}

function visualContainerObjects(title, type, style = {}) {
  const isCard = type === "cardVisual";
  return {
    title: [{ properties: {
      show: literal(style.titleShow ?? !isCard),
      text: literal(title),
      fontColor: fill(style.titleColor ?? colors.ink),
      fontSize: literal(style.titleFontSize ?? 12),
      fontFamily: literal("Segoe UI Semibold"),
      bold: literal(true),
      alignment: literal("left"),
    } }],
    background: [{ properties: {
      show: literal(style.backgroundShow ?? true),
      color: fill(style.background ?? colors.card),
      transparency: literal(style.transparency ?? 0),
    } }],
    border: [{ properties: {
      show: literal(style.borderShow ?? true),
      color: fill(style.borderColor ?? colors.border),
      radius: literal(style.radius ?? 12),
      width: literal(style.borderWidth ?? 1),
    } }],
    visualHeader: [{ properties: { show: literal(false) } }],
  };
}

function visual(page, name, type, position, queryState, projections = [], options = {}) {
  const sortDefinition = options.sortBy
    ? { sort: [{ field: options.sortBy.field, direction: options.sortDirection ?? "Descending" }] }
    : { isDefaultSort: true };
  const payload = {
    $schema: "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
    name,
    position: { ...position, tabOrder: position.z },
    visual: {
      visualType: type,
      query: { queryState, sortDefinition },
      objects: visualObjects(options.title ?? name, type, options.accent ?? colors.blue, options),
      visualContainerObjects: visualContainerObjects(options.title ?? name, type, options),
    },
  };
  if (projections.length) payload.filterConfig = { filters: projections.map(filterFor) };
  writeJson(path.join(pagesDir, page, "visuals", name, "visual.json"), payload);
}

function card(page, name, title, measureName, x, y, width, height, accent, z, style = {}) {
  const m = measure("executive", measureName, title || measureName);
  visual(page, name, "cardVisual", { x, y, width, height, z }, { Data: { projections: [m] } }, [m], {
    title, accent, ...style,
  });
}

function chart(page, name, type, title, queryState, projections, x, y, width, height, accent, z, style = {}) {
  visual(page, name, type, { x, y, width, height, z }, queryState, projections, {
    title, accent, ...style,
  });
}

function slicer(page, name, title, projection, x, y, width, height, z) {
  visual(page, name, "slicer", { x, y, width, height, z }, { Values: { projections: [projection] } }, [projection], {
    title, accent: colors.blue,
  });
}

function imageVisual(page, name, x, y, width, height, z) {
  writeJson(path.join(pagesDir, page, "visuals", name, "visual.json"), {
    $schema: "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.10.0/schema.json",
    name,
    position: { x, y, width, height, z, tabOrder: z },
    visual: {
      visualType: "image",
      objects: {
        image: [{ properties: { sourceFile: { image: {
          name: { expr: { Literal: { Value: "'Masterplop logo.png'" } } },
          url: { expr: { ResourcePackageItem: { PackageName: "RegisteredResources", PackageType: 1, ItemName: "Masterplop_logo.png" } } },
          scaling: { expr: { Literal: { Value: "'Fit'" } } },
        } } } }],
      },
    },
  });
}

function page(name, displayName) {
  cleanDir(path.join(pagesDir, name, "visuals"));
  writeJson(path.join(pagesDir, name, "page.json"), {
    $schema: "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
    name,
    displayName,
    displayOption: "FitToPage",
    width: 1280,
    height: 720,
    objects: {
      background: [{ properties: { color: fill(colors.page), transparency: literal(0) } }],
    },
  });
}

function header(pageName, titleMeasure, subtitleMeasure) {
  card(pageName, "header_background", "", "Fondo cabecera", 0, 0, 1280, 88, colors.navy, 0, {
    titleShow: false, labelShow: false, background: colors.navy, borderColor: colors.navy,
    valueColor: colors.navy, valueFontSize: 1, radius: 0, padding: 0,
  });
  imageVisual(pageName, "brand_logo", 20, 9, 90, 70, 1);
  card(pageName, "header_title", "", titleMeasure, 124, 6, 680, 76, colors.card, 2, {
    titleShow: false, labelShow: false, background: colors.navy, borderColor: colors.navy,
    valueColor: colors.card, valueFontSize: 28, radius: 0, padding: 10,
  });
  card(pageName, "header_subtitle", "", subtitleMeasure, 816, 10, 266, 68, colors.card, 3, {
    titleShow: false, labelShow: false, background: colors.navy, borderColor: colors.navy,
    valueColor: "#C7D5F5", valueFontSize: 12, valueAlignment: "right", radius: 0, padding: 8,
  });
  card(pageName, "header_quality", "Calidad de datos", "Estado calidad", 1096, 10, 160, 68, colors.green, 4, {
    background: "#111F42", borderColor: "#31466F", valueColor: "#5EE28A", valueFontSize: 16,
    labelColor: "#AEBDE0", labelFontSize: 9, radius: 12, padding: 8,
  });
}

const configs = {
  executive: {
    file: "executive.csv",
    columns: {
      active_cards: "int64", transaction_count: "int64", total_net_spend_usd: "decimal",
      avg_transaction_amount_usd: "decimal", total_cashback_usd: "decimal", beneficiary_card_count: "int64",
      min_transaction_date: "date", max_transaction_date: "date",
    },
  },
  volume: {
    file: "volume.csv",
    columns: { period_year: "int64", period_quarter: "int64", quarter_start_date: "date", product_type: "string", active_cards: "int64", transaction_count: "int64", period_label: "string" },
    addPeriod: true,
    sortBy: { period_label: "quarter_start_date" },
  },
  quarterly_ticket: {
    file: "quarterly_ticket.csv",
    columns: { period_year: "int64", period_quarter: "int64", quarter_start_date: "date", net_spend_usd: "decimal", active_credit_cards: "int64", net_spend_per_active_card_usd: "decimal", period_label: "string" },
    addPeriod: true,
    sortBy: { period_label: "quarter_start_date" },
  },
  regional_ticket: {
    file: "regional_ticket.csv",
    columns: { issuer_country: "string", product_name: "string", transaction_count: "int64", net_spend_usd: "decimal", avg_transaction_amount_usd: "decimal" },
  },
  top_mcg: {
    file: "top_mcg.csv",
    columns: { spend_rank: "int64", mcg_code: "int64", mcg_code_original: "string", mcg_name: "string", net_spend_usd: "decimal", net_spend_share_pct: "decimal", transaction_count: "int64", global_net_spend_usd: "decimal" },
  },
  top_mcg_5: {
    file: "top_mcg_5.csv",
    columns: { spend_rank: "int64", mcg_code: "int64", mcg_code_original: "string", mcg_name: "string", net_spend_usd: "decimal", net_spend_share_pct: "decimal", transaction_count: "int64", global_net_spend_usd: "decimal" },
  },
  contactless: {
    file: "contactless.csv",
    columns: { issuer_country: "string", contactless_net_spend_usd: "decimal", total_net_spend_usd: "decimal", contactless_net_spend_pct: "decimal", contactless_transaction_count: "int64", transaction_count: "int64" },
  },
  contactless_5: {
    file: "contactless_5.csv",
    columns: { issuer_country: "string", contactless_net_spend_usd: "decimal", total_net_spend_usd: "decimal", contactless_net_spend_pct: "decimal", contactless_transaction_count: "int64", transaction_count: "int64" },
  },
  cashback: {
    file: "cashback.csv",
    columns: { campaign_month: "date", eligible_transaction_count: "int64", positive_eligible_transaction_count: "int64", negative_eligible_transaction_count: "int64", eligible_card_count: "int64", beneficiary_card_count: "int64", capped_card_count: "int64", net_eligible_spend_usd: "decimal", uncapped_cashback_rounded_usd: "decimal", total_cashback_usd: "decimal", cap_savings_usd: "decimal", cashback_if_rounded_after_sum_usd: "decimal", rounding_timing_difference_usd: "decimal", seven_pct_of_global_net_spend_usd: "decimal" },
  },
  cashback_sensitivity: {
    file: "cashback_sensitivity.csv",
    columns: { eligible_card_count: "int64", beneficiary_card_count: "int64", positive_eligible_transaction_count: "int64", positive_eligible_spend_usd: "decimal", positive_only_cashback_usd: "decimal", incremental_cost_vs_net_usd: "decimal" },
  },
  cashback_is_xb: {
    file: "cashback_is_xb.csv",
    columns: { is_xb_eligible_transaction_count: "int64", beneficiary_card_count: "int64", net_eligible_spend_usd: "decimal", incorrect_is_xb_cashback_usd: "decimal", difference_vs_official_usd: "decimal" },
  },
  cashback_diagnostic: {
    file: "cashback_diagnostic.csv",
    columns: { diagnostic_status: "string", transaction_count: "int64", net_spend_usd: "decimal" },
  },
  quality: {
    file: "quality.csv",
    columns: { row_count: "int64", invalid_amounts: "int64", invalid_dates: "int64", invalid_times: "int64", unclassified_mcg_transactions: "int64", is_xb_country_discrepancies: "int64", failed_data_quality_checks: "int64", failed_kpi_checks: "int64", failed_cashback_checks: "int64" },
  },
  campaign_scenarios: {
    file: "campaign_scenarios.csv",
    columns: { scenario_order: "int64", scenario: "string", amount_usd: "decimal" },
    sortBy: { scenario: "scenario_order" },
  },
  campaign_bridge: {
    file: "campaign_bridge.csv",
    columns: { step_order: "int64", step: "string", amount_usd: "decimal" },
    sortBy: { step: "step_order" },
  },
};

function mType(type) {
  return ({ int64: "Int64.Type", decimal: "Currency.Type", date: "type date", string: "type text" })[type];
}

function tmdlType(type) {
  return ({ int64: "int64", decimal: "decimal", date: "dateTime", string: "string" })[type];
}

function columnFormat(type, name) {
  if (type === "int64") return "#,0";
  if (type === "decimal") return name.includes("pct") ? "0.00" : "$ #,0.00";
  if (type === "date") return "dd-MM-yyyy";
  return null;
}

function mQuery(config) {
  const filePath = path.join(dataDir, config.file);
  // Embed the small, already-aggregated CSV as Base64 so the PBIP remains
  // portable and never publishes an author-specific absolute filesystem path.
  const embeddedCsv = fs.readFileSync(filePath).toString("base64");
  const sourceColumns = Object.entries(config.columns).filter(([name]) => name !== "period_label");
  const transforms = sourceColumns.map(([name, type]) => `{\"${name}\", ${mType(type)}}`).join(", ");
  const lines = [
    "let",
    `    EmbeddedCsv = \"${embeddedCsv}\",`,
    "    Source = Csv.Document(Binary.FromText(EmbeddedCsv, BinaryEncoding.Base64), [Delimiter=\",\", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),",
    "    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
    `    Typed = Table.TransformColumnTypes(Headers, {${transforms}}, \"en-US\")`,
  ];
  if (config.addPeriod) {
    lines[lines.length - 1] += ",";
    lines.push("    WithPeriod = Table.AddColumn(Typed, \"period_label\", each Text.From([period_year]) & \" T\" & Text.From([period_quarter]), type text)");
    lines.push("in", "    WithPeriod");
  } else {
    lines.push("in", "    Typed");
  }
  return lines.join("\n");
}

const measures = [
  ["Tarjetas activas", "MAX(executive[active_cards])", "#,0"],
  ["Transacciones", "MAX(executive[transaction_count])", "#,0"],
  ["Gasto neto USD", "MAX(executive[total_net_spend_usd])", "$ #,0.00"],
  ["Ticket promedio USD", "MAX(executive[avg_transaction_amount_usd])", "$ #,0.00"],
  ["Cashback oficial USD", "MAX(cashback[total_cashback_usd])", "$ #,0.00"],
  ["Tarjetas beneficiadas", "MAX(cashback[beneficiary_card_count])", "#,0"],
  ["Tarjetas topadas", "MAX(cashback[capped_card_count])", "#,0"],
  ["Gasto elegible USD", "MAX(cashback[net_eligible_spend_usd])", "$ #,0.00"],
  ["Transacciones elegibles", "MAX(cashback[eligible_transaction_count])", "#,0"],
  ["Ahorro por tope USD", "MAX(cashback[cap_savings_usd])", "$ #,0.00"],
  ["Porcentaje topadas", "DIVIDE([Tarjetas topadas], [Tarjetas beneficiadas])", "0.00%"],
  ["Costo sin devoluciones USD", "MAX(cashback_sensitivity[positive_only_cashback_usd])", "$ #,0.00"],
  ["Costo is_xb incorrecto USD", "MAX(cashback_is_xb[incorrect_is_xb_cashback_usd])", "$ #,0.00"],
  ["Brecha is_xb USD", "[Costo is_xb incorrecto USD] - [Cashback oficial USD]", "$ #,0.00"],
  ["Ticket regional USD", "DIVIDE(SUM(regional_ticket[net_spend_usd]), SUM(regional_ticket[transaction_count]))", "$ #,0.00"],
  ["Tarjetas activas periodo", "SUM(volume[active_cards])", "#,0"],
  ["Ticket trimestral credito USD", "MAX(quarterly_ticket[net_spend_per_active_card_usd])", "$ #,0.00"],
  ["Monto escenario USD", "SUM(campaign_scenarios[amount_usd])", "$ #,0.00"],
  ["Monto puente USD", "SUM(campaign_bridge[amount_usd])", "$ #,0.00"],
  ["Transacciones diagnostico", "SUM(cashback_diagnostic[transaction_count])", "#,0"],
  ["Participacion MCG", "DIVIDE(SUM(top_mcg[net_spend_usd]), MAX(top_mcg[global_net_spend_usd]))", "0.00%"],
  ["Participacion MCG Top5", "DIVIDE(SUM(top_mcg_5[net_spend_usd]), MAX(top_mcg_5[global_net_spend_usd]))", "0.00%"],
  ["Adopcion contactless", "DIVIDE(SUM(contactless[contactless_net_spend_usd]), SUM(contactless[total_net_spend_usd]))", "0.00%"],
  ["Adopcion contactless Top5", "DIVIDE(SUM(contactless_5[contactless_net_spend_usd]), SUM(contactless_5[total_net_spend_usd]))", "0.00%"],
  ["Crecimiento tarjetas credito", "VAR T1 = CALCULATE(MAX(volume[active_cards]), volume[period_quarter] = 1, volume[product_type] = \"Crédito\") VAR T2 = CALCULATE(MAX(volume[active_cards]), volume[period_quarter] = 2, volume[product_type] = \"Crédito\") RETURN DIVIDE(T2, T1) - 1", "0.00%"],
  ["Crecimiento ticket credito", "VAR T1 = CALCULATE(MAX(quarterly_ticket[net_spend_per_active_card_usd]), quarterly_ticket[period_quarter] = 1) VAR T2 = CALCULATE(MAX(quarterly_ticket[net_spend_per_active_card_usd]), quarterly_ticket[period_quarter] = 2) RETURN DIVIDE(T2, T1) - 1", "0.00%"],
  ["Concentracion Top 3", "DIVIDE(SUMX(TOPN(3, ALL(top_mcg), top_mcg[net_spend_usd], DESC), top_mcg[net_spend_share_pct]), 100)", "0.00%"],
  ["Lider contactless", "VAR Lider = TOPN(1, ALL(contactless), contactless[contactless_net_spend_pct], DESC) RETURN MAXX(Lider, contactless[issuer_country]) & \" · \" & FORMAT(DIVIDE(MAXX(Lider, contactless[contactless_net_spend_pct]), 100), \"0.0%\")", null],
  ["Estado calidad", "IF(MAX(quality[failed_data_quality_checks]) + MAX(quality[failed_kpi_checks]) + MAX(quality[failed_cashback_checks]) = 0, \"Conciliado\", \"Revisar\")", null],
  ["Titulo resumen", "\"Resumen Ejecutivo\"", null],
  ["Titulo transaccional", "\"Análisis Transaccional\"", null],
  ["Titulo campana", "\"Campaña Mayo 2024\"", null],
  ["Subtitulo general", "\"Datos agregados · Sin IDs\"", null],
  ["Regla mercado regional", "\"Mercado = país emisor (ctry_card)\"", null],
  ["Regla elegibilidad", "\"Mayo · Crédito · emisor Chile\"", null],
  ["Regla geografia", "\"Fuera de Chile · campo ctry_mrch\"", null],
  ["Regla beneficio", "\"7% neto positivo · tope USD 50\"", null],
  ["Regla redondeo", "\"Por tarjeta · antes de sumar\"", null],
  ["Fondo cabecera", "\"\"", null],
];

function tableTmdl(name, config) {
  const output = [`table ${name}`, `\tlineageTag: ${crypto.randomUUID()}`, ""];
  if (name === "executive") {
    for (const [measureName, expression, format] of measures) {
      output.push(`\tmeasure '${measureName.replace(/'/g, "''")}' = ${expression}`);
      if (format) output.push(`\t\tformatString: ${format}`);
      output.push(`\t\tlineageTag: ${crypto.randomUUID()}`, "");
    }
  }
  for (const [columnName, type] of Object.entries(config.columns)) {
    output.push(`\tcolumn ${columnName}`);
    output.push(`\t\tdataType: ${tmdlType(type)}`);
    const format = columnFormat(type, columnName);
    if (format) output.push(`\t\tformatString: ${format}`);
    if (config.sortBy?.[columnName]) output.push(`\t\tsortByColumn: ${config.sortBy[columnName]}`);
    output.push(`\t\tlineageTag: ${crypto.randomUUID()}`);
    output.push(`\t\tsummarizeBy: ${["int64", "decimal"].includes(type) ? "sum" : "none"}`);
    output.push(`\t\tsourceColumn: ${columnName}`, "");
  }
  output.push(`\tpartition ${name} = m`, "\t\tmode: import", "\t\tsource =");
  for (const line of mQuery(config).split("\n")) output.push(`\t\t\t\t${line}`);
  output.push("", "\tannotation PBI_ResultType = Table", "");
  return output.join("\n");
}

// Safe aggregate inputs only.
cleanDir(dataDir);
for (const file of ["executive.csv", "volume.csv", "quarterly_ticket.csv", "regional_ticket.csv", "top_mcg.csv", "contactless.csv", "cashback.csv", "cashback_sensitivity.csv", "cashback_is_xb.csv", "cashback_diagnostic.csv", "quality.csv"]) {
  copyFile(path.join(sourceDataDir, file), path.join(dataDir, file));
}
copyFirstRows(path.join(sourceDataDir, "top_mcg.csv"), path.join(dataDir, "top_mcg_5.csv"), 5);
copyFirstRows(path.join(sourceDataDir, "contactless.csv"), path.join(dataDir, "contactless_5.csv"), 5);

const manifest = JSON.parse(fs.readFileSync(path.join(sourceDataDir, "manifest.json"), "utf8"));
const cb = manifest.datasets.cashback.records[0];
const sensitivity = manifest.datasets.cashback_sensitivity.records[0];
const xb = manifest.datasets.cashback_is_xb.records[0];
writeText(path.join(dataDir, "campaign_scenarios.csv"), [
  "scenario_order,scenario,amount_usd",
  `1,Oficial neto,${cb.total_cashback_usd}`,
  `2,Sin descontar devoluciones,${sensitivity.positive_only_cashback_usd}`,
  `3,is_xb incorrecto,${xb.incorrect_is_xb_cashback_usd}`,
  "",
].join("\n"));
writeText(path.join(dataDir, "campaign_bridge.csv"), [
  "step_order,step,amount_usd",
  `1,Cashback sin tope,${cb.uncapped_cashback_rounded_usd}`,
  `2,Ahorro por tope,-${cb.cap_savings_usd}`,
  "",
].join("\n"));

cleanDir(modelDefinition);
ensureDir(tableDir);
writeText(path.join(modelDefinition, "database.tmdl"), "database\n\tcompatibilityLevel: 1600\n");
writeText(path.join(modelDefinition, "model.tmdl"), [
  "model Model",
  "\tculture: es-CL",
  "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
  "\tsourceQueryCulture: es-CL",
  "\tdataAccessOptions",
  "\t\tlegacyRedirects",
  "\t\treturnErrorValuesAsNull",
  "",
  `annotation PBI_QueryOrder = [ ${Object.keys(configs).map(x => `\"${x}\"`).join(", ")} ]`,
  "annotation __PBI_TimeIntelligenceEnabled = 0",
  "annotation PBI_ProTooling = [\"DevMode\"]",
  "",
  ...Object.keys(configs).map(name => `ref table ${name}`),
  "",
].join("\n"));
for (const [name, config] of Object.entries(configs)) writeText(path.join(tableDir, `${name}.tmdl`), tableTmdl(name, config));

writeJson(path.join(modelDir, "definition.pbism"), {
  $schema: "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
  version: "4.2",
  settings: { qnaEnabled: false },
});
writeJson(path.join(modelDir, ".platform"), {
  $schema: "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  metadata: { type: "SemanticModel", displayName: projectName },
  config: { version: "2.0", logicalId: crypto.randomUUID() },
});

cleanDir(reportDefinition);
ensureDir(pagesDir);
cleanDir(resourceDir);
copyFile(path.join(workspace, "Masterplop logo.png"), path.join(resourceDir, "Masterplop_logo.png"));
const themeName = "Masterplop_Executive.json";
writeJson(path.join(resourceDir, themeName), {
  $schema: "https://raw.githubusercontent.com/microsoft/powerbi-desktop-samples/main/Report%20Theme%20JSON%20Schema/reportThemeSchema-2.149.json",
  name: "Masterplop Executive",
  dataColors: [colors.blue, colors.purple, colors.yellow, colors.green, colors.red],
  background: colors.page,
  foreground: colors.ink,
  tableAccent: colors.blue,
  textClasses: {
    title: { fontFace: "Segoe UI Semibold", color: colors.ink },
    label: { fontFace: "Segoe UI", color: colors.muted },
    callout: { fontFace: "Segoe UI Semibold", color: colors.ink },
  },
  visualStyles: {
    "*": { "*": { "*": [{
      displayUnits: 1,
      labelDisplayUnits: 1,
      titleDisplayUnits: 1,
      detailDisplayUnits: 1,
      valueDisplayUnits: 1,
      secLabelDisplayUnits: 1,
      titleLabelDisplayUnits: 1,
    }] } },
    cardVisual: { "*": { "*": [{
      $id: "default",
      displayUnits: 1,
      labelDisplayUnits: 1,
      titleDisplayUnits: 1,
      detailDisplayUnits: 1,
      valueDisplayUnits: 1,
      secLabelDisplayUnits: 1,
      titleLabelDisplayUnits: 1,
    }] } },
  },
});
writeJson(path.join(reportDefinition, "version.json"), {
  $schema: "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
  version: "2.0.0",
});
writeJson(path.join(reportDefinition, "report.json"), {
  $schema: "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
  themeCollection: { customTheme: { name: themeName, reportVersionAtImport: { visual: "2.10.0", report: "3.4.0", page: "2.3.1" }, type: "RegisteredResources" } },
  resourcePackages: [{ name: "RegisteredResources", type: "RegisteredResources", items: [
    { name: themeName, path: themeName, type: "CustomTheme" },
    { name: "Masterplop_logo.png", path: "Masterplop_logo.png", type: "Image" },
  ] }],
  settings: { useEnhancedTooltips: true },
});
writeJson(path.join(reportDir, "definition.pbir"), {
  $schema: "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
  version: "4.0",
  datasetReference: { byPath: { path: `../${projectName}.SemanticModel` } },
});
writeJson(path.join(reportDir, ".platform"), {
  $schema: "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  metadata: { type: "Report", displayName: projectName },
  config: { version: "2.0", logicalId: crypto.randomUUID() },
});

writeJson(path.join(pagesDir, "pages.json"), {
  $schema: "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
  pageOrder: ["resumen_ejecutivo", "analisis_transaccional", "campana_mayo_2024"],
  activePageName: "resumen_ejecutivo",
});

page("resumen_ejecutivo", "1 · Resumen Ejecutivo");
page("analisis_transaccional", "2 · Análisis Transaccional");
page("campana_mayo_2024", "3 · Campaña Mayo 2024");

header("resumen_ejecutivo", "Titulo resumen", "Subtitulo general");
const summaryCards = [
  ["Tarjetas activas", "Tarjetas activas", colors.blue, 22], ["Transacciones", "Transacciones", colors.blue, 22],
  ["Gasto neto USD", "Gasto neto USD", colors.purple, 12], ["Ticket promedio USD", "Ticket promedio USD", colors.purple, 19],
  ["Cashback mayo USD", "Cashback oficial USD", "#B77900", 18], ["Beneficiadas", "Tarjetas beneficiadas", colors.purple, 22],
];
summaryCards.forEach(([title, measureName, accent, fontSize], i) => card("resumen_ejecutivo", `kpi_${i + 1}`, title, measureName, 24 + i * 207, 98, 192, 82, accent, 10 + i, { valueFontSize: fontSize }));
const insightCards = [
  ["Actividad crédito T2 vs T1", "Crecimiento tarjetas credito", colors.purple],
  ["Ticket crédito T2 vs T1", "Crecimiento ticket credito", colors.purple],
  ["Concentración Top 3", "Concentracion Top 3", colors.blue],
  ["Líder contactless", "Lider contactless", colors.green],
];
insightCards.forEach(([title, measureName, accent], i) => card("resumen_ejecutivo", `insight_${i + 1}`, title, measureName, 24 + i * 309, 194, 294, 74, accent, 20 + i, { valueFontSize: 18 }));
const top5Category = col("top_mcg_5", "mcg_name", "Categoría MCG");
const top5Value = measure("executive", "Participacion MCG Top5", "Participación");
chart("resumen_ejecutivo", "top5_mcg", "clusteredBarChart", "Top 5 categorías por participación del gasto neto", { Category: { projections: [top5Category] }, Y: { projections: [top5Value] } }, [top5Category, top5Value], 24, 284, 606, 392, colors.purple, 30, { sortBy: top5Value });
const c5Category = col("contactless_5", "issuer_country", "País emisor");
const c5Value = measure("executive", "Adopcion contactless Top5", "Adopción contactless");
chart("resumen_ejecutivo", "top5_contactless", "clusteredBarChart", "Top 5 mercados por adopción contactless", { Category: { projections: [c5Category] }, Y: { projections: [c5Value] } }, [c5Category, c5Value], 650, 284, 606, 392, colors.blue, 31, { sortBy: c5Value });

header("analisis_transaccional", "Titulo transaccional", "Subtitulo general");
slicer("analisis_transaccional", "slicer_tipo", "Tipo", col("volume", "product_type", "Tipo"), 24, 96, 180, 64, 10);
slicer("analisis_transaccional", "slicer_pais", "País emisor", col("regional_ticket", "issuer_country", "País emisor"), 218, 96, 210, 64, 11);
slicer("analisis_transaccional", "slicer_producto", "Producto", col("regional_ticket", "product_name", "Producto"), 442, 96, 180, 64, 12);
card("analisis_transaccional", "note_market", "Definición regional", "Regla mercado regional", 636, 96, 620, 64, colors.blue, 13, { calloutFontSize: 13, calloutColor: colors.muted });
const volumePeriod = col("volume", "period_label", "Período");
const volumeType = col("volume", "product_type", "Tipo");
const activeCards = measure("executive", "Tarjetas activas periodo", "Tarjetas activas");
chart("analisis_transaccional", "volume_chart", "clusteredColumnChart", "Tarjetas distintas por trimestre y tipo", { Category: { projections: [volumePeriod] }, Series: { projections: [volumeType] }, Y: { projections: [activeCards] } }, [volumePeriod, volumeType, activeCards], 24, 174, 400, 190, colors.blue, 20, { useThemeColors: true });
const ticketPeriod = col("quarterly_ticket", "period_label", "Período");
const ticketValue = measure("executive", "Ticket trimestral credito USD", "Ticket crédito USD");
chart("analisis_transaccional", "ticket_chart", "lineChart", "Ticket trimestral de crédito", { Category: { projections: [ticketPeriod] }, Y: { projections: [ticketValue] } }, [ticketPeriod, ticketValue], 440, 174, 400, 190, colors.yellow, 21);
const regionalProduct = col("regional_ticket", "product_name", "Producto");
const regionalValue = measure("executive", "Ticket regional USD", "Ticket regional");
chart("analisis_transaccional", "regional_chart", "clusteredColumnChart", "Ticket regional por producto · filtre país emisor", { Category: { projections: [regionalProduct] }, Y: { projections: [regionalValue] } }, [regionalProduct, regionalValue], 856, 174, 400, 190, colors.blue, 22);
const topCategory = col("top_mcg", "mcg_name", "Categoría MCG");
const topValue = measure("executive", "Participacion MCG", "Participación");
chart("analisis_transaccional", "top_mcg", "clusteredBarChart", "Top 10 MCG · denominador global", { Category: { projections: [topCategory] }, Y: { projections: [topValue] } }, [topCategory, topValue], 24, 378, 606, 302, colors.purple, 30, { sortBy: topValue });
const contactCategory = col("contactless", "issuer_country", "País emisor");
const contactValue = measure("executive", "Adopcion contactless", "Adopción");
chart("analisis_transaccional", "contactless", "clusteredBarChart", "Adopción contactless por país emisor", { Category: { projections: [contactCategory] }, Y: { projections: [contactValue] } }, [contactCategory, contactValue], 650, 378, 606, 302, colors.blue, 31, { sortBy: contactValue });

header("campana_mayo_2024", "Titulo campana", "Subtitulo general");
const campaignCards = [
  ["Cashback oficial USD", "Cashback oficial USD", "#B77900", 18], ["Beneficiadas", "Tarjetas beneficiadas", colors.purple, 22],
  ["Topadas", "Tarjetas topadas", colors.purple, 22], ["Gasto elegible USD", "Gasto elegible USD", colors.purple, 14],
  ["Tx elegibles", "Transacciones elegibles", colors.blue, 21], ["Ahorro por tope USD", "Ahorro por tope USD", colors.purple, 18],
];
campaignCards.forEach(([title, measureName, accent, fontSize], i) => card("campana_mayo_2024", `campaign_kpi_${i + 1}`, title, measureName, 24 + i * 207, 98, 192, 82, accent, 10 + i, { valueFontSize: fontSize }));
const rules = [
  ["1 · Elegibilidad", "Regla elegibilidad"], ["2 · Geografía", "Regla geografia"],
  ["3 · Beneficio", "Regla beneficio"], ["4 · Redondeo", "Regla redondeo"],
];
rules.forEach(([title, measureName], i) => card("campana_mayo_2024", `rule_${i + 1}`, title, measureName, 24 + i * 309, 194, 294, 72, colors.blue, 20 + i, { valueFontSize: 11, valueColor: colors.ink, labelColor: colors.blue }));
const bridgeStep = col("campaign_bridge", "step", "Concepto");
const bridgeAmount = measure("executive", "Monto puente USD", "Monto USD");
chart("campana_mayo_2024", "bridge", "waterfallChart", "Puente de costo: cashback sin tope menos ahorro", { Category: { projections: [bridgeStep] }, Y: { projections: [bridgeAmount] } }, [bridgeStep, bridgeAmount], 24, 284, 396, 390, colors.purple, 30);
const scenarioCategory = col("campaign_scenarios", "scenario", "Escenario");
const scenarioAmount = measure("executive", "Monto escenario USD", "Costo USD");
chart("campana_mayo_2024", "scenarios", "clusteredColumnChart", "Sensibilidad del costo de campaña", { Category: { projections: [scenarioCategory] }, Y: { projections: [scenarioAmount] } }, [scenarioCategory, scenarioAmount], 436, 284, 396, 390, colors.yellow, 31);
const diagCategory = col("cashback_diagnostic", "diagnostic_status", "Diagnóstico");
const diagCount = measure("executive", "Transacciones diagnostico", "Transacciones");
chart("campana_mayo_2024", "diagnostic", "clusteredBarChart", "Geografía real versus flag is_xb", { Category: { projections: [diagCategory] }, Y: { projections: [diagCount] } }, [diagCategory, diagCount], 848, 284, 408, 390, colors.blue, 32);

writeJson(path.join(root, `${projectName}.pbip`), {
  $schema: "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
  version: "1.0",
  artifacts: [{ report: { path: `${projectName}.Report` } }],
  settings: { enableAutoRecovery: true },
});

console.log(`Generated ${projectName}.pbip with ${Object.keys(configs).length} aggregate tables and 3 pages.`);
