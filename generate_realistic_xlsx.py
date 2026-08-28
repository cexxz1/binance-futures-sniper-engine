import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# run_claude_spec_audit.py'dan çıkan gerçek işlemler
trades_data = [
    {"sym": "ZECUSDT", "entry_dt": "03.08.2026 10:00", "exit_dt": "06.08.2026 01:00", "lev": 18, "entry_p": 481.18, "exit_p": 507.59, "dur": 63, "margin": 120.00, "pos": 2160.00, "cost": 4.10, "pnl": 110.15, "bal": 230.15, "reason": "1H Kapanış Trend Sonu"},
    {"sym": "POLUSDT", "entry_dt": "07.08.2026 09:00", "exit_dt": "07.08.2026 19:00", "lev": 25, "entry_p": 0.07626, "exit_p": 0.07499, "dur": 10, "margin": 230.15, "pos": 5753.75, "cost": 8.63, "pnl": -104.42, "bal": 125.73, "reason": "1H Kapanış Trend Sonu"},
    {"sym": "CRVUSDT", "entry_dt": "08.08.2026 03:00", "exit_dt": "11.08.2026 07:00", "lev": 25, "entry_p": 0.21590, "exit_p": 0.25925, "dur": 76, "margin": 157.16, "pos": 3929.06, "cost": 8.25, "pnl": 771.60, "bal": 897.33, "reason": "Trailing SL / Zırhlı Stop"},
    {"sym": "ESPUSDT", "entry_dt": "14.08.2026 11:00", "exit_dt": "14.08.2026 13:00", "lev": 18, "entry_p": 0.07600, "exit_p": 0.07448, "dur": 2, "margin": 897.33, "pos": 16151.94, "cost": 22.61, "pnl": -345.65, "bal": 551.68, "reason": "Trailing SL / Zırhlı Stop"},
    {"sym": "WLDUSDT", "entry_dt": "14.08.2026 15:00", "exit_dt": "14.08.2026 21:00", "lev": 14, "entry_p": 0.34580, "exit_p": 0.33888, "dur": 6, "margin": 551.68, "pos": 7723.52, "cost": 10.81, "pnl": -165.50, "bal": 386.18, "reason": "Trailing SL / Zırhlı Stop"},
    {"sym": "CAKEUSDT", "entry_dt": "16.08.2026 09:00", "exit_dt": "18.08.2026 02:00", "lev": 25, "entry_p": 1.45020, "exit_p": 1.45280, "dur": 41, "margin": 386.18, "pos": 9654.50, "cost": 17.38, "pnl": -0.25, "bal": 385.93, "reason": "1H Kapanış Trend Sonu"},
    {"sym": "ARBUSDT", "entry_dt": "18.08.2026 08:00", "exit_dt": "21.08.2026 19:00", "lev": 18, "entry_p": 0.07597, "exit_p": 0.09396, "dur": 83, "margin": 482.41, "pos": 8683.43, "cost": 21.71, "pnl": 2012.30, "bal": 2398.23, "reason": "Trailing SL / Zırhlı Stop"},
    {"sym": "ZECUSDT", "entry_dt": "26.08.2026 22:00", "exit_dt": "27.08.2026 01:00", "lev": 18, "entry_p": 810.64, "exit_p": 794.42, "dur": 3, "margin": 2398.23, "pos": 43168.14, "cost": 60.44, "pnl": -925.32, "bal": 1472.91, "reason": "Trailing SL / Zırhlı Stop"}
]

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "30G Gercekci Denetim"

headers = [
    "İşlem No", "Parite", "Giriş Tarihi", "Çıkış Tarihi", "Kaldıraç",
    "Giriş Fiyatı ($)", "Çıkış Fiyatı ($)", "Süre (Saat)", "Marjin ($)",
    "Pozisyon ($)", "Ödenen Komisyon & Fonlama ($)", "Net PnL ($)", "Net PnL (TL)",
    "Net Kasa ($)", "Net Kasa (TL)", "Çıkış Nedeni"
]

header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
border_thin = Border(left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'), top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9'))

ws.append(headers)
for col in range(1, len(headers)+1):
    cell = ws.cell(row=1, column=col)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center")

for idx, t in enumerate(trades_data, 1):
    row = [
        idx, t['sym'], t['entry_dt'], t['exit_dt'], f"{t['lev']}x",
        t['entry_p'], t['exit_p'], t['dur'], t['margin'],
        t['pos'], t['cost'], t['pnl'], t['pnl'] * 48.0,
        t['bal'], t['bal'] * 48.0, t['reason']
    ]
    ws.append(row)
    r_idx = idx + 1
    
    pnl_cell = ws.cell(row=r_idx, column=12)
    if t['pnl'] >= 0:
        pnl_cell.fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        pnl_cell.font = Font(name="Arial", color="375623", bold=True)
    else:
        pnl_cell.fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
        pnl_cell.font = Font(name="Arial", color="C65911", bold=True)

    for c in range(1, len(headers)+1):
        ws.cell(row=r_idx, column=c).border = border_thin

for col in ws.columns:
    max_l = max(len(str(cell.value or '')) for cell in col)
    col_letter = get_column_letter(col[0].column)
    ws.column_dimensions[col_letter].width = max(max_l + 3, 12)

out_xlsx = "C:/Users/depco/OneDrive/Desktop/30_GUNLUK_GERCEKCI_AKILLI_RAPOR.xlsx"
wb.save(out_xlsx)
print(f"[OK] Rapor Basariyla Kaydedildi: {out_xlsx}")
