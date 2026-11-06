from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H, SCALE = 1536, 1024, 2
OUTPUT = Path("MotorPulse_AI_Ontario.png")

BG = "#F2FAFC"
NAVY = "#062B59"
INK = "#09264B"
BLUE = "#0879E8"
TEAL = "#00A6A6"
CYAN = "#27C9DD"
PURPLE = "#7554C8"
MUTED = "#496580"
WHITE = "#FFFFFF"
RED = "#F04459"
GREEN = "#12A88A"

REGULAR_FONT = r"C:\Windows\Fonts\Inter-Regular.ttf"
MEDIUM_FONT = r"C:\Windows\Fonts\Inter-Medium.ttf"
BOLD_FONT = r"C:\Windows\Fonts\Inter-SemiBold.ttf"


def font(size: int, bold: bool = False, medium: bool = False) -> ImageFont.FreeTypeFont:
    path = BOLD_FONT if bold else MEDIUM_FONT if medium else REGULAR_FONT
    return ImageFont.truetype(path, size * SCALE)


def rounded_box(
    draw: ImageDraw.ImageDraw,
    bounds: tuple[int, int, int, int],
    radius: int,
    fill: str,
    outline: str | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(
        tuple(value * SCALE for value in bounds),
        radius=radius * SCALE,
        fill=fill,
        outline=outline,
        width=width * SCALE,
    )


def draw_line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    fill: str,
    width: int = 2,
) -> None:
    draw.line(
        [(x * SCALE, y * SCALE) for x, y in points],
        fill=fill,
        width=width * SCALE,
        joint="curve",
    )


def draw_text(
    draw: ImageDraw.ImageDraw,
    point: tuple[int, int],
    value: str,
    size: int,
    fill: str = INK,
    bold: bool = False,
    medium: bool = False,
    anchor: str | None = None,
) -> None:
    draw.text(
        (point[0] * SCALE, point[1] * SCALE),
        value,
        font=font(size, bold, medium),
        fill=fill,
        anchor=anchor,
    )


def centered_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    value: str,
    size: int,
    fill: str = INK,
    bold: bool = False,
) -> None:
    draw_text(draw, (x, y), value, size, fill, bold, anchor="mm")


def create_poster() -> None:
    image = Image.new("RGB", (W * SCALE, H * SCALE), BG)
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, W * SCALE, 166 * SCALE), fill=WHITE)
    draw.polygon(
        [(0, 166 * SCALE), (W * SCALE, 166 * SCALE), (W * SCALE, 177 * SCALE), (0, 195 * SCALE)],
        fill="#DDF4FA",
    )
    draw.ellipse((1374 * SCALE, -112 * SCALE, 1607 * SCALE, 121 * SCALE), fill="#EAF8FB")
    draw.ellipse((-87 * SCALE, 68 * SCALE, 96 * SCALE, 251 * SCALE), fill="#EFF9FC")

    portrait = Image.open("profilePic.jpg").convert("RGB").crop((600, 250, 1840, 1490))
    portrait = ImageOps.fit(
        portrait,
        (120 * SCALE, 120 * SCALE),
        method=Image.Resampling.LANCZOS,
        centering=(0.47, 0.43),
    )
    mask = Image.new("L", (120 * SCALE, 120 * SCALE), 0)
    ImageDraw.Draw(mask).ellipse((2 * SCALE, 2 * SCALE, 118 * SCALE, 118 * SCALE), fill=255)
    image.paste(portrait, (26 * SCALE, 23 * SCALE), mask)
    draw = ImageDraw.Draw(image)
    draw.ellipse((25 * SCALE, 22 * SCALE, 147 * SCALE, 144 * SCALE), outline=BLUE, width=3 * SCALE)
    rounded_box(draw, (26, 143, 151, 169), 13, WHITE, outline="#B9DFFF")
    centered_text(draw, 88, 156, "Diptangshu Dolui", 12, NAVY, True)

    rounded_box(draw, (177, 39, 249, 111), 17, NAVY)
    rounded_box(draw, (193, 57, 232, 92), 7, "#103E72", outline=CYAN, width=2)
    draw_line(draw, [(181, 64), (193, 64)], CYAN, 3)
    draw_line(draw, [(181, 84), (193, 84)], CYAN, 3)
    draw_line(draw, [(232, 66), (240, 66)], CYAN, 3)
    draw_line(draw, [(232, 84), (240, 84)], CYAN, 3)
    draw_line(draw, [(195, 76), (202, 76), (207, 67), (213, 85), (218, 73), (229, 73)], "#72F2E3", 3)
    draw_text(draw, (264, 39), "MotorPulse", 40, NAVY, True)
    draw_text(draw, (491, 39), "AI", 40, TEAL, True)
    draw_text(draw, (266, 91), "SENSE  |  DETECT  |  PLAN", 15, MUTED, True)

    rounded_box(draw, (1124, 38, 1497, 91), 26, "#E8F7FA", outline="#B6E9F0")
    draw.ellipse((1142 * SCALE, 55 * SCALE, 1160 * SCALE, 73 * SCALE), fill=GREEN)
    draw_text(draw, (1171, 49), "ONTARIO, CANADA", 17, NAVY, True)
    draw_text(draw, (1171, 72), "INDUSTRIAL EDGE AI", 10, MUTED, True)

    centered_text(draw, 768, 179, "Smarter signals. Fewer emergency motor stops.", 32, NAVY, True)
    centered_text(
        draw,
        768,
        216,
        "A 10-motor Ontario facility scenario: detect abnormal vibration early, then plan a human-reviewed inspection.",
        15,
        MUTED,
    )

    rounded_box(draw, (34, 239, 1502, 295), 16, NAVY)
    rounded_box(draw, (49, 250, 246, 284), 16, "#0C477F")
    centered_text(draw, 147, 267, "ONTARIO CONTEXT", 12, "#8EEBF0", True)
    draw_text(draw, (269, 252), "+1.6%", 25, WHITE, True)
    draw_text(
        draw,
        (366, 256),
        "Ontario real GDP growth in 2023; Ontario contributed almost half of Canada's GDP growth.",
        14,
        WHITE,
        medium=True,
    )
    draw_text(
        draw,
        (366, 276),
        "Statistics Canada, 2023 provincial GDP release (regional context, not a motor-failure loss estimate).",
        10,
        "#B8D7EA",
    )

    card_y, card_h, card_w = 311, 134, 474
    cards = [
        (34, "ANNUAL FAILURE-COST EXPOSURE*", "$37.6K", "Production contribution at risk + urgent-repair premium", BLUE),
        (531, "GROSS SAVINGS OPPORTUNITY*", "$11.3K", "30% base case  |  $7.5K-$15.0K at 20-40%", TEAL),
        (1028, "PLANNED CAPACITY RECOVERED", "5.8 h", "Per year, if the avoided production can be recovered", PURPLE),
    ]
    for x, label, value, caption, accent in cards:
        rounded_box(draw, (x, card_y, x + card_w, card_y + card_h), 18, WHITE, outline="#D6EAF2")
        rounded_box(draw, (x + 18, card_y + 19, x + 25, card_y + card_h - 18), 4, accent)
        draw_text(draw, (x + 42, card_y + 18), label, 13, MUTED, True)
        draw_text(draw, (x + 42, card_y + 38), value, 37, accent, True)
        draw_text(draw, (x + 42, card_y + 92), caption, 12, INK, medium=True)

    rounded_box(draw, (34, 463, 1008, 840), 20, WHITE, outline="#D6EAF2")
    rounded_box(draw, (1027, 463, 1502, 840), 20, WHITE, outline="#D6EAF2")
    draw_text(draw, (59, 482), "MOTORPULSE AI  /  FROM SIGNAL TO SCHEDULED ACTION", 16, NAVY, True)
    draw_text(draw, (59, 508), "Edge-first condition monitoring for motors, pumps and fans", 12, MUTED)

    centers = [(213, 596), (520, 596), (827, 596)]
    for (cx, cy), color in zip(centers, [BLUE, TEAL, PURPLE]):
        draw.ellipse(((cx - 49) * SCALE, (cy - 49) * SCALE, (cx + 49) * SCALE, (cy + 49) * SCALE), fill=color)

    draw_line(draw, [(174, 596), (185, 596), (192, 578), (202, 615), (211, 585), (222, 603), (235, 603), (249, 603)], WHITE, 4)
    draw.ellipse((497 * SCALE, 573 * SCALE, 543 * SCALE, 619 * SCALE), outline=WHITE, width=3 * SCALE)
    draw_line(draw, [(507, 599), (514, 599), (519, 587), (525, 610), (531, 597), (537, 597)], WHITE, 3)
    draw.ellipse((506 * SCALE, 580 * SCALE, 512 * SCALE, 586 * SCALE), fill=WHITE)
    draw.ellipse((531 * SCALE, 610 * SCALE, 537 * SCALE, 616 * SCALE), fill=WHITE)
    draw_line(draw, [(808, 613), (835, 586)], WHITE, 6)
    draw.ellipse((800 * SCALE, 608 * SCALE, 817 * SCALE, 625 * SCALE), outline=WHITE, width=3 * SCALE)
    draw_line(draw, [(831, 583), (840, 574), (847, 578), (841, 586), (850, 594), (844, 600), (836, 592)], WHITE, 3)

    for x in [282, 589]:
        draw_line(draw, [(x, 596), (x + 31, 596)], "#94CBE9", 3)
        draw.polygon([((x + 31) * SCALE, 590 * SCALE), ((x + 42) * SCALE, 596 * SCALE), ((x + 31) * SCALE, 602 * SCALE)], fill="#94CBE9")

    workflow = [
        (213, "SENSE", "Vibration / temperature", "Current / RPM where available", BLUE),
        (520, "DETECT", "Learn a healthy baseline", "Flag drift with an anomaly score", TEAL),
        (827, "PLAN", "Explain the changed signal", "Technician confirms and schedules work", PURPLE),
    ]
    for cx, title, first, second, color in workflow:
        centered_text(draw, cx, 662, title, 17, color, True)
        centered_text(draw, cx, 687, first, 13, INK, True)
        centered_text(draw, cx, 708, second, 11, MUTED)

    rounded_box(draw, (58, 750, 982, 818), 13, "#EFF8FB")
    draw_text(draw, (78, 762), "PROTOTYPE TODAY", 11, TEAL, True)
    draw_text(draw, (78, 781), "Statistical vibration-baseline anomaly detection; no validated fault classifier, remaining-life estimate,", 12, INK, medium=True)
    draw_text(draw, (78, 800), "automatic motor control or safety function. Alerts support, not replace, technician judgment.", 12, INK, medium=True)

    draw_text(draw, (1051, 482), "10-MOTOR ONTARIO FACILITY", 15, NAVY, True)
    draw_text(draw, (1051, 506), "Illustrative base case  /  CAD per year", 11, MUTED)
    draw_line(draw, [(1051, 530), (1478, 530)], "#D8E9EF", 1)

    rows = [
        (543, "EXPECTED UNPLANNED EVENTS", "6 events / 25 motors x 10", "2.4 / yr", True),
        (595, "PRODUCTION CONTRIBUTION AT RISK", "2.4 x 8 h x $1,500 / h", "$28,800", True),
        (647, "URGENT-REPAIR PREMIUM", "2.4 x ($4,500 - $850)", "$8,760", True),
        (699, "MODELLED ANNUAL EXPOSURE", "$28,800 + $8,760", "$37,560", False),
    ]
    for index, (y, label, formula, result, separator) in enumerate(rows):
        draw_text(draw, (1051, y), label, 10, MUTED, True)
        draw_text(draw, (1051, y + 17), formula, 12, INK)
        draw_text(draw, (1467, y + 17), result, 15 if index == 3 else 13, NAVY if index == 3 else BLUE, True, anchor="ra")
        if separator:
            draw_line(draw, [(1051, y + 41), (1478, y + 41)], "#EDF3F6" if index < 2 else "#D8E9EF", 1)

    rounded_box(draw, (1048, 746, 1481, 817), 12, "#E8F8F5")
    draw_text(draw, (1063, 757), "30% EARLY-PLANNING SCENARIO", 10, GREEN, True)
    draw_text(draw, (1063, 777), "$37,560 x 30% = $11,268 gross", 15, NAVY, True)
    draw_text(draw, (1063, 799), "20-40% sensitivity: $7,512-$15,024", 11, MUTED)

    draw_text(draw, (45, 862), "* MODEL, NOT AN OBSERVED ONTARIO TOTAL", 11, RED, True)
    draw_text(draw, (45, 884), "Inputs scaled linearly from the MotorPulse Physical AI Client Projection (25 motors; 6 events/year; 8 h/event; $1,500 lost contribution/hour;", 11, INK)
    draw_text(draw, (45, 904), "$4,500 emergency vs $850 planned repair; 20-40% conversion sensitivity). Gross potential before system cost; no energy or labor savings included.", 11, INK)
    draw_text(draw, (45, 924), "Assumes recovered production is saleable. Validate failure frequency, downtime cost and repair differentials against a real site's CMMS and production records.", 11, INK)
    draw_text(draw, (45, 953), "No defensible public Ontario-wide dollar total for motor-failure losses was identified; this is a transparent 10-motor scenario, not provincial spending.", 11, MUTED, True)
    draw_text(draw, (45, 979), "Regional context: Statistics Canada, Gross domestic product by industry: Provinces and territories, 2023 (May 1, 2024): statcan.gc.ca/n1/daily-quotidien/240501/dq240501a-eng.htm", 9, MUTED)

    draw.rectangle((0, 1000 * SCALE, W * SCALE, H * SCALE), fill=NAVY)
    draw_text(draw, (44, 1008), "MOTORPULSE AI", 13, WHITE, True)
    draw_text(draw, (194, 1008), "Sense early. Plan confidently. Keep people in control.", 12, "#B9D9EA")
    draw_text(draw, (1490, 1008), "ONTARIO  /  CANADA", 10, "#8EEBF0", True, anchor="ra")

    image = image.resize((W, H), Image.Resampling.LANCZOS)
    image.save(OUTPUT, optimize=True)
    print(f"Created {OUTPUT.resolve()} ({OUTPUT.stat().st_size:,} bytes)")
    print("Model check: exposure = 2.4 x (8 x 1500 + 4500 - 850) = 37560; 30% = 11268; recovered hours = 5.76")


if __name__ == "__main__":
    create_poster()
