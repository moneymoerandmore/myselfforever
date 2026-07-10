# 身份事实候选抽取报告

- Generated: 2026-07-10T16:38:31+08:00
- Source outputs: `C:\Users\cloud\Documents\Codex\2026-06-03\skill\outputs`
- Candidate output: `runtime\self-core\identity-facts\candidates.jsonl`
- Privacy posture: snippets are short review excerpts; confirmed facts should still cite refs instead of copying long chat text.

## 结论

- 用户显式校对的做饭事实优先级最高：用户完全不会做饭，数字我不得自称会做饭或愿意做饭。
- 本轮聊天抽取只产出候选，不自动提升为 confirmed facts。
- 对游泳、开车这类能力事实，如果没有直接“我会/我不会”的强证据，运行时应保持中性，不替用户认领。

## Theme Summary

| theme | matches | positive | negative | constraint | mention |
| --- | --- | --- | --- | --- | --- |
| 做饭/下厨 | 271 | 0 | 0 | 224 | 47 |
| 游泳/水性 | 43 | 1 | 0 | 2 | 40 |
| 开车/驾照/自驾 | 547 | 5 | 2 | 200 | 340 |
| 旅行规划 | 813 | 21 | 0 | 0 | 792 |
| 养宠/猫 | 1155 | 214 | 0 | 0 | 941 |
| 育儿/家庭照护 | 1474 | 415 | 0 | 0 | 1059 |
| AI/产品/组织工作 | 3335 | 3335 | 0 | 0 | 0 |

## Candidate Records

| id | fact_type | polarity | confidence | statement |
| --- | --- | --- | --- | --- |
| ifc-20260710-cooking-ecc9a04a0bd7 | boundary | constraint | high | 用户已显式校对：完全不会做饭；聊天抽取只作为旁证，不再生成相反候选。 |
| ifc-20260710-swimming-6699958c39fd | boundary | constraint | low | 关于“游泳/水性”存在多条聊天证据，但方向混杂，需要人工确认。 |
| ifc-20260710-driving-5d0ea3b3c1a6 | capability | positive | medium | 多次第一人称聊天证据显示：用户大概率会开车，并曾提到自己开车、开车接人或开车前往。 |
| ifc-20260710-travel_planning-11547711698d | habit | positive | medium | 聊天证据倾向显示：用户经常涉及并可能熟悉“旅行规划”。 |
| ifc-20260710-pets-d7397e558e96 | role | positive | medium | 聊天证据倾向显示：用户经常涉及并可能熟悉“养宠/猫”。 |
| ifc-20260710-parenting-e77555eade37 | role | positive | medium | 聊天证据倾向显示：用户经常涉及并可能熟悉“育儿/家庭照护”。 |
| ifc-20260710-ai_product_work-accceecd2ea1 | habit | positive | medium | 聊天证据倾向显示：用户经常涉及并可能熟悉“AI/产品/组织工作”。 |

## Evidence Samples

### 做饭/下厨
| kind | ref | time | polarity | source_hash | snippet |
| --- | --- | --- | --- | --- | --- |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=64577 | 2026-05-13 19:01:53 | constraint | 4848995fef | 点外卖啊 |
| episode | ep_010991 | 2026-05-13 18:59:50 | constraint | 4848995fef | 不对啊 叶莉莎不是请假了么 请假还出去混了？ 点外卖啊 求解要灵活 不焦虑才能多活几年 天天 pua 宝宝 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=153887 | 2026-04-28 12:05:33 | constraint | 85cb21acd4 | 下雨了 点了外卖了 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=153476 | 2026-04-24 18:52:37 | constraint | 85cb21acd4 | 外卖了书记 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=150575 | 2026-04-07 23:21:10 | constraint | 85cb21acd4 | 搞个屁外卖 |
| episode | ep_005510 | 2026-04-07 23:19:06 | constraint | 85cb21acd4 | 谷歌都没跌 我本来计划烈度加大 双底 我抄第二个底 结果不下来 我亏麻了 害 阿里也是能跌 搞个屁外卖 |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=63502 | 2026-04-07 11:38:14 | constraint | 4848995fef | 我中午吃外卖 |
| episode | ep_011936 | 2026-04-07 11:38:14 | constraint | 4848995fef | 我中午吃外卖 不要等我 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=144181 | 2026-03-03 18:30:21 | constraint | 85cb21acd4 | chaoran 喊我开会去了 我点个外卖 |
| candidate | 群聊_Z哥学习群.json#localId=23752 | 2026-02-25 23:36:36 | constraint | 2717e7d9ae | 外卖指数又开始了？ |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=142593 | 2026-02-25 15:06:37 | constraint | 85cb21acd4 | 不是 外卖又绿了 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=142387 | 2026-02-24 16:10:34 | constraint | 85cb21acd4 | 就是吃了个外卖 |
| episode | ep_007893 | 2026-02-24 16:09:59 | constraint | 85cb21acd4 | 我血糖叫了 2 小时了 明天带我吃饭 就是吃了个外卖 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=141908 | 2026-02-20 14:14:21 | constraint | 85cb21acd4 | 搞外卖的 搞新能源车的 都是垃圾 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=141285 | 2026-02-17 22:24:29 | constraint | 85cb21acd4 | 二是 这些互联网公司 ai 不纯粹 搞个鸡把外卖 |
| episode | ep_003994 | 2026-02-17 22:21:01 | constraint | 85cb21acd4 | 存储 alvin 还在带头抄底[引用 菜得不配说话：现在只有存储和台积电没走坏了吧] 比我当时买谷歌还坚决 我是不太敢碰了 恒生坑大爹 你看我这两个建仓点 在技术上是完美的壳 就因为高点没卖 现在是亏的 我相信个鸡把科技 其实是利好的 但是有两个反逻辑 我们没跟上 一是 市场觉… |

### 游泳/水性
| kind | ref | time | polarity | source_hash | snippet |
| --- | --- | --- | --- | --- | --- |
| candidate | 私聊_葉莎莎Lisa🐈.json#localId=26517 | 2020-11-22 14:15:31 | positive | 5279693b7c | 猫咪居然会游泳啊 |
| candidate | 私聊_葉莎莎Lisa🐈.json#localId=59157 | 2022-03-06 15:55:11 | constraint | 5279693b7c | 世界上最美的溺水者 |
| episode | ep_017578 | 2022-03-06 15:52:24 | constraint | 5279693b7c | 这个本 太强了 世界上最美的溺水者 特别适合你 立意立的上天了 |
| candidate | 私聊_1469.json#localId=59601 | 2026-04-27 23:26:59 | mention | 57ff771672 | 赶紧学游泳 |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=57000 | 2025-12-11 16:48:45 | mention | 4848995fef | 体检异常指标干预建议清单 一、持续异常需重点关注的指标 1. 尿蛋白（两次均超参考值，第二次轻度升高至313.0mg/L） • 核心风险：长期升高可能提示肾脏滤过功能受损，需排查慢性肾炎、糖尿病肾病（结合血糖变化）等潜在问题。 • 干预建议： ◦ 就医检查：尽快到肾内科就诊，完… |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=105870 | 2024-12-09 23:31:17 | mention | 85cb21acd4 | 毛老师又潜水了[引用 刘智：[链接]] |
| episode | ep_006382 | 2024-12-09 23:31:17 | mention | 85cb21acd4 | 毛老师又潜水了[引用 刘智：[链接]] 肯定啊[引用 张骏：好像只能继续印钱+扩大赤字吧] 相信gov就对了 因果律武器 会干的 和社会主义没关系 和中华民族伟大复兴很有关系 都在说这个[引用 刘智：[图片]] |
| candidate | 群聊_小宝今天请客了吗？.json#localId=70189 | 2024-08-05 19:57:30 | mention | ba0a30be5c | 游泳队 |
| candidate | 群聊_小宝今天请客了吗？.json#localId=59545 | 2024-01-13 17:29:54 | mention | ba0a30be5c | 又不会都投[引用 在泳池小便是可耻行为：不过2kw的人口。。。现在开票才五分之一] |
| episode | ep_009480 | 2024-01-13 17:28:59 | mention | ba0a30be5c | 大局已定 又不会都投[引用 在泳池小便是可耻行为：不过2kw的人口。。。现在开票才五分之一] 别别别 要和平[引用 Kevin Lee：感觉很快就能核平台湾自由行了[捂脸]] 我必找你 我给女儿设计了一套去台湾读大学 然后我去台湾陪读加旅游的 人生计划 |
| candidate | 群聊_小宝今天请客了吗？.json#localId=59511 | 2024-01-13 15:09:10 | mention | ba0a30be5c | 目前选情如何[引用 在泳池小便是可耻行为：今天是不是我家赖宝要登基了？] |
| candidate | 群聊_小宝今天请客了吗？.json#localId=59121 | 2024-01-08 23:57:56 | mention | ba0a30be5c | 嗯 太贵我就不卖了[引用 在泳池小便是可耻行为：[链接]] |
| candidate | 群聊_小宝今天请客了吗？.json#localId=59094 | 2024-01-08 22:45:19 | mention | ba0a30be5c | 明天[引用 在泳池小便是可耻行为：连我的快乐之源便宜德都没了] |
| episode | ep_009993 | 2024-01-08 22:45:19 | mention | ba0a30be5c | 明天[引用 在泳池小便是可耻行为：连我的快乐之源便宜德都没了] 龙钞 如果要卖 市场价卖给我啊 我只抽了币 没抽钞 |
| candidate | 群聊_小宝今天请客了吗？.json#localId=58874 | 2024-01-06 00:35:03 | mention | ba0a30be5c | 恒源祥 羊羊羊[引用 在泳池小便是可耻行为：还有那个三羊牌，怎么想都是想映射恒源祥] |
| candidate | 私聊_1469.json#localId=27084 | 2024-01-05 21:25:01 | mention | 57ff771672 | 我晚会游戏 |

### 开车/驾照/自驾
| kind | ref | time | polarity | source_hash | snippet |
| --- | --- | --- | --- | --- | --- |
| candidate | 群聊_小宝今天请客了吗？.json#localId=51867 | 2023-04-17 10:47:55 | negative | ba0a30be5c | 你不会开车 |
| episode | ep_009829 | 2023-04-17 10:47:44 | negative | ba0a30be5c | 自驾啊 你不会开车 没事了 没事啊 这又不丢人 这又没啥的 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=131009 | 2025-08-18 21:52:50 | positive | 85cb21acd4 | 我这会开车 |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=19004 | 2023-01-10 12:24:46 | positive | 4848995fef | 或者找时间我去开车接你们 |
| episode | ep_010518 | 2023-01-10 12:24:35 | positive | 4848995fef | 全都邮寄 开车就不要来了 或者找时间我去开车接你们 没有运东西这件事 非常愚蠢 为什么要买餐具 开车就不要来 停车钱都够买餐具了 放家里 二年后带梅陇去 |
| candidate | 私聊_刘智.json#localId=430 | 2018-09-30 15:38:13 | positive | 6cd88e352b | 这样 我一会要开车了，我直接回邮件把。 |
| episode | ep_015036 | 2018-09-30 15:34:26 | positive | 6cd88e352b | 征稿活动是不是还是精准点好呢？ 全站是不是太大了。。。 他跟我说她要吧几个活动一起申请的 这里还是只有征稿啊 我问问他 [撇嘴]她又说是你负责的 这样 我一会要开车了，我直接回邮件把。 建议一个范围 应该是沟通岔了 没关系 [撇嘴]没对上 就这几个分区吧 可以的 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=151044 | 2026-04-10 00:21:44 | constraint | 85cb21acd4 | 附近的停车场 说小米车太宽了 不让进 |
| episode | ep_005518 | 2026-04-10 00:21:25 | constraint | 85cb21acd4 | 我肯定不会买 我上次去华山医院看病 找车位找了1小时 附近的停车场 说小米车太宽了 不让进 垃圾小米 |
| candidate | 私聊_刘智.json#localId=28249 | 2026-02-22 11:56:37 | constraint | 6cd88e352b | 这里停车场好像一共不到 10 个车位 |
| episode | ep_015888 | 2026-02-22 11:56:26 | constraint | 6cd88e352b | 哇 慢慢来不急 这里停车场好像一共不到 10 个车位 |
| episode | ep_013273 | 2026-02-11 17:25:22 | constraint | 57ff771672 | 直接出发 你打车去 我开车去 6.30 到 我不回来了 |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=55243 | 2025-11-17 20:38:18 | constraint | 4848995fef | 我们为什么要对出租车司机 快递员说谢谢 |
| episode | ep_010331 | 2025-11-17 20:36:05 | constraint | 4848995fef | 宝宝好啊 挺好的 爱在传递 宝宝现在的爱心 就是爸爸最认可的世界观 世界是一面镜子 你对他笑他就对你笑 你对他哭他就对你哭 所以为什么说爱笑的女人运气不会差呢 这个世界观 两个宝宝都应该学习 一生都会很幸福 我们为什么要对出租车司机 快递员说谢谢 也是因为这个原因 欺负人[引用… |
| candidate | 群聊_Z哥学习群.json#localId=17895 | 2025-10-13 15:52:27 | constraint | 2717e7d9ae | 司机该死 也不代表小米无责 |
| episode | ep_013811 | 2025-09-19 13:27:27 | constraint | 57ff771672 | 你别开车 打车去 不用啊 我跟朴素的 我很朴素 |

### 旅行规划
| kind | ref | time | polarity | source_hash | snippet |
| --- | --- | --- | --- | --- | --- |
| candidate | 群聊_小宝今天请客了吗？.json#localId=79100 | 2025-03-16 22:41:58 | positive | ba0a30be5c | deepseek帮我做的攻略 |
| candidate | 群聊_小宝今天请客了吗？.json#localId=78212 | 2025-02-11 13:40:35 | positive | ba0a30be5c | 你们上次让我定的酒店 |
| episode | ep_009474 | 2025-02-11 13:40:27 | positive | ba0a30be5c | 我没看见 我不配 你们上次让我定的酒店 我定的时候 500 现在涨到 1100 了 这是支撑我这这个月最开心的事 |
| candidate | 私聊_1469.json#localId=42090 | 2024-10-30 16:14:54 | positive | 57ff771672 | 那我定个下下周末机票 |
| episode | ep_013843 | 2024-10-30 16:14:46 | positive | 57ff771672 | 那就是还没拍照哦 那我定个下下周末机票 你能周五或者周一请假么 多玩一天 |
| candidate | 私聊_1469.json#localId=41733 | 2024-10-04 22:22:26 | positive | 57ff771672 | 我是不是要定机票了 |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=29063 | 2024-01-16 13:09:27 | positive | 4848995fef | 等公司给我定好酒店我发你 |
| episode | ep_010565 | 2024-01-16 13:07:07 | positive | 4848995fef | 我跟你说 我 2.2 去芜湖慰问员工 你可以 2.3 来芜湖接我一起回来 2.2 我们年会 要去各个分公司慰问员工 我选了个最近的就是想方便回来 正好时间也赶上了 等公司给我定好酒店我发你 |
| candidate | 私聊_1469.json#localId=18131 | 2023-08-07 17:56:05 | positive | 57ff771672 | 我来定酒店和火车 |
| episode | ep_013203 | 2023-08-07 17:55:59 | positive | 57ff771672 | 定了告诉我 我来定酒店和火车 这些我都知道了[引用 小lisa🐰：住丽豪酒店 就距离威尔斯亲王医院很近啊] 我后面要给你定一个月 所以这次去踩点 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=79907 | 2023-07-24 00:21:28 | positive | 85cb21acd4 | 我做了好久丽水的攻略 |
| episode | ep_006666 | 2023-07-24 00:19:14 | positive | 85cb21acd4 | 这是哪里啊 这么牛逼 杨家堂村去了么 我做了好久丽水的攻略 一直没去 书记自驾的么 |
| candidate | 群聊_小宝今天请客了吗？.json#localId=48846 | 2022-12-26 21:51:00 | positive | ba0a30be5c | 笑死[引用 葱油拌面＋：我是做攻略的朋友，她是给repo的朋友（然而我没去成一点发言权没有！] |
| episode | ep_009424 | 2022-12-26 21:40:33 | positive | ba0a30be5c | 苏苏是丽水的呀[引用 洗手高手：苏苏是，但她病了，你问，我们帮你谷歌一下，大家一起进步嘛] 丽水我以前问过 哈哈哈[引用 阿水：好吃 很顶 都是碳水] 谷歌能有答案[引用 洗手高手：苏苏是，但她病了，你问，我们帮你谷歌一下，大家一起进步嘛] 我早就查拉 都很会玩啊[引用 千喵喵… |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=11920 | 2022-03-02 15:25:20 | positive | 4848995fef | 我信用卡那个定酒店真的太便宜了 |
| candidate | 私聊_葉莎莎Lisa🐈.json#localId=29246 | 2020-12-21 11:24:54 | positive | 5279693b7c | 那我就定酒店 |

### 养宠/猫
| kind | ref | time | polarity | source_hash | snippet |
| --- | --- | --- | --- | --- | --- |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=60766 | 2026-02-15 14:05:11 | positive | 4848995fef | 放了[引用 老方：要不要把猫粮全部放入投喂机，以便猫按时按需进食] |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=52290 | 2025-10-09 20:06:30 | positive | 4848995fef | 我们家也就猫治得了他 |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=50348 | 2025-09-04 12:34:12 | positive | 4848995fef | 我这个同事养了十几只猫 |
| episode | ep_011404 | 2025-09-04 12:33:57 | positive | 4848995fef | 2000 配种 生了 4 只全留了[引用 小lisa🔮：多钱] 这是其中一只 我这个同事养了十几只猫 |
| candidate | 私聊_1469.json#localId=39447 | 2024-07-04 17:48:18 | positive | 57ff771672 | 我们家的猫 |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=34665 | 2024-07-04 15:35:24 | positive | 4848995fef | 猫粮不好就换 |
| episode | ep_011278 | 2024-07-04 15:34:46 | positive | 4848995fef | 怎么回事 别是中暑了 猫粮不好就换 那为什么不吃饭不拉屎啊 |
| candidate | 私聊_妈.json#localId=4161 | 2024-06-09 21:38:15 | positive | b0a139e5d6 | 然后表不挂 后面我还会继续买别的机器猫 |
| episode | ep_016032 | 2024-06-09 21:37:40 | positive | b0a139e5d6 | 你找人帮我打钉子吧[引用 🍁淡墨染香：儿子机器猫画很好看，挂起来] 两幅画都有钉子 都钉上 客厅里 然后表不挂 后面我还会继续买别的机器猫 如果不够 记得跟我讲[引用 🍁淡墨染香：还有你说买菜钱，其实你给过了，每个季度租房租金多给[amount]，等于每月买菜钱[amount]… |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=31273 | 2024-03-25 15:47:55 | positive | 4848995fef | 我们家猫咪？ |
| candidate | 私聊_1469.json#localId=25437 | 2023-12-14 14:30:25 | positive | 57ff771672 | 我还给他铲屎了 |
| episode | ep_012879 | 2023-12-14 14:27:05 | positive | 57ff771672 | 笑死[引用 小lisa🐰：猫都跟我不熟了] 别啊[引用 小lisa🐰：我现在吧客厅直接换了] 在启动很难的 你先改 20 把 我关系的呀 我还给他铲屎了 都正常的 尿和屎都有 今天早上 |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=27238 | 2023-11-25 15:48:46 | positive | 4848995fef | 被我妈欺负的[引用 老方：我们家猫咪的眼神好像是永远弱弱的] |
| candidate | 私聊_1469.json#localId=21540 | 2023-10-08 22:59:23 | positive | 57ff771672 | 猫粮在哪 |
| candidate | 私聊_葉莎莎Lisa🐈.json#localId=79803 | 2023-10-02 21:35:10 | positive | 5279693b7c | 没我们家猫可爱吧 |
| candidate | 私聊_1469.json#localId=20770 | 2023-09-23 15:40:35 | positive | 57ff771672 | 我去猫粮一下吧 |

### 育儿/家庭照护
| kind | ref | time | polarity | source_hash | snippet |
| --- | --- | --- | --- | --- | --- |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=65080 | 2026-05-29 13:32:40 | positive | 4848995fef | 天才[引用 老方：晚上，宝宝拉我去他们房间，让我在床边坐坐。奶奶不让我坐他们床上，宝宝见了于是拉着我的手出去搬了一把椅子进来让我坐（开始椅子是宝宝自己搬的，就是儿子买回的软椅）] |
| episode | ep_019570 | 2026-05-26 16:23:52 | positive | c7c727f781 | 这不就是我女儿嘛 11[引用 Qiuliang：看见孩子] |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=158187 | 2026-05-25 13:42:19 | positive | 85cb21acd4 | 还好我孩子不计划上公立 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=158179 | 2026-05-25 13:40:48 | positive | 85cb21acd4 | 什么孩子上学 家人看病 |
| episode | ep_006742 | 2026-05-25 13:37:10 | positive | 85cb21acd4 | 还是要报团科技才行 @[person] 找找财阀？ 什么孩子上学 家人看病 公司不行了么 还好我孩子不计划上公立 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=154930 | 2026-05-06 19:24:11 | positive | 85cb21acd4 | 现在看完全没法去幼儿园 |
| episode | ep_007737 | 2026-05-06 19:23:50 | positive | 85cb21acd4 | 刘老板这么超前啊？ 我还在为女儿延迟入园做准备 现在看完全没法去幼儿园 |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=63930 | 2026-04-21 17:59:28 | positive | 4848995fef | 我跟你说 孩子不是一定要社交的 |
| episode | ep_010916 | 2026-04-21 17:59:28 | positive | 4848995fef | 我跟你说 孩子不是一定要社交的 不要觉得这是什么问题 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=150635 | 2026-04-08 12:11:40 | positive | 85cb21acd4 | 懂[捂脸][引用 菜得不配说话：我那时候在抱娃] |
| episode | ep_007656 | 2026-04-08 12:10:33 | positive | 85cb21acd4 | 我都是 9.30 上的车 吃么大哥们 懂[捂脸][引用 菜得不配说话：我那时候在抱娃] |
| candidate | 群聊_一家亲 温柔对待彼此.json#localId=63138 | 2026-03-27 13:15:56 | positive | 4848995fef | 确实非常不利于消化，而且对孩子的身体、习惯、大脑发育都有一连串负面影响，很多家庭看似“省事”，其实代价很大。 一、为什么一边看视频一边吃饭，不利于消化？ 1. 大脑注意力被抢走，肠胃“摸鱼” 吃饭时注意力全在电视/手机上，大脑会减少对消化系统的调控： ◦ 唾液、胃液分泌变少 ◦… |
| episode | ep_007580 | 2026-03-22 13:46:23 | positive | 85cb21acd4 | 好耶[引用 Gdier：下回找个周末一起出来溜娃] 不过我们家女儿 还非常怕生人 牛逼啊[引用 张骏：沉浸作业不能自拔。。。] |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=146634 | 2026-03-14 22:43:37 | positive | 85cb21acd4 | 我刚哄娃睡觉 |
| episode | ep_005243 | 2026-03-12 20:43:42 | positive | 85cb21acd4 | 卧槽[引用 菜得不配说话：今天娃也见识命令行了] 太可爱了 我让我女儿帮我选过股票 我当时买了 [amount] 涨了 10% 卖了 也算是我女儿帮我赚的第一桶金了 |
| candidate | 私聊_1469.json#localId=59047 | 2026-03-11 13:21:08 | positive | 57ff771672 | 怎么上呢[引用 小lisa🔮：孩子如果长期不上幼儿园 和爷爷奶奶相看两厌 不懂如何游戏 那只会沉浸在pad和手机里] |

### AI/产品/组织工作
| kind | ref | time | polarity | source_hash | snippet |
| --- | --- | --- | --- | --- | --- |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=159895 | 2026-06-03 11:42:01 | positive | 85cb21acd4 | 花生产品实力非常强 但是很难推出去 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=159894 | 2026-06-03 11:41:55 | positive | 85cb21acd4 | 其实 ai时代 产品不难做 推广还是难 |
| episode | ep_004893 | 2026-06-03 11:39:47 | positive | 85cb21acd4 | 创不了 花生如果都搞不好 更别谈创业 花生能搞成 果断创业 睿总就是黄埔军校 其实 ai时代 产品不难做 推广还是难 花生产品实力非常强 但是很难推出去 这也是为啥 我说我要和毛老师先对清楚 你做的事本质到底是干嘛的 因为我想换位到你的角度 想想他该怎么推广 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=159773 | 2026-06-02 22:39:46 | positive | 85cb21acd4 | 忙碌了一天 终于把微信聊天记录 搞成模型可以读取的json格式了 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=159383 | 2026-05-30 22:10:51 | positive | 85cb21acd4 | 你就说歌会能不能 ai 替代吧 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=159271 | 2026-05-29 20:20:38 | positive | 85cb21acd4 | 哦哦 那个产品 |
| episode | ep_005088 | 2026-05-29 20:20:38 | positive | 85cb21acd4 | 哦哦 那个产品 我也没啊 是不是我们看着就清心寡欲 不对 应该是知道我无权无势 刘老板是清心寡欲 卧槽！[引用 Gdier：方总的妹子都跑去色诱毛老师了] [尴尬][引用 菜得不配说话：[链接]] |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=158970 | 2026-05-28 16:42:12 | positive | 85cb21acd4 | 还是产品最菜 |
| episode | ep_005694 | 2026-05-28 16:41:46 | positive | 85cb21acd4 | 你可能就被二师弟了[引用 张骏：19年劝毛老师跟我一起在无锡开个技术外包公司，开始发展第二曲线] 让公司只用你的外包 还是产品最菜 我都不知道怎么用公司赚钱 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=158624 | 2026-05-28 14:27:21 | positive | 85cb21acd4 | 虽然 ai 能提效 |
| episode | ep_005445 | 2026-05-28 14:26:55 | positive | 85cb21acd4 | 涨了兄弟们！ 我昨晚和腾讯的人吃饭 虽然 ai 能提效 但是为什么有的公司不裁员 有的公司裁员 因为毛利对 b 站重要 对腾讯不重要 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=158502 | 2026-05-27 15:31:12 | positive | 85cb21acd4 | 后来我想想 我们准备用 ai 时代的搞法 |
| episode | ep_005444 | 2026-05-27 15:30:38 | positive | 85cb21acd4 | 营销 leader 居然增值那边没有这种人才么 其实我最近也想要这种人 后来我想想 我们准备用 ai 时代的搞法 就不用旧时代的人了 |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=158408 | 2026-05-27 09:41:22 | positive | 85cb21acd4 | 目标价190-210 |
| episode | ep_004973 | 2026-05-27 09:40:37 | positive | 85cb21acd4 | 阳光电源！ 就是说他q2业绩反转 我听说的 目标价190-210 老板能带带我 别让我是群里最落后的一个 不对 我可以一直是最落后的一个 别让我落后大家太多 今天！ |
| candidate | 群聊_梯妹日常AI炒股打游戏.json#localId=158341 | 2026-05-26 18:54:28 | positive | 85cb21acd4 | 毛老师啥时候给我说说[引用 浪客剑心：本质上AI Native 组织，如何管理产品需求，产品知识库，以及 研发流的打通] |

## Manual Promotion Rules

1. 用户显式纠错 > 多次强证据 > 单次聊天提及。
2. 能力事实必须有直接表达，比如“我会/不会/不敢/没驾照”；仅出现行程、停车、司机、外卖，不等于能力。
3. 旅行、AI、工作等高频主题可以作为偏好或熟悉领域候选，但不要写成身份、职业或承诺。
4. 任何涉及家庭、公司、真实姓名、住址、健康和财务的事实，默认留在候选或关系层，不直接公开进 SelfCore。

