# 《中華新韻》派生數據審計

## 1 性質

《中華新韻》十四韻是以**韻母**歸部的規範，不是字表。因此「由拼音派生」本身是規則的正確應用，
但性質上只能是 `COMPUTED`，不能稱作原書採錄。

## 2 規則表（本輪明文化）

| 韻 | 韻母 | 說明 |
|---|---|---|
| 一麻 | a,ia,ua | a/ia/ua |
| 二波 | o,e,uo | o/e/uo（含 ê 部分） |
| 三皆 | ie,üe | ie/üe |
| 四开 | ai,uai | ai/uai |
| 五微 | ei,ui(uei) | ei/ui |
| 六豪 | ao,iao | ao/iao |
| 七尤 | ou,iu(iou) | ou/iu |
| 八寒 | an,ian,uan,üan | an/ian/uan/üan |
| 九文 | en,in,un(uen),ün | en/in/un/ün |
| 十唐 | ang,iang,uang | ang/iang/uang |
| 十一庚 | eng,ing,ong,iong | eng/ing/ong/iong |
| 十二齐 | i,er,ü | i/er/ü（舌面 i） |
| 十三支 | -i(zhi/chi/shi/ri/zi/ci/si) | 舌尖前/後 i |
| 十四姑 | u | u |

## 3 派生結果

| 項目 | 值 |
|---|---:|
| 派生記錄 | 7216 |
| 與十四韻命名相符 | 7216 |
| 不符 | 0 |

## 4 多音字處理

現有派生只按一個讀音歸部，多音字未展開。這是已知限制：
例如「行」xíng/háng 分屬十一庚與十唐，派生表只會給一條。
凡需多音判斷的場合，必須回查 `ph_polyphone_r2_09`，不能直接用派生結果。

## 5 與其他體系的關係

**不可**用中華新韻的部去校《詞林正韻》。二者相隔七百年，語音基礎完全不同。
本輪在 `ph_systems_r2_08` 中 `modern_rhyme` 標為 `DERIVED`，在 `SIX_RHYME_SYSTEM_COMPARISON.md` 中單列一欄，
不與歷史韻書併排計算。