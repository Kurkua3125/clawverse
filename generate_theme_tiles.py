#!/usr/bin/env python3
"""Generate theme tile packs for Clawverse Sprint 22."""
from PIL import Image, ImageDraw
import os, math, random

CATALOG = os.path.dirname(os.path.abspath(__file__)) + '/catalog'
TERRAIN = os.path.join(CATALOG, 'terrain')
OBJECTS = os.path.join(CATALOG, 'objects')
os.makedirs(TERRAIN, exist_ok=True)
os.makedirs(OBJECTS, exist_ok=True)

DIAMOND = [(64,0),(127,32),(64,63),(0,32)]

def iso_diamond(d, fill, outline):
    d.polygon(DIAMOND, fill=fill, outline=outline)

# ═══════════════════════════════════════════════════════
# CASTLE THEME
# ═══════════════════════════════════════════════════════

def gen_castle_floor():
    img = Image.new('RGBA', (128, 64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    iso_diamond(d, (120,120,130,255), (95,95,105,255))
    # Cobblestone pattern
    for i in range(4):
        y = 14 + i * 12
        d.line([(28+i*3, y), (100-i*3, y)], fill=(100,100,110,255), width=1)
    for i in range(3):
        x = 40 + i * 18
        d.line([(x, 10), (x+10, 55)], fill=(105,105,115,255), width=1)
    img.save(os.path.join(TERRAIN, 'castle_floor.png'))

def gen_castle_wall():
    """128x96 block tile — dark stone wall."""
    img = Image.new('RGBA', (128, 96), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Top face
    top = [(64,0),(127,32),(64,64),(0,32)]
    d.polygon(top, fill=(85,85,95,255), outline=(65,65,75,255))
    # Front-left face
    fl = [(0,32),(64,64),(64,96),(0,64)]
    d.polygon(fl, fill=(70,70,80,255), outline=(55,55,65,255))
    # Front-right face
    fr = [(64,64),(127,32),(127,64),(64,96)]
    d.polygon(fr, fill=(60,60,70,255), outline=(50,50,60,255))
    # Brick lines on front faces
    for i in range(3):
        y = 70 + i * 10
        d.line([(4, y-20), (62, y+10)], fill=(55,55,65,255), width=1)
        d.line([(66, y+10), (125, y-20)], fill=(45,45,55,255), width=1)
    img.save(os.path.join(TERRAIN, 'castle_wall.png'))

def gen_castle_carpet():
    img = Image.new('RGBA', (128, 64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    iso_diamond(d, (140,30,30,255), (180,140,50,255))
    # Gold trim lines inside
    inner = [(64,6),(121,32),(64,57),(7,32)]
    d.polygon(inner, fill=None, outline=(200,160,60,255))
    inner2 = [(64,10),(117,32),(64,53),(11,32)]
    d.polygon(inner2, fill=None, outline=(180,140,40,200))
    img.save(os.path.join(TERRAIN, 'castle_carpet.png'))

def gen_throne():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Seat
    d.rectangle([40,75,88,100], fill=(180,140,40,255), outline=(140,100,20,255))
    # Back rest
    d.rectangle([44,30,84,78], fill=(200,160,50,255), outline=(160,120,30,255))
    # Crown decoration on top
    d.polygon([(54,30),(64,15),(74,30)], fill=(220,180,60,255), outline=(180,140,30,255))
    d.polygon([(48,30),(54,20),(60,30)], fill=(210,170,50,255))
    d.polygon([(68,30),(74,20),(80,30)], fill=(210,170,50,255))
    # Armrests
    d.rectangle([32,65,42,90], fill=(170,130,35,255), outline=(130,90,20,255))
    d.rectangle([86,65,96,90], fill=(170,130,35,255), outline=(130,90,20,255))
    # Jewels
    d.ellipse([60,40,68,48], fill=(200,30,30,255))
    d.ellipse([56,52,64,60], fill=(30,80,200,255))
    d.ellipse([68,52,76,60], fill=(30,180,80,255))
    # Legs
    d.rectangle([42,98,50,112], fill=(140,100,20,255))
    d.rectangle([78,98,86,112], fill=(140,100,20,255))
    img.save(os.path.join(OBJECTS, 'throne.png'))

def gen_torch_wall():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Wall bracket
    d.rectangle([58,50,70,90], fill=(80,70,60,255), outline=(60,50,40,255))
    # Torch handle
    d.rectangle([60,30,68,55], fill=(120,80,30,255), outline=(90,60,20,255))
    # Flame
    d.polygon([(64,10),(54,35),(64,28),(74,35)], fill=(255,180,30,255))
    d.polygon([(64,15),(58,32),(64,26),(70,32)], fill=(255,220,60,255))
    d.polygon([(64,18),(60,28),(64,24),(68,28)], fill=(255,255,150,255))
    # Glow
    for r in range(15, 0, -3):
        alpha = int(30 * (r / 15))
        d.ellipse([64-r, 20-r, 64+r, 20+r], fill=(255,200,80,alpha))
    img.save(os.path.join(OBJECTS, 'torch_wall.png'))

def gen_armor_stand():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Stand base
    d.rectangle([50,105,78,115], fill=(80,70,60,255), outline=(60,50,40,255))
    d.rectangle([60,85,68,108], fill=(70,60,50,255))
    # Body armor
    d.polygon([(44,45),(84,45),(88,85),(40,85)], fill=(160,160,170,255), outline=(120,120,130,255))
    # Helmet
    d.ellipse([48,18,80,50], fill=(150,150,160,255), outline=(110,110,120,255))
    d.rectangle([56,36,72,48], fill=(100,100,110,200))  # visor
    # Shoulders
    d.ellipse([30,42,52,58], fill=(155,155,165,255), outline=(115,115,125,255))
    d.ellipse([76,42,98,58], fill=(155,155,165,255), outline=(115,115,125,255))
    # Arms
    d.rectangle([34,56,46,80], fill=(145,145,155,255))
    d.rectangle([82,56,94,80], fill=(145,145,155,255))
    # Highlight
    d.line([(56,50),(56,80)], fill=(200,200,210,255), width=1)
    img.save(os.path.join(OBJECTS, 'armor_stand.png'))

def gen_banner_red():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Pole
    d.rectangle([62,10,66,110], fill=(140,100,30,255), outline=(100,70,20,255))
    # Banner fabric
    d.polygon([(66,20),(110,25),(108,80),(66,75)], fill=(170,25,25,255), outline=(130,15,15,255))
    # Banner detail (lion/crest shape)
    d.ellipse([78,38,96,58], fill=(200,160,40,255))
    # Bottom taper
    d.polygon([(66,75),(108,80),(108,90),(87,85),(66,90)], fill=(170,25,25,255))
    # Pole cap
    d.ellipse([58,6,70,18], fill=(200,160,50,255), outline=(160,120,30,255))
    img.save(os.path.join(OBJECTS, 'banner_red.png'))

def gen_castle_gate():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Left tower
    d.rectangle([15,20,40,110], fill=(100,100,110,255), outline=(75,75,85,255))
    # Right tower
    d.rectangle([88,20,113,110], fill=(100,100,110,255), outline=(75,75,85,255))
    # Arch top
    d.pieslice([38,30,90,80], 180, 0, fill=(80,80,90,255), outline=(60,60,70,255))
    # Gate opening
    d.rectangle([40,55,88,110], fill=(40,30,25,255))
    # Arch outline
    d.arc([38,30,90,80], 180, 0, fill=(60,60,70,255), width=2)
    # Gate bars
    for x in range(46, 86, 8):
        d.line([(x,45),(x,110)], fill=(90,80,70,255), width=2)
    for y in range(60, 110, 12):
        d.line([(42,y),(86,y)], fill=(90,80,70,255), width=1)
    # Tower tops (battlements)
    for x in [15,25,30,88,98,103]:
        d.rectangle([x,14,x+8,24], fill=(110,110,120,255), outline=(80,80,90,255))
    img.save(os.path.join(OBJECTS, 'castle_gate.png'))

# ═══════════════════════════════════════════════════════
# INDOOR/ROOM THEME
# ═══════════════════════════════════════════════════════

def gen_wood_floor():
    img = Image.new('RGBA', (128, 64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    iso_diamond(d, (160,120,70,255), (130,95,50,255))
    # Plank lines
    for i in range(5):
        y = 10 + i * 10
        d.line([(20+i*4, y), (108-i*4, y)], fill=(140,100,55,255), width=1)
    # Grain detail
    for i in range(3):
        x = 45 + i * 15
        d.line([(x,15),(x+5,50)], fill=(150,110,65,200), width=1)
    img.save(os.path.join(TERRAIN, 'wood_floor.png'))

def gen_tile_floor():
    img = Image.new('RGBA', (128, 64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    iso_diamond(d, (220,220,225,255), (190,190,195,255))
    # Grid lines for tiles
    for i in range(1, 4):
        y = i * 16
        d.line([(16+i*8, y-5), (112-i*8, y+5)], fill=(200,200,205,255), width=1)
    for i in range(1, 4):
        x = 32 + i * 16
        d.line([(x, 8+i*2), (x+8, 56-i*2)], fill=(200,200,205,255), width=1)
    img.save(os.path.join(TERRAIN, 'tile_floor.png'))

def gen_carpet_blue():
    img = Image.new('RGBA', (128, 64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    iso_diamond(d, (50,80,150,255), (35,60,120,255))
    # Pattern
    inner = [(64,8),(119,32),(64,55),(9,32)]
    d.polygon(inner, fill=None, outline=(70,100,170,255))
    img.save(os.path.join(TERRAIN, 'carpet_blue.png'))

def gen_sofa():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Base
    d.rounded_rectangle([20,65,108,100], radius=6, fill=(80,60,140,255), outline=(60,40,110,255))
    # Back
    d.rounded_rectangle([20,40,108,70], radius=8, fill=(90,70,150,255), outline=(70,50,120,255))
    # Cushions
    d.rounded_rectangle([24,68,62,95], radius=4, fill=(100,80,160,255))
    d.rounded_rectangle([66,68,104,95], radius=4, fill=(100,80,160,255))
    # Armrests
    d.rounded_rectangle([14,55,26,95], radius=4, fill=(75,55,130,255))
    d.rounded_rectangle([102,55,114,95], radius=4, fill=(75,55,130,255))
    # Legs
    d.rectangle([24,98,30,108], fill=(120,90,40,255))
    d.rectangle([98,98,104,108], fill=(120,90,40,255))
    img.save(os.path.join(OBJECTS, 'sofa.png'))

def gen_tv():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Screen frame
    d.rectangle([20,30,108,85], fill=(30,30,35,255), outline=(20,20,25,255))
    # Screen
    d.rectangle([24,34,104,81], fill=(40,60,100,255))
    # Screen reflection
    d.polygon([(24,34),(60,34),(24,60)], fill=(60,80,120,80))
    # Stand
    d.rectangle([56,85,72,95], fill=(40,40,45,255))
    d.rectangle([44,93,84,100], fill=(35,35,40,255))
    # Power light
    d.ellipse([60,86,64,90], fill=(0,200,0,255))
    img.save(os.path.join(OBJECTS, 'tv.png'))

def gen_bookcase():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Frame
    d.rectangle([28,15,100,110], fill=(130,85,40,255), outline=(100,65,25,255))
    # Shelves
    for y in [38, 60, 82]:
        d.rectangle([30,y,98,y+3], fill=(110,70,30,255))
    # Books on shelves
    colors = [(180,40,40),(40,80,160),(40,140,60),(180,140,40),(140,40,140),(40,140,140)]
    for shelf_y in [18, 41, 63]:
        x = 33
        for i in range(8):
            c = colors[i % len(colors)]
            w = random.randint(6, 10)
            h = random.randint(14, 18)
            d.rectangle([x, shelf_y+20-h, x+w, shelf_y+20], fill=c, outline=(c[0]-20,c[1]-20,c[2]-20))
            x += w + 1
            if x > 92: break
    img.save(os.path.join(OBJECTS, 'bookcase.png'))

def gen_dining_table():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Table top (isometric-ish)
    d.polygon([(64,40),(110,55),(64,70),(18,55)], fill=(160,110,50,255), outline=(130,85,35,255))
    # Legs
    d.line([(25,55),(25,90)], fill=(120,80,30,255), width=3)
    d.line([(103,55),(103,90)], fill=(120,80,30,255), width=3)
    d.line([(64,70),(64,95)], fill=(120,80,30,255), width=3)
    # Plate
    d.ellipse([50,45,78,58], fill=(230,230,235,255), outline=(200,200,205,255))
    img.save(os.path.join(OBJECTS, 'dining_table.png'))

def gen_lamp_floor():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Base
    d.ellipse([48,100,80,112], fill=(60,60,65,255), outline=(45,45,50,255))
    # Pole
    d.rectangle([62,35,66,102], fill=(70,70,75,255))
    # Shade
    d.polygon([(44,20),(84,20),(90,45),(38,45)], fill=(240,220,180,255), outline=(200,180,140,255))
    # Glow
    for r in range(20, 0, -4):
        alpha = int(25 * (r / 20))
        d.ellipse([64-r, 30-r, 64+r, 30+r], fill=(255,240,200,alpha))
    img.save(os.path.join(OBJECTS, 'lamp_floor.png'))

def gen_window():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Frame
    d.rectangle([25,20,103,95], fill=(180,150,100,255), outline=(140,110,70,255))
    # Glass panes
    d.rectangle([30,25,62,55], fill=(150,200,230,255))
    d.rectangle([66,25,98,55], fill=(140,190,220,255))
    d.rectangle([30,59,62,90], fill=(140,190,220,255))
    d.rectangle([66,59,98,90], fill=(150,200,230,255))
    # Curtains
    d.polygon([(20,18),(32,18),(28,95),(16,95)], fill=(180,60,60,255))
    d.polygon([(96,18),(108,18),(112,95),(100,95)], fill=(180,60,60,255))
    # Curtain rod
    d.rectangle([16,15,112,20], fill=(140,110,70,255))
    img.save(os.path.join(OBJECTS, 'window_curtains.png'))

def gen_door_interior():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Door frame
    d.rectangle([35,10,93,110], fill=(150,110,60,255), outline=(120,85,40,255))
    # Door panel
    d.rectangle([39,14,89,106], fill=(170,125,65,255), outline=(140,100,45,255))
    # Panel details
    d.rectangle([44,20,84,50], fill=None, outline=(150,110,55,255))
    d.rectangle([44,58,84,98], fill=None, outline=(150,110,55,255))
    # Handle
    d.ellipse([78,58,86,66], fill=(200,180,100,255), outline=(170,150,70,255))
    img.save(os.path.join(OBJECTS, 'door_interior.png'))

# ═══════════════════════════════════════════════════════
# JAPANESE GARDEN THEME
# ═══════════════════════════════════════════════════════

def gen_zen_sand():
    img = Image.new('RGBA', (128, 64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    iso_diamond(d, (210,200,175,255), (190,180,155,255))
    # Raked lines (curved)
    for i in range(6):
        y = 12 + i * 8
        pts = [(30+i*3, y), (50, y-2+i), (78, y+2-i), (98-i*3, y)]
        d.line(pts, fill=(195,185,160,255), width=1)
    img.save(os.path.join(TERRAIN, 'zen_sand.png'))

def gen_moss_stone():
    img = Image.new('RGBA', (128, 64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    iso_diamond(d, (100,110,90,255), (80,90,70,255))
    # Stone pattern with moss
    d.ellipse([40,20,55,30], fill=(90,100,80,255))
    d.ellipse([65,25,80,35], fill=(85,95,75,255))
    d.ellipse([50,35,70,45], fill=(95,105,85,255))
    # Moss patches
    d.ellipse([35,22,42,28], fill=(60,130,50,180))
    d.ellipse([72,30,78,36], fill=(55,120,45,180))
    d.ellipse([55,40,62,46], fill=(65,135,55,180))
    img.save(os.path.join(TERRAIN, 'moss_stone.png'))

def gen_bamboo_floor():
    img = Image.new('RGBA', (128, 64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    iso_diamond(d, (190,175,120,255), (170,155,100,255))
    # Bamboo mat slats
    for i in range(8):
        y = 8 + i * 7
        d.line([(22+i*3, y), (106-i*3, y)], fill=(175,160,105,255), width=1)
    # Cross weave
    for i in range(4):
        x = 40 + i * 14
        d.line([(x, 10+i), (x+6, 54-i)], fill=(180,165,110,200), width=1)
    img.save(os.path.join(TERRAIN, 'bamboo_floor.png'))

def gen_torii_gate():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Pillars
    d.rectangle([28,35,38,115], fill=(180,30,30,255), outline=(140,20,20,255))
    d.rectangle([90,35,100,115], fill=(180,30,30,255), outline=(140,20,20,255))
    # Top beam (kasagi) — curved
    d.rectangle([18,18,110,28], fill=(190,35,35,255), outline=(150,25,25,255))
    # Extends
    d.polygon([(14,18),(22,12),(22,28),(14,28)], fill=(190,35,35,255))
    d.polygon([(114,18),(106,12),(106,28),(114,28)], fill=(190,35,35,255))
    # Lower beam (nuki)
    d.rectangle([25,38,103,44], fill=(170,28,28,255), outline=(135,20,20,255))
    # Center tablet
    d.rectangle([52,26,76,40], fill=(200,180,100,255), outline=(170,150,70,255))
    img.save(os.path.join(OBJECTS, 'torii_gate.png'))

def gen_stone_lantern():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Base
    d.polygon([(48,105),(80,105),(84,112),(44,112)], fill=(140,140,135,255), outline=(110,110,105,255))
    # Pillar
    d.rectangle([56,60,72,107], fill=(150,150,145,255), outline=(120,120,115,255))
    # Light chamber
    d.rectangle([44,40,84,64], fill=(160,160,155,255), outline=(125,125,120,255))
    # Light window
    d.rectangle([50,44,78,58], fill=(255,230,150,200))
    # Roof
    d.polygon([(38,40),(90,40),(96,30),(32,30)], fill=(145,145,140,255), outline=(115,115,110,255))
    d.polygon([(52,30),(76,30),(64,18)], fill=(140,140,135,255), outline=(110,110,105,255))
    # Glow
    for r in range(12, 0, -3):
        alpha = int(20 * (r / 12))
        d.ellipse([64-r, 50-r, 64+r, 50+r], fill=(255,220,130,alpha))
    img.save(os.path.join(OBJECTS, 'stone_lantern.png'))

def gen_bonsai():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Pot
    d.polygon([(42,90),(86,90),(82,110),(46,110)], fill=(160,80,40,255), outline=(130,60,25,255))
    d.rectangle([40,86,88,92], fill=(170,85,42,255), outline=(135,65,28,255))
    # Trunk
    d.line([(64,88),(64,60)], fill=(100,70,30,255), width=4)
    d.line([(64,70),(48,50)], fill=(90,65,28,255), width=3)
    d.line([(64,65),(82,48)], fill=(90,65,28,255), width=3)
    # Foliage clouds
    d.ellipse([34,30,70,58], fill=(40,120,40,255))
    d.ellipse([55,25,95,55], fill=(45,130,45,255))
    d.ellipse([44,20,80,48], fill=(50,140,50,255))
    d.ellipse([30,38,58,54], fill=(38,115,38,255))
    d.ellipse([65,35,90,52], fill=(42,125,42,255))
    img.save(os.path.join(OBJECTS, 'bonsai.png'))

def gen_koi_pond():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Pond shape (elliptical)
    d.ellipse([15,40,113,100], fill=(40,80,140,255), outline=(80,100,100,255))
    # Inner water
    d.ellipse([22,46,106,94], fill=(50,100,160,255))
    # Lily pads
    d.ellipse([35,55,50,65], fill=(40,130,50,255))
    d.ellipse([75,60,90,70], fill=(45,135,55,255))
    # Koi fish (simple)
    d.ellipse([50,68,65,76], fill=(220,120,30,255))
    d.polygon([(50,72),(44,68),(44,76)], fill=(220,120,30,255))
    d.ellipse([80,55,92,62], fill=(230,230,230,255))
    d.polygon([(80,58),(74,55),(74,62)], fill=(230,230,230,255))
    # Ripples
    d.arc([40,50,88,80], 200, 340, fill=(100,160,210,150), width=1)
    img.save(os.path.join(OBJECTS, 'koi_pond.png'))

def gen_bamboo_cluster():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Stalks
    for x_off, h in [(50, 20), (58, 15), (66, 25), (74, 18), (62, 10)]:
        d.rectangle([x_off, h, x_off+5, 105], fill=(80,160,60,255), outline=(60,130,40,255))
        # Nodes
        for y in range(h+15, 100, 18):
            d.rectangle([x_off-1, y, x_off+6, y+2], fill=(70,140,50,255))
    # Leaves
    for (lx, ly) in [(42,20),(55,10),(70,18),(80,14),(48,30),(75,25)]:
        d.polygon([(lx,ly),(lx+15,ly-3),(lx+18,ly+2)], fill=(60,150,50,255))
        d.polygon([(lx+2,ly+2),(lx+16,ly+5),(lx+12,ly-2)], fill=(70,160,55,255))
    img.save(os.path.join(OBJECTS, 'bamboo_cluster.png'))

# ═══════════════════════════════════════════════════════
# SPACE THEME
# ═══════════════════════════════════════════════════════

def gen_metal_floor():
    img = Image.new('RGBA', (128, 64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    iso_diamond(d, (140,145,155,255), (110,115,125,255))
    # Grid lines
    for i in range(5):
        y = 10 + i * 10
        d.line([(25+i*4, y), (103-i*4, y)], fill=(125,130,140,255), width=1)
    for i in range(4):
        x = 38 + i * 14
        d.line([(x, 12+i), (x+7, 52-i)], fill=(125,130,140,255), width=1)
    # Rivets
    for i in range(3):
        for j in range(3):
            rx = 40 + j * 18
            ry = 18 + i * 14
            d.ellipse([rx, ry, rx+3, ry+3], fill=(160,165,175,255))
    img.save(os.path.join(TERRAIN, 'metal_floor.png'))

def gen_space_glass():
    img = Image.new('RGBA', (128, 64), (0,0,0,0))
    d = ImageDraw.Draw(img)
    iso_diamond(d, (20,25,60,200), (40,50,90,255))
    # Stars
    random.seed(42)
    for _ in range(12):
        sx = random.randint(20, 108)
        sy = random.randint(10, 54)
        # Check if point is roughly within diamond
        if abs(sx - 64) * 32 + abs(sy - 32) * 64 < 64 * 32:
            d.point((sx, sy), fill=(255,255,255,200))
            if random.random() > 0.6:
                d.point((sx+1, sy), fill=(200,200,255,150))
    # Glass edge highlight
    d.line([(64,2),(125,32)], fill=(80,100,150,100), width=1)
    img.save(os.path.join(TERRAIN, 'space_glass.png'))

def gen_control_panel():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Console body
    d.rounded_rectangle([20,40,108,100], radius=4, fill=(70,75,85,255), outline=(50,55,65,255))
    # Screen
    d.rectangle([28,45,80,72], fill=(20,50,30,255))
    # Screen content (data lines)
    for y in range(48, 70, 4):
        w = random.randint(20, 48)
        d.line([(30,y),(30+w,y)], fill=(0,200,80,200), width=1)
    # Buttons
    colors = [(200,40,40),(40,200,40),(40,100,200),(200,200,40)]
    for i, c in enumerate(colors):
        bx = 86 + (i % 2) * 10
        by = 48 + (i // 2) * 12
        d.ellipse([bx, by, bx+7, by+7], fill=c)
    # Slider
    d.rectangle([28,78,100,82], fill=(50,55,65,255))
    d.rectangle([55,76,65,84], fill=(180,180,190,255))
    # Top display
    d.rectangle([35,30,93,42], fill=(80,85,95,255), outline=(60,65,75,255))
    d.text((40,32), "SYS OK", fill=(0,255,100,255))
    img.save(os.path.join(OBJECTS, 'control_panel.png'))

def gen_antenna():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Base
    d.rectangle([52,95,76,112], fill=(120,125,135,255), outline=(90,95,105,255))
    # Pole
    d.rectangle([62,30,66,97], fill=(150,155,165,255), outline=(120,125,135,255))
    # Dish
    d.pieslice([25,15,103,70], 200, 340, fill=(160,165,175,255), outline=(130,135,145,255))
    d.ellipse([55,32,73,50], fill=(180,185,195,255))
    # Signal waves
    for r in [8, 14, 20]:
        d.arc([64-r, 25-r, 64+r, 25+r], 220, 320, fill=(100,200,255,150), width=1)
    img.save(os.path.join(OBJECTS, 'antenna.png'))

def gen_space_plant():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Glass dome
    d.pieslice([25,20,103,90], 180, 0, fill=(180,220,240,60), outline=(140,180,200,120))
    d.rectangle([25,55,103,90], fill=(0,0,0,0))
    d.arc([25,20,103,90], 180, 0, fill=(140,180,200,120), width=2)
    # Base
    d.rectangle([30,80,98,95], fill=(120,125,135,255), outline=(90,95,105,255))
    # Plant inside
    d.rectangle([60,55,68,82], fill=(60,120,40,255))
    d.ellipse([40,30,75,60], fill=(50,150,50,200))
    d.ellipse([55,25,90,55], fill=(60,160,60,200))
    d.ellipse([45,35,80,58], fill=(55,155,55,200))
    # Soil
    d.ellipse([44,72,84,86], fill=(100,70,40,255))
    img.save(os.path.join(OBJECTS, 'space_plant.png'))

def gen_robot():
    img = Image.new('RGBA', (128, 128), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Body
    d.rounded_rectangle([40,45,88,90], radius=6, fill=(180,185,195,255), outline=(140,145,155,255))
    # Head
    d.rounded_rectangle([45,20,83,50], radius=8, fill=(190,195,205,255), outline=(150,155,165,255))
    # Eyes
    d.ellipse([52,28,62,38], fill=(0,200,255,255))
    d.ellipse([66,28,76,38], fill=(0,200,255,255))
    d.ellipse([55,31,59,35], fill=(255,255,255,255))
    d.ellipse([69,31,73,35], fill=(255,255,255,255))
    # Antenna
    d.rectangle([62,12,66,22], fill=(200,50,50,255))
    d.ellipse([60,8,68,16], fill=(255,80,80,255))
    # Arms
    d.rectangle([30,50,42,75], fill=(170,175,185,255), outline=(135,140,150,255))
    d.rectangle([86,50,98,75], fill=(170,175,185,255), outline=(135,140,150,255))
    # Legs
    d.rectangle([46,88,58,108], fill=(160,165,175,255), outline=(130,135,145,255))
    d.rectangle([70,88,82,108], fill=(160,165,175,255), outline=(130,135,145,255))
    # Chest panel
    d.rectangle([52,55,76,78], fill=(60,65,75,255))
    d.ellipse([58,60,70,72], fill=(0,255,100,200))
    img.save(os.path.join(OBJECTS, 'robot.png'))


# ═══════════════════════════════════════════════════════
# GENERATE ALL
# ═══════════════════════════════════════════════════════
if __name__ == '__main__':
    random.seed(42)
    
    print("Generating Castle theme tiles...")
    gen_castle_floor()
    gen_castle_wall()
    gen_castle_carpet()
    gen_throne()
    gen_torch_wall()
    gen_armor_stand()
    gen_banner_red()
    gen_castle_gate()
    
    print("Generating Indoor/Room theme tiles...")
    gen_wood_floor()
    gen_tile_floor()
    gen_carpet_blue()
    gen_sofa()
    gen_tv()
    gen_bookcase()
    gen_dining_table()
    gen_lamp_floor()
    gen_window()
    gen_door_interior()
    
    print("Generating Japanese Garden theme tiles...")
    gen_zen_sand()
    gen_moss_stone()
    gen_bamboo_floor()
    gen_torii_gate()
    gen_stone_lantern()
    gen_bonsai()
    gen_koi_pond()
    gen_bamboo_cluster()
    
    print("Generating Space theme tiles...")
    gen_metal_floor()
    gen_space_glass()
    gen_control_panel()
    gen_antenna()
    gen_space_plant()
    gen_robot()
    
    print("✅ All theme tiles generated!")
