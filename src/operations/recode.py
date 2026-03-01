import msvcrt
import os
from pathlib import Path

from src.core.i18n import g_message
from src.core.console import cinput, cprint, easy_cinput

OPERATION_NAME = g_message.WF_20251204_194720


TEXT_ENCODINGS = ["ascii", "big5", "big5hkscs", "cp037", "cp273", "cp424", "cp437", "cp500", "cp720", "cp737", "cp775", 
                  "cp850", "cp852", "cp855", "cp856", "cp857", "cp858", "cp860", "cp861", "cp862", "cp863", "cp864", 
                  "cp865", "cp866", "cp869", "cp874", "cp875", "cp932", "cp949", "cp950", "cp1006", "cp1026", "cp1125", 
                  "cp1140", "cp1250", "cp1251", "cp1252", "cp1253", "cp1254", "cp1255", "cp1256", "cp1257", "cp1258", 
                  "euc_jp", "euc_jis_2004", "euc_jisx0213", "euc_kr", "gb2312", "gbk", "gb18030", "hz", "iso2022_jp", 
                  "iso2022_jp_1", "iso2022_jp_2", "iso2022_jp_2004", "iso2022_jp_3", "iso2022_jp_ext", "iso2022_kr", 
                  "latin_1", "iso8859_2", "iso8859_3", "iso8859_4", "iso8859_5", "iso8859_6", "iso8859_7", "iso8859_8", 
                  "iso8859_9", "iso8859_10", "iso8859_11", "iso8859_13", "iso8859_14", "iso8859_15", "iso8859_16", 
                  "johab", "koi8_r", "koi8_t", "koi8_u", "kz1048", "mac_cyrillic", "mac_greek", "mac_iceland", 
                  "mac_latin2", "mac_roman", "mac_turkish", "ptcp154", "shift_jis", "shift_jis_2004", "shift_jisx0213", 
                  "utf_32", "utf_32_be", "utf_32_le", "utf_16", "utf_16_be", "utf_16_le", "utf_7", "utf_8", "utf_8_sig"]

PREFERRED_ENCODINGS = ["utf_8_sig", "utf_8", "shift_jis", "shift_jis_2004", "big5hkscs", "cp932", "shift_jisx0213", 
                       "utf_16", "utf_16_le", "gbk", "gb18030"]

ENCODINGS = PREFERRED_ENCODINGS + list(set(TEXT_ENCODINGS) - set(PREFERRED_ENCODINGS))


def recode():
    cprint(g_message.WF_20251204_194721)

    directory = easy_cinput(g_message.WF_20251204_194722, return_type=Path)
    suffixs_str = easy_cinput(g_message.WF_20251204_194723, default=".cue", return_type=str)
    accept_suffixs = set(map(str.lower, map(str.strip, suffixs_str.split(","))))
    result_prefix = easy_cinput(g_message.WF_20251204_194724, default="__recoded_utf_8__", return_type=str)

    # 待处理文件
    files = [f for f in Path(directory).rglob("*") 
             if f.is_file() and 
             f.suffix.lower() in accept_suffixs and 
             not f.name.startswith(result_prefix) and 
             not (f.parent / f"{result_prefix}{f.name}").exists()]

    # 文件索引，编码索引
    i, j = 0, 0
    max_i, max_j = len(files) - 1, len(ENCODINGS) - 1

    # j 的方向，取值为 -1 或 1
    dir_j = 1

    while True:

        try:
            # 文件 i 以编码 j 读取
            text = files[i].read_text(ENCODINGS[j])
            os.system("cls")
            print(text)
            print("-"*64)
            print(f"{j}/{max_j} {ENCODINGS[j]}")
            print(f"{i}/{max_i} {files[i]}")
            print(g_message.WF_20251204_194725)
        except Exception:
            j = max(0, min(j + dir_j, max_j))
            if (dir_j == -1 and j != 0) or (dir_j == 1 and j != max_j):
                continue
        
        inp = msvcrt.getch().decode().lower()
        if inp == "w":
            i, j = max(0, i - 1), 0
            dir_j = 1
        elif inp == "s":
            i, j = min(i + 1, max_i), 0
            dir_j = 1
        elif inp == "a":
            dir_j = -1
            j = max(0, j + dir_j)
        elif inp == "d":
            dir_j = 1
            j = min(j + dir_j, max_j)
        elif inp == "\r":
            newfile = files[i].parent / f"{result_prefix}{files[i].name}"
            newfile.write_text(text, encoding="utf_8")
            i, j = min(i + 1, max_i), 0
            dir_j = 1
        elif inp == "p":
            os.system(f"explorer {files[i].parent}")
        elif inp == "q":
            return
        else:
            return
