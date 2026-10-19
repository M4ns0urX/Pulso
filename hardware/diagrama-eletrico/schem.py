import sys
out = sys.argv[1]
W, H = 2000, 1330
S = []
C = dict(pwr='#C0392B', gnd='#33404f', i2c='#1F6FB2', spi='#7B3FA0', gpio='#0E7C7B', rf='#B7791F', ink='#1d2430', box='#1F3A5F')

def add(s): S.append(s)
def line(pts, col=C['ink'], w=2.2, dash=None):
    d = 'M' + ' L'.join(f'{x} {y}' for x, y in pts)
    add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"{" stroke-dasharray=%s" % chr(34)+dash+chr(34) if dash else ""}/>')
def dot(x, y, col=C['ink']): add(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{col}"/>')
def text(x, y, t, size=14, w=400, col=C['ink'], anchor='start', italic=False):
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{col}" text-anchor="{anchor}"{" font-style=%sitalic%s" % (chr(34),chr(34)) if italic else ""}>{t}</text>')
def tag(x, y, name, col, side='r'):
    # net label flag; side = direction it points
    w = 9 * len(name) + 18
    if side == 'r':
        add(f'<path d="M{x} {y} l10 -11 h{w} v22 h-{w} z" fill="#fff" stroke="{col}" stroke-width="2"/>')
        text(x + 10 + w / 2, y + 5, name, 13, 700, col, 'middle')
    else:
        add(f'<path d="M{x} {y} l-10 -11 h-{w} v22 h{w} z" fill="#fff" stroke="{col}" stroke-width="2"/>')
        text(x - 10 - w / 2, y + 5, name, 13, 700, col, 'middle')
def gnd(x, y):
    line([(x, y), (x, y + 12)], C['gnd'])
    for i, hw in enumerate([12, 8, 4]):
        line([(x - hw, y + 12 + i * 5), (x + hw, y + 12 + i * 5)], C['gnd'], 2)
def ic(x, y, w, h, ref, name, left=(), right=(), top=(), bottom=(), pitch=32, sub=None):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#F4F7FB" stroke="{C["box"]}" stroke-width="2.5"/>')
    text(x + 2, y - 10, f'{ref}', 13, 700, '#5b6675')
    text(x + w / 2, y + h / 2 + 6 if not (top or bottom) else y + h / 2, name, 16, 800, C['box'], 'middle')
    if sub: text(x + w / 2, y + h / 2 + 20, sub, 12.5, 400, '#5b6675', 'middle')
    P = {}
    for i, p in enumerate(left):
        yy = y + 28 + i * pitch; P[p] = (x, yy); text(x + 8, yy + 5, p, 12.5, 600, '#33404f')
    for i, p in enumerate(right):
        yy = y + 28 + i * pitch; P[p] = (x + w, yy); text(x + w - 8, yy + 5, p, 12.5, 600, '#33404f', 'end')
    n = len(top)
    for i, p in enumerate(top):
        xx = x + w * (i + 1) / (n + 1); P[p] = (xx, y); text(xx, y + 18, p, 12.5, 600, '#33404f', 'middle')
    n = len(bottom)
    for i, p in enumerate(bottom):
        xx = x + w * (i + 1) / (n + 1); P[p] = (xx, y + h); text(xx, y + h - 8, p, 12.5, 600, '#33404f', 'middle')
    return P
def res(x, y, label, vertical=True, col=C['ink']):
    if vertical:
        add(f'<rect x="{x-7}" y="{y}" width="14" height="34" fill="#fff" stroke="{col}" stroke-width="2"/>')
        text(x + 12, y + 22, label, 12, 600, '#5b6675')
        return (x, y), (x, y + 34)
    add(f'<rect x="{x}" y="{y-7}" width="34" height="14" fill="#fff" stroke="{col}" stroke-width="2"/>')
    text(x + 17, y - 12, label, 12, 600, '#5b6675', 'middle')
    return (x, y), (x + 34, y)
def cap(x, y, label, col=C['ink'], left=False):
    line([(x - 12, y), (x + 12, y)], col, 2.5); line([(x - 12, y + 7), (x + 12, y + 7)], col, 2.5)
    text(x - 16 if left else x + 16, y + 8, label, 12, 600, '#5b6675', 'end' if left else 'start')
    return (x, y), (x, y + 7)
def section(x, y, w, h, title):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="none" stroke="#CBD3DD" stroke-width="2" stroke-dasharray="8 6"/>')
    add(f'<rect x="{x+18}" y="{y-12}" width="{len(title)*9.6+24}" height="24" rx="12" fill="#1F3A5F"/>')
    text(x + 30, y + 5, title, 13, 700, '#fff')

add('<rect width="100%" height="100%" fill="#fff"/>')
text(30, 40, 'Diagrama elétrico da braçadeira Pulso', 24, 700, C['box'])
text(30, 64, 'Esquema simplificado em blocos com os sinais principais. Nomes em etiqueta indicam ligação entre pontos com o mesmo nome.', 14, 400, '#5b6675')

# ================= SECTION 1: POWER =================
section(20, 100, 1960, 380, '1 · ALIMENTAÇÃO E BATERIA')
# J1 pogo
J1 = ic(50, 150, 130, 160, 'J1', 'Pogo', right=['+5V', 'TX', 'RX', 'GND'], sub=None)
text(115, 330, 'carga magnética', 12, 400, '#5b6675', 'middle')
# TVS
x5 = J1['+5V']; line([x5, (340, x5[1])], C['pwr'], 2.6)
dot(300, x5[1], C['pwr']); line([(300, x5[1]), (300, 220)], C['pwr'])
add('<path d="M288 238 h24 l-12 -18 z" fill="#fff" stroke="#C0392B" stroke-width="2"/>'); line([(286, 220), (314, 220)], C['pwr'], 2.5)
text(316, 248, 'D1', 12, 700, '#5b6675'); line([(300, 238), (300, 262)], C['gnd']); gnd(300, 262)
line([J1['GND'], (205, J1['GND'][1]), (205, 262)], C['gnd']); gnd(205, 262)
tag(J1['TX'][0] + 4, J1['TX'][1], 'UART_TX', C['gpio']); tag(J1['RX'][0] + 4, J1['RX'][1], 'UART_RX', C['gpio'])
# U1 charger
U1 = ic(340, 150, 190, 170, 'U1', 'BQ24075', left=['IN', '', '', 'GND'], right=['SYS', 'BAT', 'CHG', 'PGOOD'], sub='carregador')

line([U1['GND'], (325, U1['GND'][1]), (325, 335)], C['gnd']); gnd(325, 335)
tag(U1['CHG'][0] + 4, U1['CHG'][1], 'CHG', C['gpio']); tag(U1['PGOOD'][0] + 4, U1['PGOOD'][1], 'PGOOD', C['gpio'])
# SYS rail
sysy = U1['SYS'][1]
line([U1['SYS'], (1120, sysy)], C['pwr'], 3)
text(560, sysy - 10, 'VSYS (3,5 – 4,4 V)', 13, 700, C['pwr'])
# BAT path -> protection -> battery
baty = U1['BAT'][1]
line([U1['BAT'], (640, baty)], C['pwr'], 2.6)
P = ic(640, 200, 190, 110, 'U2 + Q1', 'Proteção', left=['B+'], right=['P+'], sub='DW01A + FS8205A')
line([(640, baty), (640, 228)], C['pwr'], 2.6)
text(560, baty - 8, 'BAT', 13, 700, C['pwr'])
# battery symbol
bx = 900
line([P['P+'], (bx, P['P+'][1]), (bx, 250)], C['pwr'], 2.6)
for i, (hw, wd) in enumerate([(26, 3), (14, 5), (26, 3), (14, 5)]):
    line([(bx - hw, 250 + i * 10), (bx + hw, 250 + i * 10)], C['ink'], wd)
text(bx, 352, 'BT1  Li-Po 3,7 V', 14, 800, C['box'], 'middle'); text(bx, 370, '1200 mAh · via J2 (JST)', 12.5, 400, '#5b6675', 'middle')
text(bx - 40, 252, '+', 16, 800, C['pwr'])
line([(bx, 280), (bx, 300)], C['gnd']); gnd(bx, 300)
# fuel gauge
G = ic(1010, 300, 200, 120, 'U3', 'MAX17048', left=['CELL', 'GND'], right=['SDA', 'SCL', 'ALRT'])
text(1110, 440, 'medidor de bateria', 12, 400, '#5b6675', 'middle')
dot(bx, 228, C['pwr']); line([(bx, 228), (955, 228), (955, G['CELL'][1]), G['CELL']], C['pwr'])
line([G['GND'], (990, G['GND'][1]), (990, 375)], C['gnd']); gnd(990, 375)
tag(G['SDA'][0] + 4, G['SDA'][1], 'SDA', C['i2c']); tag(G['SCL'][0] + 4, G['SCL'][1], 'SCL', C['i2c']); tag(G['ALRT'][0] + 4, G['ALRT'][1], 'ALRT', C['gpio'])
# buck
B = ic(1120, 150, 170, 120, 'U4', 'TPS62840', left=['VIN', 'EN'], right=['SW', 'VOS'], sub='buck 3,3 V')
line([(1100, sysy), (1100, B['EN'][1]), B['EN']], C['pwr']); dot(1100, sysy, C['pwr'])
# inductor
sw = B['SW']; line([sw, (1320, sw[1])], C['ink'])
add(f'<path d="M1320 {sw[1]} q9 -16 18 0 q9 -16 18 0 q9 -16 18 0 q9 -16 18 0" fill="none" stroke="#1d2430" stroke-width="2.4"/>')
text(1356, sw[1] - 20, 'L1 2,2 µH', 12, 700, '#5b6675', 'middle')
v3 = (1392, sw[1]); line([v3, (1520, v3[1])], C['pwr'], 3)
line([B['VOS'], (1420, B['VOS'][1]), (1420, v3[1])], C['ink'], 1.8); dot(1420, v3[1], C['pwr'])
dot(1460, v3[1], C['pwr']); line([(1460, v3[1]), (1460, 232)], C['pwr']); cap(1460, 232, 'C2 22 µF', left=True); line([(1460, 239), (1460, 255)], C['gnd']); gnd(1460, 255)
text(1430, v3[1] - 12, '3V3', 14, 800, C['pwr'])
# LDO
L = ic(1520, 150, 160, 100, 'U5', 'TLV75518', left=['IN'], right=['OUT'], sub='LDO 1,8 V')
line([L['OUT'], (1740, L['OUT'][1])], C['pwr'], 2.6); tag(1740, L['OUT'][1], '1V8', C['pwr'])
dot(1500, v3[1], C['pwr']); line([(1500, v3[1]), (1500, 300), (1740, 300)], C['pwr'], 2.6); tag(1740, 300, '3V3', C['pwr'])
line([(1120, sysy), (1110, sysy)], C['pwr'])
dot(1080, sysy, C['pwr']); line([(1080, sysy), (1080, 120), (1740, 120)], C['pwr'], 2.6); tag(1740, 120, 'VSYS', C['pwr'])
# GND notes
text(40, 455, 'Bateria → proteção → carregador com power-path (VSYS) → buck 3,3 V (rádios e lógica) e LDO 1,8 V (núcleo do sensor). O carregador alimenta o sistema mesmo com a bateria descarregada.', 13, 400, '#5b6675', italic=True)

# ================= SECTION 2: LOGIC =================
section(20, 520, 1960, 780, '2 · PROCESSAMENTO, SENSORES E COMUNICAÇÃO')
# MCU
lp = ['PA0 SOS', 'PB5 LED_R', 'PB6 LED_G', 'PB7 MOTOR', 'PA9 CHG', 'PA10 ALRT', 'PB3 UART_TX', 'PB4 UART_RX']
rp = ['PA5 SCK', 'PA6 MISO', 'PA7 MOSI', 'PA4 NSS', 'PB8 UWB_IRQ', 'PB9 UWB_RST', 'PB10 UWB_WAKE', 'PA11 SDA', 'PA12 SCL', 'PB12 PPG_INT', 'PB13 IMU_INT']
U = ic(780, 640, 340, 420, 'U6', '', left=lp, right=rp, top=['VDD', 'RF'], bottom=['GND', 'SWDIO', 'SWCLK', 'NRST'], pitch=34)
text(950, 860, 'RAK3172', 22, 800, C['box'], 'middle'); text(950, 884, 'STM32WLE5', 13, 600, '#5b6675', 'middle'); text(950, 902, 'MCU + rádio LoRa', 13, 400, '#5b6675', 'middle')
# power + rf + gnd + swd
line([U['VDD'], (U['VDD'][0], 600)], C['pwr'], 2.4); tag(U['VDD'][0], 600, '3V3', C['pwr'], 'r')
rf = U['RF']; line([rf, (rf[0], 590)], C['rf'], 2.6)
add(f'<path d="M{rf[0]} 590 l-16 -26 h32 z" fill="#fff" stroke="{C["rf"]}" stroke-width="2.4"/>'); line([(rf[0], 590), (rf[0], 564)], C['rf'], 2.4)
text(rf[0] + 26, 576, 'ANT1 helicoidal 915 MHz', 13, 700, C['rf'])
line([U['GND'], (U['GND'][0], 1085)], C['gnd']); gnd(U['GND'][0], 1085)
J3 = ic(870, 1130, 250, 90, 'J3', 'Tag-Connect SWD', top=['SWDIO', 'SWCLK', 'NRST'])
for k in ['SWDIO', 'SWCLK', 'NRST']:
    a = U[k]; b = J3[k]; my = 1105
    line([a, (a[0], my), (b[0], my), b], C['gpio'], 1.8)
text(995, 1240, 'gravação / depuração', 12, 400, '#5b6675', 'middle')

# --- left peripherals (clusters with net tags) ---
for k in lp:
    p = U[k]; nm = k.split(' ')[1]; line([p, (765, p[1])], C['gpio']); tag(765, p[1], nm, C['gpio'], 'l')
def ctitle(x, y, t): text(x, y, t, 12.5, 800, '#8995A5')
# SOS
ctitle(60, 590, 'BOTÃO SOS')
ny = 670
line([(300, 600), (300, 610)], C['pwr']); tag(300, 600, '3V3', C['pwr'], 'r')
res(300, 610, 'R1 100 kΩ', True, C['gpio']); line([(300, 644), (300, ny)], C['gpio']); dot(300, ny, C['gpio'])
line([(300, ny), (236, ny)], C['gpio'])
add(f'<circle cx="232" cy="{ny}" r="4" fill="#fff" stroke="#1d2430" stroke-width="2"/><circle cx="182" cy="{ny}" r="4" fill="#fff" stroke="#1d2430" stroke-width="2"/>')
line([(186, ny - 4), (230, ny - 18)], C['ink'], 2.4); line([(208, ny - 11), (208, ny - 26)], C['ink'], 2); line([(196, ny - 26), (220, ny - 26)], C['ink'], 2.4)
text(207, ny - 36, 'SW1', 13, 800, '#B83227', 'middle')
line([(178, ny), (130, ny), (130, ny + 10)], C['gnd']); gnd(130, ny + 10)
dot(370, ny, C['gpio']); line([(370, ny), (370, ny + 16)], C['gpio']); cap(370, ny + 16, 'C1 100 nF'); line([(370, ny + 23), (370, ny + 34)], C['gnd']); gnd(370, ny + 34)
line([(300, ny), (480, ny)], C['gpio']); tag(480, ny, 'SOS', C['gpio'], 'r')
# LEDs
ctitle(60, 780, 'LEDs DE STATUS')
for y, col, ref, rr, nm in [(815, '#C0392B', 'D2', 'R2 1 kΩ', 'LED_R'), (875, '#2EA36B', 'D3', 'R3 1 kΩ', 'LED_G')]:
    line([(130, y), (226, y)], C['gnd'])
    add(f'<path d="M250 {y-11} v22 l-20 -11 z" fill="{col}" stroke="{col}" stroke-width="2"/>'); line([(228, y - 12), (228, y + 12)], col, 2.6)
    add(f'<path d="M238 {y-16} l8 -10 M248 {y-16} l6 -8" stroke="{col}" stroke-width="1.6"/>')
    text(240, y + 30, ref, 12, 700, col, 'middle')
    line([(250, y), (300, y)], C['gpio']); res(300, y, rr, False, C['gpio']); line([(334, y), (480, y)], C['gpio']); tag(480, y, nm, C['gpio'], 'r')
line([(130, 815), (130, 885)], C['gnd']); gnd(130, 885)
# Motor
ctitle(60, 950, 'MOTOR DE VIBRAÇÃO')
line([(300, 965), (300, 975)], C['pwr']); tag(300, 965, '3V3', C['pwr'], 'r')
dot(300, 985, C['pwr']); line([(300, 975), (300, 995)], C['pwr'])
add('<circle cx="300" cy="1015" r="20" fill="#fff" stroke="#1d2430" stroke-width="2.4"/>'); text(300, 1021, 'M', 15, 800, C['ink'], 'middle')
text(330, 1012, 'M1', 12, 700, '#5b6675')
line([(300, 985), (230, 985), (230, 1000)], C['ink'])
add('<path d="M218 1018 h24 l-12 -16 z" fill="#fff" stroke="#1d2430" stroke-width="2"/>'); line([(218, 1001), (242, 1001)], C['ink'], 2.4)
text(210, 1016, 'D4', 12, 700, '#5b6675', 'end')
line([(230, 1018), (230, 1050), (300, 1050)], C['ink']); dot(300, 1050)
line([(300, 1035), (300, 1068), (312, 1068)], C['ink'])
for yy in (1062, 1078, 1094): line([(312, yy), (312, yy + 10)], C['ink'], 2.6)
line([(324, 1062), (324, 1104)], C['ink'], 2.6)
line([(312, 1098), (300, 1098), (300, 1112)], C['gnd']); gnd(300, 1112)
text(290, 1086, 'Q2', 12, 700, '#5b6675', 'end')
line([(324, 1083), (360, 1083)], C['gpio']); res(360, 1083, 'R4 100 Ω', False, C['gpio']); line([(394, 1083), (480, 1083)], C['gpio']); tag(480, 1083, 'MOTOR', C['gpio'], 'r')
# --- right peripherals ---
# DWM3000
D = ic(1360, 600, 250, 300, 'U7', 'DWM3000', left=['SPICLK', 'SPIMISO', 'SPIMOSI', 'SPICSn', 'IRQ', 'RSTn', 'WAKEUP'], top=['VDD'], bottom=['GND'], pitch=34, sub=None)
text(1485, 778, 'UWB · antena integrada', 12.5, 400, '#5b6675', 'middle')
for i, (a, b, col) in enumerate([('PA5 SCK', 'SPICLK', C['spi']), ('PA6 MISO', 'SPIMISO', C['spi']), ('PA7 MOSI', 'SPIMOSI', C['spi']), ('PA4 NSS', 'SPICSn', C['spi']), ('PB8 UWB_IRQ', 'IRQ', C['gpio']), ('PB9 UWB_RST', 'RSTn', C['gpio']), ('PB10 UWB_WAKE', 'WAKEUP', C['gpio'])]):
    pa = U[a]; pb = D[b]; mx = 1200 + i * 18
    line([pa, (mx, pa[1]), (mx, pb[1]), pb], col, 2)
line([D['VDD'], (D['VDD'][0], 575)], C['pwr']); tag(D['VDD'][0], 575, '3V3', C['pwr'], 'r')
line([D['GND'], (D['GND'][0], 918)], C['gnd']); gnd(D['GND'][0], 918)
text(1290, 618, 'SPI', 13, 800, C['spi'], 'middle')
# I2C bus
sda = U['PA11 SDA']; scl = U['PA12 SCL']
busx_end = 1940
line([sda, (busx_end, sda[1])], C['i2c'], 2.4); line([scl, (busx_end, scl[1])], C['i2c'], 2.4)
text(1150, sda[1] - 8, 'I²C', 13, 800, C['i2c'])
# pullups
for x0, yy, nm in [(1180, sda[1], 'R5 4,7 kΩ'), (1250, scl[1], 'R6 4,7 kΩ')]:
    dot(x0, yy, C['i2c'])
for x0, yy, nm in [(1180, sda[1], 'R5'), (1250, scl[1], 'R6')]:
    pass
tag(busx_end, sda[1], 'SDA', C['i2c'], 'r') if False else None
# MAX30102
M = ic(1300, 1000, 230, 170, '', 'MAX30102', top=['SDA', 'SCL', 'INT'], bottom=['VDD', 'VLED+', 'GND'], sub='U8 · BPM + SpO2')
I = ic(1640, 1000, 200, 170, '', 'LIS2DH12', top=['SDA', 'SCL', 'INT1'], bottom=['VDD', 'GND'], sub='U9 · acelerômetro')
for dev in (M, I):
    a = dev['SDA']; b = dev['SCL']
    line([a, (a[0], sda[1])], C['i2c'], 2); dot(a[0], sda[1], C['i2c'])
    line([b, (b[0], scl[1])], C['i2c'], 2); dot(b[0], scl[1], C['i2c'])
pi = U['PB12 PPG_INT']; ii = U['PB13 IMU_INT']
line([pi, (M['INT'][0], pi[1]), M['INT']], C['gpio'], 2)
line([ii, (1240, ii[1]), (1240, 986), (I['INT1'][0], 986), I['INT1']], C['gpio'], 2)
# pullups drawn as resistors up to 3V3 at right end of bus
for xx, yy, lab in [(1880, sda[1], 'R5 4,7 kΩ'), (1925, scl[1], 'R6 4,7 kΩ')]:
    dot(xx, yy, C['i2c']); line([(xx, yy), (xx, yy - 36)], C['i2c']); res(xx, yy - 70, '', True, C['i2c']); line([(xx, yy - 70), (xx, 930 - 0 if False else yy - 84)], C['pwr'])
text(1955, 965, 'R5, R6 4,7 kΩ (pull-up)', 12, 700, '#5b6675', 'end')
line([(1880, sda[1] - 84), (1925, sda[1] - 84)], C['pwr']); line([(1925, scl[1] - 84), (1925, sda[1] - 84)], C['pwr'])
tag(1880, sda[1] - 84, '3V3', C['pwr'], 'l')
text(1960, sda[1] + 5, '', 12)
tag(1940, sda[1], '', C['i2c']) if False else None
text(1945, sda[1] + 22, '', 12)
# bottom power pins of sensors
for dev, pins in [(M, [('VDD', '1V8', C['pwr']), ('VLED+', 'VSYS', C['pwr'])]), (I, [('VDD', '3V3', C['pwr'])])]:
    for p, nm, col in pins:
        x0, y0 = dev[p]; dy = 60 if p == 'VLED+' else 30
        if dev is I:
            line([(x0, y0), (x0, y0 + dy), (x0 - 6, y0 + dy)], col); tag(x0 - 6, y0 + dy, nm, col, 'l')
        else:
            line([(x0, y0), (x0, y0 + dy), (x0 + 6, y0 + dy)], col); tag(x0 + 6, y0 + dy, nm, col, 'r')
for dev in (M, I):
    x0, y0 = dev['GND']; line([(x0, y0), (x0, y0 + 20)], C['gnd']); gnd(x0, y0 + 20)
text(1535, sda[1] + 22, '→ U3 (MAX17048)', 12, 600, C['i2c'])

# legend
lx, ly = 40, 1280
for i, (nm, col) in enumerate([('Alimentação', C['pwr']), ('Terra (GND)', C['gnd']), ('I²C', C['i2c']), ('SPI', C['spi']), ('Sinais digitais / GPIO', C['gpio']), ('RF / antena', C['rf'])]):
    x = lx + i * 230
    line([(x, ly), (x + 36, ly)], col, 4); text(x + 46, ly + 5, nm, 14, 600, C['ink'])

svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Inter">' + ''.join(S) + '</svg>'
open(out, 'w').write('<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#fff}</style></head><body><div id="fig" style="display:inline-block">' + svg + '</div></body></html>')
