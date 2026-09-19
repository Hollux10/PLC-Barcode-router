"""Dependency-free PDF report generator producing valid PDF 1.4 output."""

PAGE_W = 612.0
PAGE_H = 792.0
MARGIN = 48.0
CONTENT_W = PAGE_W - 2 * MARGIN


def _esc(s):
    s = str(s)
    s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return s.encode("latin-1", "replace").decode("latin-1")


def _fmt_color(c):
    return f"{c[0]:.3f} {c[1]:.3f} {c[2]:.3f}"


class _Builder:
    def __init__(self):
        self.pages = []
        self.ops = []
        self.pages.append(self.ops)
        self.y = MARGIN
        self.x = MARGIN

    def new_page(self):
        self.ops = []
        self.pages.append(self.ops)
        self.y = MARGIN
        self.x = MARGIN

    def ensure(self, h):
        if self.y + h > PAGE_H - MARGIN:
            self.new_page()

    def text_at(self, text, x, top_y, size=10, bold=False, color=(0.93, 0.95, 0.98)):
        self.ops.append(_fmt_color(color) + " rg")
        font = "F2" if bold else "F1"
        baseline = PAGE_H - (top_y + size * 0.8)
        self.ops.append(
            f"BT /{font} {size} Tf 1 0 0 1 {x:.1f} {baseline:.1f} Tm ({_esc(text)}) Tj ET"
        )

    def text_line(self, text, size=10, bold=False, color=(0.93, 0.95, 0.98), indent=0):
        self.ensure(size * 1.4)
        self.text_at(text, self.x + indent, self.y, size=size, bold=bold, color=color)
        self.y += size * 1.45

    def rect(self, x, y, w, h, color):
        self.ops.append(
            f"{_fmt_color(color)} rg {x:.1f} {PAGE_H - y - h:.1f} {w:.1f} {h:.1f} re f"
        )

    def line(self, x1, y1, x2, y2, color=(0.30, 0.40, 0.55), width=0.6):
        self.ops.append(
            f"{width} w {_fmt_color(color)} RG "
            f"{x1:.1f} {PAGE_H - y1:.1f} m {x2:.1f} {PAGE_H - y2:.1f} l S"
        )

    def spacer(self, h=10):
        self.y += h

    def table(self, headers, rows, widths, font_size=9,
              header_bg=(0.13, 0.20, 0.35), row_h=None, repeat_header=True):
        if row_h is None:
            row_h = font_size * 2.1
        total_w = sum(widths)
        x0 = MARGIN + max(CONTENT_W - total_w, 0) * 0.5

        def draw_header():
            self.rect(x0, self.y, total_w, row_h, header_bg)
            cx = x0
            for i, h in enumerate(headers):
                self.text_at(h, cx + 6, self.y + (row_h - font_size) * 0.5,
                             size=font_size, bold=True, color=(1.0, 1.0, 1.0))
                cx += widths[i]
            self.y += row_h

        draw_header()
        for idx, row in enumerate(rows):
            if self.y + row_h > PAGE_H - MARGIN:
                self.new_page()
                if repeat_header:
                    draw_header()
            bg = (0.09, 0.11, 0.17) if idx % 2 else (0.06, 0.08, 0.13)
            self.rect(x0, self.y, total_w, row_h, bg)
            cx = x0
            for i, cell in enumerate(row):
                self.text_at(cell, cx + 6, self.y + (row_h - font_size) * 0.5,
                             size=font_size)
                cx += widths[i]
            self.y += row_h


def _assemble(streams):
    num_pages = len(streams)
    catalog_num, pages_num, f1, f2 = 1, 2, 3, 4
    res_nums, page_nums, stream_nums = [], [], []
    counter = 5
    for _ in range(num_pages):
        res_nums.append(counter); counter += 1
        page_nums.append(counter); counter += 1
        stream_nums.append(counter); counter += 1

    objs = {}
    objs[catalog_num] = "<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{n} 0 R" for n in page_nums)
    objs[pages_num] = f"<< /Type /Pages /Count {num_pages} /Kids [{kids}] >>"
    objs[f1] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    objs[f2] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"

    for i in range(num_pages):
        body = "\n".join(streams[i])
        objs[res_nums[i]] = f"<< /Font << /F1 {f1} 0 R /F2 {f2} 0 R >> >>"
        objs[stream_nums[i]] = f"<< /Length {len(body.encode('latin-1')) + 1} >>\nstream\n{body}\nendstream"
        objs[page_nums[i]] = (
            f"<< /Type /Page /Parent {pages_num} 0 R "
            f"/MediaBox [0 0 {PAGE_W:.0f} {PAGE_H:.0f}] "
            f"/Resources {res_nums[i]} 0 R /Contents {stream_nums[i]} 0 R >>"
        )

    out = bytearray(b"%PDF-1.4\n")
    xref = {}
    for num in sorted(objs):
        xref[num] = len(out)
        body = objs[num]
        if isinstance(body, str):
            body = body.encode("latin-1")
        out += f"{num} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_pos = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for num in sorted(objs):
        out += f"{xref[num]:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objs) + 1} /Root {catalog_num} 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    return bytes(out)


def build_report_pdf(data):
    """Build a PDF report from a data dict and return the bytes."""
    b = _Builder()

    b.text_at(data["title"], MARGIN, MARGIN, size=18, bold=True, color=(1.0, 1.0, 1.0))
    b.y += 26
    b.text_line("Generated: " + str(data.get("generated", "-")), size=10)
    b.text_line("Session started: " + str(data.get("started", "-")), size=10)
    b.text_line("Session duration: " + str(data.get("duration", "-")), size=10)
    b.line(MARGIN, b.y, PAGE_W - MARGIN, b.y)
    b.spacer(8)

    b.text_line("Summary", size=13, bold=True, color=(0.59, 0.72, 0.96))
    b.spacer(6)
    summary = [
        ("Total offload events", str(data.get("total", 0))),
        ("Attempts (OFL)", str(data.get("attempts", 0))),
        ("Confirmed (SUP)", str(data.get("confirmed", 0))),
        ("Wrong offloads", str(data.get("wrong_offloads", 0))),
        ("Success rate", str(data.get("success_rate", 0)) + "%"),
    ]
    b.table(
        ["Metric", "Value"],
        summary,
        [CONTENT_W * 0.6, CONTENT_W * 0.4],
        font_size=10,
    )
    b.spacer(16)

    counts = data.get("counts", [])
    b.text_line("Event Counts", size=13, bold=True, color=(0.59, 0.72, 0.96))
    b.spacer(6)
    if counts:
        rows = [[c["code"], c["label"], str(c["count"])] for c in counts]
        b.table(["Code", "Reason", "Count"], rows, [72, CONTENT_W - 152, 80], font_size=9)
    else:
        b.text_line("No events recorded.", size=9, color=(0.6, 0.65, 0.75))
    b.spacer(16)

    by_dest = data.get("by_dest", [])
    b.text_line("Offloads by Destination", size=13, bold=True, color=(0.59, 0.72, 0.96))
    b.spacer(6)
    if by_dest:
        rows = [
            [d["destination"], str(d["total"]), str(d["attempts"]),
             str(d["confirmed"]), str(d.get("wrong", 0)), str(d["success_rate"]) + "%"]
            for d in by_dest
        ]
        b.table(
            ["Destination", "Total", "Attempts", "Confirmed", "Wrong", "Success"],
            rows,
            [84, 84, 84, 84, 84, 96],
            font_size=9,
        )
    else:
        b.text_line("No destination data recorded.", size=9, color=(0.6, 0.65, 0.75))
    b.spacer(16)

    events = data.get("events", [])
    b.text_line("Recent Offload Events", size=13, bold=True, color=(0.59, 0.72, 0.96))
    b.spacer(6)
    if events:
        rows = [
            [e["time"], e["location"], e["item"], e.get("sent_destination") or "-",
             e["destination"], e["reason"]]
            for e in events[:100]
        ]
        b.table(
            ["Time", "Location", "Item", "Sent", "Destination", "Reason"],
            rows,
            [70, 80, 80, 80, 90, 116],
            font_size=8,
        )
    else:
        b.text_line("No events recorded.", size=9, color=(0.6, 0.65, 0.75))

    return _assemble(b.pages)