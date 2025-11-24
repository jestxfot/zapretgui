from ..constants import LABEL_RECOMMENDED, LABEL_GAME, LABEL_CAUTION, LABEL_EXPERIMENTAL, LABEL_STABLE, LABEL_WARP
from config import BIN_FOLDER

BASE_ARG = "--filter-tcp=80,443 --filter-l7=tls --ipset=ipset-rutracker.txt"

# Стратегии для остальных сайтов
RUTRACKER_TCP_STRATEGIES = {
    # ============================================================
    # ПРОСТЫЕ СТРАТЕГИИ
    # ============================================================
    
    "multisplit_split_pos_1": {
        "name": "Multisplit позиция 1",
        "description": "Простая резка на первом байте",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multisplit:pos=1"""
    },
    
    "datanoack": {
        "name": "DataNoAck",
        "description": "Убирает ACK флаг из пакетов",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=pktmod:tcp_flags_unset=ack"""
    },
    
    "multisplit_datanoack": {
        "name": "Multisplit + DataNoAck",
        "description": "Резка на позиции 2 с убиранием ACK",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multisplit:pos=2:tcp_flags_unset=ack"""
    },
    
    "multisplit_datanoack_split_pos_1": {
        "name": "Multisplit pos1 + DataNoAck",
        "description": "Резка на позиции 1 с убиранием ACK",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multisplit:pos=1:tcp_flags_unset=ack"""
    },
    
    # ============================================================
    # FAKE + FAKEDSPLIT
    # ============================================================
    
    "other_fakedsplit_ttl2": {
        "name": "Fake + Fakedsplit TTL=2",
        "description": "Точный перевод оригинала (нулевой паттерн)",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:ip_ttl=2:ip6_ttl=2:tls_mod=rnd,rndsni,dupsid --lua-desync=fakedsplit:pos=1:ip_ttl=2:ip6_ttl=2"""
    },
    
    "other_fakedsplit_ttl2_optimized": {
        "name": "Fake + Fakedsplit TTL=2 (Optimized)",
        "description": "rnd+rndsni при старте, dupsid на лету",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-init="fake_tls_custom = tls_mod(fake_default_tls,'rnd,rndsni')" --lua-desync=fake:blob=fake_tls_custom:ip_ttl=2:ip6_ttl=2:tls_mod=dupsid --lua-desync=fakedsplit:pos=1:ip_ttl=2:ip6_ttl=2"""
    },
    
    # ============================================================
    # DUP + SEQOVL
    # ============================================================
    
    "multisplit_226_seqovl_file": {
        "name": "Multisplit SeqOvl 226 (File)",
        "description": "С загрузкой TLS из файла",
        "author": "hz",
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d1 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=multisplit:seqovl=226:seqovl_pattern=tls_google"""
    },
    
    "multisplit_226_seqovl_dynamic": {
        "name": "Multisplit SeqOvl 226 (Dynamic)",
        "description": "Генерация TLS на лету",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--lua-init="tls_google = tls_mod(fake_default_tls,'sni=www.google.com')" {BASE_ARG} --payload=tls_client_hello --out-range=-d1 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=multisplit:seqovl=226:seqovl_pattern=tls_google"""
    },
    "original_bolvan_v2_badsum_max": {
        "name": "Мессенджер Max",
        "description": "Fake (6 повторов) + Multidisorder на позициях 1,midsld",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:tcp_ack=-66000:repeats=6:tls_mod=rnd,dupsid,sni=web.max.ru --lua-desync=multidisorder:pos=1,midsld"""
    },
    "original_bolvan_v2_badsum_max_2": {
        "name": "Мессенджер Max v2",
        "description": "Fake (6 повторов) + Multidisorder на позициях 1,midsld",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:tcp_ack=-66000:repeats=6:tls_mod=rnd,dupsid,sni=web.max.ru --lua-desync=multidisorder:pos=1,midsld:tcp_ack=-66000"""
    },
    "original_bolvan_v2_badsum_max_optimized": {
        "name": "Мессенджер Max (Optimized)",
        "description": "Оптимизированная версия с генерацией SNI при старте",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-init="fake_max = tls_mod(fake_default_tls,'rnd,sni=web.max.ru')" --lua-desync=fake:blob=fake_max:tcp_ack=-66000:repeats=6:tls_mod=dupsid --lua-desync=multidisorder:pos=1,midsld"""
    },
    "YTDisBystro_34_v1": {
        "name": "YTDisBystro 3.4 v1 (all ports)",
        "description": "Multisplit с overlap 211 байт (паттерн из tls_clienthello_5.bin)",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--blob=bin_tls5:@{BIN_FOLDER}\\tls_clienthello_5.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multisplit:seqovl=211:seqovl_pattern=bin_tls5"""
    },
    "YTDisBystro_34_v1_dynamic": {
        "name": "YTDisBystro 3.4 v1 Dynamic (all ports)",
        "description": "Multisplit с overlap 211 байт (динамическая генерация)",
        "author": "hz",
        "label": None,
        "args": f"""--lua-init="bin_tls5 = tls_mod(fake_default_tls,'rnd')" {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multisplit:seqovl=211:seqovl_pattern=bin_tls5"""
    },
    "other_seqovl": {
        "name": "Multidisorder seqovl 211 & pattern 5",
        "description": "Multidisorder (обратный порядок) с overlap 211 байт",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--blob=bin_tls5:@{BIN_FOLDER}\\tls_clienthello_5.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multidisorder:seqovl=211:seqovl_pattern=bin_tls5"""
    },
    "multisplit_286_pattern": {
        "name": "YTDisBystro 3.4 v2 (1)",
        "description": "Multisplit с overlap 286 + дублирование первых 3 пакетов",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls11:@{BIN_FOLDER}\\tls_clienthello_11.bin {BASE_ARG} --payload=tls_client_hello --out-range=-n3 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=multisplit:seqovl=286:seqovl_pattern=bin_tls11"""
    },
    "multisplit_226_pattern_18": {
        "name": "Multisplit seqovl 226 (pattern 18)",
        "description": "Multisplit с overlap 226 + дублирование первых 3 пакетов",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls18:@{BIN_FOLDER}\\tls_clienthello_18.bin {BASE_ARG} --payload=tls_client_hello --out-range=-n3 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=multisplit:seqovl=226:seqovl_pattern=bin_tls18"""
    },
    "multisplit_sniext_midsld_18": {
        "name": "Multisplit sniext+1,midsld (fixed overlap)",
        "description": "Резка на позициях sniext+1 и midsld, overlap 3 байта (вместо midsld-1)",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multisplit:pos=sniext+1,midsld:seqovl=3""",
    },
    "multisplit_sniext_midsld": {
        "name": "Multisplit sniext+1,midsld",
        "description": "Резка на позициях sniext+1 и midsld (без overlap или с фиксированным)",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multisplit:pos=sniext+1,midsld"""
    },
    "multisplit_308_pattern": {
        "name": "Multisplit seqovl 308 (pattern 9)",
        "description": "Multisplit с overlap 308 + дублирование первых 3 пакетов",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls9:@{BIN_FOLDER}\\tls_clienthello_9.bin {BASE_ARG} --payload=tls_client_hello --out-range=-n3 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=multisplit:seqovl=308:seqovl_pattern=bin_tls9"""
    },
    "googlevideo_fakeddisorder_datanoack_1": {
        "name": "GoogleVideo FakedDisorder datanoack",
        "description": "Fake (4 нуля) + FakedDisorder на midsld с datanoack",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=0x00000000:tcp_flags_unset=ack --lua-desync=fakeddisorder:pos=midsld:tcp_flags_unset=ack"""
    },
    "googlevideo_fakeddisorder_datanoack_tls": {
        "name": "GoogleVideo FakedDisorder datanoack (TLS)",
        "description": "Fake (TLS) + FakedDisorder с datanoack",
        "author": None,
        "label": None,  # Экспериментальный
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:tcp_flags_unset=ack --lua-desync=fakeddisorder:pos=midsld:tcp_flags_unset=ack"""
    },
    "tcpseg_211_simple": {
        "name": "SeqOvl 211 (Simple, No Split)",
        "description": "Только overlap 211 байт, без резки и дублирования",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls5:@{BIN_FOLDER}\\tls_clienthello_5.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=211:seqovl_pattern=bin_tls5"""
    },

    "tcpseg_226_simple": {
        "name": "SeqOvl 226 (Simple, No Split)",
        "description": "Только overlap 226 байт, без резки и дублирования",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls18:@{BIN_FOLDER}\\tls_clienthello_18.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=226:seqovl_pattern=bin_tls18"""
    },

    "tcpseg_286_simple": {
        "name": "SeqOvl 286 (Simple, No Split)",
        "description": "Только overlap 286 байт, без резки и дублирования",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls11:@{BIN_FOLDER}\\tls_clienthello_11.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=286:seqovl_pattern=bin_tls11"""
    },

    "tcpseg_308_simple": {
        "name": "SeqOvl 308 (Simple, No Split)",
        "description": "Только overlap 308 байт, без резки и дублирования",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls9:@{BIN_FOLDER}\\tls_clienthello_9.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=308:seqovl_pattern=bin_tls9"""
    },
    # ============================================================
    # TCPSEG: SEQOVL + DUP (БЕЗ РЕЗКИ)
    # ============================================================

    "tcpseg_211_dup_d1": {
        "name": "SeqOvl 211 + Dup (No Split)",
        "description": "Overlap 211 + дублирование 1-го пакета, БЕЗ резки",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls5:@{BIN_FOLDER}\\tls_clienthello_5.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d1 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=211:seqovl_pattern=bin_tls5"""
    },

    "tcpseg_226_dup_d1": {
        "name": "SeqOvl 226 + Dup (No Split)",
        "description": "Overlap 226 + дублирование 1-го пакета, БЕЗ резки",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls18:@{BIN_FOLDER}\\tls_clienthello_18.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d1 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=226:seqovl_pattern=bin_tls18"""
    },

    "tcpseg_226_dup_n3": {
        "name": "SeqOvl 226 + Dup n3 (No Split)",
        "description": "Overlap 226 + дублирование первых 3 пакетов, БЕЗ резки",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls18:@{BIN_FOLDER}\\tls_clienthello_18.bin {BASE_ARG} --payload=tls_client_hello --out-range=-n3 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=226:seqovl_pattern=bin_tls18"""
    },

    "tcpseg_286_dup_n3": {
        "name": "SeqOvl 286 + Dup n3 (No Split)",
        "description": "Overlap 286 + дублирование первых 3 пакетов, БЕЗ резки",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls11:@{BIN_FOLDER}\\tls_clienthello_11.bin {BASE_ARG} --payload=tls_client_hello --out-range=-n3 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=286:seqovl_pattern=bin_tls11"""
    },

    "tcpseg_308_dup_n3": {
        "name": "SeqOvl 308 + Dup n3 (No Split)",
        "description": "Overlap 308 + дублирование первых 3 пакетов, БЕЗ резки",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls9:@{BIN_FOLDER}\\tls_clienthello_9.bin {BASE_ARG} --payload=tls_client_hello --out-range=-n3 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=308:seqovl_pattern=bin_tls9"""
    },
    # ============================================================
    # TCPSEG: ДИНАМИЧЕСКИЕ (БЕЗ ФАЙЛОВ)
    # ============================================================

    "tcpseg_226_google_simple": {
        "name": "SeqOvl 226 Google (Simple, No Split)",
        "description": "Overlap 226 с Google SNI, без резки и дублирования",
        "author": "hz",
        "label": LABEL_RECOMMENDED,  # Рекомендуется - не требует файлов
        "args": f"""--lua-init="tls_google = tls_mod(fake_default_tls,'sni=www.google.com')" {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=226:seqovl_pattern=tls_google"""
    },

    "tcpseg_226_google_dup_d1": {
        "name": "SeqOvl 226 Google + Dup (No Split)",
        "description": "Overlap 226 с Google SNI + дублирование 1-го пакета, БЕЗ резки",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""--lua-init="tls_google = tls_mod(fake_default_tls,'sni=www.google.com')" {BASE_ARG} --payload=tls_client_hello --out-range=-d1 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=226:seqovl_pattern=tls_google"""
    },

    "tcpseg_226_google_dup_n3": {
        "name": "SeqOvl 226 Google + Dup n3 (No Split)",
        "description": "Overlap 226 с Google SNI + дублирование первых 3 пакетов, БЕЗ резки",
        "author": "hz",
        "label": None,
        "args": f"""--lua-init="tls_google = tls_mod(fake_default_tls,'sni=www.google.com')" {BASE_ARG} --payload=tls_client_hello --out-range=-n3 --lua-desync=send:repeats=2 --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=226:seqovl_pattern=tls_google"""
    },

    # ============================================================
    # TCPSEG: С FOOLING
    # ============================================================

    "tcpseg_226_datanoack": {
        "name": "SeqOvl 226 + DataNoAck (No Split)",
        "description": "Overlap 226 с убиранием ACK флага, БЕЗ резки",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls18:@{BIN_FOLDER}\\tls_clienthello_18.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=226:seqovl_pattern=bin_tls18:tcp_flags_unset=ack"""
    },

    "tcpseg_226_ttl": {
        "name": "SeqOvl 226 + TTL (No Split)",
        "description": "Overlap 226 с TTL=5, БЕЗ резки",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls18:@{BIN_FOLDER}\\tls_clienthello_18.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=226:seqovl_pattern=bin_tls18:ip_ttl=5:ip6_ttl=5"""
    },

    "tcpseg_226_badseq": {
        "name": "SeqOvl 226 + BadSeq (No Split)",
        "description": "Overlap 226 с badseq, БЕЗ резки",
        "author": "hz",
        "label": None,
        "args": f"""--blob=bin_tls18:@{BIN_FOLDER}\\tls_clienthello_18.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=226:seqovl_pattern=bin_tls18:tcp_ack=-66000"""
    },

    # ============================================================
    # GOOGLEVIDEO СТРАТЕГИИ
    # ============================================================

    "googlevideo_fakedsplit": {
        "name": "GoogleVideo FakedSplit badseq",
        "description": "FakedSplit × 10 повторов, badseq, TTL=4",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fakedsplit:pos=1:tcp_ack=-66000:repeats=10:ip_ttl=4:ip6_ttl=4"""
    },

    "googlevideo_fakeddisorder_datanoack": {
        "name": "GoogleVideo FakedDisorder datanoack",
        "description": "Fake (4 нуля) + FakedDisorder на midsld с datanoack",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=0x00000000:tcp_flags_unset=ack --lua-desync=fakeddisorder:pos=midsld:tcp_flags_unset=ack"""
    },

    "googlevideo_fakedsplit_lite": {
        "name": "GoogleVideo FakedSplit badseq (Lite)",
        "description": "FakedSplit × 6 повторов (экономия трафика)",
        "author": None,
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fakedsplit:pos=1:tcp_ack=-66000:repeats=6:ip_ttl=4:ip6_ttl=4"""
    },

    # ============================================================
    # GOOGLEVIDEO СТРАТЕГИИ
    # ============================================================

    "googlevideo_split": {
        "name": "GoogleVideo Split cutoff d2",
        "description": "Split × 10 повторов, badseq, TTL=4, только первые 2 пакета",
        "author": None,
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d2 --lua-desync=multisplit:pos=1:tcp_ack=-66000:repeats=10:ip_ttl=4:ip6_ttl=4"""
    },

    "googlevideo_fakedsplit": {
        "name": "GoogleVideo FakedSplit badseq",
        "description": "FakedSplit × 10 повторов (к фейкам), badseq, TTL=4",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fakedsplit:pos=1:tcp_ack=-66000:repeats=10:ip_ttl=4:ip6_ttl=4"""
    },

    "googlevideo_fakeddisorder_datanoack": {
        "name": "GoogleVideo FakedDisorder datanoack",
        "description": "Fake (4 нуля) + FakedDisorder на midsld с datanoack",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=0x00000000:tcp_flags_unset=ack --lua-desync=fakeddisorder:pos=midsld:tcp_flags_unset=ack"""
    },

    "googlevideo_split_lite": {
        "name": "GoogleVideo Split cutoff (Lite)",
        "description": "Split × 6 повторов (экономия), cutoff d2",
        "author": None,
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d2 --lua-desync=multisplit:pos=1:tcp_ack=-66000:repeats=6:ip_ttl=4:ip6_ttl=4"""
    },
    "googlevideo_multidisorder": {
        "name": "GoogleVideo MultiDisorder Complex",
        "description": "Сложная стратегия MultiDisorder с 8 частями в обратном порядке, seqovl=1",
        "author": None,
        "label": LABEL_STABLE,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multidisorder:pos=1,host+2,sld+2,sld+5,sniext+1,sniext+2,endhost-2:seqovl=1"""
    },
    "googlevideo_multidisorder_simple": {
        "name": "GoogleVideo MultiDisorder (Simple)",
        "description": "MultiDisorder с 3 позициями (4 части)",
        "author": None,
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multidisorder:pos=1,midsld,endhost-2:seqovl=1"""
    },
    "googlevideo_multidisorder_pattern": {
        "name": "GoogleVideo MultiDisorder (Pattern)",
        "description": "MultiDisorder с TLS паттерном в overlap",
        "author": None,
        "label": None,
        "args": f"""--blob=bin_tls5:@{BIN_FOLDER}\\tls_clienthello_5.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multidisorder:pos=1,host+2,sld+2,sld+5,sniext+1,sniext+2,endhost-2:seqovl=211:seqovl_pattern=bin_tls5"""
    },
    "googlevideo_multisplit_pattern": {
        "name": "GoogleVideo MultiSplit Pattern 7",
        "description": "MultiSplit с 3 частями (pos 2,midsld-2), seqovl=1, паттерн из bin_tls7",
        "author": None,
        "label": None,
        "args": f"""--blob=bin_tls7:@{BIN_FOLDER}\\tls_clienthello_7.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multisplit:pos=2,midsld-2:seqovl=1:seqovl_pattern=bin_tls7"""
    },

    # ============================================================
    # GOOGLEVIDEO FAKEDDISORDER СТРАТЕГИИ
    # ============================================================

    "googlevideo_fakeddisorder_datanoack": {
        "name": "GoogleVideo FakedDisorder datanoack",
        "description": "Fake (4 нуля) + FakedDisorder на midsld с datanoack",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=0x00000000:tcp_flags_unset=ack --lua-desync=fakeddisorder:pos=midsld:tcp_flags_unset=ack"""
    },

    "googlevideo_fakeddisorder": {
        "name": "GoogleVideo FakedDisorder AutoTTL",
        "description": "FakedDisorder с паттерном bin_tls7, seqovl=1, badseq, autottl",
        "author": None,
        "label": None,
        "args": f"""--blob=bin_tls7:@{BIN_FOLDER}\\tls_clienthello_7.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fakeddisorder:pos=2,midsld-2:pattern=bin_tls7:seqovl=1:tcp_ack=-66000:ip_autottl=0,3-20:ip6_autottl=0,3-20"""
    },

    # ============================================================
    # GOOGLEVIDEO FAKEDSPLIT СТРАТЕГИИ
    # ============================================================

    "googlevideo_fakedsplit": {
        "name": "GoogleVideo FakedSplit badseq",
        "description": "FakedSplit × 10 повторов, badseq, TTL=4 (фиксированный)",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fakedsplit:pos=1:tcp_ack=-66000:repeats=10:ip_ttl=4:ip6_ttl=4"""
    },

    "googlevideo_fakedsplit_simple": {
        "name": "GoogleVideo FakedSplit Simple",
        "description": "FakedSplit × 8 повторов, badseq, AutoTTL (адаптивный)",
        "author": None,
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fakedsplit:pos=1:tcp_ack=-66000:repeats=8:ip_autottl=0,3-20:ip6_autottl=0,3-20"""
    },

    "googlevideo_fakedsplit_lite": {
        "name": "GoogleVideo FakedSplit Simple (Lite)",
        "description": "FakedSplit × 6 повторов (экономия трафика)",
        "author": None,
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fakedsplit:pos=1:tcp_ack=-66000:repeats=6:ip_autottl=0,3-20:ip6_autottl=0,3-20"""
    },

    # ============================================================
    # GOOGLEVIDEO SPLIT СТРАТЕГИИ
    # ============================================================

    "googlevideo_split": {
        "name": "GoogleVideo Split cutoff d2",
        "description": "Split × 10 повторов, badseq, TTL=4, cutoff d2",
        "author": None,
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d2 --lua-desync=multisplit:pos=1:tcp_ack=-66000:repeats=10:ip_ttl=4:ip6_ttl=4"""
    },

    "googlevideo_split_aggressive": {
        "name": "GoogleVideo Split Aggressive",
        "description": "Split × 15 повторов, badseq, TTL=3, cutoff d3 (АГРЕССИВНАЯ)",
        "author": None,
        "label": LABEL_CAUTION,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d3 --lua-desync=multisplit:pos=1:tcp_ack=-66000:repeats=15:ip_ttl=3:ip6_ttl=3"""
    },

    # ============================================================
    # GOOGLEVIDEO MULTIDISORDER СТРАТЕГИИ
    # ============================================================

    "googlevideo_multidisorder": {
        "name": "GoogleVideo MultiDisorder Complex",
        "description": "Сложная стратегия с 8 частями (старая YouTube)",
        "author": None,
        "label": LABEL_STABLE,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multidisorder:pos=1,host+2,sld+2,sld+5,sniext+1,sniext+2,endhost-2:seqovl=1"""
    },

    "googlevideo_multidisorder_midsld": {
        "name": "GoogleVideo MultiDisorder MidSLD",
        "description": "MultiDisorder с 3 частями (midsld,midsld+2), × 10 повторов",
        "author": None,
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multidisorder:pos=midsld,midsld+2:seqovl=1:tcp_ack=-66000:repeats=10"""
    },

    # ============================================================
    # TCPSEG + DROP: SEQOVL БЕЗ РЕЗКИ (С ДРОПОМ ОРИГИНАЛА)
    # ============================================================


    "tcpseg_211_simple_drop": {
        "name": "SeqOvl 211 Simple (с drop)",
        "description": "Overlap 211 байт, без резки, с дропом оригинала",
        "args": f"""--blob=bin_tls5:@{BIN_FOLDER}\\tls_clienthello_5.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=211:seqovl_pattern=bin_tls5 --lua-desync=drop:payload=known"""
    },
    
    "tcpseg_226_google_drop": {
        "name": "SeqOvl 226 Google (с drop)",
        "description": "Overlap 226 байт с Google SNI, с дропом оригинала",
        "args": f"""--lua-init="tls_google = tls_mod(fake_default_tls,'sni=www.google.com')" {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=226:seqovl_pattern=tls_google --lua-desync=drop:payload=known"""
    },
    
    "tcpseg_286_drop": {
        "name": "SeqOvl 286 (с drop)",
        "description": "Overlap 286 байт, с дропом оригинала",
        "args": f"""--blob=bin_tls11:@{BIN_FOLDER}\\tls_clienthello_11.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=tcpseg:pos=0,-1:seqovl=286:seqovl_pattern=bin_tls11 --lua-desync=drop:payload=known"""
    },

    # ============================================================
    # FAKE + MULTISPLIT КОМБО
    # ============================================================

    "googlevideo_fake_multisplit": {
        "name": "GoogleVideo Fake+MultiSplit",
        "description": "Fake (Google TLS, badseq) + MultiSplit 3 части (1,sld+1, badseq)",
        "author": None,
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:tcp_ack=-66000 --lua-desync=multisplit:pos=1,sld+1:seqovl=1:tcp_ack=-66000"""
    },

    "googlevideo_fake_multisplit_no_ovl": {
        "name": "GoogleVideo Fake+MultiSplit (No Overlap)",
        "description": "Fake + MultiSplit без overlap",
        "author": None,
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:tcp_ack=-66000 --lua-desync=multisplit:pos=1,sld+1:tcp_ack=-66000"""
    },

    "googlevideo_fake_multisplit_repeats": {
        "name": "GoogleVideo Fake+MultiSplit (Fake×3)",
        "description": "Fake × 3 повтора + MultiSplit",
        "author": None,
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:tcp_ack=-66000:repeats=3 --lua-desync=multisplit:pos=1,sld+1:seqovl=1:tcp_ack=-66000"""
    },

    "googlevideo_fake_multisplit_autottl": {
        "name": "GoogleVideo Fake+MultiSplit (AutoTTL)",
        "description": "Fake + MultiSplit с AutoTTL вместо badseq",
        "author": None,
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:ip_autottl=0,3-20:ip6_autottl=0,3-20 --lua-desync=multisplit:pos=1,sld+1:seqovl=1:ip_autottl=0,3-20:ip6_autottl=0,3-20"""
    },


    "fake_autottl_repeats_6_badseq": {
        "name": "alt mgts (v1) 1.6.1 / 1.8.4",
        "description": "Fake Google TLS × 6 повторов, AutoTTL+2, badseq (МГТС)",
        "author": "hz",
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:ip_autottl=2,3-20:ip6_autottl=2,3-20:repeats=6:tcp_ack=-66000"""
    },

    "altmgts2_lite": {
        "name": "alt mgts (v2) Lite",
        "description": "Fake × 4 повтора, TCP MD5",
        "author": "hz",
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:repeats=4:tcp_md5"""
    },

    "altmgts2_custom_md5": {
        "name": "alt mgts (v2) Custom MD5",
        "description": "Fake × 6, TCP MD5 с кастомными данными",
        "author": "hz",
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:repeats=6:tcp_md5=0xDEADBEEFDEADBEEFDEADBEEFDEADBEEF"""
    },

    "altmgts2_161_3": {
        "name": "alt mgts (v3) 1.6.1",
        "description": "Fake Google TLS × 6, AutoTTL+2, TCP MD5 (МГТС v3 - золотая середина)",
        "author": "hz",
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:ip_autottl=2,3-20:ip6_autottl=2,3-20:repeats=6:tcp_md5"""
    },

    "altmgts_v3_aggressive": {
        "name": "alt mgts (v3) Aggressive",
        "description": "v3 с 10 повторами",
        "author": "hz",
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:ip_autottl=2,3-20:ip6_autottl=2,3-20:repeats=10:tcp_md5"""
    },

    "altmgts_v3_autottl1": {
        "name": "alt mgts (v3) AutoTTL+1",
        "description": "v3 с AutoTTL+1 (меньший delta)",
        "author": "hz",
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:ip_autottl=1,3-20:ip6_autottl=1,3-20:repeats=6:tcp_md5"""
    },

    "altmgts_v3_lite": {
        "name": "alt mgts (v3) Lite",
        "description": "v3 с 4 повторами (экономия)",
        "author": "hz",
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:ip_autottl=2,3-20:ip6_autottl=2,3-20:repeats=4:tcp_md5"""
    },

    "original_bolvan_v2_badsum_lite": {
        "name": "Если стратегия не работает смени её!",
        "description": "Fake (Google TLS, rnd,dupsid) × 6 + MultiDisorder (1,midsld) с badseq (универсальная)",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multidisorder:pos=1,midsld:tcp_ack=-66000"""
    },

    "original_bolvan_v2_badsum": {
        "name": "Если стратегия не работает смени её!",
        "description": "Fake (Google TLS, rnd,dupsid) × 6 + MultiDisorder (1,midsld) с badseq (универсальная)",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:tcp_ack=-66000:repeats=6:tls_mod=rnd,dupsid,sni=www.google.com --lua-desync=multidisorder:pos=1,midsld:tcp_ack=-66000"""
    },

    "original_bolvan_v2_badsum_lite": {
        "name": "Universal Strategy (Lite)",
        "description": "Fake × 4 + MultiDisorder (экономия)",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:tcp_ack=-66000:repeats=4:tls_mod=rnd,dupsid,sni=www.google.com --lua-desync=multidisorder:pos=1,midsld:tcp_бack=-66000"""
    },

    "original_bolvan_v2_autottl": {
        "name": "Universal Strategy (AutoTTL)",
        "description": "Fake × 6 + MultiDisorder с AutoTTL вместо badseq",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:ip_autottl=0,3-20:ip6_autottl=0,3-20:repeats=6:tls_mod=rnd,dupsid,sni=www.google.com --lua-desync=multidisorder:pos=1,midsld:ip_autottl=0,3-20:ip6_autottl=0,3-20"""
    },

    "original_bolvan_v2_badsum_simple": {
        "name": "Universal Strategy (Simple)",
        "description": "Fake × 6 + MultiDisorder (только midsld)",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:tcp_ack=-66000:repeats=6:tls_mod=rnd,dupsid,sni=www.google.com --lua-desync=multidisorder:pos=midsld:tcp_ack=-66000"""
    },

    "original_bolvan_v2_max_md5": {
        "name": "Universal Strategy (Max)",
        "description": "Fake × 6 + MultiDisorder + TCP MD5",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:tcp_ack=-66000:tcp_md5:repeats=6:tls_mod=rnd,dupsid,sni=www.google.com --lua-desync=multidisorder:pos=1,midsld:tcp_ack=-66000:tcp_md5"""
    },

    "other_multidisorder": {
        "name": "multidisorder 6 md5sig",
        "description": "Fake (дефолтный TLS) × 6 + MultiDisorder (1,midsld) с TCP MD5 (стабильная)",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:repeats=6:tcp_md5 --lua-desync=multidisorder:pos=1,midsld:tcp_md5"""
    },

    "other_multidisorder_google": {
        "name": "MultiDisorder 6 MD5 (Google)",
        "description": "С Google TLS фейком",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:repeats=6:tcp_md5 --lua-desync=multidisorder:pos=1,midsld:tcp_md5"""
    },

    "other_multidisorder_dynamic": {
        "name": "MultiDisorder 6 MD5 (Dynamic)",
        "description": "С динамическими TLS модификациями",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:repeats=6:tcp_md5:tls_mod=rnd,dupsid --lua-desync=multidisorder:pos=1,midsld:tcp_md5"""
    },

    "other_multidisorder_lite": {
            "name": "MultiDisorder 4 MD5 (Lite)",
            "description": "× 4 повтора (экономия)",
            "author": "hz",
            "label": LABEL_STABLE,
            "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:repeats=4:tcp_md5 --lua-desync=multidisorder:pos=1,midsld:tcp_md5"""
        },

    "other_multidisorder_autottl": {
        "name": "MultiDisorder 6 MD5+AutoTTL",
        "description": "С AutoTTL для адаптации",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:repeats=6:tcp_md5:ip_autottl=0,3-20:ip6_autottl=0,3-20 --lua-desync=multidisorder:pos=1,midsld:tcp_md5:ip_autottl=0,3-20:ip6_autottl=0,3-20"""
    },

    "other_multidisorder_2": {
        "name": "original bol-van v2",
        "description": "Fake (дефолтный TLS) × 6 + MultiDisorder (1,midsld) с BadSeq + TCP MD5 (оригинальная стратегия)",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:repeats=6:tcp_ack=-66000:tcp_md5 --lua-desync=multidisorder:pos=1,midsld:tcp_ack=-66000:tcp_md5"""
    },

    "other_multidisorder_2_google": {
        "name": "original bol-van v2 (Google)",
        "description": "С Google TLS фейком",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:repeats=6:tcp_ack=-66000:tcp_md5 --lua-desync=multidisorder:pos=1,midsld:tcp_ack=-66000:tcp_md5"""
    },

    "other_multidisorder_2_v3": {
        "name": "original bol-van v3",
        "description": "v2 + TLS модификации (максимальная)",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:repeats=6:tcp_ack=-66000:tcp_md5:tls_mod=rnd,dupsid,sni=www.google.com --lua-desync=multidisorder:pos=1,midsld:tcp_ack=-66000:tcp_md5"""
    },

    "other_multidisorder_2_autottl": {
        "name": "original bol-van v2 (AutoTTL)",
        "description": "v2 + AutoTTL для адаптации",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multidisorder:pos=1,midsld:tcp_ack=-66000:ip_ttl=2,3-20:ip6_ttl=2,3-20"""
    },

    "other_multidisorder_2_autottl_2": {
        "name": "original bol-van v2 v2 (AutoTTL)",
        "description": "v2 + AutoTTL для адаптации",
        "author": "hz",
        "label": LABEL_STABLE,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=multidisorder:pos=1,midsld:tcp_ack=-66000:tcp_md5:ip_autottl=0,3-20:ip_autottl=0,3-20"""
    },

    "other2": {
        "name": "original bol-van v2 (badsum)",
        "description": "Fake (дефолтный TLS) × 6 + MultiDisorder (1,midsld) только с BadSeq (базовая версия)",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:repeats=6:tcp_ack=-66000 --lua-desync=multidisorder:pos=1,midsld:tcp_ack=-66000"""
    },

    "other2_google": {
        "name": "bol-van v2 badsum (Google)",
        "description": "Базовая + Google TLS",
        "author": "hz",
        "label": None,
        "args": f"""--blob=tls_google:@{BIN_FOLDER}\\tls_clienthello_www_google_com.bin {BASE_ARG} --payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=tls_google:repeats=6:tcp_ack=-66000 --lua-desync=multidisorder:pos=1,midsld:tcp_ack=-66000"""
    },

    "fake_fakedsplit_autottl_2": {
        "name": "fake fakedsplit badseq",
        "description": "Fake HTTP + FakedSplit с AutoTTL+2, badseq (рекомендуется для HTTP порт 80)",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG}--payload=tls_client_hello --out-range=-d10 --lua-desync=fake:blob=fake_default_tls:ip_autottl=2,3-20:ip6_autottl=2,3-20:tcp_ack=-66000 --lua-desync=fakedsplit:pos=1:ip_autottl=2,3-20:ip6_autottl=2,3-20:tcp_ack=-66000"""
    },

    "fake_fakedsplit_autottl_2": {
        "name": "fake fakedsplit badseq",
        "description": "Рекомендуется для 80 порта (HTTP)",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=badseq"""
    },

    "multisplit_seqovl_2_midsld": {
        "name": "fake multisplit seqovl 2 midsld",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-http=0x0F0F0F0F --dpi-desync-fooling=md5sig"""
    },
    "multisplit_fake_tls_badseq": {
        "name": "YTDisBystro 3.4 v1",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=badseq --dpi-desync-autottl --dup=2 --dup-fooling=badseq --dup-autottl --dup-cutoff=n3"""
    },
    "multisplit_fake_tls_md5sig": {
        "name": "YTDisBystro 3.4 v3",
        "description": "Хорошая базовая комлектация для старта",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=sld+1 --dpi-desync-fake-tls=0x0F0F0E0F --dpi-desync-fake-tls=tls_clienthello_14.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },
    "multisplit_17": {
        "name": "YTDisBystro 3.4",
        "description": "Мульти нарезка с md5sig и фейком TLS",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-pos=2,midsld --dpi-desync-fake-tls=tls_clienthello_17.bin --dpi-desync-fake-tls-mod=rnd,dupsid --dpi-desync-fooling=md5sig --dpi-desync-autottl --dup=2 --dup-fooling=md5sig --dup-autottl --dup-cutoff=n3"""
    },
    "other4": {
        "name": "fakedsplit badseq 10",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl"""
    },
    "other5": {
        "name": "multidisorder datanoack deepseek",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=tls_clienthello_chat_deepseek_com.bin"""
    },
    "general_altv2_161": {
        "name": "general (alt v2) 1.6.1",
        "description": "Устаревший split2 с seqovl 652 и паттерном 4",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{BASE_ARG} --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_altv2_161": {
        "name": "general (alt v2) 1.6.1",
        "description": "split2 с seqovl 652 и паттерном 4 для варпа (МОЖЕТ СЛОМАТЬ САЙТЫ!)",
        "author": "hz",
        "label": LABEL_WARP,
        "args": f"""--filter-tcp=80,443 --dpi-desync=split2 --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "other6": {
        "name": "general (alt1) 1.8.1",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,split --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt183": {
        "name": "general (alt) 1.8.3",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-autottl=5 --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt2183": {
        "name": "general (alt2) 1.8.3 / 1.8.4",
        "description": "Потом опишу подробнее",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=652 --dpi-desync-split-pos=2 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt3183_2": {
        "name": "general (alt v3) 1.8.2 / 1.8.4",
        "description": "fakedsplit pos 1 autottl badseq repeats 8",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-repeats=8"""
    },
    "general_alt4_182": {
        "name": "general (alt v4) 1.8.2 / 1.8.4",
        "description": "fake multisplit repeats 6 md5sig tls google",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-repeats=6 --dpi-desync-fooling=md5sig --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin"""
    },
    "general_alt6_184": {
        "name": "general (alt v6) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt7_184": {
        "name": "general (alt v7) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-pos=2,sniext+1 --dpi-desync-split-seqovl=679 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin"""
    },
    "general_alt8_185": {
        "name": "general (alt v8) 1.8.5",
        "description": "fake autottl repeats 6 badseq increment 2",
        "author": "V3nilla",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=2"""
    },
    "general_alt8_185_2": {
        "name": "general (alt v8) 1.8.5 (2)",
        "description": "fake autottl repeats 6 badseq increment 0",
        "author": "V3nilla",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=0"""
    },
    "general_alt8_185_3": {
        "name": "general (alt v8) 1.8.5 (3)",
        "description": "fake autottl repeats 6 badseq increment 100000",
        "author": "V3nilla",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake --dpi-desync-fake-tls-mod=none --dpi-desync-repeats=6 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=100000"""
    },
    "general_fake_tls_auto_alt_184": {
        "name": "general (fake TLS auto alt) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-split-pos=1 --dpi-desync-autottl --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-repeats=8 --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_alt2_184": {
        "name": "general (fake TLS auto alt2) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-badseq-increment=10000000 --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_alt3_184": {
        "name": "general (fake TLS auto alt3) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=681 --dpi-desync-split-pos=1 --dpi-desync-fooling=ts --dpi-desync-repeats=8 --dpi-desync-split-seqovl-pattern=tls_clienthello_www_google_com.bin --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com"""
    },
    "general_fake_tls_auto_184": {
        "name": "general (fake TLS auto) 1.8.4",
        "description": "multisplit seqovl 681 pos 1 seqovl pattern",
        "author": "Flowseal",
        "label": None,
        "args": f"""{BASE_ARG} --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=badseq --dpi-desync-fake-tls-mod=rnd,dupsid,sni=sun6-21.userapi.com"""
    },
    "rutracker_tcp_none": {
        "name": "Не применять для остальных",
        "description": "Отключить обработку остальных сайтов",
        "author": "System",
        "label": None,
        "args": ""
    }
}