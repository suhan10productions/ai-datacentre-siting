"""Builds the calculation workbook for the paper. All results are formulas."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.comments import Comment

OUT = "datacentre_model_calculations.xlsx"
F = "Arial"
BLUE, GREEN, BLACK = "0000FF", "008000", "000000"
HDR_FILL = PatternFill("solid", fgColor="E7E6E6")
KEY_FILL = PatternFill("solid", fgColor="FFFF00")
thin = Side(style="thin", color="BFBFBF")
BOTTOM = Border(bottom=thin)

wb = Workbook()


def font(color=BLACK, bold=False, size=10, italic=False):
    return Font(name=F, color=color, bold=bold, size=size, italic=italic)


def title(ws, text, note):
    ws["B2"] = text
    ws["B2"].font = font(bold=True, size=13)
    ws["B3"] = note
    ws["B3"].font = font(italic=True, size=9, color="595959")


def header(ws, row, labels, col=2):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=lab)
        c.font = font(bold=True)
        c.fill = HDR_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
        c.border = BOTTOM


def put(ws, ref, value, fmt=None, color=BLACK, bold=False, fill=None):
    c = ws[ref]
    c.value = value
    c.font = font(color=color, bold=bold)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    return c


def widths(ws, w):
    for col, width in w.items():
        ws.column_dimensions[col].width = width


# =================================================================== Inputs
ws = wb.active
ws.title = "Inputs"
title(ws, "Model inputs",
      "Blue cells are inputs; edit these and every result recalculates. "
      "Low / Central / High are the sensitivity range used in Section 4.2.")
header(ws, 5, ["Parameter", "Low", "Central", "High", "Unit", "Source"])
rows = [
    ("Installed IT capacity, 2031", 180, 200, 220, "GW",
     "JLL (2026), Section 3.2; tested range of plus or minus 10%"),
    ("Server idle power share", 0.20, 0.27, 0.36, "fraction of maximum power",
     "Shehabi et al. (2024), LBNL, p. 27: conventional servers 36% (2023), 27% (2028); AI servers 20%. "
     "Central holds the 2028 value flat to 2031"),
    ("PUE", 1.04, 1.30, 1.57, "ratio",
     "Low: RAND new-build trajectory. Central: 2031 capacity shares applied to 1.15 (hyperscale, just below LBNL 2023 range 1.16-1.28) and 1.57 (rest) = 1.29, rounded. "
     "High: Uptime Institute fleet average. Section 3.2"),
    ("Grid carbon intensity", 345, 395, 445, "g CO2 per kWh",
     "High: IEA 2024 global average. Low: IEA 2025-2027 decline (~3.6%/yr) carried to 2031. Central: midpoint"),
    ("WUE (direct water)", 0.32, 0.48, 1.8, "L per kWh of IT energy",
     "Central: upper end of LBNL 2024 projected US average (p. 49). Low: LBNL 2024 hyperscale median (p. 48). High: LBNL 2016 average"),
]
for i, (lab, lo, ce, hi, unit, src) in enumerate(rows):
    r = 6 + i
    put(ws, f"B{r}", lab)
    pct = "0%" if lab.startswith("Server idle") else ("0.00" if lab in ("PUE",) else
                                                      ("0.00" if "WUE" in lab else "#,##0"))
    for col, v in zip("CDE", (lo, ce, hi)):
        put(ws, f"{col}{r}", v, pct, BLUE)
    ws[f"D{r}"].fill = KEY_FILL
    put(ws, f"F{r}", unit)
    put(ws, f"G{r}", src)
    ws[f"G{r}"].alignment = Alignment(wrap_text=True, vertical="top")

put(ws, "B11", "Base-year calibration factor (rho)")
put(ws, "C11", "=Calibration!$C$29", "0.000", GREEN)
put(ws, "D11", "=Calibration!$C$29", "0.000", GREEN, fill=KEY_FILL)
put(ws, "E11", 1.0, "0.000", BLUE)
put(ws, "F11", "ratio")
put(ws, "G11", "Low and central: calibrated so the model reproduces the IEA's 2026 estimate (Calibration sheet, Eq. 7). "
               "High: no calibration (model as built)")
ws["G11"].alignment = Alignment(wrap_text=True, vertical="top")

header(ws, 12, ["Constant", "Value", "", "", "Unit", "Source"])
consts = [
    ("Hours per year", 8760, "#,##0", "hours", "365 x 24"),
    ("LBNL series start year", 2014, "0", "year", "Shehabi et al. (2024), p. 28"),
    ("LBNL series end year", 2027, "0", "year", "Shehabi et al. (2024), p. 28"),
    ("Projection year", 2031, "0", "year", "Section 3.2"),
    ("UNU-INWEH water footprint, 2030", 9.3, "0.0", "trillion litres",
     "UNU-INWEH (2026); direct plus electricity-generation water"),
    ("Energy basis of the UNU figure", 945, "#,##0", "TWh", "IEA 2030 base case, Sections 1 and 4.1"),
    ("S&P 2030 demand estimate", 1587, "#,##0", "TWh", "S&P Global 451 Research, Sections 1 and 4.1"),
    ("Committed nuclear capacity", 9.8, "0.0", "GW", "SMR Intel (2026), Section 5.2"),
    ("Nuclear capacity factor", 0.90, "0%", "fraction", "Typical US fleet, Section 5.2"),
]
for i, (lab, v, fmt, unit, src) in enumerate(consts):
    r = 13 + i
    put(ws, f"B{r}", lab)
    put(ws, f"C{r}", v, fmt, BLUE)
    put(ws, f"F{r}", unit)
    put(ws, f"G{r}", src)
widths(ws, {"A": 2, "B": 34, "C": 10, "D": 10, "E": 10, "F": 24, "G": 70})
for r in range(6, 12):
    ws.row_dimensions[r].height = 30

# Named references used below (cell addresses)
CAP, IDLE, PUE, GRID, WUE, RHO = 6, 7, 8, 9, 10, 11          # rows; C=low D=central E=high
HOURS, Y0, Y1, YP, UNU_W, UNU_E, SP, NUC, NUC_CF = (f"Inputs!$C${r}" for r in range(13, 22))


def inp(row, level):
    return f"Inputs!${'CDE'[level]}${row}"


# =================================================================== Utilisation
wu = wb.create_sheet("Utilisation")
title(wu, "Fleet utilisation and electrical load factor (Section 3.2)",
      "LBNL facility-type utilisation (operational time) extrapolated linearly to 2031, "
      "weighted by capacity share, then converted to electrical load with the idle share.")
header(wu, 5, ["Facility type", "2014", "2027", "Extrapolated 2031", "Source"])
lbnl = [("Hyperscale", 0.45, 0.50), ("Colocation", 0.21, 0.35), ("Internal / small", 0.11, 0.20)]
for i, (lab, a, b) in enumerate(lbnl):
    r = 6 + i
    put(wu, f"B{r}", lab)
    put(wu, f"C{r}", a, "0.0%", BLUE)
    put(wu, f"D{r}", b, "0.0%", BLUE)
    put(wu, f"E{r}", f"=D{r}+(D{r}-C{r})/({Y1}-{Y0})*({YP}-{Y1})", "0.00%")
    put(wu, f"F{r}", "Shehabi et al. (2024), p. 28")

header(wu, 10, ["Capacity-share scenario", "Hyperscale share", "Colocation share",
                "Internal / small share", "Weighted utilisation",
                "Load factor (central idle share)", "Note"])
shares = [("Slower consolidation (low)", 0.60, 0.40 * 14 / 33, 0.40 * 19 / 33,
           "Hyperscale 60%, rest in the 2031 ratio 14:19 (assumption)"),
          ("Central (Synergy projection)", 0.67, 0.14, 0.19,
           "Synergy Research Group (2026): hyperscale 67%, on-premises 19%, colocation 14% by difference"),
          ("All-hyperscale (high)", 1.0, 0.0, 0.0, "Upper bound")]
for i, (lab, h, c, s, note) in enumerate(shares):
    r = 11 + i
    put(wu, f"B{r}", lab, bold=(i == 1))
    for col, v in zip("CDE", (h, c, s)):
        put(wu, f"{col}{r}", v, "0%", BLUE)
    put(wu, f"F{r}", f"=C{r}*$E$6+D{r}*$E$7+E{r}*$E$8", "0.00%", bold=(i == 1))
    put(wu, f"G{r}", f"={inp(IDLE, 1)}+(1-{inp(IDLE, 1)})*F{r}", "0.0%", bold=(i == 1))
    put(wu, f"H{r}", note)
put(wu, "B15", "Check: shares sum to 100%")
for i in range(3):
    put(wu, f"C{16 + i}", f"=C{11 + i}+D{11 + i}+E{11 + i}", "0%")
    put(wu, f"B{16 + i}", shares[i][0])
put(wu, "B20", "Load factor = idle share + (1 - idle share) x utilisation  "
               "(Shehabi et al., 2024, pp. 18-19: linear interpolation between idle and maximum power)")
wu["B20"].font = font(italic=True, size=9)
widths(wu, {"A": 2, "B": 30, "C": 13, "D": 13, "E": 15, "F": 14, "G": 16, "H": 60})
wu.row_dimensions[10].height = 30

ULOW, UCEN, UHIGH = "Utilisation!$F$11", "Utilisation!$F$12", "Utilisation!$F$13"
U = [ULOW, UCEN, UHIGH]


# =================================================================== Calibration
wc = wb.create_sheet("Calibration")
title(wc, "Base-year check and calibration (Section 3.2, Eq. 7)",
      "Runs the model for 2026 and compares it with published estimates of 2026 use. "
      "rho = IEA 2026 estimate / model 2026 facility energy.")
header(wc, 5, ["Item", "Value", "Unit", "Source"])
calrows = [
    (6, "Installed IT capacity, start of 2026", 103, "#,##0", "GW", "JLL (2026)", BLUE),
    (7, "Completions expected during 2025", 7, "#,##0", "GW", "JLL (2025)", BLUE),
    (8, "Average installed capacity, 2025", "=C6-C7/2", "#,##0.0", "GW", "mid-year", BLACK),
    (9, "Hyperscale share, 2025", 0.48, "0.0%", "", "Synergy Research Group (2026)", BLUE),
    (10, "Colocation share, 2025", 0.20, "0.0%", "", "Synergy Research Group (2026)", BLUE),
    (11, "On-premises (internal) share, 2025", 0.32, "0.0%", "", "Synergy Research Group (2026)", BLUE),
    (12, "Hyperscale utilisation, 2025", f"=Utilisation!$D$6+(Utilisation!$D$6-Utilisation!$C$6)/({Y1}-{Y0})*(2025-{Y1})", "0.00%", "", "LBNL trend at 2025", BLACK),
    (13, "Colocation utilisation, 2025", f"=Utilisation!$D$7+(Utilisation!$D$7-Utilisation!$C$7)/({Y1}-{Y0})*(2025-{Y1})", "0.00%", "", "LBNL trend at 2025", BLACK),
    (14, "Internal / small utilisation, 2025", f"=Utilisation!$D$8+(Utilisation!$D$8-Utilisation!$C$8)/({Y1}-{Y0})*(2025-{Y1})", "0.00%", "", "LBNL trend at 2025", BLACK),
    (15, "Fleet utilisation, 2025", "=C9*C12+C10*C13+C11*C14", "0.00%", "", "capacity-weighted", BLACK),
    (16, "Idle share, 2023", 0.36, "0%", "of max power", "Shehabi et al. (2024), p. 27", BLUE),
    (17, "Idle share, 2028", 0.27, "0%", "of max power", "Shehabi et al. (2024), p. 27", BLUE),
    (18, "Idle share, 2025", "=C16+(C17-C16)*2/5", "0.0%", "of max power", "linear interpolation", BLACK),
    (19, "Load factor, 2025", "=C18+(1-C18)*C15", "0.00%", "", "Eq. 6", BLACK),
    (20, "PUE, 2025", 1.56, "0.00", "", "Uptime Institute (2024) fleet average", BLUE),
    (21, "Model facility energy, 2025", f"=C8*C19*{HOURS}/1000*C20", "#,##0", "TWh", "Eqs. 1-2 with rho = 1", BLACK),
    (22, "IEA data centre use, 2024", 415, "#,##0", "TWh", "IEA (2025a)", BLUE),
    (23, "IEA growth in 2025", 0.17, "0%", "", "IEA (2026)", BLUE),
    (24, "IEA estimate, 2025", "=C22*(1+C23)", "#,##0", "TWh", "", BLACK),
    (25, "451 Research, 2025", 860, "#,##0", "TWh", "S&P Global (2025), includes crypto mining", BLUE),
    (26, "Model / IEA, 2025", "=C21/C24", "0.00", "x", "", BLACK),
    (27, "Model / 451 Research, 2025", "=C21/C25", "0.00", "x", "", BLACK),
    (28, "IEA energy per GW of capacity, 2025", "=C24/C8", "0.00", "TWh per GW", "", BLACK),
    (29, "Calibration factor rho", "=C24/C21", "0.000", "", "Eq. 7", BLACK),
    (30, "IEA energy per GW of capacity, 2030", f"={UNU_E}/{inp(CAP, 1)}", "0.00", "TWh per GW", "IEA 2030 / JLL 2030", BLACK),
]
for r, lab, v, fmt, unit, src, col in calrows:
    put(wc, f"B{r}", lab, bold=(r == 29))
    put(wc, f"C{r}", v, fmt, col, bold=(r == 29), fill=KEY_FILL if r == 29 else None)
    put(wc, f"D{r}", unit)
    put(wc, f"E{r}", src)
widths(wc, {"A": 2, "B": 40, "C": 12, "D": 14, "E": 50})

# =================================================================== Results
wr = wb.create_sheet("Results")
title(wr, "Results (Sections 4 and 5.2)",
      "Every value is a formula. Green cells pull from other sheets.")

# --- A. Central chain
put(wr, "B5", "A. Central case, step by step", bold=True)
header(wr, 6, ["Step", "Value", "Unit", "Formula"])
chain = [
    ("Weighted utilisation", f"={UCEN}", "0.00%", "share of time servers are working", "Utilisation sheet", GREEN),
    ("Idle power share", f"={inp(IDLE, 1)}", "0%", "fraction of maximum power", "Inputs", GREEN),
    ("Electrical load factor", "=C8+(1-C8)*C7", "0.0%", "fraction of maximum power", "idle + (1 - idle) x utilisation", BLACK),
    ("Calibration factor rho", f"={inp(RHO, 1)}", "0.000", "ratio", "Calibration sheet", GREEN),
    ("IT energy", f"=C10*{inp(CAP, 1)}*C9*{HOURS}/1000", "#,##0.0", "TWh", "rho x capacity x load factor x hours / 1000", BLACK),
    ("Total facility energy", f"=C11*{inp(PUE, 1)}", "#,##0.0", "TWh", "IT energy x PUE", BLACK),
    ("Emissions", f"=C12*{inp(GRID, 1)}/1000", "#,##0.0", "Mt CO2", "facility energy x grid intensity / 1000", BLACK),
    ("Direct water", f"=C11*{inp(WUE, 1)}/1000", "0.00", "trillion litres", "IT energy x WUE / 1000", BLACK),
    ("UNU implied combined intensity", f"={UNU_W}*1000/{UNU_E}", "0.00", "L per kWh", "UNU water / UNU energy", BLACK),
    ("Combined water (direct + generation)", "=C12*C15/1000", "0.0", "trillion litres", "facility energy x combined intensity / 1000", BLACK),
    ("Combined / direct ratio", "=C16/C14", "0.0", "x", "", BLACK),
]
for i, (lab, f, fmt, unit, desc, col) in enumerate(chain):
    r = 7 + i
    put(wr, f"B{r}", lab)
    put(wr, f"C{r}", f, fmt, col, bold=lab in ("Emissions", "Direct water"))
    put(wr, f"D{r}", unit)
    put(wr, f"E{r}", desc)

# --- B. Table 8.1
put(wr, "B19", "B. Results under the three PUE values (Section 4.1 table)", bold=True)
header(wr, 20, ["", "New-build (low PUE)", "Blended fleet (central)", "Current fleet (high PUE)", "Unit"])
labels81 = [("PUE", "{pue}", "0.00", ""),
            ("IT energy", "=$C$11", "#,##0.0", "TWh"),
            ("Total facility energy", "=$C$11*{pue}", "#,##0.0", "TWh"),
            ("Emissions, static grid", "=$C$11*{pue}*" + inp(GRID, 2) + "/1000", "#,##0.0", "Mt CO2"),
            ("Emissions, decarbonising grid", "=$C$11*{pue}*" + inp(GRID, 0) + "/1000", "#,##0.0", "Mt CO2"),
            ("Direct water", "=$C$14", "0.00", "trillion litres")]
for i, (lab, tmpl, fmt, unit) in enumerate(labels81):
    r = 21 + i
    put(wr, f"B{r}", lab)
    for j, col in enumerate("CDE"):
        pref = inp(PUE, j)
        f = tmpl.format(pue=pref) if "{pue}" in tmpl else tmpl
        if lab == "PUE":
            f = "=" + pref
        put(wr, f"{col}{r}", f, fmt, GREEN if lab == "PUE" else BLACK)
    put(wr, f"F{r}", unit)

# --- C. Bundled scenarios
put(wr, "B29", "C. Bundled scenarios (Section 4.2)", bold=True)
header(wr, 30, ["Scenario", "Capacity (GW)", "Utilisation", "Idle share", "Load factor", "PUE",
                "Grid (g/kWh)", "WUE (L/kWh)", "rho", "IT energy (TWh)", "Facility energy (TWh)",
                "CO2 (Mt)", "Direct water (tn L)", "Combined water (tn L)"])
for j, name in enumerate(["Low impact", "Central", "High impact"]):
    r = 31 + j
    put(wr, f"B{r}", name, bold=(j == 1))
    put(wr, f"C{r}", f"={inp(CAP, j)}", "#,##0", GREEN)
    put(wr, f"D{r}", f"={U[j]}", "0.0%", GREEN)
    put(wr, f"E{r}", f"={inp(IDLE, j)}", "0%", GREEN)
    put(wr, f"F{r}", f"=E{r}+(1-E{r})*D{r}", "0.0%")
    put(wr, f"G{r}", f"={inp(PUE, j)}", "0.00", GREEN)
    put(wr, f"H{r}", f"={inp(GRID, j)}", "#,##0", GREEN)
    put(wr, f"I{r}", f"={inp(WUE, j)}", "0.0", GREEN)
    put(wr, f"J{r}", f"={inp(RHO, j)}", "0.000", GREEN)
    put(wr, f"K{r}", f"=J{r}*C{r}*F{r}*{HOURS}/1000", "#,##0.0")
    put(wr, f"L{r}", f"=K{r}*G{r}", "#,##0.0")
    put(wr, f"M{r}", f"=L{r}*H{r}/1000", "#,##0", bold=True)
    put(wr, f"N{r}", f"=K{r}*I{r}/1000", "0.00", bold=True)
    put(wr, f"O{r}", f"=L{r}*$C$15/1000", "0.0")

# --- D. One-at-a-time sensitivity
put(wr, "B36", "D. One-at-a-time sensitivity, emissions (Section 4.2)", bold=True)
header(wr, 37, ["Parameter varied", "Emissions at low end (Mt)", "Emissions at high end (Mt)",
                "Swing as % of central"])
# emissions(cap, u, idle, pue, grid)


def em(cap, u, idle, pue, grid, rho):
    return f"={rho}*{cap}*({idle}+(1-{idle})*{u})*{HOURS}/1000*{pue}*{grid}/1000"


c = dict(cap=inp(CAP, 1), u=UCEN, idle=inp(IDLE, 1), pue=inp(PUE, 1), grid=inp(GRID, 1), rho=inp(RHO, 1))
sens = [("Base-year calibration (rho)", "rho", [inp(RHO, 0), inp(RHO, 2)]),
        ("PUE", "pue", [inp(PUE, 0), inp(PUE, 2)]),
        ("Grid carbon intensity", "grid", [inp(GRID, 0), inp(GRID, 2)]),
        ("Capacity", "cap", [inp(CAP, 0), inp(CAP, 2)]),
        ("Idle power share", "idle", [inp(IDLE, 0), inp(IDLE, 2)]),
        ("Utilisation", "u", [ULOW, UHIGH])]
for i, (lab, key, ends) in enumerate(sens):
    r = 38 + i
    put(wr, f"B{r}", lab)
    for col, val in zip("CD", ends):
        p = dict(c)
        p[key] = val
        put(wr, f"{col}{r}", em(**p), "#,##0")
    put(wr, f"E{r}", f"=(D{r}-C{r})/$C$13", "0%", bold=True)

put(wr, "B45", "Water swing (trillion litres)", bold=True)
header(wr, 46, ["Parameter varied", "Low end", "High end", "Swing"])
for i, (lab, row) in enumerate([("WUE", WUE), ("Capacity", CAP)]):
    r = 47 + i
    put(wr, f"B{r}", lab)
    if lab == "WUE":
        lo = f"=$C$11*{inp(WUE, 0)}/1000"
        hi = f"=$C$11*{inp(WUE, 2)}/1000"
    else:
        lo = f"=$C$10*{inp(CAP, 0)}*$C$9*{HOURS}/1000*{inp(WUE, 1)}/1000"
        hi = f"=$C$10*{inp(CAP, 2)}*$C$9*{HOURS}/1000*{inp(WUE, 1)}/1000"
    put(wr, f"C{r}", lo, "0.00")
    put(wr, f"D{r}", hi, "0.00")
    put(wr, f"E{r}", f"=D{r}-C{r}", "0.00")

# --- E. Cross-checks
put(wr, "B51", "E. Cross-checks", bold=True)
header(wr, 52, ["Check", "Value", "Unit", "Section"])
checks = [
    ("Central facility energy vs IEA 2030 (945 TWh)", f"=C12/{UNU_E}", "0.00", "x", "4.1"),
    ("Uncalibrated central facility energy (rho = 1)", f"=C12/C10", "#,##0", "TWh", "4.1"),
    ("Combined water vs UNU 9.3 tn L", f"=C16/{UNU_W}", "0.00", "x", "4.3"),
    ("Nuclear annual supply", f"={NUC}*{NUC_CF}*{HOURS}/1000", "#,##0.0", "TWh", "5.2"),
    ("Nuclear share of central facility demand", "=C56/C12", "0.0%", "", "5.2"),
    ("Effect of idle-power conversion on energy", "=C9/C7", "0.00", "x (load factor / utilisation)", "3.2"),
]
for i, (lab, f, fmt, unit, sec) in enumerate(checks):
    r = 53 + i
    put(wr, f"B{r}", lab)
    put(wr, f"C{r}", f, fmt)
    put(wr, f"D{r}", unit)
    put(wr, f"E{r}", "Section " + sec)
widths(wr, {"A": 2, "B": 44, "C": 15, "D": 15, "E": 15, "F": 12, "G": 10, "H": 11,
            "I": 11, "J": 9, "K": 13, "L": 14, "M": 10, "N": 13, "O": 14})
wr.row_dimensions[30].height = 30
wr.row_dimensions[37].height = 30
wc.sheet_view.showGridLines = False
for ws_ in wb:
    ws_.sheet_view.showGridLines = False

wb.save(OUT)
print("saved", OUT)
