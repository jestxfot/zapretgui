
from ..constants import LABEL_RECOMMENDED, LABEL_STABLE, LABEL_GAME, LABEL_CAUTION

GOOGLEVIDEO_BASE_ARG = "--filter-tcp=443 --hostlist-domains=googlevideo.com"

"""
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=multidisorder --dpi-desync-split-pos=1,sniext+1,host+1,midsld-2,midsld,midsld+2,endhost-1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake --dpi-desync-ttl=8 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake --dpi-desync-fooling=badsum --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake --dpi-desync-fooling=datanoack --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakedsplit --dpi-desync-ttl=7 --dpi-desync-split-pos=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakedsplit --dpi-desync-fooling=datanoack --dpi-desync-split-pos=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakedsplit --dpi-desync-fooling=md5sig --dpi-desync-split-pos=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=7 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=7 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=7 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=7 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=7 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=badsum --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=badsum --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=badseq --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=datanoack --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=md5sig --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=md5sig --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=md5sig --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-ttl=7 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-ttl=7 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=badsum --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=badsum --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=badsum --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=badseq --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=md5sig --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=md5sig --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=md5sig --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-ttl=9 --dpi-desync-split-pos=midsld
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-fooling=badsum --dpi-desync-split-pos=midsld
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-fooling=badseq --dpi-desync-split-pos=midsld
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=2 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=2 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=badsum --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=badsum --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=md5sig --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=7 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=7 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=7 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=badsum --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=md5sig --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=md5sig --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=multisplit --dpi-desync-split-pos=10 --dpi-desync-split-seqovl=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=multisplit --dpi-desync-split-pos=10,sniext+1 --dpi-desync-split-seqovl=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=multisplit --dpi-desync-split-pos=10,sniext+4 --dpi-desync-split-seqovl=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=multisplit --dpi-desync-split-pos=10,midsld --dpi-desync-split-seqovl=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakedsplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=midsld
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=3 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=3 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=4 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=4 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=syndata,multisplit --dpi-desync-split-pos=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=syndata,multisplit --dpi-desync-split-pos=1,midsld
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake --dpi-desync-ttl=8 --wssize 1:6 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake --dpi-desync-fooling=badsum --wssize 1:6 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake --dpi-desync-fooling=datanoack --wssize 1:6 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakedsplit --dpi-desync-ttl=9 --wssize 1:6 --dpi-desync-split-pos=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakedsplit --dpi-desync-fooling=badsum --wssize 1:6 --dpi-desync-split-pos=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakedsplit --dpi-desync-fooling=datanoack --wssize 1:6 --dpi-desync-split-pos=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=7 --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=7 --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=7 --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=7 --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=badsum --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=badsum --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=badsum --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=datanoack --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap

ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=datanoack --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=md5sig --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=md5sig --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=md5sig --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-ttl=7 --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-ttl=7 --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=badsum --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=badsum --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=badsum --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=datanoack --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=datanoack --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=md5sig --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-ttl=9 --wssize 1:6 --dpi-desync-split-pos=midsld
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --wssize 1:6 --dpi-desync-split-pos=1,midsld
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=badsum --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=badsum --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=badsum --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=md5sig --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=7 --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=7 --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=7 --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=md5sig --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=md5sig --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=md5sig --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=multisplit --dpi-desync-split-pos=10,sniext+1 --dpi-desync-split-seqovl=1 --wssize 1:6
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakedsplit --dpi-desync-ttl=1 --dpi-desync-autottl=1 --wssize 1:6 --dpi-desync-split-pos=1
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=1 --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=1 --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --wssize 1:6 --dpi-desync-split-pos=midsld
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=2 --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=2 --wssize 1:6 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=2 --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=3 --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=4 --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=5 --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=5 --wssize 1:6 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=2 --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
ipv4 rr8---sn-jvhnu5g-c35z.googlevideo.com curl_test_https_tls12 : winws --wf-l3=ipv4 --wf-tcp=443 --dpi-desync=syndata,multisplit --wssize 1:6 --dpi-desync-split-pos=1,midsld
--wf-tcp=443 --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld
--wf-tcp=443 --dpi-desync=multidisorder --dpi-desync-split-pos=1,sniext+1,host+1,midsld-2,midsld,midsld+2,endhost-1
--wf-tcp=443 --dpi-desync=fake --dpi-desync-ttl=7 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake --dpi-desync-fooling=badsum --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake --dpi-desync-fooling=datanoack --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fakedsplit --dpi-desync-ttl=8 --dpi-desync-split-pos=1
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=7 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=7 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=badsum --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=badsum --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=badsum --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=md5sig --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-fooling=md5sig --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-ttl=7 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-ttl=7 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-ttl=7 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=badsum --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=datanoack --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-fooling=md5sig --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-ttl=8 --dpi-desync-split-pos=midsld
--wf-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld
--wf-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-fooling=md5sig --dpi-desync-split-pos=midsld
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=badsum --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=badseq --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=badseq --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-fooling=md5sig --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=7 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=badsum --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=badsum --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=md5sig --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=md5sig --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=multisplit --dpi-desync-split-pos=10,sniext+1 --dpi-desync-split-seqovl=1
--wf-tcp=443 --dpi-desync=multisplit --dpi-desync-split-pos=10,sniext+4 --dpi-desync-split-seqovl=1
--wf-tcp=443 --dpi-desync=fake --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fakedsplit --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=1
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,fakedsplit --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=midsld
--wf-tcp=443 --dpi-desync=fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=midsld
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=3 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=4 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=4 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,multidisorder --dpi-desync-ttl=1 --dpi-desync-autottl=5 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000
--wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=1 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
--wf-tcp=443 --dpi-desync=fake,fakeddisorder --dpi-desync-ttl=1 --dpi-desync-autottl=2 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap
"""

GOOGLEVIDEO_STRATEGIES = {
    "googlevideo_fakeddisorder_datanoack_1": {
        "name": "GoogleVideo FakedDisorder datanoack",
        "description": "Базовая стратегия FakedDisorder для GoogleVideo с datanoack ()",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=fake,fakeddisorder --dpi-desync-fooling=datanoack --dpi-desync-split-pos=midsld --dpi-desync-fake-tls=0x00000000"""
    },
    "multidisorder_midsld": {
        "name": "multidisorder midsld",
        "description": "Базовая стратегия multidisorder и midsld",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=multidisorder --dpi-desync-split-pos=1,midsld"""
    },
    "multidisorder_midsld_syndata": {
        "name": "syndata multidisorder midsld",
        "description": "syndata и multidisorder и midsld (работает на все сайты!)",
        "author": None,
        "label": LABEL_CAUTION,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=syndata,multidisorder --dpi-desync-split-pos=1,midsld"""
    },
    "googlevideo_fakedsplit": {
        "name": "GoogleVideo FakedSplit badseq",
        "description": "Базовая стратегия FakedSplit для GoogleVideo с badseq",
        "author": None,
        "label": LABEL_RECOMMENDED,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=4"""
    },
    "googlevideo_split": {
        "name": "GoogleVideo Split cutoff",
        "description": "Стратегия Split для GoogleVideo с cutoff",
        "author": None,
        "label": None,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-cutoff=d2 --dpi-desync-ttl=4"""
    },
    "googlevideo_multidisorder": {
        "name": "GoogleVideo MultiDisorder Complex",
        "description": "Сложная стратегия MultiDisorder с множественными позициями разреза",
        "author": None,
        "label": LABEL_STABLE,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1,host+2,sld+2,sld+5,sniext+1,sniext+2,endhost-2"""
    },
    "googlevideo_multisplit_pattern": {
        "name": "GoogleVideo MultiSplit Pattern 7",
        "description": "MultiSplit с паттерном ClientHello 7",
        "author": None,
        "label": None,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=2,midsld-2 --dpi-desync-split-seqovl-pattern=tls_clienthello_7.bin"""
    },
    "googlevideo_fakeddisorder": {
        "name": "GoogleVideo FakedDisorder AutoTTL",
        "description": "FakedDisorder с паттерном и AutoTTL",
        "author": None,
        "label": None,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=fakeddisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=2,midsld-2 --dpi-desync-fakedsplit-pattern=tls_clienthello_7.bin --dpi-desync-fooling=badseq --dpi-desync-autottl"""
    },
    "googlevideo_fakedsplit_simple": {
        "name": "GoogleVideo FakedSplit Simple",
        "description": "Простая стратегия FakedSplit с позицией 1",
        "author": None,
        "label": None,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=8 --dpi-desync-autottl"""
    },
    "googlevideo_split_aggressive": {
        "name": "GoogleVideo Split Aggressive",
        "description": "Агрессивная стратегия Split с множеством повторов",
        "author": None,
        "label": LABEL_CAUTION,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=15 --dpi-desync-cutoff=d3 --dpi-desync-ttl=3"""
    },
    "googlevideo_multidisorder_midsld": {
        "name": "GoogleVideo MultiDisorder MidSLD",
        "description": "MultiDisorder с разрезом по середине SLD",
        "author": None,
        "label": None,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld,midsld+2 --dpi-desync-fooling=badseq --dpi-desync-repeats=10"""
    },
    "googlevideo_fake_multisplit": {
        "name": "GoogleVideo Fake+MultiSplit",
        "description": "Комбинация Fake и MultiSplit",
        "author": None,
        "label": None,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1,sld+1 --dpi-desync-fake-tls=tls_clienthello_www_google_com.bin --dpi-desync-fooling=badseq"""
    },
    "fake_fakedsplit_md5sig_80_port": {
        "name": "Fake FakedSplit MD5Sig increment 10M",
        "description": "Особая стратегия Fake+FakedSplit с двойным MD5Sig и большим инкрементом для обхода детектов",
        "author": None,
        "label": None,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=fake,fakedsplit --dpi-desync-fooling=md5sig --dup=1 --dup-cutoff=n2 --dup-fooling=md5sig --dpi-desync-split-pos=midsld --dpi-desync-badseq-increment=10000000"""
    },
    "fake_multisplit_datanoack_wssize_midsld": {
        "name": "GoogleVideo Fake+MultiSplit datanoack wssize midsld",
        "description": "Экспериментальная стратегия Fake+MultiSplit с datanoack, wssize и разрезом по середине SLD",
        "author": None,
        "label": LABEL_CAUTION,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} ---dpi-desync=fake,multisplit --dpi-desync-fooling=datanoack --wssize 1:6 --dpi-desync-split-pos=midsld --dpi-desync-fake-tls-mod=rnd,dupsid,rndsni,padencap"""
    },
    "multisplit_split_pos_1": {
        "name": "multisplit split pos 1",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=multisplit --dpi-desync-split-pos=1"""
    },
    "datanoack": {
        "name": "datanoack",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync-fooling=datanoack"""
    },
    "multisplit_datanoack": {
        "name": "multisplit datanoack",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=multisplit --dpi-desync-fooling=datanoack"""
    },
    "multisplit_datanoack_split_pos_1": {
        "name": "multisplit datanoack split pos 1",
        "description": "Потом опишу подробнее",
        "author": "hz",
        "label": LABEL_RECOMMENDED,
        "args": f"""{GOOGLEVIDEO_BASE_ARG} --dpi-desync=multisplit --dpi-desync-fooling=datanoack --dpi-desync-split-pos=1"""
    },
    "googlevideo_tcp_none": {
        "name": "Не применять для GoogleVideo",
        "description": "Отключить обработку GoogleVideo",
        "author": "System",
        "label": None,
        "args": ""
    }
}