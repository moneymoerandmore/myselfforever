# 蒸馏前语料审计

- Generated: 2026-07-02T21:33:41
- Source outputs: `C:\Users\cloud\Documents\Codex\2026-06-03\skill\outputs`
- Privacy posture: report keeps episode IDs and score metadata only; chat text stays in the external JSONL artifacts.

## 结论

- Verdict: structurally ready for manual distillation sampling.
- Layer counts: core 7623; style 3903; counter 2931; background 5204.
- Duplicate episode IDs across layer files: 0.
- Rows missing `bucket_scores`: 0.
- Rows whose internal `bucket` mismatches file layer: 0.
- Rows with missing previous or next context: 2.
- `ep_010569` placement: found; score-resort core rank by three_views/thinking/message_count: 1.

## Layer Summary

| layer | rows | source_files | chat_kind | three_views_avg | three_views_p90 | thinking_avg |
| --- | --- | --- | --- | --- | --- | --- |
| core | 7623 | 16 | {'private': 2839, 'group': 4784} | 8.22 | 11.0 | 7.47 |
| style | 3903 | 16 | {'private': 1422, 'group': 2481} | 6.0 | 6.0 | 3.69 |
| counter | 2931 | 16 | {'private': 877, 'group': 2054} | 7.54 | 11.0 | 6.49 |
| background | 5204 | 16 | {'group': 3468, 'private': 1736} | 6.0 | 6.0 | 3.12 |

## Score Distributions

### core
| score | min | p50 | p90 | max | avg |
| --- | --- | --- | --- | --- | --- |
| three_views | 6 | 9.0 | 11.0 | 23 | 8.22 |
| worldview | 2 | 2.0 | 6.0 | 8 | 2.59 |
| lifeview | 1 | 2.0 | 5.0 | 8 | 2.38 |
| values | 1 | 2.0 | 5.0 | 8 | 3.25 |
| thinking | 4 | 7.0 | 11.0 | 11 | 7.47 |
| style | 3 | 7.0 | 8.0 | 10 | 6.61 |
| counter | 1 | 2.0 | 2.0 | 2 | 2.0 |

### style
| score | min | p50 | p90 | max | avg |
| --- | --- | --- | --- | --- | --- |
| three_views | 3 | 6.0 | 6.0 | 6 | 6.0 |
| worldview | 1 | 2.0 | 2.0 | 2 | 2.0 |
| lifeview | 1 | 2.0 | 2.0 | 4 | 2.0 |
| values | 1 | 2.0 | 2.0 | 2 | 2.0 |
| thinking | 1 | 4.0 | 5.0 | 5 | 3.69 |
| style | 6 | 7.0 | 10.0 | 10 | 7.81 |
| counter | 1 | 2.0 | 2.0 | 2 | 2.0 |

### counter
| score | min | p50 | p90 | max | avg |
| --- | --- | --- | --- | --- | --- |
| three_views | 6 | 6.0 | 11.0 | 21 | 7.54 |
| worldview | 2 | 2.0 | 5.0 | 8 | 2.45 |
| lifeview | 2 | 2.0 | 2.0 | 7 | 2.26 |
| values | 2 | 2.0 | 5.0 | 8 | 2.83 |
| thinking | 2 | 6.0 | 11.0 | 11 | 6.49 |
| style | 3 | 5.0 | 8.0 | 10 | 6.04 |
| counter | 7 | 7.0 | 7.0 | 7 | 7 |

### background
| score | min | p50 | p90 | max | avg |
| --- | --- | --- | --- | --- | --- |
| three_views | 3 | 6.0 | 6.0 | 6 | 6.0 |
| worldview | 1 | 2.0 | 2.0 | 2 | 2.0 |
| lifeview | 1 | 2.0 | 2.0 | 2 | 2.0 |
| values | 1 | 2.0 | 2.0 | 2 | 2.0 |
| thinking | 2 | 3.0 | 5.0 | 5 | 3.12 |
| style | 3 | 4.0 | 5.0 | 5 | 4.45 |
| counter | 1 | 2.0 | 2.0 | 2 | 2.0 |

## High Three-Views Core Sample

| episode_id | three_views | worldview | lifeview | values | thinking | message_count | avg_chars | max_single_chars | tags | source_hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ep_010569 | 23 | 7 | 8 | 8 | 7 | 7 | 9.9 | 15 | style,conflict | 4848995fef |
| ep_010292 | 22 | 7 | 8 | 7 | 10 | 41 | 11.7 | 44 | style,explanation | 4848995fef |
| ep_014564 | 21 | 7 | 7 | 7 | 11 | 95 | 12.9 | 54 | style,planning,explanation,conflict,taste,decision | 6cd88e352b |
| ep_015008 | 21 | 8 | 6 | 7 | 8 | 15 | 35.9 | 245 | style | 6cd88e352b |
| ep_013095 | 21 | 7 | 8 | 6 | 8 | 7 | 8.6 | 14 | style | 57ff771672 |
| ep_003047 | 20 | 7 | 6 | 7 | 7 | 16 | 10.1 | 21 | style,taste | c720b9e4ae |
| ep_003019 | 19 | 7 | 7 | 5 | 10 | 31 | 10.4 | 28 | style,conflict,decision,explanation | c720b9e4ae |
| ep_008941 | 19 | 7 | 7 | 5 | 10 | 9 | 9.3 | 17 | style,planning,decision | 0225fc76e3 |
| ep_004632 | 19 | 7 | 5 | 7 | 10 | 4 | 26.3 | 55 | decision,style | 85cb21acd4 |
| ep_000973 | 19 | 8 | 6 | 5 | 8 | 11 | 18.5 | 120 | style,conflict | acb4e1dc73 |
| ep_014576 | 18 | 7 | 6 | 5 | 11 | 46 | 9.9 | 43 | style,explanation,decision,taste | 6cd88e352b |
| ep_000402 | 18 | 7 | 6 | 5 | 11 | 31 | 10.7 | 60 | style,decision,planning,explanation | acb4e1dc73 |

## Key Episode Check

| episode_id | bucket | line_no | three_views | worldview | lifeview | values | thinking | message_count | tags | source_hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ep_010569 | core | 3 | 23 | 7 | 8 | 8 | 7 | 7 | style,conflict | 4848995fef |

## Boundary Flags

| flag | rows | by_layer |
| --- | --- | --- |
| core_low_three_views | 6147 | {'core': 6147} |
| background_high_three_views | 0 | {} |
| style_high_three_views | 0 | {} |
| counter_high_three_views | 42 | {'counter': 42} |
| copylike_or_long_burst | 99 | {'core': 56, 'style': 7, 'counter': 13, 'background': 23} |
| very_large_burst | 5 | {'core': 1, 'counter': 4} |

## Flag Samples

### core_low_three_views
| episode_id | bucket | three_views | thinking | style | counter | message_count | avg_chars | max_single_chars | tags | source_hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ep_003763 | core | 9 | 10 | 8 | 2 | 69 | 7.6 | 27 | style,conflict,explanation | 97344f42f6 |
| ep_012981 | core | 9 | 11 | 8 | 2 | 42 | 6.9 | 24 | style,planning,conflict | 57ff771672 |
| ep_016221 | core | 9 | 11 | 8 | 2 | 42 | 7.7 | 19 | style,taste,decision,explanation | 5279693b7c |
| ep_014587 | core | 9 | 11 | 8 | 2 | 38 | 9.3 | 38 | style,conflict,planning,taste,decision,explanation | 6cd88e352b |
| ep_000399 | core | 9 | 8 | 8 | 2 | 36 | 7 | 17 | style,taste | acb4e1dc73 |
| ep_016223 | core | 9 | 11 | 8 | 2 | 34 | 8 | 20 | style,decision,planning,conflict,explanation | 5279693b7c |
| ep_003963 | core | 9 | 11 | 8 | 2 | 33 | 10.5 | 34 | style,decision | 85cb21acd4 |
| ep_014596 | core | 9 | 11 | 8 | 2 | 33 | 8.1 | 25 | style,decision | 6cd88e352b |
| ep_014598 | core | 9 | 11 | 8 | 2 | 32 | 9.8 | 16 | style,decision,conflict,explanation | 6cd88e352b |
| ep_014599 | core | 9 | 11 | 8 | 2 | 32 | 8.8 | 20 | style,explanation,conflict | 6cd88e352b |
| ep_004767 | core | 9 | 8 | 10 | 2 | 32 | 8.2 | 24 | style | 85cb21acd4 |
| ep_014602 | core | 9 | 8 | 8 | 2 | 31 | 8.4 | 22 | style,conflict,taste | 6cd88e352b |

### background_high_three_views
- None.

### style_high_three_views
- None.

### counter_high_three_views
| episode_id | bucket | three_views | thinking | style | counter | message_count | avg_chars | max_single_chars | tags | source_hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ep_010291 | counter | 21 | 10 | 8 | 7 | 50 | 11.6 | 62 | style,reflection,explanation,decision,conflict | 4848995fef |
| ep_018642 | counter | 20 | 11 | 8 | 7 | 48 | 9.3 | 32 | style,taste,explanation,decision,planning,conflict | c7c727f781 |
| ep_000401 | counter | 19 | 11 | 8 | 7 | 33 | 9.9 | 29 | style,conflict,reflection,explanation | acb4e1dc73 |
| ep_010293 | counter | 19 | 10 | 8 | 7 | 32 | 16.5 | 47 | taste,style,planning,conflict,explanation | 4848995fef |
| ep_008900 | counter | 19 | 10 | 8 | 7 | 20 | 6.5 | 21 | style,taste,decision,explanation,conflict | 0225fc76e3 |
| ep_003056 | counter | 19 | 10 | 5 | 7 | 14 | 8.8 | 18 | style,explanation,reflection | c720b9e4ae |
| ep_009452 | counter | 19 | 10 | 8 | 7 | 8 | 12.8 | 22 | explanation,style,planning,decision,taste | ba0a30be5c |
| ep_000671 | counter | 19 | 8 | 8 | 7 | 7 | 12.9 | 34 | style,reflection,conflict | acb4e1dc73 |
| ep_000855 | counter | 19 | 7 | 8 | 7 | 4 | 21.8 | 58 | style,reflection | acb4e1dc73 |
| ep_003016 | counter | 18 | 10 | 8 | 7 | 37 | 11.8 | 35 | style,conflict,decision,planning,explanation,reflection | c720b9e4ae |
| ep_003021 | counter | 18 | 10 | 8 | 7 | 23 | 18.1 | 152 | style,reflection,conflict,taste,explanation | c720b9e4ae |
| ep_004042 | counter | 18 | 11 | 8 | 7 | 18 | 16.6 | 37 | style,conflict,reflection,decision,explanation,planning | 85cb21acd4 |

### copylike_or_long_burst
| episode_id | bucket | three_views | thinking | style | counter | message_count | avg_chars | max_single_chars | tags | source_hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ep_015008 | core | 21 | 8 | 8 | 2 | 15 | 35.9 | 245 | style | 6cd88e352b |
| ep_000944 | core | 17 | 10 | 8 | 2 | 15 | 24.8 | 267 | style,planning,conflict | acb4e1dc73 |
| ep_000011 | core | 16 | 10 | 7 | 2 | 7 | 72.6 | 332 | decision,explanation,taste,style | 945e3007a0 |
| ep_004011 | counter | 15 | 11 | 8 | 7 | 21 | 35.5 | 339 | style,conflict,explanation,decision,reflection | 85cb21acd4 |
| ep_016092 | core | 15 | 8 | 8 | 2 | 7 | 52.7 | 322 | style,planning,taste | b0a139e5d6 |
| ep_003658 | core | 15 | 4 | 3 | 2 | 2 | 61.5 | 112 | style | c720b9e4ae |
| ep_015969 | counter | 14 | 10 | 8 | 7 | 62 | 10.4 | 192 | style,explanation,conflict,reflection | b0a139e5d6 |
| ep_000414 | counter | 14 | 11 | 8 | 7 | 22 | 20.8 | 205 | style,decision,explanation,reflection,taste | acb4e1dc73 |
| ep_018083 | core | 14 | 8 | 4 | 2 | 3 | 57.7 | 145 | style,explanation | 5279693b7c |
| ep_003832 | core | 14 | 9 | 4 | 2 | 2 | 54.5 | 84 | style,explanation | 97344f42f6 |
| ep_008103 | core | 14 | 5 | 3 | 2 | 2 | 83 | 155 | style | 85cb21acd4 |
| ep_015860 | core | 14 | 5 | 3 | 2 | 2 | 79.5 | 151 | style | 6cd88e352b |

### very_large_burst
| episode_id | bucket | three_views | thinking | style | counter | message_count | avg_chars | max_single_chars | tags | source_hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ep_014564 | core | 21 | 11 | 8 | 2 | 95 | 12.9 | 54 | style,planning,explanation,conflict,taste,decision | 6cd88e352b |
| ep_018641 | counter | 17 | 11 | 8 | 7 | 103 | 8.6 | 59 | style,explanation,taste,decision,reflection,conflict | c7c727f781 |
| ep_012788 | counter | 16 | 11 | 8 | 7 | 130 | 6.9 | 16 | style,conflict,explanation,taste,planning,reflection | 57ff771672 |
| ep_014562 | counter | 15 | 11 | 8 | 7 | 109 | 9.2 | 24 | style,conflict,taste,explanation,decision,planning | 6cd88e352b |
| ep_014563 | counter | 11 | 11 | 8 | 7 | 96 | 9.8 | 21 | style,reflection,explanation,planning,conflict | 6cd88e352b |

## Suggested Manual Review Order

1. Read the high three-views core sample first, especially worldview/lifeview/values-balanced episodes.
2. Review `very_large_burst` and `copylike_or_long_burst` before using them as expression DNA.
3. Inspect `background_high_three_views`; promote only if the self burst contains a stable value judgment rather than context.
4. Use style episodes for rhythm and interaction mechanics, not for copying one-off words or private nicknames.
5. Use counter episodes to define guardrails: uncertainty, over-force, conflict, and non-auto-send boundaries.

