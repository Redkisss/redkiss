# -*- coding: utf-8 -*-
"""Работа с товары.xlsx: чтение, дописывание новых строк, подсветка ошибок."""
import os
import re
import tempfile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from common import XLSX, norm

SHEET_ITEMS = "Товары"
SHEET_SET = "Настройки"
H_FOLDER, H_TITLE, H_DESC, H_SIZE, H_MAT, H_STATUS, H_PRICE, H_NEW, H_HIDE, H_ORDER = (
    "Папка", "Название", "Описание", "Размер", "Материал", "Статус", "Цена", "Новинка", "Скрыть", "Порядок")
H_CAT = "Категория (не менять)"
HEADERS = [H_FOLDER, H_TITLE, H_DESC, H_SIZE, H_MAT, H_STATUS, H_PRICE, H_NEW, H_HIDE, H_ORDER, H_CAT]
STATUSES = ["В наличии", "Под заказ", "Продано"]

RED_FILL = PatternFill("solid", start_color="FFF8CFCF", end_color="FFF8CFCF")
HEAD_FILL = PatternFill("solid", start_color="FF5C0012", end_color="FF5C0012")
HEAD_FONT = Font(bold=True, color="FFEAE0CF")
GRAY_FONT = Font(italic=True, color="FF888888")

DEFAULT_SETTINGS = [
    ("Написать мне (ссылка)", "https://t.me/antsuanna"),
    ("Описание сайта (для поисковиков и превью)",
     "Авторские фигурки из смолы ручной работы: милые бюсты с огромными чёрными глазами, "
     "кровь, готика и немного любви."),
    ("Адрес сайта (заполнится сам после публикации)", ""),
]
DEFAULT_SOCIALS = [
    ("Pinterest", "https://ru.pinterest.com/redkiss_world/"),
    ("TikTok", "https://www.tiktok.com/@redkiss_world"),
    ("Telegram", "https://t.me/redkisss"),
]

YES = {"да", "yes", "y", "1", "true", "+", "x", "✓", "д"}


def is_yes(v):
    return norm(v) in YES


def cell_str(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def normalize_link(url):
    url = cell_str(url)
    if not url:
        return ""
    if re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I):
        return url
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", url):
        return "mailto:" + url
    return "https://" + url.lstrip("/")


class ExcelRow:
    def __init__(self, num):
        self.num = num
        self.folder = ""
        self.title = ""
        self.desc = ""
        self.size = ""
        self.material = ""
        self.status = ""
        self.price = None
        self.is_new = False
        self.hide = False
        self.order = None


class XlsxBook:
    def __init__(self, path, rep):
        self.path = path
        self.rep = rep
        self.rows = []
        self.settings = {"contact": "", "description": "", "site_url": "", "socials": []}
        self.wb = None
        self.dirty = False
        self.broken = False   # файл не читается — не трогаем его
        self.unreadable_locked = False
        self.cols = {}
        self._load()

    # ---------- чтение ----------
    def _load(self):
        if not self.path.exists():
            self.rep.warn("Файла товары.xlsx не было — создаю новый.")
            self.wb = self._template()
            self.dirty = True
        else:
            try:
                self.wb = load_workbook(self.path)
            except PermissionError:
                self.unreadable_locked = True
                self.broken = True
                return
            except Exception as e:  # битый файл
                self.rep.error(f"Не получилось открыть товары.xlsx ({type(e).__name__}). "
                               "Файл не изменён. Пересохрани его в Excel или удали — тогда создам новый.")
                self.broken = True
                return
        self._ensure_sheets()
        self._read_items()
        self._read_settings()

    def _ensure_sheets(self):
        if SHEET_ITEMS not in self.wb.sheetnames:
            self.rep.warn("В товары.xlsx нет листа «Товары» — создаю.")
            self._make_items_sheet(self.wb.create_sheet(SHEET_ITEMS, 0))
            self.dirty = True
        if SHEET_SET not in self.wb.sheetnames:
            self.rep.warn("В товары.xlsx нет листа «Настройки» — создаю.")
            self._make_settings_sheet(self.wb.create_sheet(SHEET_SET))
            self.dirty = True

    def _map_cols(self, ws):
        cols = {}
        for c in range(1, ws.max_column + 1):
            h = norm(ws.cell(1, c).value)
            for name in HEADERS:
                if h == norm(name) or (name == H_CAT and h.startswith("категория")):
                    cols.setdefault(name, c)
        # недостающие колонки допишем справа
        for name in HEADERS:
            if name not in cols:
                last = max([ws.max_column] + list(cols.values())) + 1
                cell = ws.cell(1, last, name)
                cell.fill, cell.font = HEAD_FILL, HEAD_FONT
                cols[name] = last
                self.dirty = True
        self.cols = cols

    def _read_items(self):
        ws = self.wb[SHEET_ITEMS]
        self._map_cols(ws)
        c = self.cols
        seen = {}
        for r in range(2, ws.max_row + 1):
            g = lambda name: ws.cell(r, c[name]).value
            folder = cell_str(g(H_FOLDER))
            others = [g(n) for n in HEADERS if n not in (H_FOLDER, H_CAT)]
            if not folder:
                if any(cell_str(v) for v in others):
                    self.rep.warn(f"Excel, строка {r}: заполнена, но не указана «Папка» — строка пропущена.")
                continue
            row = ExcelRow(r)
            row.folder = folder
            row.title = cell_str(g(H_TITLE))
            raw_desc = g(H_DESC)
            row.desc = "" if raw_desc is None else str(raw_desc).replace("\r\n", "\n").strip()
            row.size = cell_str(g(H_SIZE))
            row.material = cell_str(g(H_MAT))
            st = cell_str(g(H_STATUS))
            if st:
                match = [s for s in STATUSES if norm(s) == norm(st)]
                if match:
                    row.status = match[0]
                else:
                    self.rep.warn(f"Excel, строка {r}: статус «{st}» не из списка "
                                  f"({', '.join(STATUSES)}) — статус не показан.")
            row.price = g(H_PRICE) if cell_str(g(H_PRICE)) else None
            row.is_new = is_yes(g(H_NEW))
            row.hide = is_yes(g(H_HIDE))
            o = cell_str(g(H_ORDER))
            if o:
                try:
                    row.order = float(o.replace(",", "."))
                except ValueError:
                    self.rep.warn(f"Excel, строка {r}: «Порядок» должен быть числом, а там «{o}» — игнорирую.")
            key = norm(folder)
            if key in seen:
                self.rep.warn(f"Excel: папка «{folder}» указана дважды (строки {seen[key]} и {r}) — "
                              f"использую первую.")
                continue
            seen[key] = r
            self.rows.append(row)

    def _read_settings(self):
        ws = self.wb[SHEET_SET]
        s = self.settings
        for r in range(2, ws.max_row + 1):
            key = norm(ws.cell(r, 1).value)
            val = cell_str(ws.cell(r, 2).value)
            if not key:
                continue
            if key.startswith("написать"):
                s["contact"] = normalize_link(val)
            elif key.startswith("описание"):
                s["description"] = val
            elif key.startswith("адрес"):
                s["site_url"] = val
        for r in range(2, ws.max_row + 1):
            name = cell_str(ws.cell(r, 4).value)
            link = cell_str(ws.cell(r, 5).value)
            if not name and not link:
                continue
            if not link:
                continue  # пустая строка-заготовка
            if not name:
                self.rep.warn(f"Настройки, соцсети, строка {r}: есть ссылка, но нет названия — пропущено.")
                continue
            s["socials"].append({"name": name, "url": normalize_link(link)})

    # ---------- запись ----------
    def _template(self):
        wb = Workbook()
        ws = wb.active
        ws.title = SHEET_ITEMS
        self._make_items_sheet(ws)
        self._make_settings_sheet(wb.create_sheet(SHEET_SET))
        return wb

    def _make_items_sheet(self, ws):
        for i, h in enumerate(HEADERS, 1):
            cell = ws.cell(1, i, h)
            cell.fill, cell.font = HEAD_FILL, HEAD_FONT
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        self._style_items(ws)

    def _make_settings_sheet(self, ws):
        for i, h in enumerate(["Параметр", "Значение"], 1):
            c = ws.cell(1, i, h)
            c.fill, c.font = HEAD_FILL, HEAD_FONT
        for i, h in enumerate(["Соцсеть", "Ссылка"], 4):
            c = ws.cell(1, i, h)
            c.fill, c.font = HEAD_FILL, HEAD_FONT
        for i, (k, v) in enumerate(DEFAULT_SETTINGS, 2):
            ws.cell(i, 1, k)
            ws.cell(i, 2, v).alignment = Alignment(wrap_text=True, vertical="top")
        for i, (k, v) in enumerate(DEFAULT_SOCIALS, 2):
            ws.cell(i, 4, k)
            ws.cell(i, 5, v)
        ws.cell(7, 1, "Подсказка: соцсети слева направо — как строки справа. Иконка подбирается по названию: "
                      "Telegram, VK, Instagram, Pinterest, TikTok, YouTube, WhatsApp, Avito, Ozon, WB. "
                      "Чтобы убрать соцсеть — сотри её ссылку. Чтобы добавить — впиши новую строку под списком.")
        ws.cell(7, 1).font = GRAY_FONT
        ws.cell(7, 1).alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells("A7:B11")
        ws.column_dimensions["A"].width = 42
        ws.column_dimensions["B"].width = 60
        ws.column_dimensions["C"].width = 3
        ws.column_dimensions["D"].width = 18
        ws.column_dimensions["E"].width = 50

    def _style_items(self, ws):
        widths = {H_FOLDER: 28, H_TITLE: 26, H_DESC: 60, H_SIZE: 12, H_MAT: 16, H_STATUS: 13,
                  H_PRICE: 11, H_NEW: 10, H_HIDE: 9, H_ORDER: 10, H_CAT: 20}
        cols = self.cols or {n: i for i, n in enumerate(HEADERS, 1)}
        for name, w in widths.items():
            if name in cols:
                ws.column_dimensions[get_column_letter(cols[name])].width = w
        ws.freeze_panes = "B2"
        ws.row_dimensions[1].height = 30
        # выпадающие списки
        ws.data_validations.dataValidation = []
        for name, formula in [(H_STATUS, '"' + ",".join(STATUSES) + '"'), (H_NEW, '"да"'), (H_HIDE, '"да"')]:
            if name in cols:
                dv = DataValidation(type="list", formula1=formula, allow_blank=True, showErrorMessage=False)
                L = get_column_letter(cols[name])
                dv.add(f"{L}2:{L}1000")
                ws.add_data_validation(dv)

    def last_row(self):
        ws = self.wb[SHEET_ITEMS]
        col = self.cols.get(H_FOLDER, 1)
        last = 1
        for r in range(2, ws.max_row + 1):
            if cell_str(ws.cell(r, col).value):
                last = r
        return last

    def sync(self, folders_info, missing_rows):
        """folders_info: [(папка, категория)] для всех найденных папок;
        новые папки дописываются. missing_rows: ExcelRow, для которых папка не найдена."""
        if self.broken or self.wb is None:
            return
        ws = self.wb[SHEET_ITEMS]
        c = self.cols
        by_key = {norm(r.folder): r for r in self.rows}
        nxt = self.last_row() + 1
        for folder, clean_folder, cat in folders_info:
            row = by_key.get(norm(folder)) or by_key.get(norm(clean_folder))
            if row is None:
                ws.cell(nxt, c[H_FOLDER], folder)
                ws.cell(nxt, c[H_CAT], cat).font = GRAY_FONT
                ws.cell(nxt, c[H_DESC]).alignment = Alignment(wrap_text=True, vertical="top")
                nxt += 1
                self.dirty = True
            else:
                cell = ws.cell(row.num, c[H_CAT])
                if cell_str(cell.value) != cat:
                    cell.value = cat
                    cell.font = GRAY_FONT
                    self.dirty = True
        missing_nums = {r.num for r in missing_rows}
        for r in range(2, ws.max_row + 1):
            if not cell_str(ws.cell(r, c[H_FOLDER]).value):
                continue
            for name in (H_FOLDER,):
                cell = ws.cell(r, c[name])
                is_red = cell.fill is not None and cell.fill.start_color is not None \
                    and cell.fill.start_color.rgb == RED_FILL.start_color.rgb
                if r in missing_nums and not is_red:
                    for col in range(1, len(c) + 1):
                        ws.cell(r, col).fill = RED_FILL
                    self.dirty = True
                elif r not in missing_nums and is_red:
                    for col in range(1, len(c) + 1):
                        ws.cell(r, col).fill = PatternFill(fill_type=None)
                    self.dirty = True
        if self.dirty:
            self._style_items(ws)

    def set_site_url(self, url):
        if self.broken or self.wb is None:
            return
        ws = self.wb[SHEET_SET]
        for r in range(2, ws.max_row + 1):
            if norm(ws.cell(r, 1).value).startswith("адрес"):
                if cell_str(ws.cell(r, 2).value) != url:
                    ws.cell(r, 2).value = url
                    self.dirty = True
                return

    def save(self):
        """Возвращает True, если записано; False — если нечего писать;
        'locked' — файл открыт в Excel."""
        if self.broken or self.wb is None or not self.dirty:
            return False
        if self.path.exists():
            try:
                with open(self.path, "r+b"):
                    pass
            except PermissionError:
                return "locked"
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(suffix=".xlsx", dir=str(self.path.parent), prefix="_tmp_")
            os.close(fd)
            self.wb.save(tmp)
            os.replace(tmp, self.path)
            tmp = None
            self.dirty = False
            return True
        except PermissionError:
            return "locked"
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
