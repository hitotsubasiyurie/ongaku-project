class Message:

    FMJEKLYK = "请输入一个存在的目录，用于存放临时文件：\n"
    AW9FDB6V = "请选择动作：\n"
    CLZWFPBZ = "退出"

    ####

    AUP6NZT5 = "硬链接克隆"
    LRH6QG61 = """
1. 原始路径和目标路径必须在同一磁盘
2. 目标路径会自动创建，因此不应该存在

原始路径：
    文件或文件夹，例如 D:\\1.txt ，例如 D:\\download
目标路径：
    对应的路径，例如 D:\\2.txt ，例如 D:\\download_2
"""
    CGXLT9YQ = "请输入原始路径：\n"
    P8C3P4XW = "请输入目标路径：\n"
    O5HIF3EV = "【错误】原始路径不存在或者目标路径已存在。"
    KOQD2Y16 = "硬链接拷贝已完成。{:d} 个文件，{:d} 个文件夹，耗时 {:.2f} 秒。\n"

    ####
    WFSEKVW9 = "删除文件"
    IXLSQ13W = """
将会删除路径。不会挪至回收站，所以速度较快。
"""
    K1ZZWV8C = "请输入路径：\n"
    PK7LLJJU = "【错误】路径不存在。"
    YO8JFLU3 = "是否确认删除（Y/N）（默认N）："

    ####

    GB5JO189 = "重新编码文本文件"
    XQIIHSJN = """
父目录路径：
    将会处理整个目录中特定文件后缀的文件
文件后缀列表：
    用英文逗号隔开，例如 .txt,.cue,.log
保存文件前缀： 
    例如 __recoded_utf_8__
    D:\\download\\1.txt 重编码后会生成 D:\\download\\__recoded_utf_8__1.txt

"""
    D1EG4CA9 = "请输入父目录路径：\n"
    DGO6VHRZ = "请输入文件后缀列表（默认为 .cue ）：\n"
    O166KECP = "请输入保存文件前缀（默认为 __recoded_utf_8__）：\n"
    JABXWHDS = """
a: 上一个编码 d: 下一个编码
w: 上一个文件 s: 下一个文件
p: 资源管理器打开路径
q: 退出
回车保存...
"""

    ####

    GBT3D4H8 = "从 VGMDB 获取专辑元数据"
    K9FYO55X = """
保存路径：
    若是目录路径，将会生成新的元数据文件。
    若是已有的元数据文件路径，将会读取，跳过已包含的专辑元数据，更新追加未包含的专辑元数据

VGMDB url ：
    frachise 页面，例如：https://vgmdb.net/product/3559
    product 页面，例如：https://vgmdb.net/product/7750
    搜索页面，例如：https://vgmdb.net/search?q=Yosuga+no+Sora&type=
"""
    YHEH6TFR = "请输入保存路径：\n"
    UZKMVOC1 = "请输入 VGMDB url ：\n"
    O9W853SZ = "【错误】不支持的 VGMDB url 。"
    W5OJ7854 = "成功获取 {:d} 张专辑元数据。元数据文件：{}\n"

    ####

    VKTS4CY7 = "从本地 MusicBrainz 数据库获取专辑元数据"
    LLZ4XB9J = "请输入待查询的元数据文件：\n"
    M82LXNFV = "请输入筛选掩码列表 [catalognumber, date, date_int, track_count] （默认为 1000, 0101）：\n"
    ZG85TEHZ = "请输入每张专辑查询结果数限制（默认为 10）：\n"
    CCKZUKK1 = "请输入排序掩码 [catalognumber, album, tracks_abstract] （默认为 111）：\n"
    ZX1XSCFX = "成功获取 {:d} 张专辑元数据。元数据文件：{}\n"

    ####

    ZJFV9Z1X = "合并多个元数据文件"
    BGF1DM8D = """
尝试将 来源元数据文件 合并至 目标元数据文件
会对两份专辑列表根据总相似度最大算法，进行一一配对
来源元数据文件将失去合并的专辑，目标元数据文件将更新信息

跳过关键字：
    目标专辑列表中，links 包含该关键字的专辑将不参与合并，例如 musicbrainz
相似度门槛：
    一一配对后，相似度仍然低于门槛的直接忽略掉。
    建议分开重复执行多次合并操作，设置门槛 90->80->75
catalognumber 必须相同：
    建议分开重复执行多次合并操作，设置 Y->N

元数据替换掩码：
    [catalognumber, date, album, tracks]
    例如，掩码 0001 代表只替换目标的 tracks 信息
    例如，掩码 0000 代表不替换任何信息，只是附加至 link
"""
    BB8Z9OR4 = "请输入目标元数据文件（合并至）：\n"
    O7USULLZ = "请输入来源元数据文件（合并从）：\n"

    VOLF5PUD = "生成合并日志"
    Q9YNQ293 = "请输入跳过关键字（例如 musicbrainz）：\n"
    R3VY3KF6 = "请输入相似度门槛（默认 90）："
    BHX8PWTM = "请输入是否 catalognumber 必须相同（Y/N）（默认Y）：\n"
    V7VQSYWB = "正在进行总相似度最大匹配..."
    NEJU5R13 = "已生成合并日志。{}"

    GCXAW6BC = "应用合并日志"
    DERFEKFV = "请输入合并日志路径：\n"
    J1H47YFK = "请输入元数据替换掩码（例如 0001）：\n"
    PLCIYBZW = "请输入是否允许自动替换目标中的空值（Y/N）（默认Y）："
    JNAIXTGI = "已应用合并日志。"

    ####

    B2BHBP2H = "匹配元数据和资源"

    U6RPQN91 = "生成匹配日志"
    QD152EVN = "请输入一个元数据文件：\n"
    I7EC4HDV = "请输入老的资源父目录：\n"
    EPNYJ37J = "请输入新的的资源父目录：\n"
    NMN5NFSN = "请输入是否音轨数目必须相等（Y/N）（默认Y）：\n"

    MJVYZVPO = "应用匹配日志"
    NAWEVS2M = "请输入匹配日志路径：\n"
    HLKQR6TI = "目标已存在。跳过，删除源文件。{}"
    YFH8PA2T = "目标存在 mp3 版本。删除，替换成 flac 版本。{}"
    HSUQBJV2 = "目标存在 flac 版本。跳过，删除源文件。{}"

    U6Q2O6NL = "精简目录，删除没有音频文件的文件夹"
    R2BBVQAA = "请输入资源父目录：\n"


    ####

    ER5LSXY9 = "创建本地 MusicBrainz 数据库"
    RT2DKKG4 = "请输入 MusicBrainz 转储文件目录：\n"
    NLYCQM7M = "请输入 tar 可执行文件路径：\n"

    
    HKGTWA9F = ""
    U5KEANSU = ""
    W1XYRJKP = ""
    VO2WSKBG = ""
    HC8KT771 = ""
    KSFA9P3U = ""
    XVJRY7T6 = ""
    EOIS3C1V = ""
