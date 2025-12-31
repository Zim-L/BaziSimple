# -*- coding: utf-8 -*-
"""
精炼版排盘 + 单字分析 + 大运简化
作者 Zim-L

依赖：
pip install lunar_python colorama
datas.py common.py ganzhi.py

datas.py common.py ganzhi.py 来源于china-testing
https://github.com/china-testing/bazi
感谢前辈的辛勤工作
"""

import argparse
import datetime
from typing import Optional, List, Tuple, Dict
import collections

from colorama import init as colorama_init, Fore, Style
from lunar_python import Solar, Lunar

from datas import *      # noqa: F403
from common import *     # noqa: F403

# 自定义的温度参考        
temps = {"甲":2, "乙":1, "丙":6, "丁":4, "戊":1, "己":-1, "庚":-1, "辛":-3, "壬":-4, "癸":-6,"子":-6, "丑":-3, "寅":3, "卯":2, "辰":-1, 
            "巳":5, "午":6, "未":3, "申":-1, "酉":-3,"戌":2, "亥":-5}
            
# colorama 颜色映射（原样）
co = {
    '木':Fore.GREEN, '火':Fore.RED, '土':Fore.YELLOW, '金':Fore.WHITE, '水':Fore.CYAN,
    '甲':Fore.LIGHTGREEN_EX, '乙':Fore.GREEN, '丙':Fore.RED, '丁':Fore.LIGHTRED_EX,
    '戊':Fore.LIGHTYELLOW_EX,'己':Fore.YELLOW,'庚':Fore.LIGHTBLACK_EX,'辛':Fore.LIGHTWHITE_EX,
    '壬':Fore.LIGHTCYAN_EX,'癸':Fore.CYAN,
    '子':Fore.CYAN,'丑':Fore.YELLOW,'寅':Fore.LIGHTGREEN_EX,'卯':Fore.GREEN,
    '辰':Fore.LIGHTYELLOW_EX,'巳':Fore.RED,'午':Fore.LIGHTRED_EX,'未':Fore.YELLOW,
    '申':Fore.LIGHTBLACK_EX,'酉':Fore.LIGHTWHITE_EX,'戌':Fore.LIGHTYELLOW_EX,'亥':Fore.LIGHTCYAN_EX
}

def paint(x:str)->str:
    return ''.join(co.get(ch,'')+ch+Style.RESET_ALL for ch in x)


# 十神全称映射
ten_full = {
    '比':'比肩','劫':'劫财','食':'食神','伤':'伤官','财':'正财','才':'偏财',
    '官':'正官','杀':'官杀','印':'正印','枭':'枭神'
}


# 五行关系
GEN={'木':'火','火':'土','土':'金','金':'水','水':'木'}
KE={'木':'土','土':'水','水':'火','火':'金','金':'木'}
def wuxing_rel(a,b)->str:
    if a==b: return "同"
    if GEN[a]==b: return "被泄"
    if GEN[b]==a: return "被生"
    if KE[a]==b: return "被耗"
    if KE[b]==a: return "被克"
    return "无"


# 温度调候判断
def temp_comment(T:int)->str:
    if T <= -15: return "急需调暖"
    if -15 < T <= -6: return "适度调暖"
    if -6 < T < 6: return "调候影响不大"
    if 6 <= T < 15: return "适度调凉"
    if T >= 15: return "急需调凉"
    return "调候影响不大"

# 扶抑判断

# 基础强弱
def is_weak_and_strong(scores, gans, zhis, me_elem):
    # 根的判断：十二运中“长生/帝旺/建禄” 
    ji12 = {'长','帝','建'}  
    # 数根的数量
    roots = sum(1 for z in zhis if ten_deities[me_elem][z] in ji12)

    # 印比 + 墓库数量
    # 天干比劫:
    gan_help = sum(1 for g in gans if ten_deities[me_elem][g] in ('比','劫','枭','印'))
    # 地支墓库:
    ku = sum(1 for z in zhis if ten_deities[me_elem][z] == '库')
    help_total = gan_help + ku

    # WEAK 判定
    if roots >= 1 or (roots == 0 and help_total > 2):
        weak = False
    else:
        weak = True

    # STRONG 判定
    if roots >= 2 or (roots == 1 and help_total >= 3):
        strong = True
    else:
        strong = False

    return weak, strong

# 扶抑分类
def classify_fu_yi(scores, gans, zhis, me_elem):
    """
    七档扶抑分类（你要求的承载力先行版）：

      从局 / 假从 / 喜扶 / 扶抑影响不大 / 喜抑 / 假专旺 / 专旺
    """

    total = sum(scores.values()) or 1
    # 身方块
    SHENG = {"木":"水", "火":"木", "土":"火", "金":"土", "水":"金"}
    M = scores.get(gan5[me_elem],0)
    H = scores.get(SHENG[gan5[me_elem]],0)
    T = M + H

    R_self = M / T if T>0 else 0
    R_total = T / total

    # 第一层：承载力判定
    weak, strong = is_weak_and_strong(scores, gans, zhis, me_elem)

    # 第二层：比例判定
    # 弱端 
    if weak:
        if R_total <= 0.1: # and R_self <= 0.25:
            return "从局", "印比力量不足10%"
        if 0.1 < R_total <= 0.25 and R_self < 0.55:
            return "假从", "比劫力量太弱"
        return "喜扶", f"正格身弱，印比占比{R_total:.2f}"

    # 强端
    if strong:
        if R_total >= 0.9 and R_self >= 0.55:
            return "专旺", "印比力量超过90%且主要气势在日主"
        if R_total >= 0.75 and R_self >= 0.55:
            return "假专旺", "印比力量超过75%且主要气势在日主"
        return "喜抑", f"正格身强，印比占比{R_total:.2f}"

    return "扶抑影响不大", "身偏弱但足够扛财官，主要看格局用神/做功" if R_total<0.5 else ("身偏强但掌印也没关系，主要看格局用神/做功" if R_total>0.5 and R_self>=0.55 else "")



# 数据结构
Gans = collections.namedtuple("Gans","year month day time")
Zhis = collections.namedtuple("Zhis","year month day time")


# 输入解析：支持 --solar, --lunar, --bazi, 或直接数字
def parse_input(args)->Tuple[Gans,Zhis,Optional[Solar],Optional[Lunar],Optional[datetime.date]]:
    if args.bazi:
        s=''.join(args.bazi).replace(' ','')
        if len(s)!=8: raise ValueError("八字格式必须 8 字")
        pillars=[s[i:i+2] for i in range(0,8,2)]
        g=Gans(*[p[0] for p in pillars])
        z=Zhis(*[p[1] for p in pillars])
        return g,z,None,None,None

    # 处理 solar / lunar / 裸日期
    if args.solar:
        Y,M,D,H=args.solar
        solar=Solar.fromYmdHms(Y,M,D,H,0,0)
        lunar=solar.getLunar()
        birth=datetime.date(Y,M,D)
    elif args.lunar:
        Y,M,D,H=args.lunar
        lunar=Lunar.fromYmdHms(Y,M,D,H,0,0)
        solar=lunar.getSolar()
        birth=datetime.date(solar.getYear(),solar.getMonth(),solar.getDay())
    else:
        if len(args.date)==4:
            Y,M,D,H=args.date
            solar=Solar.fromYmdHms(Y,M,D,H,0,0)
            lunar=solar.getLunar()
            birth=datetime.date(Y,M,D)
        else:
            raise ValueError("必须提供 --solar / --lunar / --bazi / 或裸 4 数字 年月日时")

    ba=lunar.getEightChar()
    g=Gans(ba.getYearGan(),ba.getMonthGan(),ba.getDayGan(),ba.getTimeGan())
    z=Zhis(ba.getYearZhi(),ba.getMonthZhi(),ba.getDayZhi(),ba.getTimeZhi())
    return g,z,solar,lunar,birth


# 五行分数（子平真诠）
def calc_scores(gans: Gans, zhis: Zhis)->Dict[str,int]:
    sc={"金":0,"木":0,"水":0,"火":0,"土":0}
    for g in gans:
        sc[gan5[g]]+=5   # noqa
    for z in list(zhis)+[zhis.month]:
        for hg in zhi5[z]: # noqa
            w=zhi5[z][hg]
            sc[gan5[hg]]+=w
    return sc


# 温度累积
def calc_temp(gans:Gans,zhis:Zhis)->int:
    return temps[gans.year]+temps[gans.month]+temps[gans.day]+temps[gans.time]+ \
           temps[zhis.year]+temps[zhis.month]*2+temps[zhis.day]+temps[zhis.time]


# 邻位（严格相邻）
def neighbours(row:int,col:int,gans:Gans,zhis:Zhis)->List[Tuple[str,str,str]]:
    def cell(r,c):
        if r==0:
            ch=gans[c]; elem=gan5[ch]
        else:
            ch=zhis[c]; elem=zhi_wuhangs[ch]
        return ch,elem
    out=[]
    if row==0:
        ch,elem=cell(1,col); out.append(("下",ch,elem))
    else:
        ch,elem=cell(0,col); out.append(("上",ch,elem))
    if col>0:
        ch,elem=cell(row,col-1); out.append(("左",ch,elem))
    if col<3:
        ch,elem=cell(row,col+1); out.append(("右",ch,elem))
    return out


# 得势：邻位存在同/被生 | 传统观点认为得势是天干还有其他透出，这里是个人的经验判断
def de_shi(elem:str,neigh)->Optional[List[str]]:
   
    hits = []
    for _, ch, e in neigh:
        rel = wuxing_rel(elem, e)
        # 常规逻辑：同 / 生
        if rel in ("同", "被生"):
            hits.append(paint(ch))
            continue
        # 特例：辰培木
        # 条件：自己是木，邻位字是地支“辰”
        # 注意：这里只处理“辰→木”的命理认定，不把其它墓库带入
        if elem == "木" and ch == "辰":
            hits.append(paint(ch) + "(培)")
            continue

    return hits if hits else None

# 墓库
MU_KU={'火':'戌','金':'丑','水':'辰','木':'未'}

def mu_ku_status(elem:str,zhis:Zhis)->Tuple[bool,str]:
    mk=MU_KU.get(elem)
    return (mk in zhis),mk

# 暗合（新增）
ANHE={('丑','寅'),('寅','丑'),('午','亥'),('亥','午'),('卯','申'),('申','卯')}

# 天地自合（整柱）
TIANDI_ZIHE={("丁","亥"),("戊","子"),("甲","午"),("己","亥"),
             ("辛","巳"),("壬","午"),("癸","巳")}

# 双冲 / 双合
GAN_CHONG={(a,b) for a,b in [( "甲","庚"),("庚","甲"),("乙","辛"),("辛","乙"),
("丙","壬"),("壬","丙"),("丁","癸"),("癸","丁")]}

# 六合表 from datas/common
def zhi_is_liuhe(a,b)->bool:
    try:
        return zhi_atts[a].get("六")==b
    except: return False


# 得月 & 天干得地 & 地支透出 & 羊刃 & 帝旺
def de_yue(elem:str,month_zhi:str)->str:
    me_elem=elem; m_elem=zhi_wuhangs[month_zhi]
    if me_elem==m_elem: return "得月(旺)"
    if wuxing_rel(m_elem,me_elem)=="被泄": return "得月(相)"
    if (month_zhi=='辰' and me_elem=='木'): return "半得月(春末)"
    if (month_zhi=='未' and me_elem=='火'): return "半得月(夏末)"
    if (month_zhi=='戌' and me_elem=='金'): return "半得月(秋末)"
    if (month_zhi=='丑' and me_elem=='水'): return "半得月(冬末)"
    return "不得月"

def de_di_for_gan(elem:str,zhis:Zhis)->Optional[List[str]]:
    hits=[z for z in zhis if zhi_wuhangs[z]==elem]
    return hits if hits else None

def tou_chu_for_zhi(elem:str,gans:Gans)->Optional[List[str]]:
    hits=[g for g in gans if gan5[g]==elem]
    return hits if hits else None

def is_yang_gan(g:str)->bool:
    return Gan.index(g)%2==0   # noqa

# 羊刃：日主阳干 & 十神=劫财
def yangren(me:str, shen_short:str)->bool:
    return is_yang_gan(me) and shen_short=='劫'

# 十二运帝旺
DIWANG_POS={
    '甲':'午','乙':'午','丙':'午','丁':'午','戊':'午','己':'午',
    '庚':'酉','辛':'酉','壬':'子','癸':'子'
}
def diwang(me:str, hits_de_di:Optional[List[str]])->Optional[str]:
    if not hits_de_di: return None
    if DIWANG_POS.get(me) in hits_de_di: return DIWANG_POS[me]
    return None


# 天干神煞
def calc_shens_for_fourpillars(gans:Gans, zhis:Zhis, me:str):
    strs = [""]*4
    all_shens = set()
    all_shens_list = []

    # 【年神】 只判 月/日/时，不判年
    for item in year_shens:
        for i in (1,2,3):
            if zhis[i] in year_shens[item][zhis.year]:
                strs[i] = item if not strs[i] else strs[i] + chr(12288) + item
                all_shens.add(item)
                all_shens_list.append(item)

    # 【月神】 判 四柱天干 or 地支；日干命中添加 ●
    for item in month_shens:
        for i in range(4):
            if gans[i] in month_shens[item][zhis.month] or zhis[i] in month_shens[item][zhis.month]:
                strs[i] = item if not strs[i] else strs[i] + chr(12288) + item
                # 重点：若此神煞落在“日干”且命中“天干”
                if i == 2 and gans[i] in month_shens[item][zhis.month]:
                    strs[i] += "●"
                all_shens.add(item)
                all_shens_list.append(item)

    # 【日神】 判 年/月/时，不判日柱
    for item in day_shens:
        for i in (0,1,3):
            if zhis[i] in day_shens[item][zhis.day]:
                strs[i] = item if not strs[i] else strs[i] + chr(12288) + item
                all_shens.add(item)
                all_shens_list.append(item)

    # 【贵神 / g_shens】 判 四柱地支 against 本命日干
    for item in g_shens:
        for i in range(4):
            if zhis[i] in g_shens[item][me]:
                strs[i] = item if not strs[i] else strs[i] + chr(12288) + item
                all_shens.add(item)
                all_shens_list.append(item)

    return strs, list(all_shens_list)


# 单字分析（天干 & 地支）
POS_GAN=["年干","月干","日干","时干"]
POS_ZHI=["年支","月支","日支","时支"]

def analyse_char(gans:Gans,zhis:Zhis,me:str,idx:int,is_gan:bool,year_zhi_for_ganzhi:str,scores)->None:
    # 基本
    row=0 if is_gan else 1
    col=idx
    if is_gan:
        ch=gans[idx]; elem=gan5[ch]; pos=POS_GAN[idx]
        sh=ten_deities[me][ch] # 短十神
        sh_full=ten_full[sh]
    else:
        ch=zhis[idx]; elem=zhi_wuhangs[ch]; pos=POS_ZHI[idx]
        mg=max(zhi5[ch],key=zhi5[ch].get)
        sh=ten_deities[me][mg]
        sh_full=ten_full[sh]

    neigh=neighbours(row,col,gans,zhis)
    neigh_desc=[]
    up=None; down=None
    for where,nb,nb_elem in neigh:
        rel=wuxing_rel(elem,nb_elem)
        if elem=="木" and nb=="辰":
            rel="培木"

        # 2) 未脆金（辛未最典型，但金在未普遍如此）
        if elem=="金" and nb=="未":
            rel="脆金"

        # 3) 金被埋（土重金埋，需判断全局五行分数）
        if elem=="土" and nb in ("申","酉"):    # 金旺地支
            if scores["金"] < scores["土"]:
                rel="埋金"
        seg=f"{where}{paint(nb)}({paint(nb_elem)}):{rel}"
        neigh_desc.append(seg)
        if where=="上": up=rel
        if where=="下": down=rel
    
    # 标记
    flags=[]

    # 盖头/截脚
    if up=="被克": flags.append("盖头")
    if down=="被克": flags.append("截脚")

    # 羊刃
    if yangren(me,sh): flags.append("羊刃")

    # 地支透出 or 天干得地
    if is_gan:
        dd=de_di_for_gan(elem,zhis)
        if dd: flags.append("得地("+paint(dd)+")")
        # 帝旺
        dw=diwang(me,dd)
        if dw: flags.append("帝旺("+paint(dw)+")")
        tc=""
    else:
        tc=tou_chu_for_zhi(elem,gans)
        if tc: flags.append("透出("+paint(tc)+")")

    # 得月
    dy=de_yue(elem,zhis.month)
    if dy!="不得月":
        flags.append(dy)

    # 得势
    ds=de_shi(elem,neigh)
    if ds:
        flags.append("得势("+paint(ds)+")")

    # 暗合（地支）
    if not is_gan:
        for j,z in enumerate(zhis):
            if j!=idx and (ch,z) in ANHE:
                flags.append("暗合("+paint(z)+")")

    # 墓库 & 冲开/刑开 （看“墓库地支”是否被打开）
    has_mk, mk = mu_ku_status(elem, zhis)
    if has_mk:
        opened = False
        for other in zhis:
            if other == mk:
                continue
            # 冲开
            if zhi_atts.get(mk, {}).get("冲") == other:
                opened = True
            # 刑开
            if zhi_atts.get(mk, {}).get("刑") == other:
                opened = True
    
        if opened:
            flags.append(f"带墓库({paint(mk)} 原局冲/刑开)")
        else:
            flags.append(f"带墓库({paint(mk)})")
                
    # 输出
    print(f"[{pos}] {('天干' if is_gan else '地支')} {paint(ch)}({paint(elem)}) 十神:{sh_full}")
    print(f"  邻位: {'  '.join(neigh_desc)}")
    if flags:
        print("  标记: "+ "  ".join(flags))

    # 与其他字的关系（含隔多少位）
    # 只对地支做六合/冲/刑/害/破/暗合，会与三合三会混合展示
    rels=[]
    if is_gan:
        myi=idx
        for j,z in enumerate(gans):
            if j==idx: continue
            dist=abs(j-idx)-1
            distinfo = f'(隔{dist}位)' if dist>0 else ''
            # 合
            if (ch,z) in gan_hes or (z,ch) in gan_hes:
                rels.append(f"六合:{paint(z)}{distinfo}")
            # 冲
            if (ch,z) in gan_chongs or (z,ch) in gan_chongs:
                rels.append(f"冲:{paint(z)}{distinfo}")

        if rels:
            print("  天干关系: "+"  ".join(rels))
    if not is_gan:
        myi=idx
             
        # 若三合成立，则不再判半合
        sanhe_done = False
        for key, wu in zhi_hes.items():  # e.g. "申子辰":"水"
            if all(z_ in zhis for z_ in key):
                middle = key[1]  # 中神位置
                info = f"{''.join([paint(zi) for zi in key])}化{paint(wu)}"
                # 中神被冲？
                if zhi_atts[middle].get("冲") in zhis:
                    info += "(中神被冲)"
                rels.append(info)
                sanhe_done = True
        
        # 三会局
        zhi_huis = {
            "亥子丑": "北方水",
            "寅卯辰": "东方木",  
            "巳午未": "南方火",       
            "申酉戌": "西方金",
        }
        for key, wu in zhi_huis.items():  # e.g. "申子辰":"水"
            if all(z_ in zhis for z_ in key):
                middle = key[1]  # 中神位置
                info = f"{''.join([paint(zi) for zi in key])}会{paint(wu)}"
                rels.append(info)
                
        for j,z in enumerate(zhis):
            if j==idx: continue
            dist=abs(j-idx)-1
            distinfo = f'(隔{dist}位)' if dist>0 else ''
            # 六合
            if zhi_atts[ch].get("六")==z:
                rels.append(f"六合:{paint(z)}{distinfo}")
            # 冲
            if zhi_atts[ch].get("冲")==z:
                rels.append(f"冲:{paint(z)}{distinfo}")
            # 刑
            if zhi_atts[ch].get("刑")==z:
                rels.append(f"刑:{paint(z)}{distinfo}")
            # 害
            if zhi_atts[ch].get("害")==z:
                rels.append(f"害:{paint(z)}{distinfo}")
            # 破
            if zhi_atts[ch].get("破")==z:
                rels.append(f"破:{paint(z)}{distinfo}")
            # 暗合
            if (ch,z) in ANHE or (z,ch) in ANHE:
                rels.append(f"暗合:{paint(z)}{distinfo}")
        
        # 重新自定义半合
        zhi_half_3hes = {
            ("申", "子"): "化水",
            ("子", "辰"): "化水",
            ("申", "辰"): "拱水",    
            ("巳", "酉"): "化金",  
            ("酉", "丑"): "化金",  
            ("巳", "丑"): "拱金",      
            ("寅", "午"): "化火",    
            ("午", "戌"): "化火",   
            ("寅", "戌"): "拱火",   
            ("亥", "卯"): "化木",
            ("亥","未"): "化木",
            ( "卯", "未"): "拱木",
        }
        # 半合
        if not sanhe_done:
            for (a,b), mode in zhi_half_3hes.items():
                # 只在当前 ch 是 a 或 b 时
                if ch not in (a,b): continue
                other = b if ch==a else a
                if other not in zhis: continue

                # eg half ('化水') or ('拱水')
                out = f"半合:{paint(other)}{mode[0]}{paint(mode[1])}"

                # === 拱特殊处理 ===
                if mode.startswith("拱"):
                    # 找到五行
                    wu = mode[1:]  # 去掉“拱”，比如“拱水”->“水”
                    # 天干五行取值
                    wu_gans = {
                        "木": ("甲","乙"),
                        "火": ("丙","丁"),
                        "土": ("戊","己"),
                        "金": ("庚","辛"),
                        "水": ("壬","癸")
                    }[wu]

                    # 看“这个地支”和“other地支”上面的天干
                    gset = set()
                    # 当前这个 ch 对应的列 idx
                    my_gan = gans[idx]
                    if my_gan in wu_gans:
                        gset.add(my_gan)

                    # 对方 other 对应的列 j
                    other_idx = zhis.index(other)
                    other_gan = gans[other_idx]
                    if other_gan in wu_gans:
                        gset.add(other_gan)

                    out += "(" + ("".join(gset) if gset else "虚") + ")"

                rels.append(out)

        
        if rels:
            print("  地支关系: "+"  ".join(rels))


    # 额外：地支神煞（全年适用，不限年干）
    strs, all_shens_list = calc_shens_for_fourpillars(gans, zhis, me)
    if not is_gan:
        this_shens = strs[idx]
        if this_shens:
            print(f"  神煞: {this_shens}")
    print()


# 整柱关系
def pillar_relations(gans:Gans,zhis:Zhis)->None:
    print("## 整柱关系")
    print()
    for i in range(4):
        gan=gans[i]; zhi=zhis[i]
        tag=[]
        if (gan,zhi) in TIANDI_ZIHE:
            tag.append("天地自合")
        # 双冲
        for j in range(4):
            if i==j: continue
            ga2=gans[j]; zh2=zhis[j]
            if (gan,ga2) in GAN_CHONG and zhi_atts[zhi].get("冲")==zh2:
                tag.append("双冲("+paint(ga2+zh2)+")")
        # 双合
        for j in range(4):
            if i==j: continue
            ga2=gans[j]; zh2=zhis[j]
            if ((gan,ga2) in gan_hes or (ga2,gan) in gan_hes) and zhi_is_liuhe(zhi,zh2):
                tag.append("双合("+paint(ga2+zh2)+")")
        print(f"  {paint(gan+zhi)} : "+ ("  ".join(tag) if tag else "无"))
    print()


# 大运（真实时间滚动）
def print_dayun(solar:Solar, lunar:Lunar, is_male:bool)->None:
    print("## 大运")
    #print("="*110)
    print()

    yun = lunar.getEightChar().getYun(is_male)

    # 起运公历时间
    start = yun.getStartSolar()                 # start: Solar
    start_dt = datetime.datetime.strptime(start.toYmdHms(), "%Y-%m-%d %H:%M:%S").date()

    today = datetime.date.today()

    for idx, du in enumerate(yun.getDaYun()[1:]):
        gz = du.getGanZhi()
        start_age = du.getStartAge()

        # 每 10 年滚动
        enter = start_dt.replace(year=start_dt.year + idx*10)
        leave = start_dt.replace(year=start_dt.year + (idx+1)*10)

        mark = " ←当前" if enter <= today < leave else ""
        print(f"{start_age:<3d} {paint(gz[0]+gz[1])}{mark}")


# 主盘输出
def print_board_simple(gans:Gans, zhis:Zhis, is_male:bool,
                       scores, temp, solar:Optional[Solar], lunar:Optional[Lunar]):
    """
    头部信息 + 四柱两行 + 十神 + 五行分数 + 温度 + 乾造/坤造
    """

    print('## 命盘\n')

    if solar and lunar:
        # 节气
        prev_jq = lunar.getPrevJieQi(True)
        next_jq = lunar.getNextJieQi(True)

        sex_str = "男命" if is_male else "女命"
        print(f"{sex_str}\t公历: {solar.getYear()}年{solar.getMonth()}月{solar.getDay()}日"
              f"\t农历: {lunar.getYear()}年{lunar.getMonth()}月{lunar.getDay()}日"
              f"\t 上运时间: {lunar.getEightChar().getYun(is_male).getStartSolar().toYmdHms().split()[0]}"
              f"\t命宫:{lunar.getEightChar().getMingGong()}  胎元:{lunar.getEightChar().getTaiYuan()}  身宫:{lunar.getEightChar().getShenGong()}")

        print(f"\t节气: {prev_jq.getName()} {prev_jq.getSolar().toYmdHms()}  ->  "
              f"{next_jq.getName()} {next_jq.getSolar().toYmdHms()}")
    else:
        # 八字模式
        sex_str = "男命" if is_male else "女命"
        print(f"{sex_str} (八字模式)")



    print()

    # 四柱两行（左右两侧并列）
    left_gan  = "  ".join(gans)
    left_zhi  = "  ".join(zhis)
    # === 计算 大运 / 流年 / 流月 / 流日 ======================================
    now = datetime.datetime.now()
    today_solar = Solar.fromDate(now)
    today_lunar = today_solar.getLunar()

    # 流年干支
    liu_nian_g, liu_nian_z = today_lunar.getYearGan(), today_lunar.getYearZhi()

    # 流月干支（已考虑节气切月）
    liu_yue_g, liu_yue_z = today_lunar.getMonthGan(), today_lunar.getMonthZhi()

    # 流日干支
    liu_ri_g, liu_ri_z = today_lunar.getDayGan(), today_lunar.getDayZhi()

    # --- 当前大运（真实滚动） ---
    yun = lunar.getEightChar().getYun(is_male)
    start = yun.getStartSolar()
    start_dt = datetime.datetime.strptime(start.toYmdHms(), "%Y-%m-%d %H:%M:%S").date()
    today = datetime.date.today()

    da_yun_g, da_yun_z = None, None
    for idx, du in enumerate(yun.getDaYun()[1:]):
        enter = start_dt.replace(year=start_dt.year + idx*10)
        leave = start_dt.replace(year=start_dt.year + (idx+1)*10)
        if enter <= today < leave:
            da_yun_g, da_yun_z = du.getGanZhi()
            break
    # 如果还没入运，则使用第一个大运
    if da_yun_g is None:
        da_yun_g, da_yun_z = yun.getDaYun()[1].getGanZhi()

    # === 输出右侧四列 =======================================================
    right_gan = " ".join([da_yun_g, liu_nian_g, liu_yue_g, liu_ri_g])
    right_zhi = " ".join([da_yun_z, liu_nian_z, liu_yue_z, liu_ri_z])

    print(f"{paint(left_gan)}  |  {paint(right_gan)}")
    print(f"{paint(left_zhi)}  |  {paint(right_zhi)}")
    
    def zhi_all_gan_shen(z):
        # 返回：丁(伤官) 戊(正财) 癸(正印) 这样的格式
        lst=[]
        for hg in zhi5[z]:
            full = ten_full[ten_deities[gans.day][hg]]
            lst.append(f"{hg}({full})")
        return " ".join(lst)

    print("地支藏气: ", " | ".join(zhi_all_gan_shen(z) for z in zhis))

    # 十神：天干十神 & 地支主气十神
    gan_shens=[]
    for seq,item in enumerate(gans):
        if seq==2: # 日干
            gan_shens.append("元男" if is_male else "元女")
        else:
            gan_shens.append(ten_full[ten_deities[gans.day][item]])
    print("天干十神: ", "  ".join(gan_shens))

    zhi_shens=[]
    for item in zhis:
        mg=max(zhi5[item],key=zhi5[item].get)
        zhi_shens.append(ten_full[ten_deities[gans.day][mg]])
    print("地支十神(主气): ", "  ".join(zhi_shens))

    # 五行分数
    fs = f"木:{scores['木']}  火:{scores['火']}  土:{scores['土']}  金:{scores['金']}  水:{scores['水']}"
    print("五行分数:", fs)

    # 调候与扶抑
    print(f"温度: {(temp+20):>3d}℃ {temp_comment(temp)}")
    tag, comment = classify_fu_yi(scores, gans, zhis, gans.day)
    print(f"扶抑: {tag}  {comment}")

    # 乾造/坤造
    zz = [''.join(p) for p in zip(gans,zhis)]
    print(("乾造:" if is_male else "坤造:"), " ".join(zz))
    print()

def main():
    colorama_init(autoreset=True)
    parser=argparse.ArgumentParser()
    parser.add_argument("--sex",choices=["m","f"],default="m")
    parser.add_argument("--solar",nargs=4,type=int)
    parser.add_argument("--lunar",nargs=4,type=int)
    parser.add_argument("--bazi",nargs="+")
    parser.add_argument("date",nargs="*",type=int)
    args=parser.parse_args()

    g,z,solar,lunar,birth=parse_input(args)
    is_male=(args.sex=="m")
    if lunar:
        print(f"{'男' if is_male else '女'}命 公历:{solar.getYear()}-{solar.getMonth()}-{solar.getDay()}  农历:{lunar.getYear()}-{lunar.getMonth()}-{lunar.getDay()}")
    else:
        print(f"{'男' if is_male else '女'}命 (八字模式)")
    
    scores=calc_scores(g,z)
    temp=calc_temp(g,z)

    print_board_simple(g,z,is_male,scores,temp,solar,lunar)

    # 单字分析
    print("## 单字分析")
    #print("="*110)
    # 天干使用 年支作为神煞推源
    year_zhi=z.year
    for i in range(4):
        analyse_char(g,z,g.day,i,True,year_zhi,scores)
    for i in range(4):
        analyse_char(g,z,g.day,i,False,year_zhi,scores)
    print()

    # 整柱关系
    pillar_relations(g,z)

    # 大运
    if lunar:
        print_dayun(solar,lunar,is_male)
    else:
        print("大运: 需提供具体出生日期可显示")
        

if __name__=="__main__":
    main()
