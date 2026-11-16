# 歷史讀音查詢樣例（30 例）

每個樣例都給出 SQL 與實查結果，結果可復算。

### 1. 「東」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='東';
select bu,tone,is_half from ph_cilin_r2_09 where charx='東';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='東';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 東 |
| 平水韻 | 上平聲一東 |
| 詞林正韻 | 第一部 |
| 中原音韻 | 東鍾 |
| 多音字表收錄 | 否 |

### 2. 「中」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='中';
select bu,tone,is_half from ph_cilin_r2_09 where charx='中';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='中';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 東、送 |
| 平水韻 | 上平聲一東、去聲一送 |
| 詞林正韻 | 第一部 |
| 中原音韻 | 東鍾 |
| 多音字表收錄 | 是 |

### 3. 「行」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='行';
select bu,tone,is_half from ph_cilin_r2_09 where charx='行';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='行';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 唐、庚、宕、映 |
| 平水韻 | 下平聲七陽、下平聲八庚、去聲二十三漾、去聲二十四敬 |
| 詞林正韻 | 第二部、第十一部 |
| 中原音韻 | 江陽、庚青 |
| 多音字表收錄 | 是 |

### 4. 「重」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='重';
select bu,tone,is_half from ph_cilin_r2_09 where charx='重';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='重';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 鍾、腫 |
| 平水韻 | 上平聲二冬、上聲二腫、去聲二宋 |
| 詞林正韻 | 第一部 |
| 中原音韻 | 東鍾 |
| 多音字表收錄 | 否 |

### 5. 「長」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='長';
select bu,tone,is_half from ph_cilin_r2_09 where charx='長';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='長';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 陽、養、漾 |
| 平水韻 | 下平聲七陽、上聲二十二養、去聲二十三漾 |
| 詞林正韻 | 第二部 |
| 中原音韻 | 江陽 |
| 多音字表收錄 | 否 |

### 6. 「樂」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='樂';
select bu,tone,is_half from ph_cilin_r2_09 where charx='樂';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='樂';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 效、覺、笑、鐸 |
| 平水韻 | 去聲十九效、入聲三覺、入聲十藥 |
| 詞林正韻 | 第十六部 |
| 中原音韻 | 蕭豪、歌戈 |
| 多音字表收錄 | 是 |

### 7. 「為」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='為';
select bu,tone,is_half from ph_cilin_r2_09 where charx='為';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='為';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 支 |
| 平水韻 | 上平聲四支、去聲四寘 |
| 詞林正韻 | 第三部 |
| 中原音韻 | 齊微 |
| 多音字表收錄 | 否 |

### 8. 「相」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='相';
select bu,tone,is_half from ph_cilin_r2_09 where charx='相';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='相';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 陽、漾 |
| 平水韻 | 下平聲七陽、去聲二十三漾 |
| 詞林正韻 | 第二部 |
| 中原音韻 | 江陽 |
| 多音字表收錄 | 是 |

### 9. 「將」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='將';
select bu,tone,is_half from ph_cilin_r2_09 where charx='將';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='將';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 陽、漾、唐、耕 |
| 平水韻 | 下平聲七陽、去聲二十三漾 |
| 詞林正韻 | 第二部 |
| 中原音韻 | 江陽 |
| 多音字表收錄 | 是 |

### 10. 「看」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='看';
select bu,tone,is_half from ph_cilin_r2_09 where charx='看';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='看';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 寒、翰 |
| 平水韻 | 上平聲十四寒、去聲十五翰 |
| 詞林正韻 | 第七部 |
| 中原音韻 | 寒山 |
| 多音字表收錄 | 是 |

### 11. 「過」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='過';
select bu,tone,is_half from ph_cilin_r2_09 where charx='過';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='過';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 戈、過、果 |
| 平水韻 | 下平聲五歌、去聲二十一箇 |
| 詞林正韻 | 第九部 |
| 中原音韻 | 歌戈 |
| 多音字表收錄 | 否 |

### 12. 「思」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='思';
select bu,tone,is_half from ph_cilin_r2_09 where charx='思';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='思';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 之、志、咍 |
| 平水韻 | 上平聲四支、去聲四寘 |
| 詞林正韻 | 第三部 |
| 中原音韻 | 支思 |
| 多音字表收錄 | 是 |

### 13. 「教」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='教';
select bu,tone,is_half from ph_cilin_r2_09 where charx='教';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='教';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 爻 |
| 平水韻 | 下平聲三肴、去聲十九效 |
| 詞林正韻 | 第八部 |
| 中原音韻 | 蕭豪 |
| 多音字表收錄 | 否 |

### 14. 「令」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='令';
select bu,tone,is_half from ph_cilin_r2_09 where charx='令';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='令';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 仙、清、青、勁 |
| 平水韻 | 下平聲八庚、去聲二十四敬 |
| 詞林正韻 | 第十一部 |
| 中原音韻 | 庚青 |
| 多音字表收錄 | 是 |

### 15. 「勝」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='勝';
select bu,tone,is_half from ph_cilin_r2_09 where charx='勝';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='勝';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 蒸、證 |
| 平水韻 | 下平聲十蒸、去聲二十五徑 |
| 詞林正韻 | 第十一部 |
| 中原音韻 | 庚青 |
| 多音字表收錄 | 是 |

### 16. 「華」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='華';
select bu,tone,is_half from ph_cilin_r2_09 where charx='華';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='華';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 麻、禡、質、佳 |
| 平水韻 | 下平聲六麻、去聲二十二禡 |
| 詞林正韻 | 第十部 |
| 中原音韻 | 家麻 |
| 多音字表收錄 | 是 |

### 17. 「從」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='從';
select bu,tone,is_half from ph_cilin_r2_09 where charx='從';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='從';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 鍾、用、東、江 |
| 平水韻 | 上平聲二冬、去聲二宋 |
| 詞林正韻 | 第一部 |
| 中原音韻 | 東鍾 |
| 多音字表收錄 | 是 |

### 18. 「分」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='分';
select bu,tone,is_half from ph_cilin_r2_09 where charx='分';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='分';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 文、問、襇 |
| 平水韻 | 上平聲十二文、去聲十三問 |
| 詞林正韻 | 第六部 |
| 中原音韻 | 真文 |
| 多音字表收錄 | 是 |

### 19. 「間」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='間';
select bu,tone,is_half from ph_cilin_r2_09 where charx='間';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='間';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 襇 |
| 平水韻 | 上平聲十五刪、去聲十六諫 |
| 詞林正韻 | 第七部 |
| 中原音韻 | 寒山 |
| 多音字表收錄 | 否 |

### 20. 「論」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='論';
select bu,tone,is_half from ph_cilin_r2_09 where charx='論';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='論';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 諄、元、慁、魂 |
| 平水韻 | 上平聲十三元、去聲十四願 |
| 詞林正韻 | 第六部 |
| 中原音韻 | 真文 |
| 多音字表收錄 | 否 |

### 21. 「知」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='知';
select bu,tone,is_half from ph_cilin_r2_09 where charx='知';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='知';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 支、寘 |
| 平水韻 | 上平聲四支 |
| 詞林正韻 | 第三部 |
| 中原音韻 | 齊微 |
| 多音字表收錄 | 否 |

### 22. 「治」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='治';
select bu,tone,is_half from ph_cilin_r2_09 where charx='治';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='治';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 之、至、志、咍 |
| 平水韻 | 上平聲四支、去聲四寘 |
| 詞林正韻 | 第三部 |
| 中原音韻 | 齊微 |
| 多音字表收錄 | 否 |

### 23. 「識」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='識';
select bu,tone,is_half from ph_cilin_r2_09 where charx='識';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='識';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 志、職 |
| 平水韻 | 去聲四寘、入聲十三職 |
| 詞林正韻 | 第三部、第十七部 |
| 中原音韻 | 齊微 |
| 多音字表收錄 | 否 |

### 24. 「食」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='食';
select bu,tone,is_half from ph_cilin_r2_09 where charx='食';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='食';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 志、職、至 |
| 平水韻 | 去聲四寘、入聲十三職 |
| 詞林正韻 | 第十七部 |
| 中原音韻 | 支思、齊微 |
| 多音字表收錄 | 否 |

### 25. 「惡」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='惡';
select bu,tone,is_half from ph_cilin_r2_09 where charx='惡';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='惡';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 模、暮、鐸、莫 |
| 平水韻 | 上平聲七虞、去聲七遇、入聲十藥 |
| 詞林正韻 | 第四部、第十六部 |
| 中原音韻 | 魚模、蕭豪、歌戈 |
| 多音字表收錄 | 是 |

### 26. 「薄」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='薄';
select bu,tone,is_half from ph_cilin_r2_09 where charx='薄';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='薄';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 鐸、姥、錫、麥 |
| 平水韻 | 入聲十藥 |
| 詞林正韻 | 第十六部 |
| 中原音韻 | 蕭豪、歌戈 |
| 多音字表收錄 | 否 |

### 27. 「度」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='度';
select bu,tone,is_half from ph_cilin_r2_09 where charx='度';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='度';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 暮、鐸、莫 |
| 平水韻 | 去聲七遇、入聲十藥 |
| 詞林正韻 | 第四部、第十六部 |
| 中原音韻 | 魚模、蕭豪、歌戈 |
| 多音字表收錄 | 是 |

### 28. 「數」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='數';
select bu,tone,is_half from ph_cilin_r2_09 where charx='數';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='數';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 麌、遇、覺、噳 |
| 平水韻 | 上聲七麌、去聲七遇、入聲二沃、入聲三覺 |
| 詞林正韻 | 第四部、第十六部 |
| 中原音韻 | 魚模 |
| 多音字表收錄 | 是 |

### 29. 「少」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='少';
select bu,tone,is_half from ph_cilin_r2_09 where charx='少';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='少';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 小、笑 |
| 平水韻 | 上聲十七篠、去聲十八嘯 |
| 詞林正韻 | 第八部 |
| 中原音韻 | 蕭豪 |
| 多音字表收錄 | 是 |

### 30. 「好」

```sql
select system,rhyme_group,tone,source_book from ph_readings_r2_08 where charx='好';
select bu,tone,is_half from ph_cilin_r2_09 where charx='好';
select bu,tone,yinyang from ph_zhongyuan_r2_09 where charx='好';
```

| 體系 | 實查結果 |
|---|---|
| 中古音 | 晧、号 |
| 平水韻 | 上聲十九皓、去聲二十號 |
| 詞林正韻 | 第八部 |
| 中原音韻 | 蕭豪 |
| 多音字表收錄 | 是 |

## 說明

上表「無記錄」並不等於該字在某體系中不存在，而是該體系的字表未覆蓋此字
（詞林正韻僅覆蓋平水韻 57%）。查詢時必須區分「沒有」與「未收」。