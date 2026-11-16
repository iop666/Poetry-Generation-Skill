#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2-08 WP-D3：30 首經典作品精讀卡（原文取自 works，可追溯；分析為本輪判斷）。

原文一律由作品庫按「作者＋首句」檢索取得，不手打，避免转录错误；
音韻與格律欄由程序計算（平水韻字表＋句讀），分析欄為人工判斷。
"""
import json, os, re, sqlite3, collections
from opencc import OpenCC

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "poetry.db")
OUT = os.path.join(ROOT, "raw", "r2_08", "works_study.json")
TODAY = "2026-11-14"
cc = OpenCC("s2t")
CJK = re.compile(r"[^\u4e00-\u9fff]")

# (序号, 体裁标签, 作者, 首句, 句法, 意象, 情感, 炼字, 技法)
CARDS = [
 (1, "五言绝句", "李白", "床前明月光",
  "以「疑」字作转，由物及人，四句一气；前两句写境，后两句写心。",
  "月光、霜、故乡；月为唯一意象，贯穿全篇。",
  "由疑霜到举头低头，乡愁在动作中完成，不着一「愁」字。",
  "「疑」字最见分寸：似霜而非霜，写月色之白、之冷、之迷离。",
  "口语入诗而合律；以动作代抒情，留白在「思」字不点破。"),
 (2, "五言绝句", "王之涣", "白日依山尽",
  "前两句写景，后两句说理，景理相生；两联皆对。",
  "白日、黄河、山、海；空间由近及远、由下而上。",
  "由登临之景生进取之志，气象阔大而不作豪语。",
  "「依」「入」二字使静景有动态，「穷」「更」二字递进。",
  "以对仗起，以议论收；二十字含四层空间，是绝句压缩的典型。"),
 (3, "五言绝句", "王维", "空山不见人",
  "以「但闻」转折，由视觉转听觉；三、四句以光反写幽暗。",
  "空山、人语、返景、青苔；声与光皆是虚写。",
  "静而不寂，幽而不冷，见禅悦之趣。",
  "「返景」二字写夕照入林，「复」字写光在苔上停留。",
  "以有声衬无声，以有光衬幽暗，是「以动写静」的范式。"),
 (4, "五言绝句", "柳宗元", "千山鸟飞绝",
  "四句皆景，前两句以「绝」「灭」写空，后两句以孤舟独钓破空。",
  "千山、万径、孤舟、蓑笠、寒江雪。",
  "贬谪后的孤峭与自持，冷到极处而不失骨力。",
  "「绝」「灭」「孤」「独」四字层层收紧，末字「雪」收束全篇。",
  "以极静写极孤；藏头「千万孤独」属后人读法，非作者自道，须分辨。"),
 (5, "七言绝句", "李白", "朝辞白帝彩云间",
  "前两句写行程之速，后两句以猿声、山影作收；一气直下。",
  "彩云、江陵、猿声、万重山。",
  "遇赦东归的轻快，喜悦在「千里」「一日」的夸张里。",
  "「辞」「还」对举，「轻」字兼写舟轻与心轻。",
  "以空间之远写时间之短，是绝句中最见飞动的一首。"),
 (6, "七言绝句", "杜牧", "远上寒山石径斜",
  "前两句写山行所见，后两句停车看枫；由行到止。",
  "寒山、石径、白云、人家、枫林、霜叶。",
  "秋景不悲，反以红艳胜春，见晚唐人的赏爱之心。",
  "「生」字写白云之活，「晚」字点时间，「红于」二字作比。",
  "以「停车」制造停顿，把观景变成事件，末句翻案。"),
 (7, "七言绝句", "苏轼", "横看成岭",
  "前两句写观察之变，后两句点破「不识」；由象入理。",
  "岭、峰、庐山、山。",
  "由游山之惑悟认知之限，理趣从容。",
  "「横」「侧」「远」「近」「高」「低」六字写尽视角。",
  "以亲身局限说理，不说教；宋诗「以理入诗」的代表。"),
 (8, "七言绝句", "王昌龄", "秦时明月汉时关",
  "前两句以时空起兴，后两句转出「无归」之叹。",
  "明月、关塞、征人、龙城、飞将。",
  "边塞之苦与思将之切，悲慨兼有。",
  "「秦时」「汉时」互文，一「未还」写尽千年。",
  "以历史纵深压现实，四句含千年，是边塞绝句的极则。"),
 (9, "五言律诗", "杜甫", "国破山河在",
  "首联总起，颔联写景，颈联写家，尾联收于白头；四联层层收束。",
  "山河、草木、花、鸟、烽火、家书、白头、簪。",
  "国破家亡之痛，以「感时」「恨别」二字为眼。",
  "「溅」「惊」以物写情，「抵万金」以俗语写至情。",
  "颔联以乐景写哀，颈联以细节写大难；律诗对仗的典范。"),
 (10, "五言律诗", "王维", "空山新雨后",
  "首联点时地，颔联写景，颈联写人，尾联自道；由景入人。",
  "空山、新雨、明月、松、清泉、石、竹、莲、浣女、渔舟。",
  "恬淡自适，末句「王孙自可留」反用楚辞，见归隐之志。",
  "「照」「流」「喧」「动」四动词使静景生动。",
  "颔联以静写静，颈联以动写静；声、光、色三者交织。"),
 (11, "五言律诗", "李白", "青山横北郭",
  "首联写别地，颔联以「此地一为别」作转，颈联写游子意，尾联写马鸣。",
  "青山、白水、孤蓬、浮云、落日、斑马。",
  "惜别而不作悲声，末以马鸣收，情在言外。",
  "「横」「绕」写地形，「孤蓬」「浮云」皆比兴。",
  "以景结情；「萧萧班马鸣」以物之有情反衬人之难舍。"),
 (12, "五言律诗", "常建", "清晨入古寺",
  "首联入寺，颔联写径，颈联写潭，尾联写声；游踪为序。",
  "古寺、初日、高林、曲径、禅房、花木、山光、潭影、钟磬。",
  "由寻幽到忘机，末句以「余」字留不尽之意。",
  "「悦」「空」二字以景写心，是情景交融的关键。",
  "以游踪为线，以声收束；「万籁此俱寂，但余钟磬音」以有声写无声。"),
 (13, "七言律诗", "杜甫", "风急天高猿啸哀",
  "前四句写景，后四句写情；八句皆对，为律诗中最严整者。",
  "风、天、猿、渚、沙、鸟、落木、长江。",
  "老病孤愁，家国之痛与身世之悲交织。",
  "「急」「高」「哀」「清」「白」五字定全篇声调；「萧萧」「滚滚」叠字见势。",
  "八句四对而不板；以壮景写哀情，愈壮愈哀。"),
 (14, "七言律诗", "杜甫", "丞相祠堂何处寻",
  "首联问寻，颔联写景，颈联论人，尾联叹志未成。",
  "柏、阶、草、叶、黄鹂、天下计、老臣心。",
  "对诸葛的崇敬与惋惜，末句「英雄泪满襟」兼含自身。",
  "「自」「空」二字写祠之寂，「频烦」「两朝」写其忠。",
  "以景写吊，以论写史；七律中「以议论为诗」的成功例。"),
 (15, "七言律诗", "李商隐", "锦瑟无端五十弦",
  "首联以锦瑟起兴，中间两联四典并置，尾联以「惘然」收。",
  "锦瑟、庄生梦蝶、望帝啼鹃、沧海月明、蓝田日暖。",
  "惘然之情，可解为悼亡、自伤或诗艺自道，诸说并存。",
  "「无端」二字定全篇怅惘，「已」「当时」写时间之错位。",
  "典故并置而不作串讲，构成朦胧多义；不解之解，正是其法。"),
 (16, "七言律诗", "刘禹锡", "王濬楼船下益州",
  "前四句写史，后四句写今；以「人世几回」作转。",
  "楼船、金陵、王气、铁锁、石头城、故垒、芦荻。",
  "兴亡之感，冷峻中含讽意。",
  "「下」「收」写势如破竹，「伤」「暗」写今日之衰。",
  "以史为镜，借六朝说当世；怀古诗的结构范式。"),
 (17, "古体诗", "陶渊明", "结庐在人境",
  "前四句设问自答，后六句写境与心；散行单句，不事对仗。",
  "人境、车马、东篱、菊、南山、山气、飞鸟。",
  "悠然自得，「真意」二字是全篇归趣。",
  "「采」字最闲，「见」字最妙：非望而见，是无心而得。",
  "以问答起，以「欲辨已忘言」收；玄言与田园合流。"),
 (18, "古体诗", "陈子昂", "前不见古人",
  "两句一联，前两句写时间，后两句写空间；四句两两对举。",
  "古人、来者、天地、幽州台、涕。",
  "怀才不遇的孤绝，苍茫无依。",
  "「不见」重出，「独」字点出全篇主角。",
  "以极简的时空框架承载极重的孤独；不假意象，直抒胸臆。"),
 (19, "古体诗", "李白", "君不见黄河之水天上来",
  "以两「君不见」起，中段铺陈宴乐，末段以「万古愁」收；长短句错落。",
  "黄河、白发、金樽、钟鼓、馔玉、五花马、千金裘。",
  "悲慨与豪纵并存，是「以酒浇愁」的最强音。",
  "「奔流」「不复回」写时间之不可逆，「天生我材」一转见自负。",
  "以夸张与反问驱动；句式长短变化即情绪起伏。"),
 (20, "古体诗", "李白", "海客谈瀛洲",
  "以「梦」为骨，由入梦、历境到惊觉；句式参差，杂用四言、五言、七言。",
  "瀛洲、天姥、镜湖、剡溪、谢公屐、青冥、金银台。",
  "对自由的向往与对现实的失望，梦醒后「失向来之烟霞」。",
  "「飞」「送」「裂」等动词见声势；「惟觉时之枕席」以实写虚。",
  "以梦境构境，以句式破格律；歌行的自由正在此。"),
 (21, "平韵词", "温庭筠", "小山重叠金明灭",
  "上片写慵起梳妆，下片写换衣照镜；以动作连缀，不作抒情语。",
  "小山、鬓云、香腮、蛾眉、镜、花、鹧鸪。",
  "闺中寂寞，以「双双金鹧鸪」反衬孤独。",
  "「度」「弄」「贴」三字写妆饰之精细，见词体「镂玉雕琼」之工。",
  "以物写人，以艳笔写冷情；花间词的典型笔法。"),
 (22, "平仄转换词", "李煜", "春花秋月何时了",
  "上下片各两转韵：由问天到忆国，由「雕栏」到「朱颜改」，末以「一江春水」作结。",
  "春花、秋月、小楼、东风、故国、雕栏、春水。",
  "亡国之痛，以问句层层逼出。",
  "「又」字写时间之无情，「改」字写人事之全非。",
  "以问起、以喻结；「一江春水」把愁量化、空间化。"),
 (23, "仄韵词", "李清照", "寻寻觅觅",
  "开篇十四叠字，继以「乍暖还寒」写时，再以雁、花、梧桐、雨层层推进。",
  "淡酒、雁、黄花、梧桐、细雨、黄昏。",
  "国破家亡、孤身漂泊的沉痛，末句「怎一个愁字了得」翻出。",
  "十四叠字由动作到心境；「独自怎生得黑」以口语入词而极工。",
  "以声写情：齿音、舌音密集，读来哽咽；慢词铺叙的极致。"),
 (24, "仄韵词", "柳永", "寒蝉凄切",
  "上片写别时，下片写别后；以「今宵酒醒何处」作时空跳跃。",
  "寒蝉、长亭、骤雨、兰舟、烟波、暮霭、杨柳、晓风、残月。",
  "羁旅离别之苦，末以「更与何人说」收，愈说愈无说处。",
  "「念」「更」二字领起虚写；「杨柳岸晓风残月」以三景叠成一句。",
  "铺叙与点染并用；上片实写、下片虚想，是慢词章法的样板。"),
 (25, "平韵词", "苏轼", "明月几时有",
  "上片问天，下片问月兼怀人；由「欲乘风归去」到「何似在人间」回落。",
  "明月、青天、琼楼玉宇、朱阁、绮户、婵娟。",
  "由超脱之想归于人间之爱，末以「千里共婵娟」作宽解。",
  "「转」「低」「照」写月之行，「不应有恨」以问代怨。",
  "以问句结构全篇；由理化情，由情入理，是词的「以诗为词」。"),
 (26, "仄韵词", "贺铸", "凌波不过横塘路",
  "上片写偶遇与阻隔，下片以「飞云冉冉」承转，末以三种闲愁作结。",
  "横塘、芳尘、琐窗、朱户、飞云、蘅皋、烟草、风絮、梅雨。",
  "可望不可即的怅惘，末句以博喻把愁量化。",
  "「不过」「目送」写距离；「试问闲愁都几许」一问领起三喻。",
  "以三景叠喻收束，是词中「博喻」的名例；句式长短与情绪同步。"),
 (27, "仄韵词", "岳飞", "怒发冲冠",
  "上片写愤，下片写志；以「靖康耻」为转折。",
  "怒发、凭栏、潇潇雨、长啸、三十功名、八千里路、贺兰山、胡虏。",
  "报国之志与雪耻之愤，声情激越。",
  "「怒」「仰」「啸」三字写动作，「空悲切」三字写不甘。",
  "以入声韵（月、歇、雪、灭）押激烈之情，声情与词情合一。"),
 (28, "仄韵词", "陆游", "红酥手",
  "上下片各三韵一转，以「错错错」「莫莫莫」两组叠字作结。",
  "红酥手、黄縢酒、宫墙柳、东风、欢情、泪痕、桃花落、池阁。",
  "夫妻离散之痛，叠字三呼，一字一泪。",
  "「错」三叠自责自怨，「莫」三叠绝望；「闲池阁」三字写尽空寂。",
  "以叠字为韵脚，声情与句式同构；此调格律的特殊正在此处。"),
 (29, "平仄通叶词", "欧阳炯", "月映长江秋水",
  "上片写江月夜景，下片写舟中客思；两片各三韵，平仄相叶。",
  "长江、秋水、星河、浅沙、汀、鸳鸯、兰舟、笛声。",
  "羁旅之思，以景起以声收，不作激语。",
  "「冷浸」二字写月色之清，「横笛」一声破静。",
  "同部平仄互叶：本调叶韵处平仄不拘，正见「通叶」与「转换」之别。"),
 (30, "平韵词", "秦观", "漠漠轻寒上小楼",
  "上片写春寒之景，下片写无所聊赖之情；以「自在飞花」「无边丝雨」对起。",
  "轻寒、小楼、晓阴、画屏、飞花、丝雨、宝帘、银钩。",
  "闲愁无端，末句「宝帘闲挂小银钩」以物之闲写人之闲。",
  "「上」字写寒之侵入，「梦」字虚写，「挂」字收得轻。",
  "以景为情，不着一「愁」；「轻」「细」「闲」三字定全篇格调。"),
]


def pingze_of(text, rp):
    out = []
    for ch in text:
        g = rp.get(ch) or rp.get(cc.convert(ch))
        if not g:
            out.append("?")
        else:
            tones = {t for _, t in g}
            out.append("平" if tones == {"平"} else ("仄" if "平" not in tones else "?"))
    return "".join(out)


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rp = collections.defaultdict(set)
    for r in con.execute("SELECT charx, rhyme_group, tone FROM ph_readings_r2_08 "
                         "WHERE system='regulated_verse'"):
        rp[r["charx"]].add((r["rhyme_group"], r["tone"]))

    cards, missing = [], []
    for no, genre, author, opening, fa, yx, qg, lz, jf in CARDS:
        op = opening
        row = None
        for q, args in (
            ("SELECT work_id,title_norm,author_name,text_punct,text_norm,collection,dynasty,source_id "
             "FROM works WHERE author_name LIKE ? AND (text_norm LIKE ? OR text_norm LIKE ?) LIMIT 1",
             ("%" + author + "%", op + "%", cc.convert(op) + "%")),
            ("SELECT work_id,title_norm,author_name,text_punct,text_norm,collection,dynasty,source_id "
             "FROM works WHERE text_norm LIKE ? LIMIT 1", (cc.convert(op) + "%",)),
            ("SELECT work_id,title_norm,author_name,text_punct,text_norm,collection,dynasty,source_id "
             "FROM works WHERE text_norm LIKE ? LIMIT 1", (op + "%",)),
        ):
            row = con.execute(q, args).fetchone()
            if row:
                break
        if not row:
            missing.append((no, genre, author, opening))
            continue
        txt = row["text_punct"] or row["text_norm"]
        chars = [c for c in txt if "\u4e00" <= c <= "\u9fff"]
        pz = pingze_of("".join(chars), rp)
        # 韵脚：句末字（以标点断句）
        sents = [s for s in re.split(r"[，。！？；、\n]", txt) if s and CJK.search(s)]
        feet = []
        for s in sents:
            cs = [c for c in s if "\u4e00" <= c <= "\u9fff"]
            if not cs:
                continue
            g = rp.get(cs[-1]) or rp.get(cc.convert(cs[-1]))
            feet.append({"char": cs[-1],
                         "group": sorted({x[0] for x in g})[0] if g else None,
                         "tone": sorted({x[1] for x in g})[0] if g else None})
        cards.append({
            "card_no": no, "genre": genre, "author": author,
            "work_id": row["work_id"], "title": row["title_norm"],
            "dynasty": row["dynasty"], "collection": row["collection"],
            "source_id": row["source_id"], "text": txt,
            "n_chars": len(chars), "n_sent": len(sents),
            "sentence_lengths": ",".join(str(len([c for c in s if "\u4e00" <= c <= "\u9fff"]))
                                         for s in sents),
            "pingze_string": pz,
            "n_ping": pz.count("平"), "n_ze": pz.count("仄"), "n_unknown_tone": pz.count("?"),
            "rhyme_feet": feet,
            "rhyme_groups": [f["group"] for f in feet],
            "analysis_zhangfa": fa, "analysis_yixiang": yx, "analysis_qinggan": qg,
            "analysis_lianzi": lz, "analysis_jifa": jf,
            "version_note": "原文取自 works（%s／%s），未经校勘" % (row["collection"], row["source_id"]),
            "verify_status": "TEXT_FROM_WORKS_NOT_COLLATED", "round": TODAY,
        })

    con.execute("DROP TABLE IF EXISTS classical_works_study_r2_08")
    con.execute("""CREATE TABLE classical_works_study_r2_08(card_no INT PRIMARY KEY, genre TEXT,
        author TEXT, work_id TEXT, title TEXT, dynasty TEXT, collection TEXT, source_id TEXT,
        text TEXT, n_chars INT, n_sent INT, sentence_lengths TEXT, pingze_string TEXT,
        n_ping INT, n_ze INT, n_unknown_tone INT, rhyme_feet TEXT, rhyme_groups TEXT,
        zhangfa TEXT, yixiang TEXT, qinggan TEXT, lianzi TEXT, jifa TEXT,
        version_note TEXT, verify_status TEXT, round TEXT)""")
    con.executemany("""INSERT INTO classical_works_study_r2_08 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
        ?,?,?,?,?,?,?,?,?,?,?)""",
                    [(c["card_no"], c["genre"], c["author"], c["work_id"], c["title"],
                      c["dynasty"], c["collection"], c["source_id"], c["text"], c["n_chars"],
                      c["n_sent"], c["sentence_lengths"], c["pingze_string"], c["n_ping"],
                      c["n_ze"], c["n_unknown_tone"],
                      json.dumps(c["rhyme_feet"], ensure_ascii=False),
                      "/".join(g or "?" for g in c["rhyme_groups"]),
                      c["analysis_zhangfa"], c["analysis_yixiang"], c["analysis_qinggan"],
                      c["analysis_lianzi"], c["analysis_jifa"], c["version_note"],
                      c["verify_status"], c["round"]) for c in cards])
    con.commit()
    json.dump({"n": len(cards), "missing": missing, "cards": cards},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("cards", len(cards), "missing", missing)
    print(json.dumps(collections.Counter(c["genre"] for c in cards), ensure_ascii=False))


if __name__ == "__main__":
    main()
