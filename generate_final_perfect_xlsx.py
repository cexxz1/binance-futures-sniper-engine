import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

trades = [
    {"sym": "ZECUSDT", "entry_dt": "03.08.2026 10:00", "exit_dt": "06.08.2026 01:00", "lev": 18, "entry_p": 481.18, "exit_p": 507.59, "dur": 63, "margin": 180.00, "pos": 3240.00, "cost": 4.54, "pnl": 171.35, "bal": 291.35, "reason": "1H Kapanış Trend Sonu"},
    {"sym": "POLUSDT", "entry_dt": "07.08.2026 09:00", "exit_dt": "07.08.2026 19:00", "lev": 25, "entry_p": 0.07626, "exit_p": 0.07499, "dur": 10, "margin": 291.35, "pos": 7283.75, "cost": 10.19, "pnl": -131.50, "bal": 159.85, "reason": "1H Kapanış Trend Sonu"},
    {"sym": "CRVUSDT", "entry_dt": "08.08.2026 03:00", "exit_dt": "11.08.2026 07:00", "lev": 25, "entry_p": 0.21590, "exit_p": 0.25925, "dur": 76, "margin": 239.78, "pos": 5994.50, "cost": 12.58, "pnl": 1190.57, "bal": 1350.42, "reason": "Trailing SL / Kâr Kilitleme"},
    {"sym": "VELVETUSDT", "entry_dt": "11.08.2026 09:00", "exit_dt": "11.08.2026 10:00", "lev": 10, "entry_p": 0.58630, "exit_p": 0.77758, "dur": 1, "margin": 1688.03, "pos": 16880.30, "cost": 23.63, "pnl": 5483.39, "bal": 6833.81, "reason": "Trailing SL / Kâr Kilitleme"},
    {"sym": "ESPUSDT", "entry_dt": "14.08.2026 11:00", "exit_dt": "14.08.2026 13:00", "lev": 18, "entry_p": 0.07600, "exit_p": 0.07448, "dur": 2, "margin": 6833.81, "pos": 123008.58, "cost": 172.21, "pnl": -2632.38, "bal": 4201.42, "reason": "Trailing SL / Zırhlı Stop"},
    {"sym": "WLDUSDT", "entry_dt": "14.08.2026 15:00", "exit_dt": "14.08.2026 21:00", "lev": 14, "entry_p": 0.34580, "exit_p": 0.33888, "dur": 6, "margin": 4201.42, "pos": 58819.88, "cost": 82.35, "pnl": -1258.75, "bal": 2942.68, "reason": "Trailing SL / Zırhlı Stop"},
    {"sym": "VELVETUSDT", "entry_dt": "16.08.2026 08:00", "exit_dt": "16.08.2026 09:00", "lev": 10, "entry_p": 1.10770, "exit_p": 1.10992, "dur": 1, "margin": 3678.35, "pos": 36783.50, "cost": 51.50, "pnl": 22.07, "bal": 2964.75, "reason": "Trailing SL / Kâr Kilitleme"},
    {"sym": "CAKEUSDT", "entry_dt": "16.08.2026 09:00", "exit_dt": "18.08.2026 02:00", "lev": 25, "entry_p": 1.45020, "exit_p": 1.45280, "dur": 41, "margin": 2964.75, "pos": 74118.75, "cost": 133.41, "pnl": -0.53, "bal": 2964.22, "reason": "1H Kapanış Trend Sonu"},
    {"sym": "ARBUSDT", "entry_dt": "18.08.2026 08:00", "exit_dt": "21.08.2026 19:00", "lev": 18, "entry_p": 0.07597, "exit_p": 0.09396, "dur": 83, "margin": 4446.33, "pos": 80033.94, "cost": 200.08, "pnl": 18773.01, "bal": 21737.22, "reason": "Trailing SL / Kâr Kilitleme"},
    {"sym": "MORPHOUSDT", "entry_dt": "23.08.2026 07:00", "exit_dt": "24.08.2026 00:00", "lev": 18, "entry_p": 2.33940, "exit_p": 2.78958, "dur": 17, "margin": 32605.83, "pos": 586904.94, "cost": 997.74, "pnl": 112060.10, "bal": 133797.32, "reason": "Trailing SL / Kâr Kilitleme"},
    {"sym": "ESPUSDT", "entry_dt": "24.08.2026 23:00", "exit_dt": "25.08.2026 20:00", "lev": 18, "entry_p": 0.08946, "exit_p": 0.08964, "dur": 21, "margin": 200695.98, "pos": 3612527.64, "cost": 6141.30, "pnl": 1806.26, "bal": 135603.59, "reason": "Trailing SL / Kâr Kilitleme"},
    {"sym": "ONTUSDT", "entry_dt": "26.08.2026 13:00", "exit_dt": "26.08.2026 14:00", "lev": 14, "entry_p": 0.05463, "exit_p": 0.05627, "dur": 1, "margin": 169504.49, "pos": 2373062.86, "cost": 3322.29, "pnl": 67869.59, "bal": 203473.18, "reason": "Trailing SL / Kâr Kilitleme"},
    {"sym": "ZECUSDT", "entry_dt": "26.08.2026 22:00", "exit_dt": "27.08.2026 01:00", "lev": 18, "entry_p": 810.64, "exit_p": 794.42, "dur": 3, "margin": 203473.18, "pos": 3662517.24, "cost": 5127.52, "pnl": -78377.87, "bal": 125095.31, "reason": "Trailing SL / Zırhlı Stop"},
    {"sym": "MOVRUSDT", "entry_dt": "27.08.2026 03:00", "exit_dt": "27.08.2026 04:00", "lev": 10, "entry_p": 0.82890, "exit_p": 1.11131, "dur": 1, "margin": 156369.14, "pos": 1563691.40, "cost": 2189.17, "pnl": 530567.60, "bal": 655662.92, "reason": "Trailing SL / Kâr Kilitleme"}
]

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "30G Resmi Tum Maliyetler Dahil"

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

for idx, t in enumerate(trades, 1):
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

out_xlsx = "C:/Users/depco/OneDrive/Desktop/30_GUNLUK_RESMI_TUM_MALIYETLER_DAHIL_RAPOR.xlsx"
wb.save(out_xlsx)
print(f"[OK] Kusursuz Rapor Kaydedildi: {out_xlsx}")
